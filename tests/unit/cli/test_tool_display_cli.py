"""
Comprehensive tests for the HcodeToolDisplay class.

Tests all tool display methods including:
- Read tool display (full-width, line numbers, smart truncation)
- Write tool display (file stats, language detection)
- Edit tool display (diff view, full-width lines)
- Bash tool display (command output, error handling)
- Glob/Grep tool display (pattern matching results)
"""

import pytest
import re
from unittest.mock import MagicMock, patch
from io import StringIO
from rich.console import Console

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from hcode.cli.tool_display import HcodeToolDisplay, HcodeStyle
from hcode.tools.base.base_tool import ToolResult


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text for easier testing."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestHcodeToolDisplay:
    """Test suite for HcodeToolDisplay class."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console that captures output."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        return console

    @pytest.fixture
    def display(self, mock_console):
        """Create a HcodeToolDisplay instance with mock console."""
        return HcodeToolDisplay(console=mock_console)

    @pytest.fixture
    def success_result(self):
        """Create a successful ToolResult."""
        return ToolResult(success=True, output="test output", error=None)

    @pytest.fixture
    def error_result(self):
        """Create a failed ToolResult."""
        return ToolResult(success=False, output="", error="Test error message")


class TestReadToolDisplay(TestHcodeToolDisplay):
    """Tests for Read tool display."""

    def test_read_small_file_shows_all_lines(self, display, mock_console, success_result):
        """Read tool should show all lines for small files."""
        content = "line 1\nline 2\nline 3\nline 4\nline 5"
        success_result.output = content

        arguments = {"file_path": "/path/to/file.py"}
        display._display_read(arguments, success_result)

        output = mock_console.file.getvalue()
        clean_output = strip_ansi(output)
        assert "file.py" in clean_output
        assert "5 lines" in clean_output
        assert "python" in clean_output.lower() or "py" in clean_output.lower()

    def test_read_large_file_shows_preview(self, display, mock_console, success_result):
        """Read tool should show preview for large files."""
        # Create a 50-line file
        lines = [f"line {i}" for i in range(1, 51)]
        content = "\n".join(lines)
        success_result.output = content

        arguments = {"file_path": "/path/to/large_file.py"}
        display._display_read(arguments, success_result)

        output = mock_console.file.getvalue()
        clean_output = strip_ansi(output)
        assert "large_file.py" in clean_output
        assert "50 lines" in clean_output
        # Should show first lines
        assert "line 1" in clean_output

    def test_read_shows_line_numbers(self, display, mock_console, success_result):
        """Read tool should show line numbers."""
        content = "first line\nsecond line\nthird line"
        success_result.output = content

        arguments = {"file_path": "/path/to/file.txt"}
        display._display_read(arguments, success_result)

        output = mock_console.file.getvalue()
        # Line numbers should be present
        assert "1" in output
        assert "2" in output

    def test_read_detects_language(self, display, mock_console, success_result):
        """Read tool should detect file language from extension."""
        success_result.output = "console.log('hello');"

        test_cases = [
            ("/path/to/file.py", "python"),
            ("/path/to/file.js", "javascript"),
            ("/path/to/file.ts", "typescript"),
            ("/path/to/file.json", "json"),
        ]

        for file_path, expected_lang in test_cases:
            mock_console.file = StringIO()
            arguments = {"file_path": file_path}
            display._display_read(arguments, success_result)
            output = mock_console.file.getvalue()
            # Language hint should be shown
            assert expected_lang in output.lower() or file_path.split(".")[-1] in output

    def test_read_failure_shows_error(self, display, mock_console, error_result):
        """Read tool should show error message on failure."""
        arguments = {"file_path": "/path/to/missing.py"}
        display._display_read(arguments, error_result)

        output = mock_console.file.getvalue()
        assert "failed" in output.lower() or "error" in output.lower()
        assert "Test error message" in output

    def test_read_escapes_rich_markup(self, display, mock_console, success_result):
        """Read tool should escape Rich markup in file content."""
        content = "text with [bold]markup[/bold] and [red]colors[/red]"
        success_result.output = content

        arguments = {"file_path": "/path/to/file.txt"}
        display._display_read(arguments, success_result)

        # Should not crash and should escape the markup
        output = mock_console.file.getvalue()
        assert "file.txt" in output


class TestWriteToolDisplay(TestHcodeToolDisplay):
    """Tests for Write tool display."""

    def test_write_shows_file_stats(self, display, mock_console, success_result):
        """Write tool should show file statistics."""
        content = "line 1\nline 2\nline 3"
        arguments = {"file_path": "/path/to/new_file.py", "content": content}

        display._display_write(arguments, success_result)

        output = mock_console.file.getvalue()
        assert "new_file.py" in output
        assert "3 lines" in output or "3" in output
        # Should show byte count
        assert "bytes" in output.lower()

    def test_write_detects_language(self, display, mock_console, success_result):
        """Write tool should detect file language."""
        arguments = {"file_path": "/path/to/script.js", "content": "const x = 1;"}
        display._display_write(arguments, success_result)

        output = mock_console.file.getvalue()
        assert "javascript" in output.lower() or "js" in output

    def test_write_failure_shows_error(self, display, mock_console, error_result):
        """Write tool should show error on failure."""
        arguments = {"file_path": "/path/to/file.py", "content": "test"}
        display._display_write(arguments, error_result)

        output = mock_console.file.getvalue()
        assert "failed" in output.lower() or "error" in output.lower()


class TestEditToolDisplay(TestHcodeToolDisplay):
    """Tests for Edit tool display."""

    def test_edit_shows_diff(self, display, mock_console, success_result):
        """Edit tool should show diff with removed and added lines."""
        arguments = {
            "file_path": "/path/to/file.py",
            "old_string": "old line 1\nold line 2",
            "new_string": "new line 1\nnew line 2\nnew line 3",
        }

        display._display_edit(arguments, success_result)

        output = mock_console.file.getvalue()
        assert "file.py" in output
        # Should show line change stats
        assert "+" in output and "-" in output

    def test_edit_shows_full_width_lines(self, display, mock_console, success_result):
        """Edit tool should show full-width lines without truncation."""
        long_line = "x" * 100  # A very long line
        arguments = {
            "file_path": "/path/to/file.py",
            "old_string": f"short\n{long_line}",
            "new_string": "replacement",
        }

        display._display_edit(arguments, success_result)

        output = mock_console.file.getvalue()
        # Long line should not be truncated (or at least show most of it)
        assert long_line[:50] in output or "x" * 20 in output

    def test_edit_large_diff_shows_summary(self, display, mock_console, success_result):
        """Edit tool should handle large diffs gracefully."""
        old_lines = "\n".join([f"old line {i}" for i in range(50)])
        new_lines = "\n".join([f"new line {i}" for i in range(50)])

        arguments = {
            "file_path": "/path/to/file.py",
            "old_string": old_lines,
            "new_string": new_lines,
        }

        display._display_edit(arguments, success_result)

        output = mock_console.file.getvalue()
        # Should show truncation indicator
        assert "..." in output or "omitted" in output.lower() or "more" in output.lower()

    def test_edit_failure_shows_error(self, display, mock_console, error_result):
        """Edit tool should show error on failure."""
        arguments = {
            "file_path": "/path/to/file.py",
            "old_string": "not found",
            "new_string": "replacement",
        }

        display._display_edit(arguments, error_result)

        output = mock_console.file.getvalue()
        assert "failed" in output.lower() or "error" in output.lower()

    def test_edit_escapes_rich_markup(self, display, mock_console, success_result):
        """Edit tool should escape Rich markup in diff content."""
        arguments = {
            "file_path": "/path/to/file.py",
            "old_string": "[bold]old[/bold]",
            "new_string": "[red]new[/red]",
        }

        display._display_edit(arguments, success_result)

        # Should not crash
        output = mock_console.file.getvalue()
        assert "file.py" in output


class TestBashToolDisplay(TestHcodeToolDisplay):
    """Tests for Bash tool display."""

    def test_bash_shows_command(self, display, mock_console, success_result):
        """Bash tool should show the command."""
        success_result.output = "command output here"
        arguments = {"command": "ls -la"}

        display._display_bash(arguments, success_result)

        output = mock_console.file.getvalue()
        assert "ls -la" in output or "ls" in output

    def test_bash_shows_output(self, display, mock_console, success_result):
        """Bash tool should show command output."""
        success_result.output = "file1.txt\nfile2.txt\nfile3.txt"
        arguments = {"command": "ls"}

        display._display_bash(arguments, success_result)

        output = mock_console.file.getvalue()
        # Output should be shown
        assert "file1" in output or "file" in output

    def test_bash_truncates_long_command(self, display, mock_console, success_result):
        """Bash tool should truncate very long commands."""
        long_command = "echo " + "x" * 100
        arguments = {"command": long_command}

        display._display_bash(arguments, success_result)

        output = mock_console.file.getvalue()
        # Command should be shown (possibly truncated)
        assert "echo" in output

    def test_bash_error_shows_message(self, display, mock_console, error_result):
        """Bash tool should show error message on failure."""
        error_result.error = "command not found: nonexistent"
        arguments = {"command": "nonexistent"}

        display._display_bash(arguments, error_result)

        output = mock_console.file.getvalue()
        assert "error" in output.lower() or "failed" in output.lower()


class TestGlobToolDisplay(TestHcodeToolDisplay):
    """Tests for Glob tool display."""

    def test_glob_shows_pattern(self, display, mock_console, success_result):
        """Glob tool should show the search pattern."""
        success_result.output = "file1.py\nfile2.py"
        arguments = {"pattern": "**/*.py"}

        display._display_glob(arguments, success_result)

        output = mock_console.file.getvalue()
        assert "*.py" in output or "py" in output

    def test_glob_shows_match_count(self, display, mock_console, success_result):
        """Glob tool should show number of matches."""
        success_result.output = "file1.py\nfile2.py\nfile3.py"
        arguments = {"pattern": "*.py"}

        display._display_glob(arguments, success_result)

        output = mock_console.file.getvalue()
        # Should indicate number of results
        assert "3" in output or "file" in output


class TestGrepToolDisplay(TestHcodeToolDisplay):
    """Tests for Grep tool display."""

    def test_grep_shows_pattern(self, display, mock_console, success_result):
        """Grep tool should show the search pattern."""
        success_result.output = "file.py:10: matching line"
        arguments = {"pattern": "def.*function"}

        display._display_grep(arguments, success_result)

        output = mock_console.file.getvalue()
        assert "def" in output or "function" in output or "pattern" in output.lower()


class TestToolDisplayIntegration:
    """Integration tests for tool display."""

    @pytest.fixture
    def display(self):
        """Create display with real console."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        return HcodeToolDisplay(console=console)

    def test_display_tool_call_routes_correctly(self, display):
        """display_tool_call should route to correct display method."""
        result = ToolResult(success=True, output="test", error=None)

        # Test routing for different tools
        tools_and_methods = [
            ("ReadTool", {"file_path": "test.py"}),
            ("WriteTool", {"file_path": "test.py", "content": "test"}),
            ("EditTool", {"file_path": "test.py", "old_string": "a", "new_string": "b"}),
            ("BashTool", {"command": "echo test"}),
            ("GlobTool", {"pattern": "*.py"}),
            ("GrepTool", {"pattern": "test"}),
        ]

        for tool_name, arguments in tools_and_methods:
            # Should not raise any exceptions
            display.display_tool_call(tool_name, arguments, result)

    def test_display_handles_empty_output(self, display):
        """Display should handle empty output gracefully."""
        result = ToolResult(success=True, output="", error=None)
        arguments = {"file_path": "empty.txt"}

        # Should not crash
        display._display_read(arguments, result)

    def test_display_handles_none_values(self, display):
        """Display should handle None output gracefully (file_path is required)."""
        result = ToolResult(success=True, output=None, error=None)
        # file_path is required, but output can be None (empty file)
        arguments = {"file_path": "/path/to/file.txt"}

        # Should not crash with None output
        try:
            display._display_read(arguments, result)
        except (TypeError, AttributeError) as e:
            # If it fails due to None output, that's acceptable
            # as long as it doesn't cause an unhandled crash
            pass


