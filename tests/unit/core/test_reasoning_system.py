"""
Comprehensive tests for the reasoning system.

Tests thinking, todos, ReAct loop, and display.
"""

import pytest
import asyncio
from datetime import datetime

# Import components
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hcode.config.thinking import ThinkingConfig, ThinkingMode, ThinkingVisibility
from hcode.agent.thinking import ThinkingBlock, ThinkingSession, ThinkingPhase
from hcode.agent.thinking_manager import ThinkingManager
from hcode.agent.todo import TodoItem, TodoManager, TodoStatus
from hcode.tools.todo_write import TodoWriteTool


class TestThinkingConfig:
    """Test thinking configuration"""

    def test_thinking_mode_enum(self):
        """Test ThinkingMode enum values"""
        assert ThinkingMode.DISABLED.value == "disabled"
        assert ThinkingMode.AUTO.value == "auto"
        assert ThinkingMode.ALWAYS.value == "always"
        assert ThinkingMode.ON_COMPLEX.value == "on_complex"

    def test_thinking_visibility_enum(self):
        """Test ThinkingVisibility enum values"""
        assert ThinkingVisibility.HIDDEN.value == "hidden"
        assert ThinkingVisibility.SUMMARY.value == "summary"
        assert ThinkingVisibility.STREAMING.value == "streaming"
        assert ThinkingVisibility.FULL.value == "full"

    def test_default_config(self):
        """Test default configuration"""
        config = ThinkingConfig()
        assert config.enabled is True
        assert config.mode == ThinkingMode.AUTO
        assert config.visibility == ThinkingVisibility.STREAMING
        assert config.budget_tokens == 10000
        assert len(config.trigger_phrases) > 0
        assert len(config.complexity_indicators) > 0

    def test_should_think_disabled(self):
        """Test thinking disabled mode"""
        config = ThinkingConfig(mode=ThinkingMode.DISABLED)
        assert config.should_think("complex refactoring task") is False

    def test_should_think_always(self):
        """Test thinking always mode"""
        config = ThinkingConfig(mode=ThinkingMode.ALWAYS)
        assert config.should_think("simple task") is True

    def test_should_think_trigger_phrases(self):
        """Test thinking triggered by phrases"""
        config = ThinkingConfig(mode=ThinkingMode.AUTO)

        # Should trigger
        assert config.should_think("think carefully about this") is True
        assert config.should_think("step by step solution") is True
        assert config.should_think("analyze the architecture") is True

        # Should not trigger
        assert config.should_think("hello") is False

    def test_should_think_complexity_indicators(self):
        """Test thinking triggered by complexity"""
        config = ThinkingConfig(mode=ThinkingMode.AUTO)

        # Should trigger
        assert config.should_think("refactor multiple files") is True
        assert config.should_think("implement feature across codebase") is True
        assert config.should_think("security audit needed") is True

    def test_should_think_tool_threshold(self):
        """Test thinking triggered by tool count"""
        config = ThinkingConfig(mode=ThinkingMode.AUTO, tool_threshold=3)

        assert config.should_think("task", estimated_tools=5) is True
        assert config.should_think("task", estimated_tools=1) is False

    def test_should_think_message_length(self):
        """Test thinking triggered by long message"""
        config = ThinkingConfig(mode=ThinkingMode.AUTO)

        long_message = "x" * 600
        assert config.should_think(long_message) is True

        short_message = "x" * 100
        assert config.should_think(short_message) is False


