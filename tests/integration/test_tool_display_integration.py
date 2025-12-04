"""
Integration tests for tool display with output handler.

Tests that the tool display correctly uses the output handler
for smart truncation, error extraction, and formatting.
"""

import pytest
import re
from io import StringIO
from unittest.mock import Mock, patch
from rich.console import Console

from src.hcode.cli.tool_display import (
    HcodeToolDisplay,
    HcodeStyle,
    StreamingDisplay,
    StatusLineDisplay,
    _output_handler,
)
from src.hcode.core.output_handler import OutputHandler, OutputType


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text for easier assertion"""
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_pattern.sub("", text)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def mock_console():
    """Create a mock console for testing output"""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=100)
    return console, output


@pytest.fixture
def tool_display(mock_console):
    """Create tool display with mock console"""
    console, _ = mock_console
    return HcodeToolDisplay(console=console)


@pytest.fixture
def mock_result():
    """Factory for creating mock tool results"""

    class MockResult:
        def __init__(self, success=True, output="", error=None):
            self.success = success
            self.output = output
            self.error = error

    return MockResult


# ============================================================
# OUTPUT HANDLER CONFIGURATION TESTS
# ============================================================


class TestOutputHandlerConfiguration:
    """Tests for output handler configuration"""

    def test_global_handler_exists(self):
        """Global output handler should be configured"""
        assert _output_handler is not None
        assert isinstance(_output_handler, OutputHandler)

    def test_handler_tail_lines(self):
        """Handler should always show last 5 lines"""
        assert _output_handler.tail_lines == 5

    def test_handler_head_lines(self):
        """Handler should show first 15 lines"""
        assert _output_handler.head_lines == 15

    def test_handler_max_lines(self):
        """Handler should have max_lines configured"""
        assert _output_handler.max_lines == 50


# ============================================================
# BASH DISPLAY TESTS
# ============================================================


class TestBashDisplay:
    """Tests for bash command output display"""

    def test_bash_small_output(self, tool_display, mock_result, mock_console):
        """Small bash output should display completely"""
        _, output = mock_console
        result = mock_result(success=True, output="Line 1\nLine 2\nLine 3")

        tool_display._display_bash({"command": "echo test"}, result)

        displayed = output.getvalue()
        assert "Bash" in displayed
        assert "echo test" in displayed

    def test_bash_large_output_truncation(self, tool_display, mock_result, mock_console):
        """Large bash output should be truncated"""
        _, output = mock_console
        large_output = "\n".join([f"Build step {i}" for i in range(200)])
        result = mock_result(success=True, output=large_output)

        tool_display._display_bash({"command": "npm run build"}, result)

        displayed = output.getvalue()
        # Should show truncation indicator
        assert "lines" in displayed.lower() or "omitted" in displayed.lower()
        # Should show latest lines section
        assert "Latest" in displayed or "Build step 199" in displayed

    def test_bash_error_extraction(self, tool_display, mock_result, mock_console):
        """Bash output with errors should highlight them"""
        _, output = mock_console
        error_output = "\n".join(
            [
                "Starting build...",
                "Compiling...",
                "ERROR: Module not found: 'missing'",
                "Build failed",
            ]
        )
        result = mock_result(success=True, output=error_output)

        tool_display._display_bash({"command": "npm run build"}, result)

        displayed = output.getvalue()
        # Should detect and show error
        assert "Error" in displayed or "ERROR" in displayed

    def test_bash_command_truncation(self, tool_display, mock_result, mock_console):
        """Long commands should be truncated in display"""
        _, output = mock_console
        long_command = "a" * 100
        result = mock_result(success=True, output="Done")

        tool_display._display_bash({"command": long_command}, result)

        displayed = output.getvalue()
        # Command should be truncated with ...
        assert "..." in displayed

    def test_bash_failed_command(self, tool_display, mock_result, mock_console):
        """Failed command should show error"""
        _, output = mock_console
        result = mock_result(success=False, output="", error="Command not found: xyz")

        tool_display._display_bash({"command": "xyz"}, result)

        displayed = output.getvalue()
        assert "Error" in displayed or "failed" in displayed.lower()

    def test_bash_no_output(self, tool_display, mock_result, mock_console):
        """Command with no output should indicate completion"""
        _, output = mock_console
        result = mock_result(success=True, output="")

        tool_display._display_bash({"command": "mkdir test"}, result)

        displayed = output.getvalue()
        assert "no output" in displayed.lower() or "completed" in displayed.lower()


# ============================================================
# READ DISPLAY TESTS
# ============================================================


class TestReadDisplay:
    """Tests for file read display"""

    def test_read_small_file(self, tool_display, mock_result, mock_console):
        """Small file should show line count"""
        _, output = mock_console
        result = mock_result(success=True, output="line 1\nline 2\nline 3")

        tool_display._display_read({"file_path": "/path/to/file.py"}, result)

        displayed = strip_ansi(output.getvalue())
        assert "Read" in displayed
        assert "file.py" in displayed
        assert "3 lines" in displayed

    def test_read_large_file_preview(self, tool_display, mock_result, mock_console):
        """Large file should show preview"""
        _, output = mock_console
        large_content = "\n".join([f"Line {i}" for i in range(200)])
        result = mock_result(success=True, output=large_content)

        tool_display._display_read({"file_path": "/path/to/large_file.py"}, result)

        displayed = strip_ansi(output.getvalue())
        assert "200 lines" in displayed

    def test_read_failed(self, tool_display, mock_result, mock_console):
        """Failed read should show error"""
        _, output = mock_console
        result = mock_result(success=False, output=None, error="File not found")

        tool_display._display_read({"file_path": "/path/to/missing.py"}, result)

        displayed = output.getvalue()
        assert "failed" in displayed.lower() or "not found" in displayed.lower()


# ============================================================
# GREP DISPLAY TESTS
# ============================================================


class TestGrepDisplay:
    """Tests for grep results display"""

    def test_grep_small_results(self, tool_display, mock_result, mock_console):
        """Small grep results should display completely"""
        _, output = mock_console
        result = mock_result(success=True, output="file1.py:10: match\nfile2.py:20: match")

        tool_display._display_grep({"pattern": "match", "path": "."}, result)

        displayed = strip_ansi(output.getvalue())
        assert "Grep" in displayed
        assert "2 matches" in displayed

    def test_grep_large_results_truncation(self, tool_display, mock_result, mock_console):
        """Large grep results should be truncated"""
        _, output = mock_console
        large_results = "\n".join([f"file{i}.py:10: match" for i in range(100)])
        result = mock_result(success=True, output=large_results)

        tool_display._display_grep({"pattern": "match"}, result)

        displayed = strip_ansi(output.getvalue())
        assert "100 matches" in displayed
        # Should show preview indicator for large results
        assert "preview" in displayed.lower() or "..." in displayed

    def test_grep_no_matches(self, tool_display, mock_result, mock_console):
        """No matches should be indicated"""
        _, output = mock_console
        result = mock_result(success=True, output="")

        tool_display._display_grep({"pattern": "notfound"}, result)

        displayed = strip_ansi(output.getvalue())
        assert "0 matches" in displayed


# ============================================================
# GLOB DISPLAY TESTS
# ============================================================


class TestGlobDisplay:
    """Tests for glob results display"""

    def test_glob_results(self, tool_display, mock_result, mock_console):
        """Glob results should show file count"""
        _, output = mock_console
        result = mock_result(success=True, output="file1.py\nfile2.py\nfile3.py")

        tool_display._display_glob({"pattern": "*.py", "path": "."}, result)

        displayed = strip_ansi(output.getvalue())
        assert "Glob" in displayed
        assert "3 files" in displayed

    def test_glob_many_results(self, tool_display, mock_result, mock_console):
        """Many glob results should be truncated"""
        _, output = mock_console
        many_files = "\n".join([f"file{i}.py" for i in range(20)])
        result = mock_result(success=True, output=many_files)

        tool_display._display_glob({"pattern": "**/*.py"}, result)

        displayed = strip_ansi(output.getvalue())
        assert "20 files" in displayed
        # Should show "and X more" indicator
        assert "more" in displayed.lower()


# ============================================================
# EDIT DISPLAY TESTS
# ============================================================


class TestEditDisplay:
    """Tests for edit display"""

    def test_edit_success(self, tool_display, mock_result, mock_console):
        """Successful edit should show file path"""
        _, output = mock_console
        result = mock_result(success=True, output="Edited")

        tool_display._display_edit(
            {"file_path": "/path/to/file.py", "old_string": "old", "new_string": "new"}, result
        )

        displayed = output.getvalue()
        assert "Edited" in displayed or "Edit" in displayed
        assert "file.py" in displayed

    def test_edit_diff_display(self, tool_display, mock_result, mock_console):
        """Edit should show diff (old -> new)"""
        _, output = mock_console
        result = mock_result(success=True, output="")

        tool_display._display_edit(
            {"file_path": "/path/to/file.py", "old_string": "old_value", "new_string": "new_value"},
            result,
        )

        displayed = output.getvalue()
        # Should show removed (-) and added (+) indicators
        assert "-" in displayed or "+" in displayed


# ============================================================
# WRITE DISPLAY TESTS
# ============================================================


class TestWriteDisplay:
    """Tests for write display"""

    def test_write_success(self, tool_display, mock_result, mock_console):
        """Successful write should show file path and size"""
        _, output = mock_console
        result = mock_result(success=True, output="")

        tool_display._display_write(
            {"file_path": "/path/to/file.py", "content": "Hello World"}, result
        )

        displayed = output.getvalue()
        assert "Wrote" in displayed or "Write" in displayed
        assert "file.py" in displayed
        assert "bytes" in displayed.lower()


# ============================================================
# GENERIC DISPLAY TESTS
# ============================================================


class TestGenericDisplay:
    """Tests for generic tool display"""

    def test_generic_success(self, tool_display, mock_result, mock_console):
        """Generic success should show completion"""
        _, output = mock_console
        result = mock_result(success=True, output="Done")

        tool_display._display_generic("CustomTool", {"param": "value"}, result)

        displayed = output.getvalue()
        assert "CustomTool" in displayed
        assert "completed" in displayed.lower()

    def test_generic_failure(self, tool_display, mock_result, mock_console):
        """Generic failure should show error"""
        _, output = mock_console
        result = mock_result(success=False, output=None, error="Something went wrong")

        tool_display._display_generic("CustomTool", {}, result)

        displayed = output.getvalue()
        assert "failed" in displayed.lower()


# ============================================================
# STYLE TESTS
# ============================================================


class TestHcodeStyle:
    """Tests for HcodeStyle constants"""

    def test_style_colors_defined(self):
        """All color constants should be defined"""
        assert HcodeStyle.DIM is not None
        assert HcodeStyle.BOLD is not None
        assert HcodeStyle.TOOL_NAME is not None
        assert HcodeStyle.TOOL_ERROR is not None
        assert HcodeStyle.TOOL_SUCCESS is not None

    def test_style_icons_defined(self):
        """All icon constants should be defined"""
        assert HcodeStyle.ICON_READ is not None
        assert HcodeStyle.ICON_WRITE is not None
        assert HcodeStyle.ICON_EDIT is not None
        assert HcodeStyle.ICON_BASH is not None
        assert HcodeStyle.ICON_GLOB is not None

    def test_style_box_chars_defined(self):
        """Box drawing characters should be defined"""
        assert HcodeStyle.BOX_H is not None
        assert HcodeStyle.BOX_V is not None
        assert HcodeStyle.BOX_TL is not None
        assert HcodeStyle.BOX_TR is not None
        assert HcodeStyle.BOX_BL is not None
        assert HcodeStyle.BOX_BR is not None


# ============================================================
# STREAMING DISPLAY TESTS
# ============================================================


class TestStreamingDisplay:
    """Tests for streaming display"""

    def test_streaming_buffer(self):
        """Streaming should buffer text"""
        display = StreamingDisplay()

        display.stream_text("Hello ")
        display.stream_text("World")

        result = display.end_stream()
        assert result == "Hello World"

    def test_thinking_indicator(self, mock_console):
        """Thinking indicator should show and clear"""
        console, output = mock_console
        display = StreamingDisplay(console=console)

        display.start_thinking("Processing")
        assert display.is_thinking is True

        display.stop_thinking()
        assert display.is_thinking is False


# ============================================================
# STATUS LINE TESTS
# ============================================================


class TestStatusLineDisplay:
    """Tests for status line display"""

    def test_status_line_render(self):
        """Status line should render all components"""
        display = StatusLineDisplay()

        line = display.render(
            model="claude-3", tokens=1000, cost=0.05, status="ready", cwd="/home/user/project"
        )

        assert "claude-3" in line
        assert "1,000" in line
        assert "$0.05" in line
        assert "ready" in line

    def test_status_line_empty(self):
        """Status line should handle empty values"""
        display = StatusLineDisplay()
        line = display.render()

        assert isinstance(line, str)


# ============================================================
# TOOL CALL ROUTING TESTS
# ============================================================


class TestToolCallRouting:
    """Tests for tool call routing"""

    def test_route_read(self, tool_display, mock_result, mock_console):
        """Read tool should route correctly"""
        _, output = mock_console
        result = mock_result(success=True, output="content")

        tool_display.display_tool_call("Read", {"file_path": "/test.py"}, result)

        displayed = output.getvalue()
        assert "Read" in displayed

    def test_route_bash(self, tool_display, mock_result, mock_console):
        """Bash tool should route correctly"""
        _, output = mock_console
        result = mock_result(success=True, output="output")

        tool_display.display_tool_call("Bash", {"command": "ls"}, result)

        displayed = output.getvalue()
        assert "Bash" in displayed

    def test_route_unknown_tool(self, tool_display, mock_result, mock_console):
        """Unknown tool should use generic display"""
        _, output = mock_console
        result = mock_result(success=True, output="result")

        tool_display.display_tool_call("UnknownTool", {"param": "value"}, result)

        displayed = output.getvalue()
        assert "UnknownTool" in displayed


# ============================================================
# INTEGRATION WITH OUTPUT HANDLER
# ============================================================


class TestOutputHandlerIntegration:
    """Tests for integration between tool display and output handler"""

    def test_bash_uses_output_handler(self, tool_display, mock_result, mock_console):
        """Bash display should use output handler for processing"""
        _, output = mock_console

        # Create output with error that should be extracted
        error_output = "\n".join(
            [
                "Starting...",
                "Processing...",
                "Traceback (most recent call last):",
                '  File "test.py", line 10, in main',
                "    raise ValueError('test')",
                "ValueError: test",
            ]
        )

        result = mock_result(success=True, output=error_output)

        tool_display._display_bash({"command": "python test.py"}, result)

        displayed = output.getvalue()
        # Should detect error
        assert "Error" in displayed or "ValueError" in displayed

    def test_large_output_shows_latest_lines(self, tool_display, mock_result, mock_console):
        """Large output should always show latest lines"""
        _, output = mock_console

        # Create 200 line output
        large_output = "\n".join([f"Step {i}" for i in range(1, 201)])
        result = mock_result(success=True, output=large_output)

        tool_display._display_bash({"command": "long-command"}, result)

        displayed = strip_ansi(output.getvalue())
        # Should show the very last line
        assert "Step 200" in displayed
        # Should indicate truncation
        assert "Latest" in displayed or "lines" in displayed.lower()
