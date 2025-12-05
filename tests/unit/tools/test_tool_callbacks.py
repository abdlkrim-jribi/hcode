"""
Tests for the tool callback system.

This module contains unit tests for the :class:`ToolCallbackManager` and its integration
with :class:`TodoWriteTool`.  The tests verify singleton behaviour, registration and
unregistration of callbacks, event emission, error handling, context‑manager usage, and
event‑history tracking.
"""

import pytest
import asyncio
from typing import List

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from hcode.tools.tool_callbacks import (
    ToolCallbackManager,
    ToolEvent,
    ToolEventType,
    CallbackContext,
    get_callback_manager,
)


class TestToolCallbackManager:
    """Tests for :class:`ToolCallbackManager`.

    The class exercises the public API of the manager, ensuring that callbacks are
    correctly registered, unregistered, and invoked.
    """

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the singleton before each test.

        This fixture runs automatically for every test method in the class, guaranteeing
        a clean manager instance.
        """
        ToolCallbackManager.reset_instance()
        yield
        ToolCallbackManager.reset_instance()

    def test_singleton_pattern(self):
        """Verify that ``get_callback_manager`` returns the same instance.

        Returns:
            None
        """
        manager1 = get_callback_manager()
        manager2 = get_callback_manager()
        assert manager1 is manager2

    def test_register_callback(self):
        """Ensure a callback can be registered for an event type.

        The test registers a dummy callback for ``TODO_UPDATE`` and checks that the
        manager reports a count of one.
        """
        manager = get_callback_manager()

        def callback(event):
            pass

        manager.register(ToolEventType.TODO_UPDATE, callback)
        assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 1

    def test_unregister_callback(self):
        """Check that a previously registered callback can be unregistered.

        Returns:
            None
        """
        manager = get_callback_manager()

        def callback(event):
            pass

        manager.register(ToolEventType.TODO_UPDATE, callback)
        result = manager.unregister(ToolEventType.TODO_UPDATE, callback)

        assert result is True
        assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 0

    def test_unregister_nonexistent_callback(self):
        """Attempt to unregister a callback that was never registered.

        The manager should return ``False`` and leave the callback count unchanged.
        """
        manager = get_callback_manager()

        def callback(event):
            pass

        result = manager.unregister(ToolEventType.TODO_UPDATE, callback)
        assert result is False

    def test_emit_event(self):
        """Emit an event and verify that registered callbacks receive it.

        The test registers a callback that appends received events to a list and then
        emits a ``ToolEvent``.  Assertions confirm the callback was invoked and the
        event data matches expectations.
        """
        manager = get_callback_manager()
        received_events: List[ToolEvent] = []

        def callback(event):
            received_events.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback)

        test_event = ToolEvent(
            event_type=ToolEventType.TODO_UPDATE,
            tool_name="TodoWrite",
            todos=[{"content": "Test", "status": "pending", "activeForm": "Testing"}],
        )
        manager.emit(test_event)

        assert len(received_events) == 1
        assert received_events[0].tool_name == "TodoWrite"
        assert len(received_events[0].todos) == 1

    def test_emit_to_multiple_callbacks(self):
        """Verify that an emitted event reaches *all* registered callbacks.

        Two callbacks are registered for the same event type; after emission each
        callback should have recorded exactly one event.
        """
        manager = get_callback_manager()
        received1: List[ToolEvent] = []
        received2: List[ToolEvent] = []

        def callback1(event):
            received1.append(event)

        def callback2(event):
            received2.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback1)
        manager.register(ToolEventType.TODO_UPDATE, callback2)

        manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="Test", todos=[]))

        assert len(received1) == 1
        assert len(received2) == 1

    def test_callback_error_does_not_break_others(self):
        """Ensure that an exception in one callback does not prevent others from running.

        A ``bad_callback`` raises ``ValueError`` while ``good_callback`` records the event.
        After emission, ``good_callback`` must still have been called.
        """
        manager = get_callback_manager()
        received: List[ToolEvent] = []

        def bad_callback(event):
            raise ValueError("Intentional error")

        def good_callback(event):
            received.append(event)

        manager.register(ToolEventType.TODO_UPDATE, bad_callback)
        manager.register(ToolEventType.TODO_UPDATE, good_callback)

        # Should not raise; good_callback should still be called
        manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="Test", todos=[]))

        assert len(received) == 1

    def test_emit_todo_update_convenience(self):
        """Test the convenience method ``emit_todo_update``.

        The method should emit a ``TODO_UPDATE`` event with the supplied todo list.
        """
        manager = get_callback_manager()
        received: List[ToolEvent] = []

        def callback(event):
            received.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback)

        test_todos = [{"content": "Task", "status": "pending", "activeForm": "Doing"}]
        manager.emit_todo_update(test_todos)

        assert len(received) == 1
        assert received[0].event_type == ToolEventType.TODO_UPDATE

    def test_unregister_all(self):
        """Unregister *all* callbacks regardless of event type.

        After calling ``unregister_all`` the manager should report zero callbacks.
        """
        manager = get_callback_manager()

        def callback1(event):
            pass

        def callback2(event):
            pass

        manager.register(ToolEventType.TODO_UPDATE, callback1)
        manager.register(ToolEventType.TOOL_START, callback2)

        count = manager.unregister_all()
        assert count == 2
        assert manager.get_callbacks_count() == 0

    def test_unregister_all_for_event_type(self):
        """Unregister all callbacks for a specific ``ToolEventType``.

        Only callbacks registered for ``TODO_UPDATE`` should be removed.
        """
        manager = get_callback_manager()

        def callback1(event):
            pass

        def callback2(event):
            pass

        manager.register(ToolEventType.TODO_UPDATE, callback1)
        manager.register(ToolEventType.TOOL_START, callback2)

        count = manager.unregister_all(ToolEventType.TODO_UPDATE)
        assert count == 1
        assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 0
        assert manager.get_callbacks_count(ToolEventType.TOOL_START) == 1

    def test_set_enabled(self):
        """Toggle the manager's enabled state and verify emission behaviour.

        When disabled, emitted events should be ignored; when re‑enabled they should be
        processed normally.
        """
        manager = get_callback_manager()
        received: List[ToolEvent] = []

        def callback(event):
            received.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback)

        # Disable emission
        manager.set_enabled(False)
        manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="Test", todos=[]))
        assert len(received) == 0

        # Re‑enable and emit again
        manager.set_enabled(True)
        manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="Test", todos=[]))
        assert len(received) == 1


class TestCallbackContext:
    """Tests for the :class:`CallbackContext` context manager.

    The context manager should automatically register a callback on entry and
    unregister it on exit, even when an exception occurs.
    """

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the singleton before each test in this class."""
        ToolCallbackManager.reset_instance()
        yield
        ToolCallbackManager.reset_instance()

    def test_context_manager_registers_callback(self):
        """Callback should be registered when entering the context manager."""
        manager = get_callback_manager()

        def callback(event):
            pass

        with CallbackContext(ToolEventType.TODO_UPDATE, callback):
            assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 1

    def test_context_manager_unregisters_on_exit(self):
        """Callback should be unregistered when exiting the context manager."""
        manager = get_callback_manager()

        def callback(event):
            pass

        with CallbackContext(ToolEventType.TODO_UPDATE, callback):
            pass

        assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 0

    def test_context_manager_unregisters_on_exception(self):
        """Even if an exception is raised, the callback must be unregistered."""
        manager = get_callback_manager()

        def callback(event):
            pass

        try:
            with CallbackContext(ToolEventType.TODO_UPDATE, callback):
                raise ValueError("Test error")
        except ValueError:
            pass

        assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 0


