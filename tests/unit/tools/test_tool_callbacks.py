"""
Tests for the tool callback system.

Tests the ToolCallbackManager and its integration with TodoWriteTool
for real-time UI updates.
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
    """Tests for ToolCallbackManager."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the singleton before each test."""
        ToolCallbackManager.reset_instance()
        yield
        ToolCallbackManager.reset_instance()

    def test_singleton_pattern(self):
        """Should return the same instance."""
        manager1 = get_callback_manager()
        manager2 = get_callback_manager()
        assert manager1 is manager2

    def test_register_callback(self):
        """Should register callbacks."""
        manager = get_callback_manager()

        def callback(event):
            pass

        manager.register(ToolEventType.TODO_UPDATE, callback)
        assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 1

    def test_unregister_callback(self):
        """Should unregister callbacks."""
        manager = get_callback_manager()

        def callback(event):
            pass

        manager.register(ToolEventType.TODO_UPDATE, callback)
        result = manager.unregister(ToolEventType.TODO_UPDATE, callback)

        assert result is True
        assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 0

    def test_unregister_nonexistent_callback(self):
        """Should return False for non-existent callback."""
        manager = get_callback_manager()

        def callback(event):
            pass

        result = manager.unregister(ToolEventType.TODO_UPDATE, callback)
        assert result is False

    def test_emit_event(self):
        """Should emit events to registered callbacks."""
        manager = get_callback_manager()
        received_events: List[ToolEvent] = []

        def callback(event):
            received_events.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback)

        test_event = ToolEvent(
            event_type=ToolEventType.TODO_UPDATE,
            tool_name="TodoWrite",
            todos=[{"content": "Test", "status": "pending", "activeForm": "Testing"}]
        )
        manager.emit(test_event)

        assert len(received_events) == 1
        assert received_events[0].tool_name == "TodoWrite"
        assert len(received_events[0].todos) == 1

    def test_emit_to_multiple_callbacks(self):
        """Should emit to all registered callbacks."""
        manager = get_callback_manager()
        received1: List[ToolEvent] = []
        received2: List[ToolEvent] = []

        def callback1(event):
            received1.append(event)

        def callback2(event):
            received2.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback1)
        manager.register(ToolEventType.TODO_UPDATE, callback2)

        manager.emit(ToolEvent(
            event_type=ToolEventType.TODO_UPDATE,
            tool_name="Test",
            todos=[]
        ))

        assert len(received1) == 1
        assert len(received2) == 1

    def test_callback_error_does_not_break_others(self):
        """Callback errors should not prevent other callbacks from running."""
        manager = get_callback_manager()
        received: List[ToolEvent] = []

        def bad_callback(event):
            raise ValueError("Intentional error")

        def good_callback(event):
            received.append(event)

        manager.register(ToolEventType.TODO_UPDATE, bad_callback)
        manager.register(ToolEventType.TODO_UPDATE, good_callback)

        # Should not raise, and good_callback should still be called
        manager.emit(ToolEvent(
            event_type=ToolEventType.TODO_UPDATE,
            tool_name="Test",
            todos=[]
        ))

        assert len(received) == 1

    def test_emit_todo_update_convenience(self):
        """Should emit TODO_UPDATE via convenience method."""
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
        """Should unregister all callbacks."""
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
        """Should unregister all callbacks for specific event type."""
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
        """Should disable/enable event emission."""
        manager = get_callback_manager()
        received: List[ToolEvent] = []

        def callback(event):
            received.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback)

        # Disable
        manager.set_enabled(False)
        manager.emit(ToolEvent(
            event_type=ToolEventType.TODO_UPDATE,
            tool_name="Test",
            todos=[]
        ))
        assert len(received) == 0

        # Re-enable
        manager.set_enabled(True)
        manager.emit(ToolEvent(
            event_type=ToolEventType.TODO_UPDATE,
            tool_name="Test",
            todos=[]
        ))
        assert len(received) == 1


