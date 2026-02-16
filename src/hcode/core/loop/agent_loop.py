"""
Agent Loop Controller for Hcode Agent.

Clean PEV (Planning-Execution-Verification) state machine
for managing the agent's main execution loop.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Set


class Phase(Enum):
    """PEV execution phases."""
    PLANNING = "planning"  # Create task.md, impl_plan.md
    EXECUTION = "execution"  # Execute tools
    VERIFICATION = "verification"  # Validate, create walkthrough
    COMPLETE = "complete"


class StopReason(Enum):
    """Why the loop stopped."""
    TASK_COMPLETE = "task_complete"
    MAX_ITERATIONS = "max_iterations"
    CIRCUIT_BREAKER = "circuit_breaker"
    STUCK_LOOP = "stuck_loop"
    ERROR = "error"


@dataclass
class LoopState:
    """
    Minimal loop state tracking.
    
    Design: Track only what's needed, compute everything else.
    """
    iteration: int = 0
    max_iterations: int = 50
    phase: Phase = Phase.PLANNING
    stop_reason: Optional[StopReason] = None

    # Error tracking
    errors: int = 0
    max_errors: int = 3

    # Response tracking
    responses: List[str] = field(default_factory=list)

    # Completed actions
    actions: List[Dict[str, Any]] = field(default_factory=list)

    # Modified files
    modified_files: Set[str] = field(default_factory=set)


class AgentLoopController:
    """
    Clean PEV state machine for agent execution.
    
    Design principles:
    - Minimal state, compute on demand
    - Explicit phase transitions
    - Simple stopping conditions
    """

    def __init__(
            self,
            console: Any = None,
            debug_mode: bool = False,
            max_iterations: int = 50,
    ):
        self.console = console
        self.debug_mode = debug_mode
        self.state = LoopState(max_iterations=max_iterations)

    def _debug(self, msg: str) -> None:
        if self.debug_mode and self.console:
            self.console.print(msg)

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def reset(self) -> None:
        """Reset for new execution."""
        self.state = LoopState(max_iterations=self.state.max_iterations)

    def tick(self) -> bool:
        """
        Start next iteration.
        
        Returns: True if can continue, False if should stop.
        """
        self.state.iteration += 1

        if self.state.iteration > self.state.max_iterations:
            self.stop(StopReason.MAX_ITERATIONS)
            return False

        if self._is_stuck():
            self.stop(StopReason.STUCK_LOOP)
            return False

        return True

    def stop(self, reason: StopReason) -> None:
        """Stop the loop with reason."""
        self.state.phase = Phase.COMPLETE
        self.state.stop_reason = reason
        self._debug(f"[yellow]Loop stopped: {reason.value}[/yellow]")

    # =========================================================================
    # Phase Management
    # =========================================================================

    @property
    def phase(self) -> Phase:
        return self.state.phase

    def transition(self, new_phase: Phase) -> None:
        """Transition to a new phase."""
        old = self.state.phase.value
        self.state.phase = new_phase
        self._debug(f"[dim]Phase: {old} → {new_phase.value}[/dim]")

    def is_complete(self) -> bool:
        return self.state.phase == Phase.COMPLETE

    # =========================================================================
    # Recording
    # =========================================================================

    def record_response(self, text: str) -> None:
        """Record a response."""
        if text.strip():
            self.state.responses.append(text)
            # Keep last 5 for stuck detection
            if len(self.state.responses) > 5:
                self.state.responses.pop(0)

    def record_action(self, tool: str, args: dict, success: bool) -> None:
        """Record a tool action."""
        self.state.actions.append({
            "tool": tool,
            "args": args,
            "success": success,
            "iteration": self.state.iteration,
        })

        # Track modified files
        if success and tool.lower() in ("write", "writetool", "edit", "edittool"):
            path = args.get("file_path") or args.get("path")
            if path:
                self.state.modified_files.add(str(path))

        # Reset errors on success
        if success:
            self.state.errors = 0

    def record_error(self) -> bool:
        """
        Record an error.
        
        Returns: True if can continue, False if circuit broken.
        """
        self.state.errors += 1
        if self.state.errors >= self.state.max_errors:
            self.stop(StopReason.CIRCUIT_BREAKER)
            return False
        return True

    # =========================================================================
    # Queries
    # =========================================================================

    def should_continue(self) -> bool:
        """Check if loop should continue."""
        return self.state.stop_reason is None and not self.is_complete()

    def _is_stuck(self) -> bool:
        """Check if stuck in a loop."""
        responses = self.state.responses
        if len(responses) < 3:
            return False

        # Check if last 3 responses are identical
        last = responses[-1][:200] if responses else ""
        return all(r[:200] == last for r in responses[-3:])

    def get_summary(self) -> Dict[str, Any]:
        """Get loop summary."""
        return {
            "iterations": self.state.iteration,
            "phase": self.state.phase.value,
            "actions": len(self.state.actions),
            "successful": sum(1 for a in self.state.actions if a["success"]),
            "modified_files": list(self.state.modified_files),
            "stop_reason": self.state.stop_reason.value if self.state.stop_reason else None,
        }


# Aliases for compatibility
LoopPhase = Phase
LoopState = LoopState
