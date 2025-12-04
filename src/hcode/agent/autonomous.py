"""
Autonomous execution engine for Claude Code-like behavior.

Provides intelligent decision-making about when to execute actions
automatically vs when to ask for confirmation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Tuple

from .modes import AgentMode, SafetyConfig, get_mode_config


class ExecutionDecision(Enum):
    """Decision about whether to execute an action"""

    EXECUTE = "execute"  # Execute immediately
    CONFIRM = "confirm"  # Ask for confirmation
    SKIP = "skip"  # Skip this action
    ABORT = "abort"  # Abort entire task


@dataclass
class ExecutionContext:
    """Context for autonomous execution"""

    mode: AgentMode
    safety_config: SafetyConfig
    actions_without_confirm: int = 0
    dangerous_actions_count: int = 0
    errors_count: int = 0
    total_actions: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    plan_approved: bool = False

    # Callbacks for user interaction
    confirmation_callback: Optional[Callable[[str], bool]] = None
    progress_callback: Optional[Callable[[str, float], None]] = None


@dataclass
class ActionProposal:
    """
    A proposed action that the agent wants to take.

    The autonomous engine decides whether to execute, confirm, or skip.
    """

    tool_name: str
    arguments: Dict[str, Any]
    reason: str  # Why this action
    risk_level: str = "safe"  # "safe", "caution", "dangerous"
    estimated_duration: float = 1.0  # seconds
    reversible: bool = True
    affects_files: List[str] = field(default_factory=list)
    affects_commands: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Auto-assess risk if not provided"""
        if self.risk_level == "safe" and not hasattr(self, "_risk_assessed"):
            self._assess_risk()
            self._risk_assessed = True

    def _assess_risk(self):
        """Automatically assess risk level"""
        safety = SafetyConfig()

        # Check for dangerous patterns
        if self.tool_name == "Bash":
            command = self.arguments.get("command", "")
            risk = safety.assess_command_risk(command)
            self.risk_level = risk.value
            if command:
                self.affects_commands.append(command)

        elif self.tool_name in ["Edit", "Write"]:
            path = self.arguments.get("path", "") or self.arguments.get("file_path", "")
            risk = safety.assess_file_risk(path, "edit")
            self.risk_level = risk.value
            if path:
                self.affects_files.append(path)
            # Write to new files is generally safe
            if self.tool_name == "Write" and not path:
                self.risk_level = "safe"

        elif self.tool_name == "Delete":
            path = self.arguments.get("path", "")
            risk = safety.assess_file_risk(path, "delete")
            self.risk_level = risk.value
            self.reversible = False
            if path:
                self.affects_files.append(path)

        elif self.tool_name == "Read" or self.tool_name == "Glob" or self.tool_name == "Grep":
            # Read operations are always safe
            self.risk_level = "safe"

        elif self.tool_name == "TodoWrite":
            # Todo operations are safe
            self.risk_level = "safe"


@dataclass
class ExecutionResult:
    """Result of an action execution"""

    success: bool
    output: str
    error: str = ""
    duration: float = 0.0
    retries: int = 0