class TestCallbackContext:
    """Tests for CallbackContext context manager."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the singleton before each test."""
        ToolCallbackManager.reset_instance()
        yield
        ToolCallbackManager.reset_instance()

    def test_context_manager_registers_callback(self):
        """Should register callback when entering context."""
        manager = get_callback_manager()

        def callback(event):
            pass

        with CallbackContext(ToolEventType.TODO_UPDATE, callback):
            assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 1

    def test_context_manager_unregisters_on_exit(self):
        """Should unregister callback when exiting context."""
        manager = get_callback_manager()

        def callback(event):
            pass

        with CallbackContext(ToolEventType.TODO_UPDATE, callback):
            pass

        assert manager.get_callbacks_count(ToolEventType.TODO_UPDATE) == 0

    def test_context_manager_unregisters_on_exception(self):
        """Should unregister callback even if exception occurs."""
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
    """Tests for TodoWriteTool callback integration."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the singleton before each test."""
        ToolCallbackManager.reset_instance()
        yield
        ToolCallbackManager.reset_instance()

    @pytest.mark.asyncio
    async def test_todowrite_emits_callback(self):
        """TodoWriteTool should emit TODO_UPDATE callback."""
        from hcode.tools.interactive_tools import TodoWriteTool

        manager = get_callback_manager()
        received: List[ToolEvent] = []

        def callback(event):
            received.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback)

        tool = TodoWriteTool()
        result = await tool.execute(todos=[
            {"content": "Task 1", "status": "in_progress", "activeForm": "Doing task 1"}
        ])

        assert result.success
        assert len(received) == 1
        assert received[0].event_type == ToolEventType.TODO_UPDATE
        assert len(received[0].todos) == 1

    @pytest.mark.asyncio
    async def test_todowrite_callback_contains_stats(self):
        """TodoWriteTool callback should include stats metadata."""
        from hcode.tools.interactive_tools import TodoWriteTool

        manager = get_callback_manager()
        received: List[ToolEvent] = []

        def callback(event):
            received.append(event)

        manager.register(ToolEventType.TODO_UPDATE, callback)

        tool = TodoWriteTool()
        await tool.execute(todos=[
            {"content": "Done", "status": "completed", "activeForm": "Done"},
            {"content": "Doing", "status": "in_progress", "activeForm": "Doing"},
            {"content": "Todo", "status": "pending", "activeForm": "Todo"},
        ])

        assert len(received) == 1
        metadata = received[0].metadata
        assert metadata["completed"] == 1
        assert metadata["in_progress"] == 1
        assert metadata["pending"] == 1


class TestEventHistory:
    """Tests for event history tracking."""

    @pytest.fixture(autouse=True)
    def reset_manager(self):
        """Reset the singleton before each test."""
        ToolCallbackManager.reset_instance()
        yield
        ToolCallbackManager.reset_instance()

    def test_get_event_history(self):
        """Should track event history."""
        manager = get_callback_manager()

        # Emit several events
        for i in range(5):
            manager.emit(ToolEvent(
                event_type=ToolEventType.TODO_UPDATE,
                tool_name=f"Test{i}",
                todos=[]
            ))

        history = manager.get_event_history()
        assert len(history) == 5

    def test_get_event_history_with_limit(self):
        """Should respect limit parameter."""
        manager = get_callback_manager()

        for i in range(10):
            manager.emit(ToolEvent(
                event_type=ToolEventType.TODO_UPDATE,
                tool_name=f"Test{i}",
                todos=[]
            ))

        history = manager.get_event_history(limit=3)
        assert len(history) == 3

    def test_get_event_history_filtered_by_type(self):
        """Should filter by event type."""
        manager = get_callback_manager()

        manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="A", todos=[]))
        manager.emit(ToolEvent(event_type=ToolEventType.TOOL_START, tool_name="B", arguments={}))
        manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="C", todos=[]))

        history = manager.get_event_history(event_type=ToolEventType.TODO_UPDATE)
        assert len(history) == 2
        assert all(e.event_type == ToolEventType.TODO_UPDATE for e in history)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
