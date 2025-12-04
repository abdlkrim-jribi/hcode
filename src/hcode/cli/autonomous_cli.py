"""
CLI integration for autonomous operation.

Provides commands and UI for switching between agent modes.
"""

from typing import Optional, Callable, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from hcode.agent.modes import AgentMode, get_mode_config
from hcode.ui import Colors, Icons, get_default_box


class AutonomousCLI:
    """
    CLI handler for autonomous mode operations.

    Provides:
    - Mode switching commands
    - Mode status display
    - Confirmation prompts
    - Progress indicators
    """

    # Command aliases
    MODE_COMMANDS = {
        "/auto": AgentMode.AUTO,
        "/interactive": AgentMode.INTERACTIVE,
        "/plan": AgentMode.PLAN,
        "/review": AgentMode.REVIEW,
        "/mode": None,  # Show current mode
    }

    COMMAND_ALIASES = {
        "/a": "/auto",
        "/i": "/interactive",
        "/p": "/plan",
        "/r": "/review",
        "/m": "/mode",
    }

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize autonomous CLI.

        Args:
            console: Rich console instance
        """
        self.console = console or Console()
        self.icons = Icons()
        self._current_mode = AgentMode.INTERACTIVE
        self._mode_change_callback: Optional[Callable[[AgentMode], None]] = None

    def set_mode_change_callback(self, callback: Callable[[AgentMode], None]):
        """Set callback for mode changes"""
        self._mode_change_callback = callback

    def set_current_mode(self, mode: AgentMode):
        """Update current mode display"""
        self._current_mode = mode

    def is_mode_command(self, input_text: str) -> bool:
        """Check if input is a mode command"""
        cmd = input_text.strip().lower()

        # Check direct commands
        if cmd in self.MODE_COMMANDS:
            return True

        # Check aliases
        if cmd in self.COMMAND_ALIASES:
            return True

        # Check "mode <name>" format
        if cmd.startswith("/mode "):
            return True

        return False

    def handle_mode_command(self, input_text: str) -> bool:
        """
        Handle mode command.

        Args:
            input_text: User input

        Returns:
            True if command was handled
        """
        cmd = input_text.strip().lower()

        # Resolve alias
        if cmd in self.COMMAND_ALIASES:
            cmd = self.COMMAND_ALIASES[cmd]

        # Handle /mode <name>
        if cmd.startswith("/mode "):
            mode_name = cmd[6:].strip()
            return self._set_mode_by_name(mode_name)

        # Handle direct mode commands
        if cmd in self.MODE_COMMANDS:
            target_mode = self.MODE_COMMANDS[cmd]

            if target_mode is None:
                # /mode - show current mode
                self.show_mode_status()
                return True
            else:
                return self._change_mode(target_mode)

        return False

    def _set_mode_by_name(self, name: str) -> bool:
        """Set mode by name string"""
        name_lower = name.lower()

        for mode in AgentMode:
            if mode.value == name_lower:
                return self._change_mode(mode)

        # Not found - show help
        self.console.print(f"[{Colors.ERROR}]Unknown mode: {name}[/]")
        self.show_mode_help()
        return False

    def _change_mode(self, new_mode: AgentMode) -> bool:
        """Change to new mode"""
        old_mode = self._current_mode
        self._current_mode = new_mode

        # Call callback
        if self._mode_change_callback:
            self._mode_change_callback(new_mode)

        # Display change
        self._display_mode_change(old_mode, new_mode)

        return True

    def _display_mode_change(self, old_mode: AgentMode, new_mode: AgentMode):
        """Display mode change notification"""
        mode_config = get_mode_config(new_mode)

        # Mode icons
        mode_icons = {
            AgentMode.INTERACTIVE: self.icons.PROMPT,
            AgentMode.AUTO: self.icons.LIGHTNING,
            AgentMode.PLAN: self.icons.TASK,
            AgentMode.REVIEW: self.icons.SEARCH,
        }

        icon = mode_icons.get(new_mode, self.icons.ARROW_RIGHT)

        # Build message
        msg = Text()
        msg.append(f" {icon} ", style=f"bold {Colors.PRIMARY}")
        msg.append("Mode: ", style=Colors.TEXT_SECONDARY)
        msg.append(f"{old_mode.value}", style=Colors.TEXT_MUTED)
        msg.append(" → ", style=Colors.TEXT_MUTED)
        msg.append(f"{new_mode.value}", style=f"bold {Colors.SUCCESS}")
        msg.append(f"\n   {mode_config.description}", style=Colors.TEXT_MUTED)

        self.console.print(msg)
        self.console.print()

    def show_mode_status(self):
        """Show current mode status"""
        mode_config = get_mode_config(self._current_mode)

        # Build status panel
        content = Text()

        # Current mode header
        content.append(f" {self.icons.LOGO} ", style=f"bold {Colors.PRIMARY}")
        content.append("Current Mode: ", style=Colors.TEXT_SECONDARY)
        content.append(f"{self._current_mode.value.upper()}\n", style=f"bold {Colors.SUCCESS}")

        # Description
        content.append(f"   {mode_config.description}\n", style=Colors.TEXT_MUTED)
        content.append("\n")

        # Settings
        content.append(" Settings:\n", style=f"bold {Colors.TEXT_SECONDARY}")

        settings = [
            ("Ask permission", mode_config.ask_permission),
            ("Show plan", mode_config.show_plan),
            ("Confirm dangerous", mode_config.confirm_dangerous),
            ("Require approval", mode_config.require_approval),
        ]

        for name, value in settings:
            icon = self.icons.CHECK if value else self.icons.CROSS
            color = Colors.SUCCESS if value else Colors.TEXT_MUTED
            content.append(f"   {icon} ", style=color)
            content.append(f"{name}\n", style=Colors.TEXT_SECONDARY)

        self.console.print(
            Panel(
                content,
                border_style=Colors.PRIMARY,
                box=get_default_box(),
                padding=(0, 1),
                width=50,
            )
        )

    def show_mode_help(self):
        """Show mode command help"""
        content = Text()

        content.append(f" {self.icons.INFO} ", style=Colors.INFO)
        content.append("Mode Commands\n\n", style=f"bold {Colors.TEXT_PRIMARY}")

        # Mode table
        modes = [
            ("/interactive", "i", "Ask before each action"),
            ("/auto", "a", "Execute automatically"),
            ("/plan", "p", "Show plan, then execute"),
            ("/review", "r", "Show plan, get approval"),
            ("/mode", "m", "Show current mode"),
        ]

        for cmd, alias, desc in modes:
            content.append(f"  {cmd:<13}", style=f"bold {Colors.SECONDARY}")
            content.append(f"(/{alias}) ", style=Colors.TEXT_MUTED)
            content.append(f"{desc}\n", style=Colors.TEXT_SECONDARY)

        content.append("\n")
        content.append(f" {self.icons.ARROW_RIGHT} ", style=Colors.PRIMARY)
        content.append("Tip: ", style=f"bold {Colors.TEXT_SECONDARY}")
        content.append("Press Shift+Tab to toggle modes", style=Colors.TEXT_MUTED)

        self.console.print(
            Panel(
                content,
                border_style=Colors.BORDER_DEFAULT,
                box=get_default_box(),
                padding=(0, 1),
                width=50,
            )
        )

    def confirm_action(self, message: str) -> bool:
        """
        Ask user for confirmation.

        Args:
            message: Confirmation message

        Returns:
            True if confirmed
        """
        self.console.print()
        self.console.print(
            Panel(
                message,
                title=f"[{Colors.WARNING}]Confirm?[/]",
                border_style=Colors.WARNING,
                box=get_default_box(),
                padding=(0, 1),
            )
        )

        try:
            response = input("  (y/n): ").strip().lower()
            return response in ["y", "yes", "ok", ""]
        except (EOFError, KeyboardInterrupt):
            return False

    def confirm_plan(self, plan_display: str, action_count: int) -> bool:
        """
        Ask user to approve execution plan.

        Args:
            plan_display: Formatted plan display
            action_count: Number of actions in plan

        Returns:
            True if approved
        """
        self.console.print()
        self.console.print(
            Panel(
                plan_display,
                title=f"[{Colors.PRIMARY}]Execution Plan[/]",
                border_style=Colors.PRIMARY,
                box=get_default_box(),
                padding=(1, 2),
            )
        )

        self.console.print()
        self.console.print(f" {self.icons.INFO} ", style=Colors.INFO, end="")
        self.console.print(f"This plan has {action_count} actions.", style=Colors.TEXT_SECONDARY)

        try:
            response = input("  Approve? (y/n): ").strip().lower()
            approved = response in ["y", "yes", "ok"]

            if approved:
                self.console.print(
                    f" {self.icons.CHECK} Plan approved", style=f"bold {Colors.SUCCESS}"
                )
            else:
                self.console.print(f" {self.icons.CROSS} Plan rejected", style=Colors.WARNING)

            return approved

        except (EOFError, KeyboardInterrupt):
            self.console.print(f" {self.icons.CROSS} Plan cancelled", style=Colors.WARNING)
            return False

    def show_progress(self, message: str, progress: float):
        """
        Show progress indicator.

        Args:
            message: Progress message
            progress: Progress value (0.0 to 1.0)
        """
        # Progress bar
        width = 20
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        pct = int(progress * 100)

        self.console.print(
            f"\r {self.icons.TOOL} [{Colors.PRIMARY}]{bar}[/] {pct}% - {message}", end=""
        )

        if progress >= 1.0:
            self.console.print()  # New line when complete

    def show_execution_stats(self, stats: Dict[str, Any]):
        """
        Show execution statistics.

        Args:
            stats: Statistics dictionary
        """
        content = Text()

        content.append(f" {self.icons.CHECK} ", style=f"bold {Colors.SUCCESS}")
        content.append("Execution Complete\n\n", style=f"bold {Colors.TEXT_PRIMARY}")

        # Mode
        content.append("  Mode: ", style=Colors.TEXT_SECONDARY)
        content.append(f"{stats.get('mode', 'unknown')}\n", style=Colors.TEXT_PRIMARY)

        # Actions
        content.append("  Actions: ", style=Colors.TEXT_SECONDARY)
        content.append(f"{stats.get('total_actions', 0)}", style=Colors.TEXT_PRIMARY)

        if stats.get("dangerous_actions", 0) > 0:
            content.append(
                f" ({stats['dangerous_actions']} required confirmation)", style=Colors.WARNING
            )
        content.append("\n")

        # Errors
        errors = stats.get("errors", 0)
        if errors > 0:
            content.append("  Errors: ", style=Colors.TEXT_SECONDARY)
            content.append(f"{errors}\n", style=Colors.ERROR)

        # Duration
        duration = stats.get("elapsed_seconds", 0)
        if duration > 0:
            content.append("  Duration: ", style=Colors.TEXT_SECONDARY)
            if duration < 60:
                content.append(f"{duration:.1f}s\n", style=Colors.TEXT_PRIMARY)
            else:
                mins = int(duration // 60)
                secs = duration % 60
                content.append(f"{mins}m {secs:.1f}s\n", style=Colors.TEXT_PRIMARY)

        # Todo progress
        todo_progress = stats.get("todo_progress", {})
        if todo_progress:
            completed = todo_progress.get("completed", 0)
            total = todo_progress.get("total", 0)
            if total > 0:
                content.append("  Tasks: ", style=Colors.TEXT_SECONDARY)
                content.append(f"{completed}/{total} completed\n", style=Colors.TEXT_PRIMARY)

        self.console.print(
            Panel(
                content,
                border_style=Colors.SUCCESS,
                box=get_default_box(),
                padding=(0, 1),
                width=50,
            )
        )

    def display_decision(self, tool_name: str, risk_level: str, decision: str, reason: str = ""):
        """
        Display execution decision.

        Args:
            tool_name: Name of the tool
            risk_level: Risk level (safe, caution, dangerous)
            decision: Decision made (execute, confirm, skip)
            reason: Reason for the action
        """
        # Risk colors
        risk_colors = {"safe": Colors.SUCCESS, "caution": Colors.WARNING, "dangerous": Colors.ERROR}

        # Risk icons
        risk_icons = {
            "safe": self.icons.CHECK,
            "caution": self.icons.WARNING,
            "dangerous": self.icons.CROSS,
        }

        color = risk_colors.get(risk_level, Colors.TEXT_SECONDARY)
        icon = risk_icons.get(risk_level, self.icons.BULLET)

        # Decision icons
        decision_icons = {
            "execute": self.icons.LIGHTNING,
            "confirm": self.icons.PROMPT,
            "skip": self.icons.ARROW_RIGHT,
            "abort": self.icons.CROSS,
        }

        dec_icon = decision_icons.get(decision, self.icons.BULLET)

        # Build message
        msg = Text()
        msg.append(f" {icon} ", style=color)
        msg.append(f"{tool_name}", style=f"bold {Colors.TEXT_PRIMARY}")
        msg.append(f" [{risk_level}]", style=color)
        msg.append(f" {dec_icon} ", style=Colors.TEXT_MUTED)
        msg.append(f"{decision}", style=Colors.TEXT_SECONDARY)

        if reason:
            msg.append(f"\n   {reason}", style=Colors.TEXT_MUTED)

        self.console.print(msg)


def create_mode_status_line(mode: AgentMode) -> Text:
    """
    Create a status line showing current mode.

    Args:
        mode: Current agent mode

    Returns:
        Rich Text object for status line
    """
    icons = Icons()

    mode_info = {
        AgentMode.INTERACTIVE: (icons.PROMPT, Colors.INFO, "INT"),
        AgentMode.AUTO: (icons.LIGHTNING, Colors.SUCCESS, "AUTO"),
        AgentMode.PLAN: (icons.TASK, Colors.WARNING, "PLAN"),
        AgentMode.REVIEW: (icons.SEARCH, Colors.TERTIARY, "REV"),
    }

    icon, color, label = mode_info.get(mode, (icons.BULLET, Colors.TEXT_MUTED, "???"))

    status = Text()
    status.append(f"{icon}", style=color)
    status.append(f" {label}", style=f"bold {color}")

    return status
