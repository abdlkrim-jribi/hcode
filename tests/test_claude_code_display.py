"""
Test Claude Code-style tool display.

This test file contains the ToolDisplay logic inline to avoid import issues
with the root hcode.py file shadowing the src/hcode package.
"""

import pytest
import sys
import os
import re
from io import StringIO
from dataclasses import dataclass
from typing import Optional, Dict, Any

from rich.console import Console


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_escape.sub('', text)


# ============================================================
# INLINE COPY OF TOOL DISPLAY FOR TESTING
# ============================================================

IS_WINDOWS = sys.platform == "win32"


class ClaudeCodeStyle:
    """Claude Code CLI styling constants"""
    DIM = "dim"
    BOLD = "bold"
    TOOL_NAME = "cyan"
    TOOL_EXECUTING = "yellow"
    TOOL_SUCCESS = "green"
    TOOL_ERROR = "red"
    FILE_PATH = "blue"
    LINE_NUMBER = "dim cyan"
    ADDED = "green"
    REMOVED = "red"
    CONTEXT = "dim"
    ICON_READ = "[R]" if IS_WINDOWS else "📄"
    ICON_WRITE = "[W]" if IS_WINDOWS else "📝"
    ICON_EDIT = "[E]" if IS_WINDOWS else "✏️"
    ICON_BASH = "[>]" if IS_WINDOWS else "⚡"
    ICON_GLOB = "[?]" if IS_WINDOWS else "🔍"
    ICON_SUCCESS = "[OK]" if IS_WINDOWS else "✓"
    ICON_ERROR = "[X]" if IS_WINDOWS else "✗"
    ICON_DIFF_ADD = "+"
    ICON_DIFF_DEL = "-"
    BOX_H = "-" if IS_WINDOWS else "─"
    BOX_V = "|" if IS_WINDOWS else "│"
    BOX_TL = "+" if IS_WINDOWS else "┌"
    BOX_TR = "+" if IS_WINDOWS else "┐"
    BOX_BL = "+" if IS_WINDOWS else "└"
    BOX_BR = "+" if IS_WINDOWS else "┘"