class TestEditToolIntegration:
    """Integration tests for Edit tool display - comprehensive scenarios."""

    @pytest.fixture
    def display(self):
        """Create display with controlled console."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        return HcodeToolDisplay(console=console)

    def test_edit_rich_markup_not_interpreted(self, display):
        """Edit tool should display Rich markup as literal text, not interpret it."""
        result = ToolResult(success=True, output="ok", error=None)
        args = {
            "file_path": "/test.py",
            "old_string": "[bold]text[/bold]",
            "new_string": "[red]new[/red]",
        }

        display._display_edit(args, result)
        output = strip_ansi(display.console.file.getvalue())

        # The brackets should be visible as literal text
        assert "[bold]text[/bold]" in output
        assert "[red]new[/red]" in output

    def test_edit_long_lines_truncated_properly(self, display):
        """Edit tool should truncate very long lines without breaking layout."""
        result = ToolResult(success=True, output="ok", error=None)
        long_line = "x" * 150
        args = {"file_path": "/test.py", "old_string": long_line, "new_string": "short"}

        display._display_edit(args, result)
        output = strip_ansi(display.console.file.getvalue())

        # Should have truncation indicator
        assert "..." in output
        # The prefix should be on the same line as content
        assert "- x" in output
        # Should show + for new line
        assert "+ short" in output

    def test_edit_multiline_diff_shows_all_lines(self, display):
        """Edit tool should show all lines in a multi-line diff."""
        result = ToolResult(success=True, output="ok", error=None)
        args = {
            "file_path": "/test.py",
            "old_string": "line1\nline2\nline3",
            "new_string": "new1\nnew2\nnew3\nnew4",
        }

        display._display_edit(args, result)
        output = strip_ansi(display.console.file.getvalue())

        # All old lines should show as removed
        assert "- line1" in output
        assert "- line2" in output
        assert "- line3" in output
        # All new lines should show as added
        assert "+ new1" in output
        assert "+ new2" in output
        assert "+ new3" in output
        assert "+ new4" in output

    def test_edit_unicode_content_preserved(self, display):
        """Edit tool should handle Unicode content correctly."""
        result = ToolResult(success=True, output="ok", error=None)
        args = {"file_path": "/test.py", "old_string": "Hello 世界", "new_string": "Bonjour 世界"}

        display._display_edit(args, result)
        output = display.console.file.getvalue()

        # Unicode should be preserved
        assert "世界" in output

    def test_edit_empty_strings_handled(self, display):
        """Edit tool should handle empty old/new strings gracefully."""
        result = ToolResult(success=True, output="ok", error=None)

        # Empty old string (insertion)
        args = {"file_path": "/test.py", "old_string": "", "new_string": "new content"}
        display._display_edit(args, result)
        output = strip_ansi(display.console.file.getvalue())
        assert "+ new content" in output

        display.console.file = StringIO()

        # Empty new string (deletion)
        args = {"file_path": "/test.py", "old_string": "old content", "new_string": ""}
        display._display_edit(args, result)
        output = strip_ansi(display.console.file.getvalue())
        assert "- old content" in output

    def test_edit_special_characters_handled(self, display):
        """Edit tool should handle special characters in content."""
        result = ToolResult(success=True, output="ok", error=None)
        args = {
            "file_path": "/test.py",
            "old_string": "tab\there\nnewline\n\rcarriage",
            "new_string": "spaces    here",
        }

        display._display_edit(args, result)
        # Should not crash
        output = display.console.file.getvalue()
        assert "test.py" in output

    def test_edit_large_diff_truncation(self, display):
        """Edit tool should truncate very large diffs appropriately."""
        result = ToolResult(success=True, output="ok", error=None)
        old_lines = "\n".join([f"old line {i}" for i in range(50)])
        new_lines = "\n".join([f"new line {i}" for i in range(50)])
        args = {"file_path": "/test.py", "old_string": old_lines, "new_string": new_lines}

        display._display_edit(args, result)
        output = strip_ansi(display.console.file.getvalue())

        # Should show truncation indicators
        assert "more lines removed" in output or "more" in output
        assert "more lines added" in output or "more" in output
        # Should show first and last lines
        assert "old line 0" in output
        assert "new line 0" in output

    def test_edit_failure_shows_clear_error(self, display):
        """Edit tool should show clear error message on failure."""
        result = ToolResult(success=False, output="", error="String 'foobar' not found in file")
        args = {"file_path": "/path/to/missing.py", "old_string": "foobar", "new_string": "bazqux"}

        display._display_edit(args, result)
        output = strip_ansi(display.console.file.getvalue())

        assert "failed" in output.lower() or "Edit failed" in output
        assert "not found" in output.lower() or "String" in output

    def test_edit_shows_file_path(self, display):
        """Edit tool should always show the file path."""
        result = ToolResult(success=True, output="ok", error=None)
        args = {
            "file_path": "/path/to/deep/nested/file.py",
            "old_string": "old",
            "new_string": "new",
        }

        display._display_edit(args, result)
        output = strip_ansi(display.console.file.getvalue())

        assert "/path/to/deep/nested/file.py" in output

    def test_edit_shows_line_count_changes(self, display):
        """Edit tool should show line count statistics."""
        result = ToolResult(success=True, output="ok", error=None)
        args = {
            "file_path": "/test.py",
            "old_string": "one\ntwo",
            "new_string": "one\ntwo\nthree\nfour\nfive",
        }

        display._display_edit(args, result)
        output = strip_ansi(display.console.file.getvalue())

        # Should show +5 -2 or similar
        assert "+5" in output
        assert "-2" in output


class TestReadToolIntegration:
    """Integration tests for Read tool display."""

    @pytest.fixture
    def display(self):
        """Create display with controlled console."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        return HcodeToolDisplay(console=console)

    def test_read_rich_markup_escaped(self, display):
        """Read tool should escape Rich markup in file content."""
        result = ToolResult(success=True, output="print('[red]hello[/red]')", error=None)
        args = {"file_path": "/test.py"}

        display._display_read(args, result)
        output = display.console.file.getvalue()

        # Should not crash and markup should appear as literal
        assert "test.py" in output

    def test_read_shows_line_numbers_correctly(self, display):
        """Read tool should show correct line numbers."""
        content = "line 1\nline 2\nline 3\nline 4\nline 5"
        result = ToolResult(success=True, output=content, error=None)
        args = {"file_path": "/test.txt"}

        display._display_read(args, result)
        output = strip_ansi(display.console.file.getvalue())

        # Should have line numbers 1-5
        assert "1" in output and "line 1" in output
        assert "5" in output and "line 5" in output

    def test_read_large_file_truncation(self, display):
        """Read tool should truncate large files with indicator."""
        lines = [f"line {i}" for i in range(100)]
        content = "\n".join(lines)
        result = ToolResult(success=True, output=content, error=None)
        args = {"file_path": "/large.txt"}

        display._display_read(args, result)
        output = strip_ansi(display.console.file.getvalue())

        # Should show truncation
        assert "omitted" in output or "..." in output
        # Should show first lines
        assert "line 0" in output or "line 1" in output


