"""
Tool execution callback system for real-time UI updates.

Provides a publish-subscribe mechanism for tool execution events,
enabling real-time UI updates when tools like TodoWrite are executed.

This is the key component for making the todo bar update in real-time
during agent execution (like Claude Code).
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Any, List, Optional


class ToolEventType(Enum):
    """Types of tool execution events."""

    TODO_UPDATE = "todo_update"
    ERROR = "error"


@dataclass
class ToolEvent:
    """
    Event emitted during tool execution.

    Attributes:
        event_type: Type of event
        tool_name: Name of the tool being executed
        arguments: Arguments passed to the tool
        result: Result from tool execution (for AFTER_EXECUTE)
        todos: Updated todo list (for TODO_UPDATE)
        error: Error message if any
        timestamp: When the event occurred
        metadata: Additional event metadata
    """

    event_type: ToolEventType
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    todos: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# Type alias for callback functions
ToolCallback = Callable[[ToolEvent], None]


class ToolCallbackManager:
    """
    Central manager for tool execution callbacks.

    Implements the singleton pattern to provide a global callback registry
    that can be accessed from anywhere in the application.

    Usage:
        # Register a callback
        manager = ToolCallbackManager.get_instance()
        manager.register(ToolEventType.TODO_UPDATE, my_callback)

        # Emit an event (from tool execution)
        manager.emit(ToolEvent(
            event_type=ToolEventType.TODO_UPDATE,
            tool_name="TodoWrite",
            todos=[...]
        ))

        # Unregister when done
        manager.unregister(ToolEventType.TODO_UPDATE, my_callback)
    """

    _instance: Optional["ToolCallbackManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the callback manager."""
        self._callbacks: Dict[ToolEventType, List[ToolCallback]] = {
            event_type: [] for event_type in ToolEventType
        }
        self._callback_lock = threading.Lock()
        self._event_history: List[ToolEvent] = []
        self._max_history = 100
        self._enabled = True

    @classmethod
    def get_instance(cls) -> "ToolCallbackManager":
        """
        Get the singleton instance.

        Thread-safe singleton implementation.

        Returns:
            The global ToolCallbackManager instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register(self, event_type: ToolEventType, callback: ToolCallback) -> None:
        """
        Register a callback for a specific event type.

        Args:
            event_type: The type of event to listen for
            callback: Function to call when event occurs
        """
        with self._callback_lock:
            if callback not in self._callbacks[event_type]:
                self._callbacks[event_type].append(callback)

    def unregister(self, event_type: ToolEventType, callback: ToolCallback) -> bool:
        """
        Unregister a callback.

        Args:
            event_type: The event type the callback was registered for
            callback: The callback function to remove

        Returns:
            True if callback was found and removed, False otherwise
        """
        with self._callback_lock:
            if callback in self._callbacks[event_type]:
                self._callbacks[event_type].remove(callback)
                return True
            return False

    def emit(self, event: ToolEvent) -> None:
        """
        Emit an event to all registered callbacks.

        Callbacks are executed synchronously in registration order.
        Exceptions in callbacks are caught and logged but don't prevent
        other callbacks from being called.

        Args:
            event: The event to emit
        """
        if not self._enabled:
            return

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Get callbacks (copy to avoid modification during iteration)
        with self._callback_lock:
            callbacks = list(self._callbacks[event.event_type])

        # Execute callbacks
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                # Log error but don't break execution
                import sys

                print(f"[Callback Error] {event.event_type.value}: {e}", file=sys.stderr)


# Convenience function to get the global manager
def get_callback_manager() -> ToolCallbackManager:
    """Get the global callback manager instance."""
    return ToolCallbackManager.get_instance()
