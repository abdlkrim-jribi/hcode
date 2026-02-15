"""
Phase manager for PEV workflow.

Manages transitions between Planning → Execution → Verification phases.
"""

from typing import Dict, Any

from ..protocols import (
    PhaseManagerProtocol,
    PhaseHandlerProtocol,
    AgentContext,
    PhaseResult,
)


class PhaseManager(PhaseManagerProtocol):
    """
    Manages PEV workflow phase transitions.

    Responsibilities:
    - Track current phase
    - Delegate to appropriate phase handler
    - Enforce phase transition rules
    - Determine workflow completion
    """

    # Phase ordering
    PHASES = ["planning", "execution", "verification"]

    def __init__(
        self,
        handlers: Dict[str, PhaseHandlerProtocol],
        initial_phase: str = "planning",
    ):
        """
        Initialize phase manager.

        Args:
            handlers: Dict mapping phase names to handlers
            initial_phase: Starting phase (default: "planning")
        """
        self.handlers = handlers
        self.current_phase = initial_phase
        self.phase_history: list[str] = [initial_phase]

        # Validate handlers exist for all phases
        for phase in self.PHASES:
            if phase not in handlers:
                raise ValueError(f"Missing handler for phase: {phase}")

    def get_current_phase(self) -> str:
        """Get name of current phase."""
        return self.current_phase

    async def execute_current_phase(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute the current phase.

        Args:
            context: Current agent context
            loop_controller: Loop controller for tracking

        Returns:
            PhaseResult from current phase handler
        """
        handler = self.handlers[self.current_phase]
        result = await handler.handle(context, loop_controller)

        # Add metadata about phase
        result.metadata["phase"] = self.current_phase
        result.metadata["phase_index"] = self.PHASES.index(self.current_phase)

        return result

    def transition_to_next_phase(self, context: AgentContext) -> bool:
        """
        Attempt to transition to next phase.

        Args:
            context: Current agent context

        Returns:
            True if transition successful
        """
        # Check if current phase is complete
        current_handler = self.handlers[self.current_phase]
        if not current_handler.can_transition_to_next(context):
            return False

        # Get next phase
        current_index = self.PHASES.index(self.current_phase)
        if current_index >= len(self.PHASES) - 1:
            # Already at last phase
            return False

        next_phase = self.PHASES[current_index + 1]

        # Transition
        self.current_phase = next_phase
        self.phase_history.append(next_phase)

        return True

    def can_complete(self, context: AgentContext) -> bool:
        """
        Check if all phases are complete.

        Args:
            context: Current agent context

        Returns:
            True if workflow is complete
        """
        # Workflow is complete if:
        # 1. We're in the verification phase
        # 2. Verification phase is complete
        if self.current_phase != "verification":
            return False

        verification_handler = self.handlers["verification"]
        return verification_handler.can_transition_to_next(context)

    def get_phase_progress(self) -> Dict[str, Any]:
        """
        Get progress through phases.

        Returns:
            Dict with phase progress information
        """
        current_index = self.PHASES.index(self.current_phase)
        return {
            "current_phase": self.current_phase,
            "phase_index": current_index,
            "total_phases": len(self.PHASES),
            "progress_percent": int((current_index + 1) / len(self.PHASES) * 100),
            "phase_history": self.phase_history,
            "completed_phases": self.phase_history[:-1] if len(self.phase_history) > 1 else [],
        }

    def reset(self, initial_phase: str = "planning") -> None:
        """
        Reset phase manager to initial state.

        Args:
            initial_phase: Phase to start from
        """
        self.current_phase = initial_phase
        self.phase_history = [initial_phase]

    def force_phase(self, phase_name: str) -> bool:
        """
        Force transition to a specific phase (for testing/debugging).

        Args:
            phase_name: Phase to transition to

        Returns:
            True if phase exists and transition succeeded
        """
        if phase_name not in self.PHASES:
            return False

        self.current_phase = phase_name
        self.phase_history.append(phase_name)
        return True

    def validate_phase_artifacts(self, context: AgentContext) -> Dict[str, Any]:
        """
        Validate artifacts for all completed phases.

        Args:
            context: Current agent context

        Returns:
            Dict with validation results for each phase
        """
        results = {}

        for phase_name in self.phase_history:
            handler = self.handlers[phase_name]
            valid, error = handler.validate_artifacts(context)
            results[phase_name] = {
                "valid": valid,
                "error": error,
                "required_artifacts": handler.get_required_artifacts(),
            }

        return results
