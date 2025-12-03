"""
Hcode-style tool execution display.

Matches the exact output format of Hcode CLI for tool calls:
- Read: Shows file path and line count
- Write: Shows file path only (no content preview)
- Edit: Shows file path with diff (old -> new)
- Bash: Shows command and full output with smart truncation
- Glob/Grep: Shows pattern and results

Features:
- Smart output truncation (head + tail with important lines preserved)
- Error extraction and highlighting
- Pattern search in outputs
- Always shows latest 5 lines of command output
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

# Import output handler for smart truncation
from ..core.output_handler import (
    OutputHandler,
    TruncatedOutput,
    ExtractedError,
    ErrorSeverity,
    OutputType,
)

# Import new UI system
from ..ui import Colors, Icons, get_palette, console as styled_console
from ..ui.theme import get_palette as get_theme_palette

# Platform detection
IS_WINDOWS = sys.platform == "win32"

# Global output handler instance
_output_handler = OutputHandler(
    head_lines=15,       # Show first 15 lines
    tail_lines=5,        # ALWAYS show last 5 lines
    max_lines=50,        # Max lines before truncation
    max_line_length=200, # Max chars per line
)


# ============================================================
# HCODE STYLE - USING MODERN THEME SYSTEM
# ============================================================

class HcodeStyle:
    """
    Hcode CLI styling constants.

    Now uses the modern UI theme system for consistent styling
    across the entire application.
    """

    def __init__(self):
        """Initialize with current theme palette."""
        self._palette = get_theme_palette()
        self._icons = Icons()
        self._update_from_theme()

    def _update_from_theme(self):
        """Update colors from the current theme."""
        palette = self._palette

        # Colors (from theme)
        self.DIM = "dim"
        self.BOLD = "bold"

        # Tool colors (from theme palette)
        self.TOOL_NAME = palette.accent
        self.TOOL_EXECUTING = palette.warning
        self.TOOL_SUCCESS = palette.success
        self.TOOL_ERROR = palette.error

        # Content colors (from theme palette)
        self.FILE_PATH = palette.info
        self.LINE_NUMBER = f"dim {palette.accent}"
        self.ADDED = palette.diff_added
        self.REMOVED = palette.diff_removed
        self.CONTEXT = palette.text_muted

        # Icons from UI system
        self.ICON_READ = self._icons.FILE
        self.ICON_WRITE = self._icons.EDIT
        self.ICON_EDIT = self._icons.EDIT
        self.ICON_BASH = self._icons.LIGHTNING
        self.ICON_GLOB = self._icons.SEARCH
        self.ICON_GREP = self._icons.SEARCH
        self.ICON_SUCCESS = self._icons.SUCCESS
        self.ICON_ERROR = self._icons.ERROR
        self.ICON_ARROW = self._icons.ARROW_RIGHT
        self.ICON_DIFF_ADD = "+"
        self.ICON_DIFF_DEL = "-"

        # Box characters from UI system (using Borders class)
        from ..ui.icons import Borders
        self.BOX_H = Borders.HORIZONTAL
        self.BOX_V = Borders.VERTICAL
        self.BOX_TL = Borders.CORNER_TL
        self.BOX_TR = Borders.CORNER_TR
        self.BOX_BL = Borders.CORNER_BL
        self.BOX_BR = Borders.CORNER_BR


# ============================================================
# TOOL DISPLAY CLASS
# ============================================================

class HcodeToolDisplay:
    """
    Hcode-style tool execution display.

    Provides consistent, clean output for all tool executions
    matching the Hcode CLI format.

    Now uses the modern UI theme system for consistent styling.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or styled_console
        self.style = HcodeStyle()
        self._icons = Icons()

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
        Display tool execution in Hcode style.

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
        """Display Read tool execution - Hcode style with smart truncation for large files"""
        file_path = arguments.get('file_path', 'unknown')

        if result.success:
            content = result.output or ""
            lines = content.split('\n') if content else []
            line_count = len(lines)

            # Hcode format: "Read file_path (X lines)"
            self.console.print(
                f"  {self.style.ICON_READ} [bold]Read[/bold] "
                f"[{self.style.FILE_PATH}]{file_path}[/] "
                f"[{self.style.DIM}]({line_count} lines)[/]"
            )

            # For very large files, show a preview with smart truncation
            if line_count > 100:
                self._show_file_preview(content, file_path)
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Read[/bold] [{self.style.FILE_PATH}]{file_path}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    def _show_file_preview(self, content: str, file_path: str, max_lines: int = 30):
        """
        Show preview of large file with smart truncation.

        Features:
        - Shows first and last lines
        - Extracts any errors/warnings
        - Detects file type for syntax highlighting hints
        """
        truncated = _output_handler.process_output(
            content,
            output_type=OutputType.FILE_CONTENT,
            extract_errors=True,
            preserve_important=True,
        )

        # Only show preview if file was truncated
        if not truncated.truncated:
            return

        self.console.print(f"    [{self.style.DIM}][Large file - showing preview][/]")

        # Show any errors found in file
        if truncated.errors_found:
            error_count = len([e for e in truncated.errors_found
                             if e.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.ERROR)])
            if error_count > 0:
                self.console.print(f"    [{self.style.TOOL_ERROR}][{error_count} potential issues found][/]")

        # Draw file preview box
        self.console.print(f"    {self.style.BOX_TL}{self.style.BOX_H * 60}{self.style.BOX_TR}")

        preview_lines = truncated.content.split('\n')[:20]  # Limit preview
        for line in preview_lines:
            display_line = line[:58] if len(line) <= 58 else line[:55] + "..."
            self.console.print(f"    {self.style.BOX_V} [{self.style.DIM}]{display_line:<58}[/] {self.style.BOX_V}")

        if len(truncated.content.split('\n')) > 20:
            self.console.print(f"    {self.style.BOX_V} [{self.style.DIM}]{'... (preview truncated)':<58}[/] {self.style.BOX_V}")

        self.console.print(f"    {self.style.BOX_BL}{self.style.BOX_H * 60}{self.style.BOX_BR}")

    # ─────────────────────────────────────────────────────────
    # WRITE TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_write(self, arguments: Dict[str, Any], result: Any):
        """Display Write tool execution - Hcode style (no content shown)"""
        file_path = arguments.get('file_path', 'unknown')
        content = arguments.get('content', '')

        if result.success:
            # Hcode format: "Wrote file_path (X bytes)"
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
        """Display Edit tool execution - Hcode style with diff"""
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
        """Show diff in Hcode style"""
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
        """Display Bash tool execution - Hcode style with output"""
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

    def _show_bash_output(self, output: str, max_lines: int = 50, show_errors: bool = True):
        """
        Show bash output with smart truncation.

        Features:
        - Always shows last 5 lines (latest output)
        - Extracts and highlights errors
        - Preserves important lines (errors, stack traces)
        - Intelligent middle truncation
        """
        # Use smart output handler
        truncated = _output_handler.process_output(
            output,
            output_type=OutputType.STDOUT,
            extract_errors=show_errors,
            preserve_important=True,
        )

        # Show error summary if errors found
        if show_errors and truncated.errors_found:
            critical_errors = [e for e in truncated.errors_found
                             if e.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.ERROR)]
            if critical_errors:
                self.console.print(f"    [{self.style.TOOL_ERROR}]=== {len(critical_errors)} Error(s) Detected ===[/]")
                for error in critical_errors[:3]:
                    error_line = str(error)[:70]
                    self.console.print(f"    [{self.style.TOOL_ERROR}]  {error_line}[/]")
                    if error.suggestion:
                        self.console.print(f"    [{self.style.DIM}]    -> {error.suggestion[:60]}[/]")
                if len(critical_errors) > 3:
                    self.console.print(f"    [{self.style.DIM}]  ... and {len(critical_errors) - 3} more errors[/]")
                self.console.print("")

        # Draw output box
        self.console.print(f"    {self.style.BOX_TL}{self.style.BOX_H * 70}{self.style.BOX_TR}")

        # Show truncation stats if truncated
        if truncated.truncated:
            stats_line = f"[{truncated.original_lines} lines total, showing {truncated.displayed_lines}]"
            self.console.print(f"    {self.style.BOX_V} [{self.style.DIM}]{stats_line:<68}[/] {self.style.BOX_V}")
            self.console.print(f"    {self.style.BOX_V}{' ' * 70}{self.style.BOX_V}")

        # Display the processed content
        content_lines = truncated.content.split('\n')
        for line in content_lines:
            # Determine line style based on content
            line_style = self.style.DIM

            # Highlight error lines
            if any(word in line.lower() for word in ['error', 'exception', 'failed', 'traceback']):
                line_style = self.style.TOOL_ERROR
            # Highlight "latest lines" section header
            elif line.startswith('--- Latest'):
                line_style = "bold cyan"
            # Highlight omission indicator
            elif line.startswith('...') and 'omitted' in line:
                line_style = "yellow"

            # Truncate long lines for display
            display_line = line[:68] if len(line) <= 68 else line[:65] + "..."

            self.console.print(f"    {self.style.BOX_V} [{line_style}]{display_line:<68}[/] {self.style.BOX_V}")

        self.console.print(f"    {self.style.BOX_BL}{self.style.BOX_H * 70}{self.style.BOX_BR}")

        # Show stack trace indicator
        if truncated.has_stack_trace:
            self.console.print(f"    [{self.style.DIM}][Stack trace detected in output][/]")

    # ─────────────────────────────────────────────────────────
    # GLOB TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_glob(self, arguments: Dict[str, Any], result: Any):
        """Display Glob tool execution - Hcode style"""
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
        """Display Grep tool execution - Hcode style with smart output handling"""
        pattern = arguments.get('pattern', '')
        path = arguments.get('path', '.')

        if result.success:
            output = result.output.strip() if result.output else ""
            matches = output.split('\n') if output else []
            match_count = len([m for m in matches if m.strip()])

            self.console.print(
                f"  {self.style.ICON_GREP} [bold]Grep[/bold] "
                f"[{self.style.TOOL_NAME}]{pattern}[/] "
                f"[{self.style.DIM}]({match_count} matches)[/]"
            )

            # Use smart truncation for large results
            if match_count > 20:
                self._show_grep_output(output, pattern, match_count)
            elif matches and match_count > 0:
                # Show first few matches for smaller results
                for m in matches[:10]:
                    if m.strip():
                        display = m[:80] + "..." if len(m) > 80 else m
                        self.console.print(f"    [{self.style.DIM}]{display}[/]")
                if match_count > 10:
                    self.console.print(f"    [{self.style.DIM}]... and {match_count - 10} more[/]")
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Grep[/bold] [{self.style.TOOL_NAME}]{pattern}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {result.error}[/]"
            )

    def _show_grep_output(self, output: str, pattern: str, total_matches: int):
        """
        Show grep output with smart truncation.

        Features:
        - Shows first matches
        - Shows last 5 matches (latest)
        - Highlights matched pattern
        """
        truncated = _output_handler.process_output(
            output,
            output_type=OutputType.STDOUT,
            extract_errors=False,
            preserve_important=False,
        )

        self.console.print(f"    [{self.style.DIM}][{total_matches} matches - showing preview][/]")

        # Draw results box
        self.console.print(f"    {self.style.BOX_TL}{self.style.BOX_H * 70}{self.style.BOX_TR}")

        result_lines = truncated.content.split('\n')
        for line in result_lines[:25]:  # Limit display
            # Highlight pattern matches
            if pattern.lower() in line.lower():
                line_style = "bold"
            elif line.startswith('---') or line.startswith('...'):
                line_style = "yellow"
            else:
                line_style = self.style.DIM

            display_line = line[:68] if len(line) <= 68 else line[:65] + "..."
            self.console.print(f"    {self.style.BOX_V} [{line_style}]{display_line:<68}[/] {self.style.BOX_V}")

        if len(result_lines) > 25:
            self.console.print(f"    {self.style.BOX_V} [{self.style.DIM}]{'... (more matches available)':<68}[/] {self.style.BOX_V}")

        self.console.print(f"    {self.style.BOX_BL}{self.style.BOX_H * 70}{self.style.BOX_BR}")

    # ─────────────────────────────────────────────────────────
    # LS TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_ls(self, arguments: Dict[str, Any], result: Any):
        """Display LS tool execution - Hcode style"""
        path = arguments.get('path', '.')

        if result.success:
            items = result.output.strip().split('\n') if result.output else []
            item_count = len([i for i in items if i.strip()])

            self.console.print(
                f"  {self._icons.FOLDER} [bold]Listed[/bold] "
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
    Hcode-style streaming text display.

    Shows AI response streaming character by character
    with thinking indicator.

    Now uses the modern UI theme system for consistent styling.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or styled_console
        self.buffer = ""
        self.is_thinking = False
        self._palette = get_theme_palette()
        self._icons = Icons()

    def start_thinking(self, message: str = "Thinking"):
        """Show thinking indicator"""
        self.is_thinking = True
        self.console.print(f"[{self._palette.text_muted}]{self._icons.THINKING} {message}...[/]", end="\r")

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
    Hcode-style status line.

    Shows model, tokens, cost, and current status at bottom.

    Now uses the modern UI theme system for consistent styling.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or styled_console
        self._palette = get_theme_palette()
        self._icons = Icons()

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
        palette = self._palette

        # Model
        if model:
            model_short = model.split('/')[-1] if '/' in model else model
            parts.append(f"[{palette.accent}]{model_short}[/]")

        # Tokens
        if tokens > 0:
            parts.append(f"[{palette.text_muted}]{tokens:,} tokens[/]")

        # Cost
        if cost > 0:
            parts.append(f"[{palette.text_muted}]${cost:.4f}[/]")

        # Status
        status_colors = {
            "ready": palette.success,
            "thinking": palette.warning,
            "executing": palette.info,
            "error": palette.error
        }
        color = status_colors.get(status, palette.text_primary)
        parts.append(f"[{color}]{status}[/]")

        # Current directory
        if cwd:
            cwd_short = os.path.basename(cwd) or cwd
            parts.append(f"[{palette.text_muted}]{self._icons.FOLDER} {cwd_short}[/]")

        return " │ ".join(parts)

    def print(self, **kwargs):
        """Print status line"""
        line = self.render(**kwargs)
        self.console.print(line)


# ============================================================
# SINGLETON INSTANCE
# ============================================================

# Global tool display instance
tool_display = HcodeToolDisplay()
streaming_display = StreamingDisplay()
status_line = StatusLineDisplay()
