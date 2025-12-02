"""
Claude Code-style tool execution display.

Matches the exact output format of Claude Code CLI for tool calls:
- Read: Shows file path and line count
- Write: Shows file path only (no content preview)
- Edit: Shows file path with diff (old -> new)
- Bash: Shows command and full output
- Glob/Grep: Shows pattern and results
"""

import os
import sys
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.rule import Rule
from rich import box

# Platform detection
IS_WINDOWS = sys.platform == "win32"


# ============================================================
# CLAUDE CODE STYLE CONSTANTS
# ============================================================

class ClaudeCodeStyle:
    """Claude Code CLI styling constants"""

    # Colors (ANSI compatible)
    DIM = "dim"
    BOLD = "bold"

    # Tool colors
    TOOL_NAME = "cyan"
    TOOL_EXECUTING = "yellow"
    TOOL_SUCCESS = "green"
    TOOL_ERROR = "red"

    # Content colors
    FILE_PATH = "blue"
    LINE_NUMBER = "dim cyan"
    ADDED = "green"
    REMOVED = "red"
    CONTEXT = "dim"

    # Icons (ASCII for compatibility)
    ICON_READ = "📄" if not IS_WINDOWS else "[R]"
    ICON_WRITE = "📝" if not IS_WINDOWS else "[W]"
    ICON_EDIT = "✏️" if not IS_WINDOWS else "[E]"
    ICON_BASH = "⚡" if not IS_WINDOWS else "[>]"
    ICON_GLOB = "🔍" if not IS_WINDOWS else "[?]"
    ICON_GREP = "🔎" if not IS_WINDOWS else "[?]"
    ICON_SUCCESS = "✓" if not IS_WINDOWS else "[OK]"
    ICON_ERROR = "✗" if not IS_WINDOWS else "[X]"
    ICON_ARROW = "→" if not IS_WINDOWS else "->"
    ICON_DIFF_ADD = "+"
    ICON_DIFF_DEL = "-"

    # Box characters
    BOX_H = "─" if not IS_WINDOWS else "-"
    BOX_V = "│" if not IS_WINDOWS else "|"
    BOX_TL = "┌" if not IS_WINDOWS else "+"
    BOX_TR = "┐" if not IS_WINDOWS else "+"
    BOX_BL = "└" if not IS_WINDOWS else "+"
    BOX_BR = "┘" if not IS_WINDOWS else "+"


# ============================================================
# TOOL DISPLAY CLASS
# ============================================================

