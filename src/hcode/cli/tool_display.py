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
from typing import Optional, Dict, Any, List, Tuple

from rich.console import Console
from rich.markup import escape
from rich.syntax import Syntax
from rich.text import Text

# Import new UI system
from hcode.ui import Icons, console as styled_console
from hcode.ui.theme import get_palette as get_theme_palette


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
        self.FILE_PATH = palette.info
        self.CONTEXT = palette.text_muted

        # Dim colors from theme
        self.TEXT_DIM = "text.dim"

        # Icons from UI system
        # Icons from UI system
        self.ICON_SUCCESS = self._icons.SUCCESS
        self.ICON_ERROR = self._icons.ERROR

        # HCode Design: Gutter & Tree-Lite
        self.GUTTER = self._icons.GUTTER_BAR
        self.ICON_FILE_CIRCLE = self._icons.ICON_FILE_CIRCLE
        self.ICON_DIR_CIRCLE = self._icons.ICON_DIR_CIRCLE
        self.PROMPT_LAMBDA = self._icons.PROMPT_LAMBDA

        # Gutter Colors
        self.COLOR_READ = palette.primary  # Cyan
        self.COLOR_WRITE = palette.success  # Green (Neon)
        self.COLOR_EDIT = palette.code_number  # Purple
        self.COLOR_BASH = palette.warning  # Orange

        # Tool Status Colors
        self.TOOL_SUCCESS = palette.success
        self.TOOL_ERROR = palette.error
        self.TOOL_NAME = palette.info


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
            self, tool_name: str, arguments: Dict[str, Any], result: Any
    ):
        """
        Display tool execution in Hcode style.

        Args:
            tool_name: Name of the tool (e.g., 'read', 'write', 'bash')
            arguments: Tool arguments
            result: Tool execution result (has .success, .output, .error)
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
        elif tool_name_lower in ["glob", "smartglob"]:
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
        """Display Read tool execution - Status Gutter Style"""
        file_path = arguments.get("file_path", "unknown")
        from pathlib import Path

        # Get file extension for syntax hint
        ext = Path(file_path).suffix.lower() if file_path else ""
        lang_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "jsx", ".tsx": "tsx", ".json": "json",
            ".yaml": "yaml", ".yml": "yaml", ".md": "markdown",
            ".html": "html", ".css": "css", ".sh": "bash",
            ".bash": "bash", ".rs": "rust", ".go": "go",
            ".java": "java", ".cpp": "cpp", ".c": "c",
            ".h": "c", ".sql": "sql", ".xml": "xml",
            ".toml": "toml", ".ini": "ini",
        }
        lang = lang_map.get(ext, "text")

        gutter_color = self.style.COLOR_READ
        gutter = f"[{gutter_color}]{self.style.GUTTER}[/]"

        if result.success:
            content = result.output or ""
            lines = content.split("\n") if content else []
            total_lines = len(lines)

            # 1. Header: ┃ Read path
            self.console.print()
            header = Text()
            header.append(f"{self.style.GUTTER} ", style=str(gutter_color))
            header.append("Read ", style=f"bold {gutter_color}")
            header.append(Path(file_path).name, style="bold white")
            try:
                parent = Path(file_path).parent.name
                if parent:
                    header.append(f" ({parent}/)", style=f"{self.style.TEXT_DIM}")
            except:
                pass
            self.console.print(header)

            # 2. Spacer: ┃
            self.console.print(f"{gutter}")

            # 3. Content Logic

            def create_content_grid(lines_to_print, start_line_num):
                # Use a single grid for the whole chunk to ensure alignment
                from rich.table import Table
                # Expand to full width to prevent squeezing
                grid = Table.grid(padding=0, expand=True)
                grid.add_column(style=f"dim {gutter_color}", no_wrap=True)  # Gutter + Line Num
                grid.add_column(style="white", ratio=1, no_wrap=True)  # Code column takes remaining space

                for i, line_content in enumerate(lines_to_print):
                    line_num = start_line_num + i
                    line_num_str = f"{line_num:>4}"

                    # Safe highlighting
                    try:
                        # Use Syntax for single line
                        # word_wrap=False ensures it does not wrap to a new line.
                        syntax = Syntax(line_content, lang, theme="monokai", line_numbers=False, word_wrap=False, code_width=None)
                    except:
                        syntax = escape(line_content)

                    prefix = Text.assemble(
                        (f"{self.style.GUTTER} ", str(gutter_color)),
                        (f"{line_num_str} ", f"{self.style.TEXT_DIM}"),
                        (f"│ ", f"{self.style.TEXT_DIM}")
                    )

                    grid.add_row(prefix, syntax)

                return grid

            if total_lines <= 10:
                self.console.print(create_content_grid(lines, 1))
            else:
                # Head (4 lines)
                head_lines = lines[:4]
                self.console.print(create_content_grid(head_lines, 1))

                # Gap
                self.console.print(
                    Text.assemble(
                        (f"{self.style.GUTTER} ", str(gutter_color)),
                        (f"   ⋮   ", f"bold {self.style.TEXT_DIM}"),
                        (f"  {total_lines - 8} lines hidden", f"italic {self.style.TEXT_DIM}")
                    )
                )

                # Tail (4 lines)
                tail_lines = lines[-4:]
                self.console.print(create_content_grid(tail_lines, total_lines - 3))

            # 4. Footer: ┃
            self.console.print(f"{gutter}")
            self.console.print()

        else:
            self.console.print(
                f"\n[{self.style.TOOL_ERROR}]┃[/] [bold red]Read failed:[/bold red] [{self.style.FILE_PATH}]{file_path}[/]"
            )
            self.console.print(f"  [red]{escape(str(result.error))}[/red]")

    # ─────────────────────────────────────────────────────────
    # WRITE TOOL DISPLAY - Claude Code Style
    # ─────────────────────────────────────────────────────────

    def _display_write(self, arguments: Dict[str, Any], result: Any):
        """Display Write tool execution - Status Gutter Style (Green)"""
        file_path = arguments.get("file_path", "unknown")
        content = arguments.get("content", "")
        from pathlib import Path

        gutter_color = self.style.COLOR_WRITE
        gutter = f"[{gutter_color}]{self.style.GUTTER}[/]"

        if result.success:
            lines = content.split("\n") if content else []
            total_lines = len(lines)
            byte_count = len(content.encode("utf-8"))

            # 1. Header: ┃ Write path
            self.console.print()
            header = Text()
            header.append(f"{self.style.GUTTER} ", style=str(gutter_color))
            header.append("Write ", style=f"bold {gutter_color}")
            header.append(Path(file_path).name, style="bold white")
            try:
                parent = Path(file_path).parent.name
                if parent:
                    header.append(f" ({parent}/)", style=f"{self.style.TEXT_DIM}")
            except:
                pass
            self.console.print(header)

            # 2. Spacer
            self.console.print(f"{gutter}")

            # 3. Content
            # self.style.ADDED_BG is hex, Rich text style needs careful handling. 
            # Reverting to explicit styling

            def print_green_line(line_content, line_num):
                # Format: ┃   1 │ content (with green bg implication?)
                # Actually, write output should just show it was written. 
                # Design spec says: "Green for Write".
                line_num_str = f"{line_num:>4}"
                self.console.print(
                    Text.assemble(
                        (f"{self.style.GUTTER} ", str(gutter_color)),
                        (f"{line_num_str} ", f"{self.style.TEXT_DIM}"),
                        (f"│ ", f"{self.style.TEXT_DIM}"),
                        (f"{line_content}", f"green")  # Make text green to indicate create/write
                    )
                )

            if total_lines <= 10:
                for i, line in enumerate(lines):
                    print_green_line(line, i + 1)
            else:
                # Head (4 lines)
                for i in range(4):
                    print_green_line(lines[i], i + 1)

                self.console.print(
                    Text.assemble(
                        (f"{self.style.GUTTER} ", str(gutter_color)),
                        (f"   ⋮   ", f"bold {self.style.TEXT_DIM}"),
                        (f"  {total_lines - 8} lines hidden", f"italic {self.style.TEXT_DIM}")
                    )
                )

                # Tail (4 lines)
                for i in range(total_lines - 4, total_lines):
                    print_green_line(lines[i], i + 1)

            # 4. Footer
            self.console.print(f"{gutter}   [dim]({byte_count} bytes written)[/dim]")
            self.console.print()

        else:
            self.console.print(
                f"\n[{self.style.TOOL_ERROR}]┃[/] [bold red]Write failed:[/bold red] [{self.style.FILE_PATH}]{file_path}[/]"
            )
            self.console.print(f"  [red]{escape(str(result.error))}[/red]")

    # ─────────────────────────────────────────────────────────
    # MULTI-EDIT TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────
    # MULTI-EDIT TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_multiedit(self, arguments: Dict[str, Any], result: Any):
        """Display MultiEdit tool execution - Status Gutter Style"""
        file_path = arguments.get("file_path", "unknown")

        gutter_color = self.style.COLOR_EDIT
        gutter = f"[{gutter_color}]{self.style.GUTTER}[/]"

        if result.success:
            metadata = result.metadata or {}
            diff_summary = metadata.get("diff_summary", "")
            total_edits = metadata.get("total_edits", 0)
            total_replacements = metadata.get("total_replacements", 0)

            # Header
            self.console.print()
            header = Text()
            header.append(f"{self.style.GUTTER} ", style=str(gutter_color))
            header.append("MultiEdit ", style=f"bold {gutter_color}")
            header.append(file_path, style="bold white")
            self.console.print(header)
            self.console.print(f"{gutter}")

            # Content Info
            info_text = Text()
            info_text.append(f" {self.style.GUTTER} ", style=str(gutter_color))
            info_text.append(" Applied ", style=f"{self.style.TEXT_DIM}")
            info_text.append(f"{total_edits} edits", style="bold white")
            info_text.append(", ", style=f"{self.style.TEXT_DIM}")
            info_text.append(f"{total_replacements} replacements", style="bold white")
            self.console.print(info_text)

            if diff_summary:
                self.console.print(
                    Text.assemble(
                        (f" {self.style.GUTTER} ", str(gutter_color)),
                        (f" {diff_summary}", f"{self.style.TEXT_DIM}")
                    )
                )

            self.console.print()

        else:
            self.console.print(
                f"\n[{self.style.TOOL_ERROR}]┃[/] [bold red]MultiEdit failed:[/bold red] [{self.style.FILE_PATH}]{file_path}[/]"
            )
            self.console.print(f"  [red]{escape(str(result.error))}[/red]")

    # ─────────────────────────────────────────────────────────
    # EDIT TOOL DISPLAY - Claude Code Style
    # ─────────────────────────────────────────────────────────

    def _display_edit(self, arguments: Dict[str, Any], result: Any):
        """Display Edit tool execution - Status Gutter Style (Purple)"""
        file_path = arguments.get("file_path", "unknown")
        old_string = arguments.get("old_string", "")
        new_string = arguments.get("new_string", "")
        import difflib

        gutter_color = self.style.COLOR_EDIT
        gutter = f"[{gutter_color}]{self.style.GUTTER}[/]"

        if result.success:
            self.console.print()
            header = Text()
            header.append(f"{self.style.GUTTER} ", style=str(gutter_color))
            header.append("Edit ", style=f"bold {gutter_color}")
            header.append(file_path, style="bold white")
            self.console.print(header)
            self.console.print(f"{gutter}")

            old_lines = old_string.splitlines()
            new_lines = new_string.splitlines()

            diff = list(difflib.unified_diff(
                old_lines,
                new_lines,
                lineterm=""
            ))

            # Skip header lines
            content_diff = diff[3:] if len(diff) > 3 else []

            for line in content_diff:
                if line.startswith("-"):
                    # Deletion
                    self.console.print(
                        Text.assemble(
                            (f"{self.style.GUTTER} ", str(gutter_color)),
                            (f" - ", "red"),
                            (line[1:], "dim red")
                        )
                    )
                elif line.startswith("+"):
                    # Addition
                    self.console.print(
                        Text.assemble(
                            (f"{self.style.GUTTER} ", str(gutter_color)),
                            (f" + ", "green"),
                            (line[1:], "green")
                        )
                    )
                else:
                    # Context
                    self.console.print(
                        Text.assemble(
                            (f"{self.style.GUTTER} ", str(gutter_color)),
                            (f"   ", "dim"),
                            (line[1:], "dim")
                        )
                    )

            self.console.print()

        else:
            self.console.print(
                f"\n[{self.style.TOOL_ERROR}]┃[/] [bold red]Edit failed:[/bold red] [{self.style.FILE_PATH}]{file_path}[/]"
            )
            self.console.print(f"  [red]{escape(str(result.error))}[/red]")

    # ─────────────────────────────────────────────────────────
    # BASH TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────
    # BASH TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────
    # BASH TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_bash(self, arguments: Dict[str, Any], result: Any):
        """Display Bash tool execution - Status Gutter Style (Orange)"""
        command = arguments.get("command", "")

        # Truncate long commands for display
        display_cmd = command if len(command) <= 60 else command[:57] + "..."

        gutter_color = self.style.COLOR_BASH
        gutter = f"[{gutter_color}]{self.style.GUTTER}[/]"

        if result.success:
            output = result.output or ""
            lines = output.split("\n")
            total_lines = len(lines)

            # Header
            self.console.print()
            header = Text()
            header.append(f"{self.style.GUTTER} ", style=str(gutter_color))
            header.append("Bash ", style=f"bold {gutter_color}")
            header.append(f"{display_cmd}", style="white")
            self.console.print(header)

            self.console.print(f"{gutter}")

            def print_bash_line(line_content):
                self.console.print(
                    Text.assemble(
                        (f"{self.style.GUTTER} ", str(gutter_color)),
                        (f"  {line_content}", f"{self.style.TEXT_DIM}")
                    )
                )

            if not output.strip():
                self.console.print(
                    Text.assemble(
                        (f"{self.style.GUTTER} ", str(gutter_color)),
                        (f"  (no output)", "italic dim")
                    )
                )
            elif total_lines <= 10:
                for line in lines:
                    print_bash_line(line)
            else:
                # Head
                for i in range(3):
                    print_bash_line(lines[i])

                self.console.print(
                    Text.assemble(
                        (f"{self.style.GUTTER} ", str(gutter_color)),
                        (f"   ⋮   ", f"bold {self.style.TEXT_DIM}"),
                        (f"  {total_lines - 6} lines hidden", f"italic {self.style.TEXT_DIM}")
                    )
                )

                # Tail
                for i in range(total_lines - 3, total_lines):
                    print_bash_line(lines[i])

            self.console.print(f"{gutter}")
            self.console.print()

        else:
            # Error Case
            error_msg = result.error if result.error else "Command failed"
            self.console.print(
                f"\n[{self.style.TOOL_ERROR}]┃[/] [bold red]Bash failed:[/bold red] [{self.style.TOOL_NAME}]{display_cmd}[/]"
            )
            self.console.print(f"  [red]{escape(str(error_msg))}[/red]")

    # ─────────────────────────────────────────────────────────
    # GLOB TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────
    # GLOB TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_glob(self, arguments: Dict[str, Any], result: Any):
        """Display Glob tool execution - Tree-Lite Style"""
        pattern = arguments.get("pattern", "*")
        path = arguments.get("path", ".")

        if result.success:
            # Check for SmartGlob metadata first
            metadata = getattr(result, "metadata", {}) or {}
            if metadata.get("files") is not None:
                files = metadata.get("files", [])
            else:
                files = result.output.strip().split("\n") if result.output else []
                files = [f.strip() for f in files if f.strip()]

            # Header
            self.console.print()
            header = Text()
            header.append("Files in ", style=f"{self.style.TEXT_DIM}")
            header.append(f"{path}", style="bold white")
            header.append(f" (pattern: {pattern})", style="dim cyan")
            self.console.print(header)

            display_files = []

            for f in files:
                # Determine icon based on simple heuristic or metadata if available
                # Logic: if ends with /, it is dir.
                is_dir = f.endswith("/") or f.endswith("\\")

                icon = self.style.ICON_DIR_CIRCLE if is_dir else self.style.ICON_FILE_CIRCLE
                color = "cyan" if is_dir else "white"

                display_files.append((icon, f, color))

            self._display_tree_lite_results(display_files, "No files found")

        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Glob[/bold] [{self.style.TOOL_NAME}]{escape(pattern)}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {escape(str(result.error))}[/]"
            )

    def _display_tree_lite_results(self, items: List[Tuple[str, str, str]], empty_text: str = "No items found"):
        """Display a list of items in Tree-Lite style."""
        total_items = len(items)

        if total_items == 0:
            self.console.print(f"  [italic dim]{empty_text}[/italic dim]")
            self.console.print()
            return

        def print_item(item):
            icon, text, color = item
            self.console.print(
                Text.assemble(
                    (f"{icon} ", f"{color}"),
                    (f"{text}", f"{color} dim" if color == "cyan" else f"{self.style.TEXT_DIM}")
                )
            )

        if total_items <= 15:
            for item in items:
                print_item(item)
        else:
            # Show first 10 and last 5
            head = items[:10]
            tail = items[-5:]
            hidden = total_items - 15

            for item in head:
                print_item(item)

            self.console.print(f"  ... {hidden} more items ...", style="italic dim")

            for item in tail:
                print_item(item)

        self.console.print()

    # ─────────────────────────────────────────────────────────
    # GREP TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────
    # GREP TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_grep(self, arguments: Dict[str, Any], result: Any):
        """Display Grep tool execution - Tree-Lite Style"""
        pattern = arguments.get("pattern", "")
        path = arguments.get("path", ".")

        if result.success:
            output = result.output.strip() if result.output else ""
            matches = output.split("\n") if output else []
            matches = [m.strip() for m in matches if m.strip()]

            # Header
            self.console.print()
            header = Text()
            header.append("Grep matches in ", style=f"{self.style.TEXT_DIM}")
            header.append(f"{path}", style="bold white")
            header.append(f" (pattern: {pattern})", style="dim cyan")
            self.console.print(header)

            display_items = []
            for m in matches:
                # Grep match format usually "file:line:content" or just "file"
                # Use simplified icon
                display_items.append((self.style.ICON_FILE_CIRCLE, m, "white"))

            self._display_tree_lite_results(display_items, "No matches found")

        else:
            self.console.print(
                f"  [{self.style.TOOL_ERROR}]{self.style.ICON_ERROR}[/] "
                f"[bold]Grep[/bold] [{self.style.TOOL_NAME}]{pattern}[/] "
                f"[{self.style.TOOL_ERROR}]failed: {escape(str(result.error))}[/]"
            )

    # ─────────────────────────────────────────────────────────
    # LS TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    # ─────────────────────────────────────────────────────────
    # LS TOOL DISPLAY
    # ─────────────────────────────────────────────────────────

    def _display_ls(self, arguments: Dict[str, Any], result: Any):
        """Display LS tool execution - Tree-Lite Style"""
        path = arguments.get("path", ".")

        if result.success:
            items = result.output.strip().split("\n") if result.output else []
            items = [i.strip() for i in items if i.strip()]

            # Header
            self.console.print()
            header = Text()
            header.append("Files in ", style=f"{self.style.TEXT_DIM}")
            header.append(f"{path}", style="bold white")
            self.console.print(header)

            display_items = []

            for f in items:
                # Basic heuristic for LS output (usually doesn't have trailing slash in simple list)
                # But we can try to guess or just use Generic File
                # If we want to be smart, we'd need to check file system, but that's expensive.
                # Let's check if it ends with / 
                is_dir = f.endswith("/") or f.endswith("\\")
                icon = self.style.ICON_DIR_CIRCLE if is_dir else self.style.ICON_FILE_CIRCLE
                color = "cyan" if is_dir else "white"

                display_items.append((icon, f, color))

            self._display_tree_lite_results(display_items, "Empty directory")

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


# ============================================================
# STREAMING DISPLAY
# ============================================================


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


status_line = StatusLineDisplay()
