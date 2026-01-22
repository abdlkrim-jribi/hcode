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
from typing import Optional, Dict, Any

from rich.console import Console
from rich.markup import escape

# Import output handler for smart truncation
from hcode.core.output_handler import (
    OutputHandler,
    ErrorSeverity,
    OutputType,
)
# Import new UI system
from hcode.ui import Icons, console as styled_console
from hcode.ui.theme import get_palette as get_theme_palette

# Platform detection
IS_WINDOWS = sys.platform == "win32"

# Global output handler instance
_output_handler = OutputHandler(
    head_lines=15,  # Show first 15 lines
    tail_lines=5,  # ALWAYS show last 5 lines
    max_lines=50,  # Max lines before truncation
    max_line_length=200,  # Max chars per line
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

    In normal mode: Claude Code-style minimal output (tool name + key info only)
    In debug mode: Full verbose output with boxes and details

    Now uses the modern UI theme system for consistent styling.
    """

    def __init__(self, console: Optional[Console] = None, debug_mode: bool = False):
        self.console = console or styled_console
        self.style = HcodeStyle()
        self._icons = Icons()
        self.debug_mode = debug_mode

    # ─────────────────────────────────────────────────────────
    # MAIN DISPLAY METHOD
    # ─────────────────────────────────────────────────────────

    def display_tool_call(
        self, tool_name: str, arguments: Dict[str, Any], result: Any, show_thinking: bool = False
    ):
        """
        Display tool execution in Hcode style.

        Args:
            tool_name: Name of the tool (e.g., 'read', 'write', 'bash')
            arguments: Tool arguments
            result: Tool execution result (has .success, .output, .error)
            show_thinking: Whether to show verbose output
        """
        tool_name_lower = tool_name.lower().replace("tool", "")

        # Route to appropriate display method
        if tool_name_lower in ["read"]:
            self._display_read(arguments, result)
        elif tool_name_lower in ["write"]:
            self._display_write(arguments, result)
        elif tool_name_lower in ["edit"]:
            self._display_edit(arguments, result)
        elif tool_name_lower in ["multiedit", "multiedittool"]:
            self._display_multiedit(arguments, result)
        elif tool_name_lower in ["bash"]:
            self._display_bash(arguments, result)
        elif tool_name_lower in ["glob"]:
            self._display_glob(arguments, result)
        elif tool_name_lower in ["grep"]:
            self._display_grep(arguments, result)
        elif tool_name_lower in ["ls"]:
            self._display_ls(arguments, result)
        else:
            self._display_generic(tool_name, arguments, result)

    # ─────────────────────────────────────────────────────────
    # READ TOOL DISPLAY - Claude Code Style
    # ─────────────────────────────────────────────────────────

    def _display_read(self, arguments: Dict[str, Any], result: Any):
        """Display Read tool execution - Claude Code style with full-width lines"""
        file_path = arguments.get("file_path", "unknown")
        from pathlib import Path

        # Get file extension for syntax hint
        ext = Path(file_path).suffix.lower() if file_path else ""
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".html": "html",
            ".css": "css",
            ".sh": "bash",
            ".bash": "bash",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".sql": "sql",
            ".xml": "xml",
            ".toml": "toml",
            ".ini": "ini",
        }
        lang = lang_map.get(ext, "")

        if result.success:
            content = result.output or ""
            lines = content.split("\n") if content else []
            line_count = len(lines)

            # Claude Code style header: ⎯⎯ Read: file_path ⎯⎯

            self.console.print(f"\n  [bold cyan]{'─' * 3} Read: {escape(file_path)} {'─' * 3}[/bold cyan]")
            self.console.print(f"  [dim]{line_count} lines{f' • {lang}' if lang else ''}[/dim]")

            # Show preview for all files (not just large ones)
            self._show_file_preview_enhanced(content, file_path, lang)
        else:
            self.console.print(
                f"\n  [bold red]✗ Read failed:[/bold red] [{self.style.FILE_PATH}]{file_path}[/]"
            )
            self.console.print(f"    [red]{escape(str(result.error))}[/red]")

    def _show_file_preview_enhanced(
        self, content: str, file_path: str, lang: str = "", max_preview_lines: int = 25
    ):
        """
        Show file preview - Claude Code style with full-width lines.

        Features:
        - Full terminal width (no truncation)
        - Syntax-aware display
        - Smart preview for large files
        - Line numbers for context
        """

        lines = content.split("\n") if content else []
        total_lines = len(lines)

        # Determine how many lines to show
        if total_lines <= max_preview_lines:
            # Small file - show all
            preview_lines = lines
            show_all = True
        else:
            # Large file - show first 15 and last 5
            first_lines = lines[:15]
            last_lines = lines[-5:]
            preview_lines = first_lines
            show_all = False

        # Display the content with line numbers
        self.console.print()  # spacing

        for i, line in enumerate(preview_lines, 1):
            # Line number + content (full width, no truncation)
            line_num = f"[dim]{i:4}[/dim]"
            # Escape any Rich markup in the line (only [ needs escaping)
            safe_line = line.replace("[", "\\[")
            self.console.print(f"  {line_num} │ {safe_line}")

        # Show truncation indicator and last lines for large files
        if not show_all:
            omitted = total_lines - 20
            self.console.print(f"  [dim]{'─' * 4} │ ... {omitted} lines omitted ...[/dim]")

            # Show last 5 lines
            for i, line in enumerate(last_lines, total_lines - 4):
                line_num = f"[dim]{i:4}[/dim]"
                safe_line = line.replace("[", "\\[")
                self.console.print(f"  {line_num} │ {safe_line}")

        self.console.print()  # spacing after

    # ─────────────────────────────────────────────────────────
    # WRITE TOOL DISPLAY - Claude Code Style
    # ─────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────
    # WRITE TOOL DISPLAY - Claude Code Style
    # ─────────────────────────────────────────────────────────

    def _display_write(self, arguments: Dict[str, Any], result: Any):
        """Display Write tool execution - Claude Code style"""
        file_path = arguments.get("file_path", "unknown")
        content = arguments.get("content", "")
        from pathlib import Path
        from rich.markup import escape

        # Get file extension for language hint
        ext = Path(file_path).suffix.lower() if file_path else ""
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".html": "html",
            ".css": "css",
            ".sh": "bash",
            ".sql": "sql",
        }
        lang = lang_map.get(ext, "")

        if result.success:
            lines = content.split("\n") if content else []
            line_count = len(lines)
            byte_count = len(content.encode("utf-8"))

            # Claude Code style header
            self.console.print(f"\n  [bold green]{'─' * 3} Write: {escape(file_path)} {'─' * 3}[/bold green]")
            self.console.print(
                f"  [dim]Created {line_count} lines ({byte_count} bytes){f' • {lang}' if lang else ''}[/dim]"
            )
        else:
            self.console.print(
                f"\n  [bold red]✗ Write failed:[/bold red] [{self.style.FILE_PATH}]{file_path}[/]"
            )
            # SAFE: Escape error message to prevent markup injection
            self.console.print(f"    [red]{escape(str(result.error))}[/red]")

    # ─────────────────────────────────────────────────────────
    # MULTI-EDIT TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_multiedit(self, arguments: Dict[str, Any], result: Any):
        """Display MultiEdit tool execution - Hcode style"""
        file_path = arguments.get("file_path", "unknown")

        if result.success:
            metadata = result.metadata or {}
            diff_summary = metadata.get("diff_summary", "")
            total_edits = metadata.get("total_edits", 0)
            total_replacements = metadata.get("total_replacements", 0)

            # Parse simple diff summary if possible to colorize
            # Expected format: "+X -Y" or similar
            if "+" in diff_summary and "-" in diff_summary:
                added = diff_summary.split("+")[1].split()[0]
                removed = diff_summary.split("-")[1].strip()
                diff_display = f"[green]+{added}[/green] [red]-{removed}[/red]"
            else:
                diff_display = diff_summary

            # Claude Code style header
            self.console.print(f"\n  [bold cyan]{'─' * 3} MultiEdit: {escape(file_path)} {'─' * 3}[/bold cyan]")
            self.console.print(
                f"  [dim]Applied {total_edits} edits ({total_replacements} replacements)[/dim]"
            )
            if diff_display:
                self.console.print(f"  {diff_display} lines changed")

        else:
            self.console.print(
                f"\n  [bold red]✗ MultiEdit failed:[/bold red] [{self.style.FILE_PATH}]{file_path}[/]"
            )
            from rich.markup import escape

            self.console.print(f"    [red]{escape(str(result.error))}[/red]")

    # ─────────────────────────────────────────────────────────
    # EDIT TOOL DISPLAY - Claude Code Style
    # ─────────────────────────────────────────────────────────

    def _display_edit(self, arguments: Dict[str, Any], result: Any):
        """Display Edit tool execution - Claude Code style with full-width diff"""
        file_path = arguments.get("file_path", "unknown")
        old_string = arguments.get("old_string", "")
        new_string = arguments.get("new_string", "")
        from rich.markup import escape

        if result.success:
            # Calculate change statistics
            old_lines = old_string.split("\n")
            new_lines = new_string.split("\n")
            lines_removed = len(old_lines)
            lines_added = len(new_lines)

            # Claude Code style header
            self.console.print(f"\n  [bold cyan]{'─' * 3} Edit: {escape(file_path)} {'─' * 3}[/bold cyan]")
            self.console.print(
                f"  [green]+{lines_added}[/green] [red]-{lines_removed}[/red] lines changed"
            )

            # Show full diff
            self._show_diff_enhanced(old_string, new_string)
        else:
            self.console.print(
                f"\n  [bold red]✗ Edit failed:[/bold red] [{self.style.FILE_PATH}]{file_path}[/]"
            )
            # SAFE: Escape error message to prevent markup injection
            self.console.print(f"    [red]{escape(str(result.error))}[/red]")

    def _show_diff_enhanced(self, old_string: str, new_string: str, max_lines: int = 20):
        """
        Show diff in Claude Code style - full width with smart truncation.

        Features:
        - Full terminal width for reasonable lines
        - Smart truncation for very long lines (>100 chars)
        - Clear visual distinction between removed and added lines
        - Line count for large diffs
        - Smart truncation for very large changes
        """
        from rich.text import Text

        old_lines = old_string.split("\n")
        new_lines = new_string.split("\n")

        self.console.print()  # spacing

        def print_diff_line(prefix: str, line: str, color: str, max_width: int = 100):
            """Print a diff line with proper truncation and no wrapping."""
            # Truncate if needed (before any escaping)
            if len(line) > max_width:
                display_line = line[: max_width - 3] + "..."
            else:
                display_line = line

            # Use Text object to avoid markup interpretation and control overflow
            text = Text()
            text.append("  ", style="")
            text.append(f"{prefix} ", style=color)
            text.append(display_line, style=color)
            self.console.print(text, overflow="ellipsis", no_wrap=True)

        # Show removed lines (red with - prefix)
        if len(old_lines) <= max_lines:
            for line in old_lines:
                print_diff_line("-", line, "red")
        else:
            # Show first 10, then truncation, then last 5
            for line in old_lines[:10]:
                print_diff_line("-", line, "red")
            omitted = len(old_lines) - 15
            self.console.print(f"  [dim red]  ... {omitted} more lines removed ...[/dim red]")
            for line in old_lines[-5:]:
                print_diff_line("-", line, "red")

        # Show added lines (green with + prefix)
        if len(new_lines) <= max_lines:
            for line in new_lines:
                print_diff_line("+", line, "green")
        else:
            # Show first 10, then truncation, then last 5
            for line in new_lines[:10]:
                print_diff_line("+", line, "green")
            omitted = len(new_lines) - 15
            self.console.print(f"  [dim green]  ... {omitted} more lines added ...[/dim green]")
            for line in new_lines[-5:]:
                print_diff_line("+", line, "green")

        self.console.print()  # spacing after

    # ─────────────────────────────────────────────────────────
    # BASH TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_bash(self, arguments: Dict[str, Any], result: Any):
        """Display Bash tool execution - Hcode style with output"""
        command = arguments.get("command", "")

        # Truncate long commands for display
        display_cmd = command if len(command) <= 60 else command[:57] + "..."

        # Show command
        self.console.print(
            f"  {self.style.ICON_BASH} [bold]Bash[/bold] "
            f"[{self.style.TOOL_NAME}]{escape(display_cmd)}[/]"
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
            error_lines = error_msg.strip().split("\n")
            if len(error_lines) == 1:
                self.console.print(f"    [{self.style.TOOL_ERROR}]Error: {escape(error_lines[0])}[/]")
            else:
                self.console.print(f"    [{self.style.TOOL_ERROR}]Error:[/]")
                for line in error_lines[:5]:
                    self.console.print(f"    [{self.style.TOOL_ERROR}]  {escape(line)}[/]")
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

        In normal mode: Minimal output, just show content directly
        In debug mode: Full verbose output with boxes and error analysis

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

        # ═══════════════════════════════════════════════════════════════════════════
        # NORMAL MODE: Claude Code-style minimal output
        # ═══════════════════════════════════════════════════════════════════════════
        if not self.debug_mode:
            # Show output directly without boxes (Claude Code style)
            content_lines = truncated.content.split("\n")
            for line in content_lines[:30]:  # Limit to 30 lines in normal mode
                # Highlight error lines
                if any(
                    word in line.lower() for word in ["error", "exception", "failed", "traceback"]
                ):
                    self.console.print(f"    [{self.style.TOOL_ERROR}]{escape(line)}[/]")
                else:
                    self.console.print(f"    [{self.style.DIM}]{escape(line)}[/]")

            if len(content_lines) > 30:
                self.console.print(
                    f"    [{self.style.DIM}]... ({len(content_lines) - 30} more lines)[/]"
                )
            return

        # ═══════════════════════════════════════════════════════════════════════════
        # DEBUG MODE: Full verbose output with boxes
        # ═══════════════════════════════════════════════════════════════════════════

        # Show error summary if errors found
        if show_errors and truncated.errors_found:
            critical_errors = [
                e
                for e in truncated.errors_found
                if e.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.ERROR)
            ]
            if critical_errors:
                self.console.print(
                    f"    [{self.style.TOOL_ERROR}]=== {len(critical_errors)} Error(s) Detected ===[/]"
                )
                for error in critical_errors[:3]:
                    error_line = str(error)[:70]
                    self.console.print(f"    [{self.style.TOOL_ERROR}]  {error_line}[/]")
                    if error.suggestion:
                        self.console.print(
                            f"    [{self.style.DIM}]    -> {error.suggestion[:60]}[/]"
                        )
                if len(critical_errors) > 3:
                    self.console.print(
                        f"    [{self.style.DIM}]  ... and {len(critical_errors) - 3} more errors[/]"
                    )
                self.console.print("")

        # Draw output box
        self.console.print(f"    {self.style.BOX_TL}{self.style.BOX_H * 70}{self.style.BOX_TR}")

        # Show truncation stats if truncated
        if truncated.truncated:
            stats_line = (
                f"[{truncated.original_lines} lines total, showing {truncated.displayed_lines}]"
            )
            self.console.print(
                f"    {self.style.BOX_V} [{self.style.DIM}]{stats_line:<68}[/] {self.style.BOX_V}"
            )
            self.console.print(f"    {self.style.BOX_V}{' ' * 70}{self.style.BOX_V}")

        # Display the processed content
        content_lines = truncated.content.split("\n")
        for line in content_lines:
            # Determine line style based on content
            line_style = self.style.DIM

            # Highlight error lines
            if any(word in line.lower() for word in ["error", "exception", "failed", "traceback"]):
                line_style = self.style.TOOL_ERROR
            # Highlight "latest lines" section header
            elif line.startswith("--- Latest"):
                line_style = "bold cyan"
            # Highlight omission indicator
            elif line.startswith("...") and "omitted" in line:
                line_style = "yellow"

            # Truncate long lines for display
            display_line = line[:68] if len(line) <= 68 else line[:65] + "..."

            self.console.print(
                f"    {self.style.BOX_V} [{line_style}]{escape(display_line):<68}[/] {self.style.BOX_V}"
            )

        self.console.print(f"    {self.style.BOX_BL}{self.style.BOX_H * 70}{self.style.BOX_BR}")

        # Show stack trace indicator
        if truncated.has_stack_trace:
            self.console.print(f"    [{self.style.DIM}][Stack trace detected in output][/]")

    # ─────────────────────────────────────────────────────────
    # GLOB TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_glob(self, arguments: Dict[str, Any], result: Any):
        """Display Glob tool execution - Hcode style"""
        pattern = arguments.get("pattern", "*")
        path = arguments.get("path", ".")

        if result.success:
            files = result.output.strip().split("\n") if result.output else []
            file_count = len([f for f in files if f.strip()])

            self.console.print(
                f"  {self.style.ICON_GLOB} [bold]Glob[/bold] "
                f"[{self.style.TOOL_NAME}]{escape(pattern)}[/] "
                f"[{self.style.DIM}]in {escape(path)}[/] "
                f"[{self.style.DIM}]({file_count} files)[/]"
            )

            # Show first few files
            if files and file_count > 0:
                for f in files[:5]:
                    if f.strip():
                        self.console.print(f"    [{self.style.DIM}]{escape(f)}[/]")
                if file_count > 5:
                    self.console.print(f"    [{self.style.DIM}]... and {file_count - 5} more[/]")
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Glob[/bold] [{self.style.TOOL_NAME}]{escape(pattern)}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {escape(str(result.error))}[/]"
            )

    # ─────────────────────────────────────────────────────────
    # GREP TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_grep(self, arguments: Dict[str, Any], result: Any):
        """Display Grep tool execution - Hcode style with smart output handling"""
        pattern = arguments.get("pattern", "")

        if result.success:
            output = result.output.strip() if result.output else ""
            matches = output.split("\n") if output else []
            match_count = len([m for m in matches if m.strip()])

            self.console.print(
                f"  {self.style.ICON_GREP} [bold]Grep[/bold] "
                f"[{self.style.TOOL_NAME}]{escape(pattern)}[/] "
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
                        self.console.print(f"    [{self.style.DIM}]{escape(display)}[/]")
                if match_count > 10:
                    self.console.print(f"    [{self.style.DIM}]... and {match_count - 10} more[/]")
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Grep[/bold] [{self.style.TOOL_NAME}]{pattern}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {escape(str(result.error))}[/]"
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

        result_lines = truncated.content.split("\n")
        for line in result_lines[:25]:  # Limit display
            # Highlight pattern matches
            if pattern.lower() in line.lower():
                line_style = "bold"
            elif line.startswith("---") or line.startswith("..."):
                line_style = "yellow"
            else:
                line_style = self.style.DIM

            display_line = line[:68] if len(line) <= 68 else line[:65] + "..."
            self.console.print(
                f"    {self.style.BOX_V} [{line_style}]{display_line:<68}[/] {self.style.BOX_V}"
            )

        if len(result_lines) > 25:
            self.console.print(
                f"    {self.style.BOX_V} [{self.style.DIM}]{'... (more matches available)':<68}[/] {self.style.BOX_V}"
            )

        self.console.print(f"    {self.style.BOX_BL}{self.style.BOX_H * 70}{self.style.BOX_BR}")

    # ─────────────────────────────────────────────────────────
    # LS TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_ls(self, arguments: Dict[str, Any], result: Any):
        """Display LS tool execution - Hcode style"""
        path = arguments.get("path", ".")

        if result.success:
            items = result.output.strip().split("\n") if result.output else []
            item_count = len([i for i in items if i.strip()])

            self.console.print(
                f"  {self._icons.FOLDER} [bold]Listed[/bold] "
                f"[{self.style.FILE_PATH}]{escape(path)}[/] "
                f"[{self.style.DIM}]({item_count} items)[/]"
            )

            # Show first few items
            if items and item_count > 0:
                for item in items[:8]:
                    if item.strip():
                        self.console.print(f"    [{self.style.DIM}]{escape(item)}[/]")
                if item_count > 8:
                    self.console.print(f"    [{self.style.DIM}]... and {item_count - 8} more[/]")
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]LS[/bold] [{self.style.FILE_PATH}]{path}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {escape(str(result.error))}[/]"
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
                self.console.print(f"    [{self.style.DIM}]{escape(preview)}[/]")
        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]{tool_name}[/bold] "
                f"[{self.style.TOOL_ERROR}]failed: {escape(str(result.error))}[/]"
            )

    # ─────────────────────────────────────────────────────────
    # SPINNER / PROGRESS DISPLAY
    # ─────────────────────────────────────────────────────────

    def show_executing(self, tool_name: str, description: str = ""):
        """Show tool is executing (spinner style)"""
        tool_name_clean = tool_name.replace("Tool", "").replace("tool", "")
        desc = description or f"Executing {tool_name_clean}..."
        self.console.print(
            f"  [{self.style.TOOL_EXECUTING}]⋯[/] [bold]{tool_name_clean}[/bold] "
            f"[{self.style.DIM}]{desc}[/]",
            end="\r",
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
        self.console.print(
            f"[{self._palette.text_muted}]{self._icons.THINKING} {message}...[/]", end="\r"
        )

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
        cwd: str = "",
    ) -> str:
        """Render status line string"""
        parts = []
        palette = self._palette

        # Model
        if model:
            model_short = model.split("/")[-1] if "/" in model else model
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
            "error": palette.error,
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