class ToolDisplay:
    """
    Claude Code-style tool execution display.

    Provides consistent, clean output for all tool executions
    matching the Claude Code CLI format.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.style = ClaudeCodeStyle()

    # ─────────────────────────────────────────────────────────
    # MAIN DISPLAY METHOD
    # ─────────────────────────────────────────────────────────

    def display_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Any,
        show_thinking: bool = False
    ):
        """
        Display tool execution in Claude Code style.

        Args:
            tool_name: Name of the tool (e.g., 'read', 'write', 'bash')
            arguments: Tool arguments
            result: Tool execution result (has .success, .output, .error)
            show_thinking: Whether to show verbose output
        """
        tool_name_lower = tool_name.lower().replace('tool', '')

        # Route to appropriate display method
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
        elif tool_name_lower in ['grep']:
            self._display_grep(arguments, result)
        elif tool_name_lower in ['ls']:
            self._display_ls(arguments, result)
        else:
            self._display_generic(tool_name, arguments, result)

    # ─────────────────────────────────────────────────────────
    # READ TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_read(self, arguments: Dict[str, Any], result: Any):
        """Display Read tool execution - Claude Code style"""
        file_path = arguments.get('file_path', 'unknown')

        if result.success:
            lines = result.output.split('\n') if result.output else []
            line_count = len(lines)

            # Claude Code format: "Read file_path (X lines)"
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

    # ─────────────────────────────────────────────────────────
    # WRITE TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_write(self, arguments: Dict[str, Any], result: Any):
        """Display Write tool execution - Claude Code style (no content shown)"""
        file_path = arguments.get('file_path', 'unknown')
        content = arguments.get('content', '')

        if result.success:
            # Claude Code format: "Wrote file_path (X bytes)"
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

    # ─────────────────────────────────────────────────────────
    # EDIT TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_edit(self, arguments: Dict[str, Any], result: Any):
        """Display Edit tool execution - Claude Code style with diff"""
        file_path = arguments.get('file_path', 'unknown')
        old_string = arguments.get('old_string', '')
        new_string = arguments.get('new_string', '')

        if result.success:
            # Header line
            self.console.print(
                f"  {self.style.ICON_EDIT} [bold]Edited[/bold] "
                f"[{self.style.FILE_PATH}]{file_path}[/]"
            )

            # Show diff
            self._show_diff(old_string, new_string)
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Edit[/bold] [{self.style.FILE_PATH}]{file_path}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    def _show_diff(self, old_string: str, new_string: str, max_lines: int = 10):
        """Show diff in Claude Code style"""
        old_lines = old_string.split('\n')
        new_lines = new_string.split('\n')

        # Truncate if too long
        show_old = old_lines[:max_lines]
        show_new = new_lines[:max_lines]

        # Show removed lines
        for line in show_old:
            self.console.print(
                f"    [{self.style.REMOVED}]{self.style.ICON_DIFF_DEL} {line}[/]"
            )

        if len(old_lines) > max_lines:
            self.console.print(
                f"    [{self.style.DIM}]... ({len(old_lines) - max_lines} more lines)[/]"
            )

        # Show added lines
        for line in show_new:
            self.console.print(
                f"    [{self.style.ADDED}]{self.style.ICON_DIFF_ADD} {line}[/]"
            )

        if len(new_lines) > max_lines:
            self.console.print(
                f"    [{self.style.DIM}]... ({len(new_lines) - max_lines} more lines)[/]"
            )

    # ─────────────────────────────────────────────────────────
    # BASH TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_bash(self, arguments: Dict[str, Any], result: Any):
        """Display Bash tool execution - Claude Code style with output"""
        command = arguments.get('command', '')

        # Truncate long commands for display
        display_cmd = command if len(command) <= 60 else command[:57] + "..."

        # Show command
        self.console.print(
            f"  {self.style.ICON_BASH} [bold]Bash[/bold] "
            f"[{self.style.TOOL_NAME}]{display_cmd}[/]"
        )

        if result.success:
            if result.output and result.output.strip():
                # Show output in a box
                self._show_bash_output(result.output)
            else:
                self.console.print(f"    [{self.style.DIM}](completed with no output)[/]")
        else:
            # Show error with proper formatting
            error_msg = result.error if result.error else "Command failed (no error message)"

            # For multi-line errors, show them properly
            error_lines = error_msg.strip().split('\n')
            if len(error_lines) == 1:
                self.console.print(
                    f"    [{self.style.TOOL_ERROR}]Error: {error_lines[0]}[/]"
                )
            else:
                self.console.print(f"    [{self.style.TOOL_ERROR}]Error:[/]")
                for line in error_lines[:5]:
                    self.console.print(f"    [{self.style.TOOL_ERROR}]  {line}[/]")
                if len(error_lines) > 5:
                    self.console.print(
                        f"    [{self.style.DIM}]... ({len(error_lines) - 5} more lines)[/]"
                    )

            # Also show stdout if present in failed commands (sometimes useful)
            if result.output and result.output.strip() and "stdout:" in result.output:
                self.console.print(f"    [{self.style.DIM}]Output before failure:[/]")
                self._show_bash_output(result.output, max_lines=10)

    def _show_bash_output(self, output: str, max_lines: int = 30):
        """Show bash output in Claude Code style"""
        lines = output.strip().split('\n')

        # Draw output box
        self.console.print(f"    {self.style.BOX_TL}{self.style.BOX_H * 60}{self.style.BOX_TR}")

        for i, line in enumerate(lines[:max_lines]):
            # Truncate long lines
            if len(line) > 58:
                line = line[:55] + "..."
            self.console.print(f"    {self.style.BOX_V} [{self.style.DIM}]{line:<58}[/] {self.style.BOX_V}")

        if len(lines) > max_lines:
            self.console.print(
                f"    {self.style.BOX_V} [{self.style.DIM}]... ({len(lines) - max_lines} more lines){' ' * 40}[/] {self.style.BOX_V}"
            )

        self.console.print(f"    {self.style.BOX_BL}{self.style.BOX_H * 60}{self.style.BOX_BR}")

    # ─────────────────────────────────────────────────────────
    # GLOB TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_glob(self, arguments: Dict[str, Any], result: Any):
        """Display Glob tool execution - Claude Code style"""
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

            # Show first few files
            if files and file_count > 0:
                for f in files[:5]:
                    if f.strip():
                        self.console.print(f"    [{self.style.DIM}]{f}[/]")
                if file_count > 5:
                    self.console.print(f"    [{self.style.DIM}]... and {file_count - 5} more[/]")
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Glob[/bold] [{self.style.TOOL_NAME}]{pattern}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    # ─────────────────────────────────────────────────────────
    # GREP TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_grep(self, arguments: Dict[str, Any], result: Any):
        """Display Grep tool execution - Claude Code style"""
        pattern = arguments.get('pattern', '')
        path = arguments.get('path', '.')

        if result.success:
            matches = result.output.strip().split('\n') if result.output else []
            match_count = len([m for m in matches if m.strip()])

            self.console.print(
                f"  {self.style.ICON_GREP} [bold]Grep[/bold] "
                f"[{self.style.TOOL_NAME}]{pattern}[/] "
                f"[{self.style.DIM}]({match_count} matches)[/]"
            )

            # Show first few matches
            if matches and match_count > 0:
                for m in matches[:5]:
                    if m.strip():
                        # Truncate long matches
                        display = m[:80] + "..." if len(m) > 80 else m
                        self.console.print(f"    [{self.style.DIM}]{display}[/]")
                if match_count > 5:
                    self.console.print(f"    [{self.style.DIM}]... and {match_count - 5} more[/]")
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Grep[/bold] [{self.style.TOOL_NAME}]{pattern}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    # ─────────────────────────────────────────────────────────
    # LS TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_ls(self, arguments: Dict[str, Any], result: Any):
        """Display LS tool execution - Claude Code style"""
        path = arguments.get('path', '.')

        if result.success:
            items = result.output.strip().split('\n') if result.output else []
            item_count = len([i for i in items if i.strip()])

            self.console.print(
                f"  📁 [bold]Listed[/bold] "
                f"[{self.style.FILE_PATH}]{path}[/] "
                f"[{self.style.DIM}]({item_count} items)[/]"
            )

            # Show first few items
            if items and item_count > 0:
                for item in items[:8]:
                    if item.strip():
                        self.console.print(f"    [{self.style.DIM}]{item}[/]")
                if item_count > 8:
                    self.console.print(f"    [{self.style.DIM}]... and {item_count - 8} more[/]")
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]LS[/bold] [{self.style.FILE_PATH}]{path}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    # ─────────────────────────────────────────────────────────
    # GENERIC TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_generic(self, tool_name: str, arguments: Dict[str, Any], result: Any):
        """Display generic tool execution"""
        if result.success:
            self.console.print(
                f"  [{self.style.TOOL_SUCCESS}]{self.style.ICON_SUCCESS}[/] "
                f"[bold]{tool_name}[/bold] "
                f"[{self.style.DIM}]completed[/]"
            )

            # Show brief output if available
            if result.output:
                preview = result.output[:100] + "..." if len(result.output) > 100 else result.output
                self.console.print(f"    [{self.style.DIM}]{preview}[/]")
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]{tool_name}[/bold] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    # ─────────────────────────────────────────────────────────
    # SPINNER / PROGRESS DISPLAY
    # ─────────────────────────────────────────────────────────

    def show_executing(self, tool_name: str, description: str = ""):
        """Show tool is executing (spinner style)"""
        tool_name_clean = tool_name.replace('Tool', '').replace('tool', '')
        desc = description or f"Executing {tool_name_clean}..."
        self.console.print(
            f"  [{self.style.TOOL_EXECUTING}]⋯[/] [bold]{tool_name_clean}[/bold] "
            f"[{self.style.DIM}]{desc}[/]",
            end="\r"
        )

    def clear_executing(self):
        """Clear the executing line"""
        self.console.print(" " * 80, end="\r")


# ============================================================
# STREAMING DISPLAY
# ============================================================

class StreamingDisplay:
    """
    Claude Code-style streaming text display.

    Shows AI response streaming character by character
    with thinking indicator.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.buffer = ""
        self.is_thinking = False

    def start_thinking(self, message: str = "Thinking"):
        """Show thinking indicator"""
        self.is_thinking = True
        self.console.print(f"[dim]◊ {message}...[/dim]", end="\r")

    def stop_thinking(self):
        """Clear thinking indicator"""
        if self.is_thinking:
            self.console.print(" " * 40, end="\r")
            self.is_thinking = False

    def stream_text(self, text: str):
        """Stream text to console"""
        self.stop_thinking()
        self.console.print(text, end="")
        self.buffer += text

    def end_stream(self):
        """End streaming and add newline"""
        self.console.print()
        result = self.buffer
        self.buffer = ""
        return result


