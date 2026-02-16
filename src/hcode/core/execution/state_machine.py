from enum import Enum
from typing import Any, Dict


# =============================================================================
# EXECUTION STATE MACHINE
# =============================================================================

class ExecutionState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionStateMachine:
    """Manages execution state and transitions."""

    TRANSITIONS = {
        ExecutionState.IDLE: {ExecutionState.PLANNING, ExecutionState.FAILED},
        ExecutionState.PLANNING: {ExecutionState.EXECUTING, ExecutionState.AWAITING_INPUT, ExecutionState.FAILED},
        ExecutionState.EXECUTING: {ExecutionState.VERIFYING, ExecutionState.RECOVERING, ExecutionState.AWAITING_INPUT, ExecutionState.FAILED},
        ExecutionState.VERIFYING: {ExecutionState.COMPLETED, ExecutionState.EXECUTING, ExecutionState.RECOVERING, ExecutionState.FAILED},
        ExecutionState.RECOVERING: {ExecutionState.PLANNING, ExecutionState.EXECUTING, ExecutionState.FAILED},
        ExecutionState.AWAITING_INPUT: {ExecutionState.PLANNING, ExecutionState.EXECUTING, ExecutionState.COMPLETED, ExecutionState.FAILED},
        ExecutionState.COMPLETED: set(),
        ExecutionState.FAILED: set(),
    }

    def __init__(self):
        self._state = ExecutionState.IDLE
        self._error_count = 0
        self._iteration_count = 0
        self._max_iterations = 50
        self._max_errors = 3

    @property
    def state(self) -> ExecutionState:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return self._state in {ExecutionState.COMPLETED, ExecutionState.FAILED}

    @property
    def should_continue(self) -> bool:
        if self.is_terminal: return False
        if self._iteration_count >= self._max_iterations: return False
        if self._error_count >= self._max_errors: return False
        return True

    def can_transition(self, to_state: ExecutionState) -> bool:
        return to_state in self.TRANSITIONS.get(self._state, set())

    def transition(self, to_state: ExecutionState, trigger: str = "") -> bool:
        if not self.can_transition(to_state):
            return False
        self._state = to_state
        self._iteration_count += 1
        return True

    def record_error(self):
        self._error_count += 1

    def reset(self):
        self._state = ExecutionState.IDLE
        self._error_count = 0
        self._iteration_count = 0

    def get_summary(self) -> Dict[str, Any]:
        return {
            "current_state": self._state.value,
            "iteration_count": self._iteration_count,
            "error_count": self._error_count,
            "is_terminal": self.is_terminal,
            "should_continue": self.should_continue,
            "transition_count": self._iteration_count,
        }
