"""
Tests for TodoWrite tool and TodoManager.

Tests todo creation, batch updates, status management, and active form generation.
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hcode.tools.todo_write import TodoWriteTool
from hcode.agent.todo import TodoManager, TodoItem, TodoStatus


class TestTodoStatus:
    """Tests for TodoStatus enum"""

    def test_status_values(self):
        """Test all status values are defined"""
        assert TodoStatus.PENDING.value == "pending"
        assert TodoStatus.IN_PROGRESS.value == "in_progress"
        assert TodoStatus.COMPLETED.value == "completed"
        assert TodoStatus.BLOCKED.value == "blocked"
        assert TodoStatus.SKIPPED.value == "skipped"

    def test_status_from_string(self):
        """Test creating status from string value"""
        assert TodoStatus("pending") == TodoStatus.PENDING
        assert TodoStatus("in_progress") == TodoStatus.IN_PROGRESS
        assert TodoStatus("completed") == TodoStatus.COMPLETED

    def test_invalid_status(self):
        """Test invalid status raises error"""
        with pytest.raises(ValueError):
            TodoStatus("invalid_status")


class TestTodoItem:
    """Tests for TodoItem dataclass"""

    def test_initialization(self):
        """Test basic todo item creation"""
        todo = TodoItem(content="Add tests")

        assert todo.content == "Add tests"
        assert todo.status == TodoStatus.PENDING
        assert todo.id is not None
        assert todo.created_at is not None
        assert todo.completed_at is None

    def test_auto_active_form_generation(self):
        """Test active form is auto-generated"""
        todo = TodoItem(content="Add tests")

        assert todo.active_form == "Adding tests"

    def test_custom_active_form(self):
        """Test custom active form is preserved"""
        todo = TodoItem(content="Add tests", active_form="Running test suite")

        assert todo.active_form == "Running test suite"

    def test_unique_ids(self):
        """Test each todo gets unique ID"""
        todo1 = TodoItem(content="Task 1")
        todo2 = TodoItem(content="Task 2")

        assert todo1.id != todo2.id

    def test_mark_in_progress(self):
        """Test marking todo as in progress"""
        todo = TodoItem(content="Add tests")
        todo.mark_in_progress()

        assert todo.status == TodoStatus.IN_PROGRESS

    def test_mark_completed(self):
        """Test marking todo as completed"""
        todo = TodoItem(content="Add tests")
        todo.mark_completed()

        assert todo.status == TodoStatus.COMPLETED
        assert todo.completed_at is not None

    def test_mark_blocked(self):
        """Test marking todo as blocked"""
        todo = TodoItem(content="Add tests")
        todo.mark_blocked(reason="Missing dependency")

        assert todo.status == TodoStatus.BLOCKED
        assert todo.metadata.get("blocked_reason") == "Missing dependency"

    def test_mark_skipped(self):
        """Test marking todo as skipped"""
        todo = TodoItem(content="Add tests")
        todo.mark_skipped(reason="Not needed")

        assert todo.status == TodoStatus.SKIPPED
        assert todo.metadata.get("skipped_reason") == "Not needed"

    def test_to_dict(self):
        """Test converting todo to dictionary"""
        todo = TodoItem(content="Add tests", active_form="Adding tests")
        data = todo.to_dict()

        assert data["content"] == "Add tests"
        assert data["status"] == "pending"
        assert data["activeForm"] == "Adding tests"
        assert "id" in data
        assert "created_at" in data

    def test_string_representation(self):
        """Test string representation"""
        todo = TodoItem(content="Add tests")

        assert "Add tests" in str(todo)
        assert "○" in str(todo)  # Pending symbol


class TestActiveFormGeneration:
    """Tests for active form generation from imperative"""

    def test_regular_verb_add(self):
        """Test 'Add' -> 'Adding'"""
        result = TodoItem.generate_active_form("Add tests")
        assert result == "Adding tests"

    def test_regular_verb_build(self):
        """Test 'Build' -> 'Building'"""
        result = TodoItem.generate_active_form("Build project")
        assert result == "Building project"

    def test_regular_verb_test(self):
        """Test 'Test' -> 'Testing'"""
        result = TodoItem.generate_active_form("Test functionality")
        assert result == "Testing functionality"

    def test_verb_ending_in_e_write(self):
        """Test 'Write' -> 'Writing'"""
        result = TodoItem.generate_active_form("Write documentation")
        assert result == "Writing documentation"

    def test_verb_ending_in_e_create(self):
        """Test 'Create' -> 'Creating'"""
        result = TodoItem.generate_active_form("Create component")
        assert result == "Creating component"

    def test_special_verb_run(self):
        """Test 'Run' -> 'Running'"""
        result = TodoItem.generate_active_form("Run tests")
        assert result == "Running tests"

    def test_special_verb_fix(self):
        """Test 'Fix' -> 'Fixing'"""
        result = TodoItem.generate_active_form("Fix bug")
        assert result == "Fixing bug"

    def test_special_verb_get(self):
        """Test 'Get' -> 'Getting'"""
        result = TodoItem.generate_active_form("Get data")
        assert result == "Getting data"

    def test_verb_update(self):
        """Test 'Update' -> 'Updating'"""
        result = TodoItem.generate_active_form("Update config")
        assert result == "Updating config"

    def test_verb_analyze(self):
        """Test 'Analyze' -> 'Analyzing'"""
        result = TodoItem.generate_active_form("Analyze codebase")
        assert result == "Analyzing codebase"

    def test_case_insensitive(self):
        """Test case insensitive matching"""
        result = TodoItem.generate_active_form("add tests")
        # Should still work
        assert "ing" in result.lower()


class TestTodoManager:
    """Tests for TodoManager"""

    def test_initialization(self):
        """Test manager initialization"""
        manager = TodoManager()

        assert manager.todos == []
        assert manager.listeners == []

    def test_batch_update(self):
        """Test batch update replaces todos"""
        manager = TodoManager()

        todos = [
            {"content": "Task 1", "status": "in_progress", "activeForm": "Working on Task 1"},
            {"content": "Task 2", "status": "pending", "activeForm": "Working on Task 2"},
        ]

        manager.batch_update(todos)

        assert len(manager.todos) == 2
        assert manager.todos[0].content == "Task 1"
        assert manager.todos[0].status == TodoStatus.IN_PROGRESS
        assert manager.todos[1].content == "Task 2"
        assert manager.todos[1].status == TodoStatus.PENDING

    def test_batch_update_replaces_existing(self):
        """Test batch update clears previous todos"""
        manager = TodoManager()

        # First update
        manager.batch_update(
            [{"content": "Old task", "status": "in_progress", "activeForm": "Old"}]
        )

        # Second update should replace
        manager.batch_update(
            [
                {"content": "New task 1", "status": "in_progress", "activeForm": "New 1"},
                {"content": "New task 2", "status": "pending", "activeForm": "New 2"},
            ]
        )

        assert len(manager.todos) == 2
        assert all("New task" in t.content for t in manager.todos)

    def test_get_all(self):
        """Test getting all todos"""
        manager = TodoManager()
        manager.batch_update(
            [
                {"content": "Task 1", "status": "in_progress", "activeForm": "T1"},
                {"content": "Task 2", "status": "pending", "activeForm": "T2"},
            ]
        )

        all_todos = manager.get_all()

        assert len(all_todos) == 2
        # Should be a copy
        all_todos.clear()
        assert len(manager.todos) == 2

    def test_get_by_status(self):
        """Test filtering todos by status"""
        manager = TodoManager()
        manager.batch_update(
            [
                {"content": "Task 1", "status": "completed", "activeForm": "T1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "T2"},
                {"content": "Task 3", "status": "pending", "activeForm": "T3"},
                {"content": "Task 4", "status": "completed", "activeForm": "T4"},
            ]
        )

        completed = manager.get_by_status(TodoStatus.COMPLETED)

        assert len(completed) == 2
        assert all(t.status == TodoStatus.COMPLETED for t in completed)

    def test_get_current(self):
        """Test getting current in-progress todo"""
        manager = TodoManager()
        manager.batch_update(
            [
                {"content": "Completed", "status": "completed", "activeForm": "C"},
                {"content": "Current", "status": "in_progress", "activeForm": "I"},
                {"content": "Pending", "status": "pending", "activeForm": "P"},
            ]
        )

        current = manager.get_current()

        assert current is not None
        assert current.content == "Current"
        assert current.status == TodoStatus.IN_PROGRESS

    def test_get_current_none(self):
        """Test getting current when none in progress"""
        manager = TodoManager()

        current = manager.get_current()

        assert current is None

    def test_get_progress(self):
        """Test progress statistics"""
        manager = TodoManager()
        manager.batch_update(
            [
                {"content": "Task 1", "status": "completed", "activeForm": "T1"},
                {"content": "Task 2", "status": "completed", "activeForm": "T2"},
                {"content": "Task 3", "status": "in_progress", "activeForm": "T3"},
                {"content": "Task 4", "status": "pending", "activeForm": "T4"},
            ]
        )

        stats = manager.get_progress()

        assert stats["total"] == 4
        assert stats["completed"] == 2
        assert stats["in_progress"] == 1
        assert stats["pending"] == 1
        assert stats["percent_complete"] == 50

    def test_get_progress_empty(self):
        """Test progress with empty list"""
        manager = TodoManager()

        stats = manager.get_progress()

        assert stats["total"] == 0
        assert stats["percent_complete"] == 0

    def test_to_dict_list(self):
        """Test converting all todos to dict list"""
        manager = TodoManager()
        manager.batch_update(
            [
                {"content": "Task 1", "status": "in_progress", "activeForm": "T1"},
                {"content": "Task 2", "status": "pending", "activeForm": "T2"},
            ]
        )

        dict_list = manager.to_dict_list()

        assert len(dict_list) == 2
        assert all(isinstance(d, dict) for d in dict_list)
        assert dict_list[0]["content"] == "Task 1"

    def test_listener_notification(self):
        """Test listeners are notified on update"""
        manager = TodoManager()
        updates_received = []

        def listener(todos):
            updates_received.append(len(todos))

        manager.add_listener(listener)
        manager.batch_update([{"content": "Task", "status": "in_progress", "activeForm": "T"}])

        assert len(updates_received) == 1
        assert updates_received[0] == 1

    def test_multiple_listeners(self):
        """Test multiple listeners all notified"""
        manager = TodoManager()
        listener1_calls = []
        listener2_calls = []

        manager.add_listener(lambda t: listener1_calls.append(True))
        manager.add_listener(lambda t: listener2_calls.append(True))

        manager.batch_update([{"content": "Task", "status": "in_progress", "activeForm": "T"}])

        assert len(listener1_calls) == 1
        assert len(listener2_calls) == 1

    def test_string_representation(self):
        """Test manager string representation"""
        manager = TodoManager()
        manager.batch_update(
            [
                {"content": "Task 1", "status": "completed", "activeForm": "T1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "T2"},
            ]
        )

        string = str(manager)

        assert "1/2" in string  # 1 completed of 2 total


class TestTodoWriteTool:
    """Tests for TodoWriteTool"""

    def test_initialization(self):
        """Test tool initialization"""
        tool = TodoWriteTool()

        assert tool.name == "TodoWrite"
        assert tool.todo_manager is not None

    def test_initialization_with_manager(self):
        """Test initialization with existing manager"""
        manager = TodoManager()
        tool = TodoWriteTool(todo_manager=manager)

        assert tool.todo_manager is manager

    def test_get_parameters(self):
        """Test parameter definition"""
        tool = TodoWriteTool()
        params = tool.get_parameters()

        param_names = [p.name for p in params]
        assert "todos" in param_names

        todos_param = next(p for p in params if p.name == "todos")
        assert todos_param.required == True

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful todo update"""
        tool = TodoWriteTool()

        todos = [
            {"content": "Task 1", "status": "in_progress", "activeForm": "Working on Task 1"},
            {"content": "Task 2", "status": "pending", "activeForm": "Working on Task 2"},
        ]

        result = await tool.execute(todos=todos)

        assert result.success == True
        assert "stats" in result.output
        assert result.output["stats"]["total"] == 2

    @pytest.mark.asyncio
    async def test_execute_validates_required_fields(self):
        """Test validation of required fields"""
        tool = TodoWriteTool()

        # Missing content
        todos = [{"status": "in_progress", "activeForm": "Working"}]

        result = await tool.execute(todos=todos)

        assert result.success == False
        assert "content" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_validates_status_field(self):
        """Test validation of status field"""
        tool = TodoWriteTool()

        # Missing status
        todos = [{"content": "Task 1", "activeForm": "Working"}]

        result = await tool.execute(todos=todos)

        assert result.success == False
        assert "status" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_validates_active_form(self):
        """Test validation of activeForm field"""
        tool = TodoWriteTool()

        # Missing activeForm
        todos = [{"content": "Task 1", "status": "in_progress"}]

        result = await tool.execute(todos=todos)

        assert result.success == False
        assert "activeForm" in result.error

    @pytest.mark.asyncio
    async def test_execute_validates_single_in_progress(self):
        """Test validation of single in-progress rule"""
        tool = TodoWriteTool()

        # Multiple in-progress
        todos = [
            {"content": "Task 1", "status": "in_progress", "activeForm": "T1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "T2"},
        ]

        result = await tool.execute(todos=todos)

        assert result.success == False
        assert "in_progress" in result.error.lower() or "one" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_validates_at_least_one_in_progress(self):
        """Test validation requires one in-progress"""
        tool = TodoWriteTool()

        # No in-progress
        todos = [
            {"content": "Task 1", "status": "pending", "activeForm": "T1"},
            {"content": "Task 2", "status": "pending", "activeForm": "T2"},
        ]

        result = await tool.execute(todos=todos)

        assert result.success == False
        assert "in_progress" in result.error.lower() or "0" in result.error

    @pytest.mark.asyncio
    async def test_execute_validates_status_values(self):
        """Test validation of status values"""
        tool = TodoWriteTool()

        # Invalid status
        todos = [{"content": "Task 1", "status": "invalid_status", "activeForm": "T1"}]

        result = await tool.execute(todos=todos)

        assert result.success == False
        assert "status" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_validates_empty_content(self):
        """Test validation rejects empty content"""
        tool = TodoWriteTool()

        todos = [{"content": "", "status": "in_progress", "activeForm": "Working"}]

        result = await tool.execute(todos=todos)

        assert result.success == False
        assert "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_validates_empty_active_form(self):
        """Test validation rejects empty activeForm"""
        tool = TodoWriteTool()

        todos = [{"content": "Task", "status": "in_progress", "activeForm": ""}]

        result = await tool.execute(todos=todos)

        assert result.success == False
        assert "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_validates_list_type(self):
        """Test validation requires list"""
        tool = TodoWriteTool()

        # Not a list
        result = await tool.execute(todos="not a list")

        assert result.success == False
        assert "list" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_validates_dict_items(self):
        """Test validation requires dict items"""
        tool = TodoWriteTool()

        # Item is not a dict
        todos = ["not a dict"]

        result = await tool.execute(todos=todos)

        assert result.success == False
        assert "dictionary" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_returns_progress_stats(self):
        """Test result includes progress stats"""
        tool = TodoWriteTool()

        todos = [
            {"content": "Completed", "status": "completed", "activeForm": "C"},
            {"content": "Current", "status": "in_progress", "activeForm": "I"},
            {"content": "Pending", "status": "pending", "activeForm": "P"},
        ]

        result = await tool.execute(todos=todos)

        assert result.success == True
        stats = result.output["stats"]
        assert stats["total"] == 3
        assert stats["completed"] == 1
        assert stats["in_progress"] == 1
        assert stats["pending"] == 1

    @pytest.mark.asyncio
    async def test_execute_returns_todos(self):
        """Test result includes current todos"""
        tool = TodoWriteTool()

        todos = [{"content": "Task 1", "status": "in_progress", "activeForm": "T1"}]

        result = await tool.execute(todos=todos)

        assert result.success == True
        assert "todos" in result.output
        assert len(result.output["todos"]) == 1

    @pytest.mark.asyncio
    async def test_execute_all_valid_statuses(self):
        """Test all valid status values work"""
        tool = TodoWriteTool()

        todos = [
            {"content": "Pending", "status": "pending", "activeForm": "P"},
            {"content": "Current", "status": "in_progress", "activeForm": "I"},
            {"content": "Done", "status": "completed", "activeForm": "D"},
            {"content": "Stuck", "status": "blocked", "activeForm": "B"},
            {"content": "Skip", "status": "skipped", "activeForm": "S"},
        ]

        result = await tool.execute(todos=todos)

        assert result.success == True
        assert result.output["stats"]["total"] == 5

    def test_get_schema(self):
        """Test schema generation"""
        tool = TodoWriteTool()
        schema = tool.get_schema()

        assert schema["name"] == "TodoWrite"
        assert "description" in schema
        assert "parameters" in schema
        assert "todos" in schema["parameters"]["properties"]


class TestTodoWorkflow:
    """Integration tests for todo workflows"""

    @pytest.mark.asyncio
    async def test_task_progression_workflow(self):
        """Test typical task progression workflow"""
        tool = TodoWriteTool()

        # Step 1: Start with initial tasks
        result1 = await tool.execute(
            todos=[
                {"content": "Read file", "status": "in_progress", "activeForm": "Reading file"},
                {"content": "Process data", "status": "pending", "activeForm": "Processing data"},
                {"content": "Write output", "status": "pending", "activeForm": "Writing output"},
            ]
        )

        assert result1.success == True
        assert result1.output["stats"]["in_progress"] == 1

        # Step 2: Complete first, start second
        result2 = await tool.execute(
            todos=[
                {"content": "Read file", "status": "completed", "activeForm": "Reading file"},
                {
                    "content": "Process data",
                    "status": "in_progress",
                    "activeForm": "Processing data",
                },
                {"content": "Write output", "status": "pending", "activeForm": "Writing output"},
            ]
        )

        assert result2.success == True
        assert result2.output["stats"]["completed"] == 1
        assert result2.output["stats"]["in_progress"] == 1

        # Step 3: Complete all
        result3 = await tool.execute(
            todos=[
                {"content": "Read file", "status": "completed", "activeForm": "Reading file"},
                {"content": "Process data", "status": "completed", "activeForm": "Processing data"},
                {
                    "content": "Write output",
                    "status": "in_progress",
                    "activeForm": "Writing output",
                },
            ]
        )

        assert result3.success == True
        assert result3.output["stats"]["completed"] == 2

    @pytest.mark.asyncio
    async def test_blocked_task_workflow(self):
        """Test workflow with blocked tasks"""
        tool = TodoWriteTool()

        # Task becomes blocked
        result = await tool.execute(
            todos=[
                {
                    "content": "Install dependency",
                    "status": "blocked",
                    "activeForm": "Installing dependency",
                },
                {
                    "content": "Resolve block",
                    "status": "in_progress",
                    "activeForm": "Resolving block",
                },
                {"content": "Continue work", "status": "pending", "activeForm": "Continuing work"},
            ]
        )

        assert result.success == True
        assert result.output["stats"]["blocked"] == 1

    @pytest.mark.asyncio
    async def test_adding_new_tasks(self):
        """Test adding new tasks during workflow"""
        tool = TodoWriteTool()

        # Initial tasks
        result1 = await tool.execute(
            todos=[{"content": "Task 1", "status": "in_progress", "activeForm": "T1"}]
        )

        # Add more tasks
        result2 = await tool.execute(
            todos=[
                {"content": "Task 1", "status": "completed", "activeForm": "T1"},
                {"content": "Task 2 (new)", "status": "in_progress", "activeForm": "T2"},
                {"content": "Task 3 (new)", "status": "pending", "activeForm": "T3"},
            ]
        )

        assert result2.success == True
        assert result2.output["stats"]["total"] == 3


class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.asyncio
    async def test_whitespace_content(self):
        """Test whitespace-only content is rejected"""
        tool = TodoWriteTool()

        todos = [{"content": "   ", "status": "in_progress", "activeForm": "Working"}]

        result = await tool.execute(todos=todos)

        assert result.success == False

    @pytest.mark.asyncio
    async def test_whitespace_active_form(self):
        """Test whitespace-only activeForm is rejected"""
        tool = TodoWriteTool()

        todos = [{"content": "Task", "status": "in_progress", "activeForm": "   "}]

        result = await tool.execute(todos=todos)

        assert result.success == False

    @pytest.mark.asyncio
    async def test_empty_list(self):
        """Test empty todo list - should fail since no in_progress"""
        tool = TodoWriteTool()

        result = await tool.execute(todos=[])

        assert result.success == False
        # Empty list has no in-progress item

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self):
        """Test special characters in content"""
        tool = TodoWriteTool()

        todos = [
            {
                "content": "Fix bug: `undefined` error in auth.js",
                "status": "in_progress",
                "activeForm": "Fixing bug",
            }
        ]

        result = await tool.execute(todos=todos)

        assert result.success == True

    @pytest.mark.asyncio
    async def test_long_content(self):
        """Test very long content"""
        tool = TodoWriteTool()
        long_content = "A" * 1000

        todos = [
            {"content": long_content, "status": "in_progress", "activeForm": "Working on long task"}
        ]

        result = await tool.execute(todos=todos)

        assert result.success == True

    @pytest.mark.asyncio
    async def test_unicode_content(self):
        """Test unicode content"""
        tool = TodoWriteTool()

        todos = [{"content": "修复错误 (Fix bug)", "status": "in_progress", "activeForm": "修复中"}]

        result = await tool.execute(todos=todos)

        assert result.success == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
