"""
Sanity Check: Agent Components Tests.

Tests the basic functionality of agent core components.
"""

import pytest
import tempfile
from pathlib import Path


class TestAgentCoreComponent:
    """Test core agent component."""

    def test_agent_import(self):
        """Test core agent imports."""
        from hcode.core.agent import HcodeAgent

        assert HcodeAgent is not None


class TestThinkingComponent:
    """Test thinking component."""

    def test_thinking_import(self):
        """Test thinking module imports."""
        from hcode.core.response.thinking_processor import ThinkingBlockProcessor

        assert ThinkingBlockProcessor is not None


class TestThinkingManagerComponent:
    """Test thinking manager component."""

    def test_thinking_manager_import(self):
        """Test thinking_manager module imports."""
        from hcode.core.execution.thinking_manager import EnhancedThinkingManager

        assert EnhancedThinkingManager is not None

    def test_thinking_manager_instantiation(self):
        """Test EnhancedThinkingManager can be instantiated."""
        from hcode.core.execution.thinking_manager import EnhancedThinkingManager

        manager = EnhancedThinkingManager()
        assert manager is not None


class TestTodoComponent:
    """Test todo component."""

    def test_todo_import(self):
        """Test todo module imports."""
        from hcode.core.todo import TodoManager, TodoItem

        assert TodoManager is not None
        assert TodoItem is not None

    def test_todo_manager_instantiation(self):
        """Test TodoManager can be instantiated."""
        from hcode.core.todo import TodoManager

        manager = TodoManager()
        assert manager is not None

    def test_todo_item_creation(self):
        """Test TodoItem can be created."""
        from hcode.core.todo import TodoItem

        item = TodoItem(content="Test task", status="pending", active_form="Testing")
        assert item is not None
        assert item.content == "Test task"
        assert item.status == "pending"


class TestToolCallParserComponent:
    """Test tool call parser component."""

    def test_tool_call_parser_import(self):
        """Test ToolCallParser imports."""
        from hcode.core.tools import ToolCallParser

        assert ToolCallParser is not None

    def test_tool_call_parser_instantiation(self):
        """Test ToolCallParser can be instantiated."""
        from hcode.core.tools import ToolCallParser

        parser = ToolCallParser()
        assert parser is not None


class TestTodoAutoUpdaterComponent:
    """Test todo auto-updater component."""

    def test_todo_auto_updater_import(self):
        """Test TodoAutoUpdater imports."""
        from hcode.core.todo import TodoAutoUpdater

        assert TodoAutoUpdater is not None


class TestAgentLoopControllerComponent:
    """Test agent loop controller component."""

    def test_loop_controller_import(self):
        """Test AgentLoopController imports."""
        from hcode.core.loop import AgentLoopController, Phase, StopReason

        assert AgentLoopController is not None
        assert Phase is not None
        assert StopReason is not None

    def test_loop_controller_instantiation(self):
        """Test AgentLoopController can be instantiated."""
        from hcode.core.loop import AgentLoopController

        controller = AgentLoopController()
        assert controller is not None
        assert controller.state.iteration == 0