class AutonomousEngine:
    """
    Autonomous execution engine.

    Makes decisions about whether to execute actions automatically
    or ask for confirmation, matching Claude Code's behavior.
    """

    def __init__(
        self, mode: AgentMode = AgentMode.INTERACTIVE, safety_config: Optional[SafetyConfig] = None
    ):
        self.mode = mode
        self.mode_config = get_mode_config(mode)
        self.safety_config = safety_config or SafetyConfig()

        # Execution tracking
        self.context = ExecutionContext(mode=mode, safety_config=self.safety_config)

        # Callbacks for interaction
        self._confirmation_callback: Optional[Callable[[str], bool]] = None
        self._progress_callback: Optional[Callable[[str, float], None]] = None
        self._display_callback: Optional[Callable[[str], None]] = None

        # Error recovery
        self.max_retries = 3
        self.retry_delays = [1, 2, 5]  # seconds

        # Execution plan
        self.current_plan: List[ActionProposal] = []

    # ============================================================
    # MODE MANAGEMENT
    # ============================================================

    def set_mode(self, mode: AgentMode):
        """Change agent mode"""
        self.mode = mode
        self.mode_config = get_mode_config(mode)
        self.context.mode = mode
        self.context.actions_without_confirm = 0
        self.context.plan_approved = False

    def get_mode(self) -> AgentMode:
        """Get current mode"""
        return self.mode

    def is_auto_mode(self) -> bool:
        """Check if in any auto mode"""
        return self.mode in [AgentMode.AUTO, AgentMode.PLAN]

    def is_plan_mode(self) -> bool:
        """Check if in plan mode"""
        return self.mode in [AgentMode.PLAN, AgentMode.REVIEW]

    def set_confirmation_callback(self, callback: Callable[[str], bool]):
        """Set callback for user confirmations"""
        self._confirmation_callback = callback
        self.context.confirmation_callback = callback

    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """Set callback for progress updates"""
        self._progress_callback = callback
        self.context.progress_callback = callback

    def set_display_callback(self, callback: Callable[[str], None]):
        """Set callback for displaying messages"""
        self._display_callback = callback

    # ============================================================
    # DECISION MAKING
    # ============================================================

    def decide_execution(self, proposal: ActionProposal) -> ExecutionDecision:
        """
        Decide whether to execute an action.

        This is the core decision logic matching Claude Code:
        - In AUTO mode: Execute unless dangerous
        - In INTERACTIVE mode: Always confirm
        - In PLAN/REVIEW mode: Execute after plan approval

        Args:
            proposal: The proposed action

        Returns:
            ExecutionDecision
        """
        # Check if we've exceeded action limit
        if self.context.actions_without_confirm >= self.mode_config.max_actions_without_confirm:
            return ExecutionDecision.CONFIRM

        # Risk-based decision
        if proposal.risk_level == "dangerous":
            # Always confirm dangerous actions
            if self.mode_config.confirm_dangerous:
                return ExecutionDecision.CONFIRM
            elif self.mode == AgentMode.INTERACTIVE:
                return ExecutionDecision.CONFIRM

        elif proposal.risk_level == "caution":
            # Caution actions: depends on mode
            if self.mode == AgentMode.INTERACTIVE:
                return ExecutionDecision.CONFIRM
            elif self.mode == AgentMode.AUTO:
                # In auto mode, execute caution items but track them
                self.context.dangerous_actions_count += 1
                return ExecutionDecision.EXECUTE

        # Mode-specific logic
        if self.mode == AgentMode.INTERACTIVE:
            # Interactive: ask for everything
            if self.mode_config.ask_permission:
                return ExecutionDecision.CONFIRM

        elif self.mode == AgentMode.AUTO:
            # Auto: execute freely (dangerous already checked above)
            return ExecutionDecision.EXECUTE

        elif self.mode in [AgentMode.PLAN, AgentMode.REVIEW]:
            # Plan modes: execute after plan approval
            if self.context.plan_approved or not self.mode_config.require_approval:
                return ExecutionDecision.EXECUTE
            else:
                return ExecutionDecision.CONFIRM

        # Default: execute
        return ExecutionDecision.EXECUTE

    def should_show_plan(self) -> bool:
        """Check if plan should be shown before execution"""
        return self.mode_config.show_plan

    def needs_plan_approval(self) -> bool:
        """Check if plan needs explicit approval"""
        return self.mode_config.require_approval and not self.context.plan_approved

    def approve_plan(self):
        """Mark the current plan as approved"""
        self.context.plan_approved = True

    # ============================================================
    # CONFIRMATION
    # ============================================================

    async def confirm_action(self, proposal: ActionProposal) -> bool:
        """Ask user for confirmation"""
        if not self._confirmation_callback:
            # No callback, default to yes in auto modes
            return self.is_auto_mode()

        # Build confirmation message
        message = self._build_confirmation_message(proposal)

        # Ask user
        return self._confirmation_callback(message)

    def _build_confirmation_message(self, proposal: ActionProposal) -> str:
        """Build confirmation message"""
        lines = []

        # Risk indicator
        risk_icons = {"safe": "[OK]", "caution": "[!]", "dangerous": "[!!]"}
        icon = risk_icons.get(proposal.risk_level, "[?]")

        lines.append(f"{icon} {proposal.tool_name}")
        lines.append(f"Reason: {proposal.reason}")

        # Show what will be affected
        if proposal.affects_files:
            files_preview = proposal.affects_files[:3]
            lines.append(f"Affects: {', '.join(files_preview)}")
            if len(proposal.affects_files) > 3:
                lines.append(f"... and {len(proposal.affects_files) - 3} more")

        if proposal.affects_commands:
            cmd_preview = proposal.affects_commands[0][:50]
            if len(proposal.affects_commands[0]) > 50:
                cmd_preview += "..."
            lines.append(f"Command: {cmd_preview}")

        # Reversibility
        if not proposal.reversible:
            lines.append("[!!] This action cannot be undone!")

        lines.append("\nProceed? (y/n)")

        return "\n".join(lines)

    # ============================================================
    # SAFETY CHECKS
    # ============================================================

    def check_safety(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if operation is safe.

        Returns:
            (is_safe, reason)
        """
        # Check bash commands
        if tool_name == "Bash":
            command = arguments.get("command", "")

            if self.safety_config.is_dangerous_command(command):
                return False, f"Dangerous command detected: {command[:50]}"

        # Check file operations
        elif tool_name in ["Edit", "Write", "Delete"]:
            path = arguments.get("path", "") or arguments.get("file_path", "")

            if self.safety_config.is_protected_file(path):
                return False, f"Protected file: {path}"

            # Check file size for auto-edit
            import os

            if os.path.exists(path):
                try:
                    size = os.path.getsize(path)
                    if size > self.safety_config.max_file_size_auto:
                        return False, f"File too large for auto-edit: {size} bytes"
                except OSError:
                    pass

        # Check directory operations
        elif tool_name == "Bash":
            command = arguments.get("command", "")
            if "rm -rf" in command or "rmdir /s" in command:
                # Extra careful with recursive delete
                for protected in self.safety_config.protected_directories:
                    if protected.lower() in command.lower():
                        return False, f"Cannot delete protected directory: {protected}"

        return True, "Safe"

    # ============================================================
    # PLANNING
    # ============================================================

    def add_to_plan(self, proposal: ActionProposal):
        """Add action to current plan"""
        self.current_plan.append(proposal)

    def clear_plan(self):
        """Clear current plan"""
        self.current_plan = []
        self.context.plan_approved = False

    def get_plan(self) -> List[ActionProposal]:
        """Get current plan"""
        return self.current_plan

    def format_plan_display(self) -> str:
        """Format plan for display"""
        if not self.current_plan:
            return "No plan created yet."

        lines = []
        lines.append("Execution Plan:")
        lines.append("=" * 40)

        for i, action in enumerate(self.current_plan, 1):
            risk_icon = {"safe": "[OK]", "caution": "[!]", "dangerous": "[!!]"}.get(
                action.risk_level, "[?]"
            )

            lines.append(f"\n{i}. {risk_icon} {action.tool_name}")
            lines.append(f"   {action.reason}")

            if action.affects_files:
                files = ", ".join(action.affects_files[:2])
                if len(action.affects_files) > 2:
                    files += f" +{len(action.affects_files) - 2} more"
                lines.append(f"   Files: {files}")

            if action.affects_commands:
                cmd = action.affects_commands[0][:40]
                if len(action.affects_commands[0]) > 40:
                    cmd += "..."
                lines.append(f"   Cmd: {cmd}")

        lines.append("\n" + "=" * 40)

        # Summary
        safe_count = sum(1 for a in self.current_plan if a.risk_level == "safe")
        caution_count = sum(1 for a in self.current_plan if a.risk_level == "caution")
        dangerous_count = sum(1 for a in self.current_plan if a.risk_level == "dangerous")

        lines.append(f"Total: {len(self.current_plan)} actions")
        if dangerous_count > 0:
            lines.append(f"[!!] {dangerous_count} dangerous action(s)")
        if caution_count > 0:
            lines.append(f"[!] {caution_count} caution action(s)")

        return "\n".join(lines)

    async def confirm_plan(self) -> bool:
        """Get user approval for plan"""
        if not self._confirmation_callback:
            return True

        # Display plan
        plan_display = self.format_plan_display()
        if self._display_callback:
            self._display_callback(plan_display)

        message = f"\nApprove this plan? ({len(self.current_plan)} actions) (y/n)"
        approved = self._confirmation_callback(message)

        if approved:
            self.context.plan_approved = True

        return approved

    # ============================================================
    # CONTEXT MANAGEMENT
    # ============================================================

    def reset_context(self):
        """Reset execution context"""
        self.context = ExecutionContext(
            mode=self.mode,
            safety_config=self.safety_config,
            confirmation_callback=self._confirmation_callback,
            progress_callback=self._progress_callback,
        )
        self.current_plan = []

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        elapsed = (datetime.now() - self.context.start_time).total_seconds()

        return {
            "mode": self.mode.value,
            "total_actions": self.context.total_actions,
            "dangerous_actions": self.context.dangerous_actions_count,
            "errors": self.context.errors_count,
            "elapsed_seconds": elapsed,
            "actions_per_minute": (self.context.total_actions / elapsed * 60) if elapsed > 0 else 0,
            "plan_approved": self.context.plan_approved,
            "plan_size": len(self.current_plan),
        }

    def track_action(self, proposal: ActionProposal, success: bool):
        """Track an executed action"""
        self.context.total_actions += 1
        self.context.actions_without_confirm += 1

        if proposal.risk_level == "dangerous":
            self.context.dangerous_actions_count += 1

        if not success:
            self.context.errors_count += 1

    def update_progress(self, message: str, progress: float):
        """Update progress if callback is set"""
        if self._progress_callback:
            self._progress_callback(message, progress)


# ============================================================
# ACTION BUILDERS
# ============================================================


def create_read_action(path: str, reason: str = "Read file contents") -> ActionProposal:
    """Create a read file action"""
    return ActionProposal(
        tool_name="Read",
        arguments={"file_path": path},
        reason=reason,
        risk_level="safe",
        affects_files=[path],
    )


def create_edit_action(
    path: str, old_str: str, new_str: str, reason: str = "Edit file"
) -> ActionProposal:
    """Create an edit file action"""
    return ActionProposal(
        tool_name="Edit",
        arguments={"file_path": path, "old_string": old_str, "new_string": new_str},
        reason=reason,
        affects_files=[path],
    )


def create_write_action(path: str, content: str, reason: str = "Write file") -> ActionProposal:
    """Create a write file action"""
    return ActionProposal(
        tool_name="Write",
        arguments={"file_path": path, "content": content},
        reason=reason,
        affects_files=[path],
    )


def create_bash_action(command: str, reason: str = "Execute command") -> ActionProposal:
    """Create a bash command action"""
    return ActionProposal(
        tool_name="Bash", arguments={"command": command}, reason=reason, affects_commands=[command]
    )


def create_search_action(
    pattern: str, path: str = ".", reason: str = "Search codebase"
) -> ActionProposal:
    """Create a search action"""
    return ActionProposal(
        tool_name="Grep",
        arguments={"pattern": pattern, "path": path},
        reason=reason,
        risk_level="safe",
    )
