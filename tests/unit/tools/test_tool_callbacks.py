"""Tests for the tool callback system — ToolEvent, ToolCallbackManager, get_callback_manager."""

import pytest
from typing import List

from hcode.tools.core.tool_callbacks import (
    ToolCallbackManager,
    ToolEvent,
    ToolEventType,
    get_callback_manager,
)


@pytest.fixture(autouse=True)
def fresh_manager(monkeypatch):
    """Reset singleton before/after each test for isolation."""
    monkeypatch.setattr(ToolCallbackManager, "_instance", None)
    yield
    monkeypatch.setattr(ToolCallbackManager, "_instance", None)


def test_tool_event_creation():
    event = ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="TodoWrite", todos=[])
    assert event.event_type == ToolEventType.TODO_UPDATE
    assert event.tool_name == "TodoWrite"
    assert event.todos == []
    assert event.timestamp is not None


def test_tool_event_type_values():
    assert ToolEventType.TODO_UPDATE.value == "todo_update"
    assert ToolEventType.ERROR.value == "error"


def test_get_callback_manager_singleton():
    manager1 = get_callback_manager()
    manager2 = get_callback_manager()
    assert manager1 is manager2


def test_register_and_emit():
    manager = get_callback_manager()
    received: List[ToolEvent] = []

    def callback(event: ToolEvent):
        received.append(event)

    manager.register(ToolEventType.TODO_UPDATE, callback)
    manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="Test", todos=[]))

    assert len(received) == 1
    assert received[0].tool_name == "Test"


def test_emit_to_multiple_callbacks():
    manager = get_callback_manager()
    received1: List[ToolEvent] = []
    received2: List[ToolEvent] = []

    manager.register(ToolEventType.TODO_UPDATE, lambda e: received1.append(e))
    manager.register(ToolEventType.TODO_UPDATE, lambda e: received2.append(e))

    manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="Multi", todos=[]))

    assert len(received1) == 1
    assert len(received2) == 1


def test_unregister_callback():
    manager = get_callback_manager()
    received: List[ToolEvent] = []

    def callback(event: ToolEvent):
        received.append(event)

    manager.register(ToolEventType.TODO_UPDATE, callback)
    removed = manager.unregister(ToolEventType.TODO_UPDATE, callback)
    assert removed is True

    manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="Test", todos=[]))
    assert len(received) == 0


def test_unregister_nonexistent_returns_false():
    manager = get_callback_manager()

    def callback(event: ToolEvent):
        pass

    result = manager.unregister(ToolEventType.TODO_UPDATE, callback)
    assert result is False


def test_callback_error_does_not_break_others():
    manager = get_callback_manager()
    received: List[ToolEvent] = []

    def bad_callback(event: ToolEvent):
        raise ValueError("boom")

    def good_callback(event: ToolEvent):
        received.append(event)

    manager.register(ToolEventType.TODO_UPDATE, bad_callback)
    manager.register(ToolEventType.TODO_UPDATE, good_callback)

    manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="Test", todos=[]))

    assert len(received) == 1


def test_event_stored_in_history():
    manager = get_callback_manager()
    manager.emit(ToolEvent(event_type=ToolEventType.TODO_UPDATE, tool_name="A", todos=[]))
    manager.emit(ToolEvent(event_type=ToolEventType.ERROR, tool_name="B", error="oops"))
    assert len(manager._event_history) == 2
