"""Tests for ClaudeCodeTodoDisplay in todo_display.py."""

import pytest
import re
from io import StringIO
from rich.console import Console

from hcode.ui.todo_display import (
    ClaudeCodeTodoDisplay,
    CHECKBOX_CHECKED,
    CHECKBOX_UNCHECKED,
    ICON_SPARKLE,
    ICON_BRANCH,
)


def strip_ansi(text: str) -> str:
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


@pytest.fixture
def display():
    console = Console(file=StringIO(), force_terminal=True, width=120)
    return ClaudeCodeTodoDisplay(console=console)


@pytest.fixture
def sample_todos():
    return [
        {"content": "Task 1", "status": "completed", "activeForm": "Completing task 1"},
        {"content": "Task 2", "status": "completed", "activeForm": "Completing task 2"},
        {"content": "Task 3", "status": "in_progress", "activeForm": "Working on task 3"},
        {"content": "Task 4", "status": "pending", "activeForm": "Pending task 4"},
    ]


def test_render_with_in_progress_task(display, sample_todos):
    result = display.render(sample_todos)
    output = strip_ansi(str(result))
    assert ICON_SPARKLE in output
    assert "Working on task 3" in output


def test_render_completed_tasks_have_checked_boxes(display, sample_todos):
    result = display.render(sample_todos)
    output = strip_ansi(str(result))
    assert CHECKBOX_CHECKED in output
    assert "Task 1" in output
    assert "Task 2" in output


def test_render_pending_tasks_have_unchecked_boxes(display, sample_todos):
    result = display.render(sample_todos)
    output = strip_ansi(str(result))
    assert CHECKBOX_UNCHECKED in output
    assert "Task 4" in output


def test_render_shows_branch_connector(display, sample_todos):
    result = display.render(sample_todos)
    output = strip_ansi(str(result))
    assert ICON_BRANCH in output


def test_render_shows_keyboard_shortcuts(display, sample_todos):
    result = display.render(sample_todos, show_shortcuts=True)
    output = strip_ansi(str(result))
    assert "esc to interrupt" in output
    assert "ctrl+t to hide todos" in output


def test_render_hides_keyboard_shortcuts(display, sample_todos):
    result = display.render(sample_todos, show_shortcuts=False)
    output = strip_ansi(str(result))
    assert "esc to interrupt" not in output


def test_render_shows_elapsed_time(display, sample_todos):
    result = display.render(sample_todos, elapsed_seconds=185)
    output = strip_ansi(str(result))
    assert "3m 5s" in output


def test_render_shows_token_count(display, sample_todos):
    result = display.render(sample_todos, token_count=9500)
    output = strip_ansi(str(result))
    assert "9.5k tokens" in output


def test_render_all_completed(display):
    todos = [
        {"content": "Task 1", "status": "completed", "activeForm": "Task 1"},
        {"content": "Task 2", "status": "completed", "activeForm": "Task 2"},
    ]
    result = display.render(todos)
    output = strip_ansi(str(result))
    assert "All tasks completed" in output


def test_render_empty_todos(display):
    result = display.render([])
    output = strip_ansi(str(result))
    assert output == ""


def test_format_duration_seconds(display):
    assert display.format_duration(45) == "45s"
    assert display.format_duration(5) == "5s"


def test_format_duration_minutes(display):
    assert display.format_duration(125) == "2m 5s"
    assert display.format_duration(60) == "1m 0s"


def test_format_tokens_small(display):
    assert display.format_tokens(500) == "500"
    assert display.format_tokens(999) == "999"


def test_format_tokens_large(display):
    assert display.format_tokens(1000) == "1.0k"
    assert display.format_tokens(9500) == "9.5k"


def test_only_pending_shows_ready(display):
    todos = [
        {"content": "Task 1", "status": "pending", "activeForm": "Task 1"},
        {"content": "Task 2", "status": "pending", "activeForm": "Task 2"},
    ]
    result = display.render(todos)
    output = strip_ansi(str(result))
    assert "Ready" in output


def test_missing_active_form_uses_content(display):
    todos = [{"content": "Task without activeForm", "status": "in_progress"}]
    result = display.render(todos)
    output = strip_ansi(str(result))
    assert "Task without activeForm" in output