class TestTodoWriteToolCallback:
    """Tests for the ``TodoWriteTool`` callback integration.

    These tests verify that the interactive tool emits the appropriate ``TODO_UPDATE``
    events and includes correct metadata.
    """

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the singleton before each test in this class."""
        ToolCallbackManager.reset_instance()
        yield
        ToolCallbackManager.reset_instance()

    @pytest.mark.asyncio
    async def test_todowrite_emits_callback(self):
        """``TodoWriteTool`` should emit a ``TODO_UPDATE`` callback after execution."""
        from hcode.tools.interactive_tools import TodoWriteTool

        manager = get_callback_manager()
        received: List[ToolEvent] = []

        def callback(event):
            received.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback)

        tool = TodoWriteTool()
        result = await tool.execute(
            todos=[{"content": "Task 1", "status": "in_progress", "activeForm": "Doing task 1"}]
        )

        assert result.success
        assert len(received) == 1
        assert received[0].event_type == ToolEventType.TODO_UPDATE
        assert len(received[0].todos) == 1

    @pytest.mark.asyncio
    async def test_todowrite_callback_contains_stats(self):
        """The callback emitted by ``TodoWriteTool`` must contain statistics metadata."""
        from hcode.tools.interactive_tools import TodoWriteTool

        manager = get_callback_manager()
        received: List[ToolEvent] = []

        def callback(event):
            received.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback)

        tool = TodoWriteTool()
        await tool.execute(
            todos=[
                {"content": "Done", "status": "completed", "activeForm": "Done"},
                {"content": "Doing", "status": "in_progress", "activeForm": "Doing"},
                {"content": "Todo", "status": "pending", "activeForm": "Todo"},
            ]
        )

        assert len(received) == 1
        metadata = received[0].metadata
        assert metadata["completed"] == 1
        assert metadata["in_progress"] == 1
        assert metadata["pending"] == 1


class TestEventHistory:
    """Tests for event‑history tracking functionality of ``ToolCallbackManager``.

    The manager should retain a chronological list of emitted events and support
    optional limiting and filtering by event type.
    """

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the singleton before each test in this class."""
        ToolCallbackManager.reset_instance()
        yield
        ToolCallbackManager.reset_instance()

    def test_get_event_history(self):
        """Emit several events and verify that the full history is recorded."""
        manager = get_callback_manager()

        # Emit several events
        for i in range(5):
            manager.emit(
                ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name=f"Test{i}", todos=[])
            )

        history = manager.get_event_history()
        assert len(history) == 5

    def test_get_event_history_with_limit(self):
        """The ``limit`` argument should restrict the number of returned events."""
        manager = get_callback_manager()

        for i in range(10):
            manager.emit(
                ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name=f"Test{i}", todos=[])
            )

        history = manager.get_event_history(limit=3)
        assert len(history) == 3

    def test_get_event_history_filtered_by_type(self):
        """When ``event_type`` is provided, only matching events should be returned."""
        manager = get_callback_manager()

        manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="A", todos=[]))
        manager.emit(ToolEvent(event_type=ToolEventType.TOOL_START, tool_name="B", arguments={}))
        manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="C", todos=[]))

        history = manager.get_event_history(event_type=ToolEventType.TODO_UPDATE)
        assert len(history) == 2
        assert all(e.event_type == ToolEventType.TODO_UPDATE for e in history)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