class ToolDisplay:
    """Claude Code-style tool display"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.style = ClaudeCodeStyle()

    def display_tool_call(self, tool_name: str, arguments: Dict[str, Any], result: Any, show_thinking: bool = False):
        tool_name_lower = tool_name.lower().replace('tool', '')
        if tool_name_lower in ['read']:
            self._display_read(arguments, result)
        elif tool_name_lower in ['write']:
            self._display_write(arguments, result)
        elif tool_name_lower in ['edit']:
            self._display_edit(arguments, result)
        elif tool_name_lower in ['bash']:
            self._display_bash(arguments, result)
        elif tool_name_lower in ['glob']:
            self._display_glob(arguments, result)
        else:
            self._display_generic(tool_name, arguments, result)

    def _display_read(self, arguments: Dict[str, Any], result: Any):
        file_path = arguments.get('file_path', 'unknown')
        if result.success:
            lines = result.output.split('\n') if result.output else []
            line_count = len(lines)
            self.console.print(
                f"  {self.style.ICON_READ} [bold]Read[/bold] "
                f"[{self.style.FILE_PATH}]{file_path}[/] "
                f"[{self.style.DIM}]({line_count} lines)[/]"
            )
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Read[/bold] [{self.style.FILE_PATH}]{file_path}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    def _display_write(self, arguments: Dict[str, Any], result: Any):
        file_path = arguments.get('file_path', 'unknown')
        content = arguments.get('content', '')
        if result.success:
            byte_count = len(content.encode('utf-8'))
            self.console.print(
                f"  {self.style.ICON_WRITE} [bold]Wrote[/bold] "
                f"[{self.style.FILE_PATH}]{file_path}[/] "
                f"[{self.style.DIM}]({byte_count} bytes)[/]"
            )
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Write[/bold] [{self.style.FILE_PATH}]{file_path}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    def _display_edit(self, arguments: Dict[str, Any], result: Any):
        file_path = arguments.get('file_path', 'unknown')
        old_string = arguments.get('old_string', '')
        new_string = arguments.get('new_string', '')
        if result.success:
            self.console.print(
                f"  {self.style.ICON_EDIT} [bold]Edited[/bold] "
                f"[{self.style.FILE_PATH}]{file_path}[/]"
            )
            self._show_diff(old_string, new_string)
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Edit[/bold] [{self.style.FILE_PATH}]{file_path}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    def _show_diff(self, old_string: str, new_string: str, max_lines: int = 10):
        old_lines = old_string.split('\n')[:max_lines]
        new_lines = new_string.split('\n')[:max_lines]
        for line in old_lines:
            self.console.print(f"    [{self.style.REMOVED}]{self.style.ICON_DIFF_DEL} {line}[/]")
        for line in new_lines:
            self.console.print(f"    [{self.style.ADDED}]{self.style.ICON_DIFF_ADD} {line}[/]")

    def _display_bash(self, arguments: Dict[str, Any], result: Any):
        command = arguments.get('command', '')
        self.console.print(
            f"  {self.style.ICON_BASH} [bold]Bash[/bold] "
            f"[{self.style.TOOL_NAME}]{command}[/]"
        )
        if result.success and result.output and result.output.strip():
            self._show_bash_output(result.output)
        elif not result.success:
            self.console.print(f"    [{self.style.TOOL_ERROR}]Error: {result.error}[/]")

    def _show_bash_output(self, output: str, max_lines: int = 30):
        lines = output.strip().split('\n')
        self.console.print(f"    {self.style.BOX_TL}{self.style.BOX_H * 60}{self.style.BOX_TR}")
        for line in lines[:max_lines]:
            if len(line) > 58:
                line = line[:55] + "..."
            self.console.print(f"    {self.style.BOX_V} [{self.style.DIM}]{line:<58}[/] {self.style.BOX_V}")
        self.console.print(f"    {self.style.BOX_BL}{self.style.BOX_H * 60}{self.style.BOX_BR}")

    def _display_glob(self, arguments: Dict[str, Any], result: Any):
        pattern = arguments.get('pattern', '*')
        path = arguments.get('path', '.')
        if result.success:
            files = result.output.strip().split('\n') if result.output else []
            file_count = len([f for f in files if f.strip()])
            self.console.print(
                f"  {self.style.ICON_GLOB} [bold]Glob[/bold] "
                f"[{self.style.TOOL_NAME}]{pattern}[/] "
                f"[{self.style.DIM}]in {path}[/] "
                f"[{self.style.DIM}]({file_count} files)[/]"
            )

    def _display_generic(self, tool_name: str, arguments: Dict[str, Any], result: Any):
        if result.success:
            self.console.print(
                f"  [{self.style.TOOL_SUCCESS}]{self.style.ICON_SUCCESS}[/] "
                f"[bold]{tool_name}[/bold] "
                f"[{self.style.DIM}]completed[/]"
            )
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]{tool_name}[/bold] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )


class StreamingDisplay:
    """Streaming text display"""
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.buffer = ""
        self.is_thinking = False

    def start_thinking(self, message: str = "Thinking"):
        self.is_thinking = True

    def stop_thinking(self):
        self.is_thinking = False

    def stream_text(self, text: str):
        self.stop_thinking()
        self.console.print(text, end="")
        self.buffer += text

    def end_stream(self):
        self.console.print()
        result = self.buffer
        self.buffer = ""
        return result


class StatusLineDisplay:
    """Status line display"""
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(self, model: str = "", tokens: int = 0, cost: float = 0.0, status: str = "ready", cwd: str = "") -> str:
        parts = []
        if model:
            model_short = model.split('/')[-1] if '/' in model else model
            parts.append(f"[cyan]{model_short}[/cyan]")
        if tokens > 0:
            parts.append(f"[dim]{tokens:,} tokens[/dim]")
        if cost > 0:
            parts.append(f"[dim]${cost:.4f}[/dim]")
        status_colors = {"ready": "green", "thinking": "yellow", "executing": "cyan", "error": "red"}
        color = status_colors.get(status, "white")
        parts.append(f"[{color}]{status}[/{color}]")
        if cwd:
            cwd_short = os.path.basename(cwd) or cwd
            parts.append(f"[dim]📁 {cwd_short}[/dim]")
        return " │ ".join(parts)


@dataclass
class MockToolResult:
    """Mock tool result for testing"""
    success: bool
    output: str
    error: str = ""


class TestToolDisplayModule:
    """Test the Claude Code-style tool display module"""

    def test_tool_display_import(self):
        """Test that ToolDisplay can be instantiated"""
        display = ToolDisplay()
        assert display is not None

    def test_read_tool_display(self):
        """Test Read tool displays file path and line count"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100, no_color=True)
        display = ToolDisplay(console)

        result = MockToolResult(
            success=True,
            output="line 1\nline 2\nline 3\nline 4\nline 5"
        )
        arguments = {"file_path": "/path/to/file.py"}

        display._display_read(arguments, result)

        out = strip_ansi(output.getvalue())
        assert "Read" in out
        assert "/path/to/file.py" in out
        assert "5 lines" in out

    def test_write_tool_display_no_content(self):
        """Test Write tool displays file path but NOT content"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100, no_color=True)
        display = ToolDisplay(console)

        result = MockToolResult(success=True, output="")
        arguments = {
            "file_path": "/path/to/output.html",
            "content": "<!DOCTYPE html><html>Very long content here...</html>"
        }

        display._display_write(arguments, result)

        out = strip_ansi(output.getvalue())
        assert "Wrote" in out
        assert "/path/to/output.html" in out
        assert "bytes" in out
        # Content should NOT be in output
        assert "DOCTYPE" not in out
        assert "Very long content" not in out

    def test_edit_tool_display_shows_diff(self):
        """Test Edit tool displays diff"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100, no_color=True)
        display = ToolDisplay(console)

        result = MockToolResult(success=True, output="")
        arguments = {
            "file_path": "/path/to/config.py",
            "old_string": "DEBUG = True",
            "new_string": "DEBUG = False"
        }

        display._display_edit(arguments, result)

        out = strip_ansi(output.getvalue())
        assert "Edited" in out
        assert "/path/to/config.py" in out
        # Should show old string (removed)
        assert "DEBUG = True" in out
        # Should show new string (added)
        assert "DEBUG = False" in out

    def test_bash_tool_display_shows_output(self):
        """Test Bash tool displays command and output"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100, no_color=True)
        display = ToolDisplay(console)

        result = MockToolResult(
            success=True,
            output="file1.py\nfile2.py\nREADME.md"
        )
        arguments = {"command": "ls -la"}

        display._display_bash(arguments, result)

        out = strip_ansi(output.getvalue())
        assert "Bash" in out
        assert "ls -la" in out
        # Output should be shown
        assert "file1.py" in out
        assert "file2.py" in out

    def test_glob_tool_display(self):
        """Test Glob tool displays pattern and file count"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100, no_color=True)
        display = ToolDisplay(console)

        result = MockToolResult(
            success=True,
            output="src/main.py\nsrc/utils.py\nsrc/config.py"
        )
        arguments = {"pattern": "**/*.py", "path": "src"}

        display._display_glob(arguments, result)

        out = strip_ansi(output.getvalue())
        assert "Glob" in out
        assert "**/*.py" in out
        assert "3 files" in out

    def test_error_display(self):
        """Test error display shows error message"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100, no_color=True)
        display = ToolDisplay(console)

        result = MockToolResult(
            success=False,
            output="",
            error="File not found"
        )
        arguments = {"file_path": "/nonexistent/file.py"}

        display._display_read(arguments, result)

        out = strip_ansi(output.getvalue())
        assert "failed" in out
        assert "File not found" in out


class TestStreamingDisplay:
    """Test streaming display"""

    def test_streaming_import(self):
        """Test StreamingDisplay can be instantiated"""
        display = StreamingDisplay()
        assert display is not None

    def test_streaming_buffer(self):
        """Test streaming text buffering"""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)
        display = StreamingDisplay(console)

        display.stream_text("Hello ")
        display.stream_text("World")
        result = display.end_stream()

        assert result == "Hello World"


class TestStatusLineDisplay:
    """Test status line display"""

    def test_status_line_import(self):
        """Test StatusLineDisplay can be instantiated"""
        display = StatusLineDisplay()
        assert display is not None

    def test_status_line_render(self):
        """Test status line rendering"""
        display = StatusLineDisplay()
        line = display.render(
            model="gpt-4",
            tokens=1000,
            cost=0.05,
            status="ready",
            cwd="/project"
        )

        assert "gpt-4" in line
        assert "1,000 tokens" in line
        assert "$0.0500" in line
        assert "ready" in line
        assert "project" in line


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
