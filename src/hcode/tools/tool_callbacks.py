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

    BEFORE_EXECUTE = "before_execute"
    AFTER_EXECUTE = "after_execute"
    TODO_UPDATE = "todo_update"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
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

    @classmethod
    def reset_instance(cls):
        """
        Reset the singleton instance.

        Useful for testing or reinitializing the callback system.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance._callbacks = {event_type: [] for event_type in ToolEventType}
                cls._instance._event_history = []
            cls._instance = None

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

    def unregister_all(self, event_type: Optional[ToolEventType] = None) -> int:
        """
        Unregister all callbacks for an event type, or all callbacks if no type specified.

        Args:
            event_type: Optional event type to clear. If None, clears all.

        Returns:
            Number of callbacks removed
        """
        with self._callback_lock:
            count = 0
            if event_type is None:
                for et in ToolEventType:
                    count += len(self._callbacks[et])
                    self._callbacks[et] = []
            else:
                count = len(self._callbacks[event_type])
                self._callbacks[event_type] = []
            return count

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

    def emit_todo_update(self, todos: List[Dict[str, Any]], tool_name: str = "TodoWrite") -> None:
        """
        Convenience method to emit a TODO_UPDATE event.

        Args:
            todos: The updated todo list
            tool_name: Name of the tool that updated todos
        """
        self.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name=tool_name, todos=todos))

    def emit_tool_start(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """
        Convenience method to emit a TOOL_START event.

        Args:
            tool_name: Name of the tool starting
            arguments: Arguments being passed to the tool
        """
        self.emit(
            ToolEvent(event_type=ToolEventType.TOOL_START, tool_name=tool_name, arguments=arguments)
        )

    def emit_tool_end(self, tool_name: str, result: Any, success: bool = True) -> None:
        """
        Convenience method to emit a TOOL_END event.

        Args:
            tool_name: Name of the tool that finished
            result: Result from the tool
            success: Whether execution was successful
        """
        self.emit(
            ToolEvent(
                event_type=ToolEventType.TOOL_END,
                tool_name=tool_name,
                result=result,
                metadata={"success": success},
            )
        )

    def get_callbacks_count(self, event_type: Optional[ToolEventType] = None) -> int:
        """
        Get the number of registered callbacks.

        Args:
            event_type: Optional event type. If None, returns total count.

        Returns:
            Number of registered callbacks
        """
        with self._callback_lock:
            if event_type is None:
                return sum(len(cbs) for cbs in self._callbacks.values())
            return len(self._callbacks[event_type])

    def get_event_history(
        self, event_type: Optional[ToolEventType] = None, limit: int = 10
    ) -> List[ToolEvent]:
        """
        Get recent events from history.

        Args:
            event_type: Optional filter by event type
            limit: Maximum number of events to return

        Returns:
            List of recent events (newest first)
        """
        history = self._event_history.copy()

        if event_type is not None:
            history = [e for e in history if e.event_type == event_type]

        return list(reversed(history[-limit:]))

    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable event emission.

        When disabled, emit() calls are no-ops.

        Args:
            enabled: Whether to enable event emission
        """
        self._enabled = enabled

    @property
    def is_enabled(self) -> bool:
        """Check if event emission is enabled."""
        return self._enabled


# Convenience function to get the global manager
def get_callback_manager() -> ToolCallbackManager:
    """Get the global callback manager instance."""
    return ToolCallbackManager.get_instance()


# Context manager for temporary callback registration
class CallbackContext:
    """
    Context manager for temporary callback registration.

    Usage:
        def my_handler(event):
            print(f"Todo updated: {event.todos}")

        with CallbackContext(ToolEventType.TODO_UPDATE, my_handler):
            # Callback is registered here
            agent.execute_task(...)
        # Callback is automatically unregistered
    """

    def __init__(self, event_type: ToolEventType, callback: ToolCallback):
        self.event_type = event_type
        self.callback = callback
        self.manager = get_callback_manager()

    def __enter__(self):
        self.manager.register(self.event_type, self.callback)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.unregister(self.event_type, self.callback)
        return False  # Don't suppress exceptions