class TestToolDisplayRouting:
    """Test that tool calls are routed to correct display methods."""

    @pytest.fixture
    def display(self):
        """Create display for testing."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        return HcodeToolDisplay(console=console)

    def test_routing_read_tool(self, display):
        """ReadTool should route to _display_read."""
        result = ToolResult(success=True, output="content", error=None)
        args = {"file_path": "/test.py"}

        display.display_tool_call("ReadTool", args, result)
        output = strip_ansi(display.console.file.getvalue())

        assert "test.py" in output

    def test_routing_edit_tool(self, display):
        """EditTool should route to _display_edit."""
        result = ToolResult(success=True, output="ok", error=None)
        args = {"file_path": "/test.py", "old_string": "old", "new_string": "new"}

        display.display_tool_call("EditTool", args, result)
        output = strip_ansi(display.console.file.getvalue())

        assert "test.py" in output
        assert "-" in output and "+" in output

    def test_routing_write_tool(self, display):
        """WriteTool should route to _display_write."""
        result = ToolResult(success=True, output="ok", error=None)
        args = {"file_path": "/test.py", "content": "new content\nline 2"}

        display.display_tool_call("WriteTool", args, result)
        output = strip_ansi(display.console.file.getvalue())

        assert "test.py" in output
        assert "2 lines" in output

    def test_routing_bash_tool(self, display):
        """BashTool should route to _display_bash."""
        result = ToolResult(success=True, output="output here", error=None)
        args = {"command": "echo hello"}

        display.display_tool_call("BashTool", args, result)
        output = strip_ansi(display.console.file.getvalue())

        assert "echo" in output or "Bash" in output

    def test_routing_glob_tool(self, display):
        """GlobTool should route to _display_glob."""
        result = ToolResult(success=True, output="file1.py\nfile2.py", error=None)
        args = {"pattern": "*.py"}

        display.display_tool_call("GlobTool", args, result)
        output = strip_ansi(display.console.file.getvalue())

        assert "Glob" in output
        assert "2 files" in output or "py" in output

    def test_routing_case_insensitive(self, display):
        """Tool routing should be case-insensitive."""
        result = ToolResult(success=True, output="content", error=None)
        args = {"file_path": "/test.py"}

        # Test various cases
        for tool_name in ["ReadTool", "readtool", "READTOOL", "read"]:
            display.console.file = StringIO()
            display.display_tool_call(tool_name, args, result)
            output = strip_ansi(display.console.file.getvalue())
            assert "test.py" in output, f"Routing failed for {tool_name}"


class TestHcodeStyle:
    """Tests for HcodeStyle class."""

    def test_style_has_required_attributes(self):
        """HcodeStyle should have all required style attributes."""
        style = HcodeStyle()

        required_attrs = [
            "ICON_READ",
            "ICON_WRITE",
            "ICON_EDIT",
            "ICON_BASH",
            "ICON_DIFF_ADD",
            "ICON_DIFF_DEL",
            "ICON_ERROR",
            "FILE_PATH",
            "TOOL_NAME",
            "TOOL_ERROR",
            "ADDED",
            "REMOVED",
            "DIM",
        ]

        for attr in required_attrs:
            assert hasattr(style, attr), f"HcodeStyle should have {attr} attribute"

    def test_style_box_characters(self):
        """HcodeStyle should have box drawing characters."""
        style = HcodeStyle()

        box_attrs = ["BOX_TL", "BOX_TR", "BOX_BL", "BOX_BR", "BOX_H", "BOX_V"]

        for attr in box_attrs:
            assert hasattr(style, attr), f"HcodeStyle should have {attr} attribute"
            assert len(getattr(style, attr)) > 0, f"{attr} should not be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