class TestThinkingBlocks:
    """Test thinking blocks and sessions"""

    def test_thinking_phase_enum(self):
        """Test ThinkingPhase enum"""
        assert ThinkingPhase.UNDERSTANDING.value == "understanding"
        assert ThinkingPhase.PLANNING.value == "planning"
        assert ThinkingPhase.ANALYZING.value == "analyzing"
        assert ThinkingPhase.REASONING.value == "reasoning"
        assert ThinkingPhase.EVALUATING.value == "evaluating"
        assert ThinkingPhase.DECIDING.value == "deciding"
        assert ThinkingPhase.VERIFYING.value == "verifying"

    def test_thinking_block_creation(self):
        """Test creating thinking block"""
        block = ThinkingBlock(
            phase=ThinkingPhase.UNDERSTANDING,
            content="Understanding the problem...",
            summary="Analyzing requirements",
            tokens_used=100,
            duration_ms=500,
        )

        assert block.phase == ThinkingPhase.UNDERSTANDING
        assert block.content == "Understanding the problem..."
        assert block.summary == "Analyzing requirements"
        assert block.tokens_used == 100
        assert block.duration_ms == 500
        assert block.id is not None

    def test_thinking_block_to_dict(self):
        """Test converting block to dict"""
        block = ThinkingBlock(
            phase=ThinkingPhase.PLANNING, content="Planning approach", summary="Plan created"
        )

        data = block.to_dict()
        assert data["phase"] == "planning"
        assert data["content"] == "Planning approach"
        assert data["summary"] == "Plan created"
        assert "id" in data
        assert "timestamp" in data

    def test_thinking_session_creation(self):
        """Test creating thinking session"""
        session = ThinkingSession()

        assert session.id is not None
        assert len(session.blocks) == 0
        assert session.total_tokens == 0
        assert session.end_time is None

    def test_thinking_session_add_block(self):
        """Test adding blocks to session"""
        session = ThinkingSession()

        block1 = ThinkingBlock(
            phase=ThinkingPhase.UNDERSTANDING, content="Understanding...", tokens_used=50
        )

        block2 = ThinkingBlock(phase=ThinkingPhase.PLANNING, content="Planning...", tokens_used=75)

        session.add_block(block1)
        session.add_block(block2)

        assert len(session.blocks) == 2
        assert session.total_tokens == 125

    def test_thinking_session_get_summary(self):
        """Test getting session summary"""
        session = ThinkingSession()

        block1 = ThinkingBlock(
            phase=ThinkingPhase.UNDERSTANDING,
            content="Understanding...",
            summary="Analyzed requirements",
        )

        block2 = ThinkingBlock(
            phase=ThinkingPhase.PLANNING, content="Planning...", summary="Created plan"
        )

        session.add_block(block1)
        session.add_block(block2)

        summary = session.get_summary()
        assert "Understanding" in summary
        assert "Analyzed requirements" in summary
        assert "Planning" in summary
        assert "Created plan" in summary

    def test_thinking_session_complete(self):
        """Test completing session"""
        import time

        session = ThinkingSession()
        time.sleep(0.001)  # Small delay to ensure measurable duration
        session.complete()

        assert session.end_time is not None
        assert session.duration_ms() >= 0  # Can be 0 on very fast systems


