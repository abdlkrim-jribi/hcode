"""
Tests for Claude Code-style todo display.

Tests the new ClaudeCodeTodoDisplay class that renders todos
in the style shown by Claude Code.
"""

import pytest
import re
from io import StringIO
from rich.console import Console

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from hcode.ui.todo_display import (
    ClaudeCodeTodoDisplay,
    render_claude_code_todos,
    print_claude_code_todos,
    CHECKBOX_CHECKED,
    CHECKBOX_UNCHECKED,
    ICON_SPARKLE,
    ICON_BRANCH,
)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text for easier testing."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestClaudeCodeTodoDisplay:
    """Tests for ClaudeCodeTodoDisplay class."""

    @pytest.fixture
    def console(self):
        """Create a mock console that captures output."""
        return Console(file=StringIO(), force_terminal=True, width=120)

    @pytest.fixture
    def display(self, console):
        """Create a ClaudeCodeTodoDisplay instance."""
        return ClaudeCodeTodoDisplay(console=console)

    @pytest.fixture
    def sample_todos(self):
        """Create sample todo list."""
        return [
            {"content": "Task 1", "status": "completed", "activeForm": "Completing task 1"},
            {"content": "Task 2", "status": "completed", "activeForm": "Completing task 2"},
            {"content": "Task 3", "status": "in_progress", "activeForm": "Working on task 3"},
            {"content": "Task 4", "status": "pending", "activeForm": "Pending task 4"},
        ]

    def test_render_with_in_progress_task(self, display, sample_todos):
        """Should show sparkle and active task name for in-progress tasks."""
        result = display.render(sample_todos)
        output = strip_ansi(str(result))

        assert ICON_SPARKLE in output
        assert "Working on task 3" in output

    def test_render_completed_tasks_have_checked_boxes(self, display, sample_todos):
        """Completed tasks should have checked checkbox."""
        result = display.render(sample_todos)
        output = strip_ansi(str(result))

        assert CHECKBOX_CHECKED in output
        assert "Task 1" in output
        assert "Task 2" in output

    def test_render_pending_tasks_have_unchecked_boxes(self, display, sample_todos):
        """Pending tasks should have unchecked checkbox."""
        result = display.render(sample_todos)
        output = strip_ansi(str(result))

        assert CHECKBOX_UNCHECKED in output
        assert "Task 4" in output

    def test_render_shows_branch_connector(self, display, sample_todos):
        """Should show branch connector for task list."""
        result = display.render(sample_todos)
        output = strip_ansi(str(result))

        assert ICON_BRANCH in output

    def test_render_shows_keyboard_shortcuts(self, display, sample_todos):
        """Should show keyboard shortcuts when enabled."""
        result = display.render(sample_todos, show_shortcuts=True)
        output = strip_ansi(str(result))

        assert "esc to interrupt" in output
        assert "ctrl+t to hide todos" in output

    def test_render_hides_keyboard_shortcuts(self, display, sample_todos):
        """Should hide keyboard shortcuts when disabled."""
        result = display.render(sample_todos, show_shortcuts=False)
        output = strip_ansi(str(result))

        assert "esc to interrupt" not in output
        assert "ctrl+t to hide todos" not in output

    def test_render_shows_elapsed_time(self, display, sample_todos):
        """Should show elapsed time when provided."""
        result = display.render(sample_todos, elapsed_seconds=185)
        output = strip_ansi(str(result))

        assert "3m 5s" in output

    def test_render_shows_token_count(self, display, sample_todos):
        """Should show token count when provided."""
        result = display.render(sample_todos, token_count=9500)
        output = strip_ansi(str(result))

        assert "9.5k tokens" in output

    def test_render_all_completed(self, display):
        """Should show 'All tasks completed' when all done."""
        todos = [
            {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "completed", "activeForm": "Task 2"},
        ]
        result = display.render(todos)
        output = strip_ansi(str(result))

        assert "All tasks completed" in output

    def test_render_empty_todos(self, display):
        """Should return empty text for no todos."""
        result = display.render([])
        output = strip_ansi(str(result))

        assert output == ""

    def test_format_duration_seconds(self, display):
        """Should format short durations as seconds."""
        assert display.format_duration(45) == "45s"
        assert display.format_duration(5) == "5s"

    def test_format_duration_minutes(self, display):
        """Should format longer durations as minutes and seconds."""
        assert display.format_duration(125) == "2m 5s"
        assert display.format_duration(60) == "1m 0s"

    def test_format_tokens_small(self, display):
        """Should format small token counts as-is."""
        assert display.format_tokens(500) == "500"
        assert display.format_tokens(999) == "999"

    def test_format_tokens_large(self, display):
        """Should format large token counts with K suffix."""
        assert display.format_tokens(1000) == "1.0k"
        assert display.format_tokens(9500) == "9.5k"
        assert display.format_tokens(15000) == "15.0k"


class TestClaudeCodeTodoConvenienceFunctions:
    """Tests for convenience functions."""

    def test_render_claude_code_todos(self):
        """render_claude_code_todos should return Text object."""
        todos = [
            {"content": "Test task", "status": "in_progress", "activeForm": "Testing"},
        ]
        result = render_claude_code_todos(todos)
        output = strip_ansi(str(result))

        assert ICON_SPARKLE in output
        assert "Testing" in output

    def test_print_claude_code_todos(self):
        """print_claude_code_todos should print to console."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        todos = [
            {"content": "Test task", "status": "completed", "activeForm": "Testing"},
        ]

        print_claude_code_todos(todos, console=console)
        output = console.file.getvalue()

        assert "Test task" in output


class TestClaudeCodeTodoEdgeCases:
    """Test edge cases for Claude Code todo display."""

    @pytest.fixture
    def display(self):
        """Create display instance."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        return ClaudeCodeTodoDisplay(console=console)

    def test_no_in_progress_no_completed(self, display):
        """Should handle todos with only pending items."""
        todos = [
            {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
            {"content": "Task 2", "status": "pending", "activeForm": "Task 2"},
        ]
        result = display.render(todos)
        output = strip_ansi(str(result))

        assert "Ready" in output
        assert CHECKBOX_UNCHECKED in output

    def test_long_task_names(self, display):
        """Should handle long task names."""
        todos = [
            {
                "content": "This is a very long task name that might wrap or cause display issues in some terminals",
                "status": "in_progress",
                "activeForm": "Working on very long task",
            },
        ]
        result = display.render(todos)
        # Should not raise any errors
        assert result is not None

    def test_special_characters_in_task(self, display):
        """Should handle special characters in task content."""
        todos = [
            {
                "content": "Fix [brackets] and (parens)",
                "status": "completed",
                "activeForm": "Fixing",
            },
            {"content": "Handle unicode: 日本語 🎉", "status": "pending", "activeForm": "Handling"},
        ]
        result = display.render(todos)
        # Should not raise any errors
        output = str(result)
        assert "brackets" in output or "Fix" in output

    def test_missing_active_form(self, display):
        """Should use content when activeForm is missing."""
        todos = [
            {"content": "Task without activeForm", "status": "in_progress"},
        ]
        result = display.render(todos)
        output = strip_ansi(str(result))

        assert "Task without activeForm" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