# ============================================================
# STATUS LINE DISPLAY
# ============================================================

class StatusLineDisplay:
    """
    Claude Code-style status line.

    Shows model, tokens, cost, and current status at bottom.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def render(
        self,
        model: str = "",
        tokens: int = 0,
        cost: float = 0.0,
        status: str = "ready",
        cwd: str = ""
    ) -> str:
        """Render status line string"""
        parts = []

        # Model
        if model:
            model_short = model.split('/')[-1] if '/' in model else model
            parts.append(f"[cyan]{model_short}[/cyan]")

        # Tokens
        if tokens > 0:
            parts.append(f"[dim]{tokens:,} tokens[/dim]")

        # Cost
        if cost > 0:
            parts.append(f"[dim]${cost:.4f}[/dim]")

        # Status
        status_colors = {
            "ready": "green",
            "thinking": "yellow",
            "executing": "cyan",
            "error": "red"
        }
        color = status_colors.get(status, "white")
        parts.append(f"[{color}]{status}[/{color}]")

        # Current directory
        if cwd:
            cwd_short = os.path.basename(cwd) or cwd
            parts.append(f"[dim]📁 {cwd_short}[/dim]")

        return " │ ".join(parts)

    def print(self, **kwargs):
        """Print status line"""
        line = self.render(**kwargs)
        self.console.print(line)


# ============================================================
# SINGLETON INSTANCE
# ============================================================

# Global tool display instance
tool_display = ToolDisplay()
streaming_display = StreamingDisplay()
status_line = StatusLineDisplay()