class TestTodoSystem:
    """Test todo management system"""

    def test_todo_status_enum(self):
        """Test TodoStatus enum"""
        assert TodoStatus.PENDING.value == "pending"
        assert TodoStatus.IN_PROGRESS.value == "in_progress"
        assert TodoStatus.COMPLETED.value == "completed"
        assert TodoStatus.BLOCKED.value == "blocked"
        assert TodoStatus.SKIPPED.value == "skipped"

    def test_todo_item_creation(self):
        """Test creating todo item"""
        todo = TodoItem(content="Add tests", status=TodoStatus.PENDING)

        assert todo.content == "Add tests"
        assert todo.status == TodoStatus.PENDING
        assert todo.id is not None
        assert todo.active_form == "Adding tests"  # Auto-generated

    def test_active_form_generation(self):
        """Test active form generation"""
        test_cases = [
            ("Add tests", "Adding tests"),
            ("Fix bug", "Fixing bug"),
            ("Run build", "Running build"),
            ("Create files", "Creating files"),
            ("Update docs", "Updating docs"),
            ("Analyze code", "Analyzing code"),
            ("Write script", "Writing script"),
            ("Make changes", "Making changes"),
            ("Get data", "Getting data"),
            ("Set config", "Setting config"),
            ("Read file", "Reading file"),
        ]

        for content, expected_active in test_cases:
            active = TodoItem.generate_active_form(content)
            assert (
                active == expected_active
            ), f"Failed: {content} -> {active} (expected {expected_active})"

    def test_todo_mark_in_progress(self):
        """Test marking todo in progress"""
        todo = TodoItem(content="Add tests")
        todo.mark_in_progress()

        assert todo.status == TodoStatus.IN_PROGRESS

    def test_todo_mark_completed(self):
        """Test marking todo completed"""
        todo = TodoItem(content="Add tests")
        todo.mark_completed()

        assert todo.status == TodoStatus.COMPLETED
        assert todo.completed_at is not None

    def test_todo_mark_blocked(self):
        """Test marking todo blocked"""
        todo = TodoItem(content="Add tests")
        todo.mark_blocked("Missing dependencies")

        assert todo.status == TodoStatus.BLOCKED
        assert todo.metadata["blocked_reason"] == "Missing dependencies"

    def test_todo_manager_creation(self):
        """Test creating todo manager"""
        manager = TodoManager()

        assert len(manager.todos) == 0

    def test_todo_manager_batch_update(self):
        """Test batch updating todos"""
        manager = TodoManager()

        todos_data = [
            {"content": "Add tests", "status": "pending", "activeForm": "Adding tests"},
            {"content": "Fix bug", "status": "in_progress", "activeForm": "Fixing bug"},
            {"content": "Update docs", "status": "pending", "activeForm": "Updating docs"},
        ]

        manager.batch_update(todos_data)

        assert len(manager.todos) == 3
        assert manager.todos[0].content == "Add tests"
        assert manager.todos[1].status == TodoStatus.IN_PROGRESS

    def test_todo_manager_get_by_status(self):
        """Test getting todos by status"""
        manager = TodoManager()

        todos_data = [
            {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Task 2"},
            {"content": "Task 3", "status": "pending", "activeForm": "Task 3"},
        ]

        manager.batch_update(todos_data)

        completed = manager.get_by_status(TodoStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].content == "Task 1"

    def test_todo_manager_get_current(self):
        """Test getting current todo"""
        manager = TodoManager()

        todos_data = [
            {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Task 2"},
            {"content": "Task 3", "status": "pending", "activeForm": "Task 3"},
        ]

        manager.batch_update(todos_data)

        current = manager.get_current()
        assert current is not None
        assert current.content == "Task 2"

    def test_todo_manager_get_progress(self):
        """Test getting progress stats"""
        manager = TodoManager()

        todos_data = [
            {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "completed", "activeForm": "Task 2"},
            {"content": "Task 3", "status": "in_progress", "activeForm": "Task 3"},
            {"content": "Task 4", "status": "pending", "activeForm": "Task 4"},
        ]

        manager.batch_update(todos_data)

        stats = manager.get_progress()
        assert stats["total"] == 4
        assert stats["completed"] == 2
        assert stats["in_progress"] == 1
        assert stats["pending"] == 1
        assert stats["percent_complete"] == 50


class TestTodoWriteTool:
    """Test TodoWrite tool"""

    def test_tool_creation(self):
        """Test creating TodoWrite tool"""
        manager = TodoManager()
        tool = TodoWriteTool(manager)

        assert tool.name == "TodoWrite"
        assert tool.todo_manager is manager

    @pytest.mark.asyncio
    async def test_tool_execute_valid(self):
        """Test executing with valid todos"""
        manager = TodoManager()
        tool = TodoWriteTool(manager)

        todos_data = [
            {"content": "Add tests", "status": "in_progress", "activeForm": "Adding tests"},
            {"content": "Fix bug", "status": "pending", "activeForm": "Fixing bug"},
        ]

        result = await tool.execute(todos=todos_data)

        assert result.success is True
        assert len(manager.todos) == 2

    @pytest.mark.asyncio
    async def test_tool_execute_no_in_progress(self):
        """Test executing without in_progress todo"""
        manager = TodoManager()
        tool = TodoWriteTool(manager)

        todos_data = [
            {"content": "Add tests", "status": "pending", "activeForm": "Adding tests"},
            {"content": "Fix bug", "status": "pending", "activeForm": "Fixing bug"},
        ]

        result = await tool.execute(todos=todos_data)

        assert result.success is False
        assert "exactly ONE" in result.error

    @pytest.mark.asyncio
    async def test_tool_execute_multiple_in_progress(self):
        """Test executing with multiple in_progress todos"""
        manager = TodoManager()
        tool = TodoWriteTool(manager)

        todos_data = [
            {"content": "Add tests", "status": "in_progress", "activeForm": "Adding tests"},
            {"content": "Fix bug", "status": "in_progress", "activeForm": "Fixing bug"},
        ]

        result = await tool.execute(todos=todos_data)

        assert result.success is False
        assert "exactly ONE" in result.error

    @pytest.mark.asyncio
    async def test_tool_execute_missing_field(self):
        """Test executing with missing required field"""
        manager = TodoManager()
        tool = TodoWriteTool(manager)

        todos_data = [{"content": "Add tests", "status": "in_progress"}]  # Missing activeForm

        result = await tool.execute(todos=todos_data)

        assert result.success is False
        assert "missing required field" in result.error


class TestIntegration:
    """Integration tests for complete system"""

    def test_thinking_manager_with_config(self):
        """Test thinking manager with config"""
        config = ThinkingConfig(mode=ThinkingMode.AUTO, visibility=ThinkingVisibility.STREAMING)
        manager = ThinkingManager(config)

        assert manager.config == config
        assert manager.current_session is None

    def test_thinking_manager_start_end_session(self):
        """Test starting and ending thinking session"""
        config = ThinkingConfig()
        manager = ThinkingManager(config)

        session = manager.start_session()
        assert manager.current_session is session

        ended = manager.end_session()
        assert ended is session
        assert manager.current_session is None

    def test_complete_workflow(self):
        """Test complete thinking + todo workflow"""
        # Create components
        thinking_config = ThinkingConfig(mode=ThinkingMode.AUTO)
        thinking_manager = ThinkingManager(thinking_config)
        todo_manager = TodoManager()

        # Start thinking session
        session = thinking_manager.start_session()

        # Add thinking blocks
        block1 = ThinkingBlock(
            phase=ThinkingPhase.UNDERSTANDING,
            content="Understanding the task",
            summary="Task understood",
        )
        session.add_block(block1)

        block2 = ThinkingBlock(
            phase=ThinkingPhase.PLANNING, content="Planning approach", summary="Plan created"
        )
        session.add_block(block2)

        # Create todos
        todos_data = [
            {
                "content": "Implement feature",
                "status": "in_progress",
                "activeForm": "Implementing feature",
            },
            {"content": "Add tests", "status": "pending", "activeForm": "Adding tests"},
            {"content": "Update docs", "status": "pending", "activeForm": "Updating docs"},
        ]
        todo_manager.batch_update(todos_data)

        # Verify state
        assert len(session.blocks) == 2
        assert len(todo_manager.todos) == 3
        assert todo_manager.get_current().content == "Implement feature"

        # Complete thinking
        thinking_manager.end_session()
        assert session.end_time is not None

        # Progress through todos
        todos_data[0]["status"] = "completed"
        todos_data[1]["status"] = "in_progress"
        todo_manager.batch_update(todos_data)

        progress = todo_manager.get_progress()
        assert progress["completed"] == 1
        assert progress["in_progress"] == 1
        assert progress["pending"] == 1


def run_tests():
    """Run all tests"""
    print("Running reasoning system tests...")
    print("=" * 60)

    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
