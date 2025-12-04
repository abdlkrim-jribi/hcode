"""
Sanity Check: Agent Components Tests.

Tests the basic functionality of agent components.
"""

import pytest
import tempfile
from pathlib import Path


class TestAgentModesComponent:
    """Test agent modes component."""

    def test_modes_import(self):
        """Test modes module imports."""
        from hcode.agent.modes import AgentMode

        assert AgentMode is not None

    def test_agent_mode_enum(self):
        """Test AgentMode enum has expected values."""
        from hcode.agent.modes import AgentMode

        # Check for common mode values
        assert hasattr(AgentMode, "NORMAL")


class TestThinkingComponent:
    """Test thinking component."""

    def test_thinking_import(self):
        """Test thinking module imports."""
        from hcode.agent.thinking import ThinkingProcessor

        assert ThinkingProcessor is not None


class TestThinkingManagerComponent:
    """Test thinking manager component."""

    def test_thinking_manager_import(self):
        """Test thinking_manager module imports."""
        from hcode.agent.thinking_manager import ThinkingManager

        assert ThinkingManager is not None

    def test_thinking_manager_instantiation(self):
        """Test ThinkingManager can be instantiated."""
        from hcode.agent.thinking_manager import ThinkingManager

        manager = ThinkingManager()
        assert manager is not None


class TestTodoComponent:
    """Test todo component."""

    def test_todo_import(self):
        """Test todo module imports."""
        from hcode.agent.todo import TodoManager, TodoItem

        assert TodoManager is not None
        assert TodoItem is not None

    def test_todo_manager_instantiation(self):
        """Test TodoManager can be instantiated."""
        from hcode.agent.todo import TodoManager

        manager = TodoManager()
        assert manager is not None

    def test_todo_item_creation(self):
        """Test TodoItem can be created."""
        from hcode.agent.todo import TodoItem

        item = TodoItem(content="Test task", status="pending", activeForm="Testing")
        assert item is not None
        assert item.content == "Test task"
        assert item.status == "pending"


class TestAutonomousComponent:
    """Test autonomous component."""

    def test_autonomous_import(self):
        """Test autonomous module imports."""
        from hcode.agent import autonomous

        assert autonomous is not None


class TestAutonomousAgentComponent:
    """Test autonomous agent component."""

    def test_autonomous_agent_import(self):
        """Test autonomous_agent module imports."""
        from hcode.agent.autonomous_agent import AutonomousAgent

        assert AutonomousAgent is not None


class TestAutonomousPromptComponent:
    """Test autonomous prompt component."""

    def test_autonomous_prompt_import(self):
        """Test autonomous_prompt module imports."""
        from hcode.agent import autonomous_prompt

        assert autonomous_prompt is not None


class TestCodingAgentComponent:
    """Test coding agent component."""

    def test_coding_agent_import(self):
        """Test coding_agent module imports."""
        from hcode.agent.coding_agent import CodingAgent

        assert CodingAgent is not None


class TestSubAgentComponent:
    """Test sub-agent component."""

    def test_sub_agent_import(self):
        """Test sub_agent module imports."""
        from hcode.agents.sub_agent import SubAgent

        assert SubAgent is not None
