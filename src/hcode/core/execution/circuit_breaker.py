"""
Circuit breaker for Hcode agent execution.

This module implements the circuit breaker pattern to prevent
cascading failures and provide graceful degradation when errors occur.
"""

import time
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    """State of the circuit breaker."""
    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreaker:
    """
    Circuit breaker for error handling in agent execution.
    
    Implements the circuit breaker pattern:
    - CLOSED: Normal operation, tracking failures
    - OPEN: Too many failures, blocking requests temporarily
    - HALF_OPEN: Testing if the service has recovered
    
    Attributes:
        max_failures: Maximum consecutive failures before opening circuit
        reset_timeout: Seconds before attempting to close circuit again
    """

    def __init__(self, max_failures: int = 3, reset_timeout: float = 30.0):
        """
        Initialize the circuit breaker.
        
        Args:
            max_failures: Maximum consecutive failures before opening
            reset_timeout: Seconds before moving from OPEN to HALF_OPEN
        """
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._success_count = 0

    @property
    def state(self) -> CircuitState:
        """Get the current circuit state."""
        self._check_state_transition()
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == CircuitState.OPEN

    def record_success(self) -> None:
        """
        Record a successful operation.
        
        In HALF_OPEN state, this closes the circuit.
        In CLOSED state, this resets the failure count.
        """
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            # After a few successes in half-open, close the circuit
            if self._success_count >= 2:
                self._close()
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """
        Record a failed operation.
        
        In HALF_OPEN state, this opens the circuit immediately.
        In CLOSED state, this increments the failure count.
        
        Args:
            error: Optional exception that caused the failure
        """
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failure during half-open, go back to open
            self._open()
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.max_failures:
                self._open()

    def can_execute(self) -> bool:
        """
        Check if an operation can be executed.
        
        Returns:
            True if the circuit allows execution
        """
        state = self.state  # This triggers state check
        return state != CircuitState.OPEN

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        self._close()

    def _open(self) -> None:
        """Open the circuit (block requests)."""
        self._state = CircuitState.OPEN
        self._last_failure_time = time.time()

    def _close(self) -> None:
        """Close the circuit (allow requests)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0

    def _half_open(self) -> None:
        """Move to half-open state (test recovery)."""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0

    def _check_state_transition(self) -> None:
        """Check if state should transition based on timeout."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.reset_timeout:
                self._half_open()

    @property
    def failure_count(self) -> int:
        """Get the current failure count."""
        return self._failure_count

    @property
    def time_until_retry(self) -> Optional[float]:
        """
        Get seconds until the circuit will attempt recovery.
        
        Returns:
            Seconds until HALF_OPEN, or None if not applicable
        """
        if self._state != CircuitState.OPEN or not self._last_failure_time:
            return None

        elapsed = time.time() - self._last_failure_time
        remaining = self.reset_timeout - elapsed
        return max(0, remaining)
