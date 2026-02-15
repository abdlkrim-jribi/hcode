"""
HCode Custom Panel Designs
Specialized panels for different content types.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from rich.align import Align
from rich.box import ROUNDED, SIMPLE
from rich.console import Group, RenderableType
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from hcode.ui.icons import Icons
from hcode.ui.theme import get_palette


# ═══════════════════════════════════════════════════════════════════════
# WELCOME PANEL
# ═══════════════════════════════════════════════════════════════════════


class WelcomePanel:
    """Welcome panel with system info and status."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        provider: str = "Anthropic",
        version: str = "1.0.0",
    ):
        self.model = model
        self.provider = provider
        self.version = version

    def render(self) -> Panel:
        """Render the welcome panel."""
        palette = get_palette()

        # System info line
        info_text = Text()
        info_text.append("◈ ", style="bold #00FF88")  # Mint green icon
        info_text.append("Model: ", style=palette.text_muted)
        info_text.append(self.model, style="bold #39FF14")  # Neon green model
        info_text.append("  │  ", style=palette.text_muted)
        info_text.append("◈ ", style="bold #00FF88")  # Mint green icon
        info_text.append("Provider: ", style=palette.text_muted)
        info_text.append(self.provider, style=f"bold {palette.accent}")

        # Commands hint
        commands_text = Text()
        commands_text.append("Commands: ", style=palette.text_muted)
        commands_text.append("/help", style="bold #39FF14")  # Neon green
        commands_text.append(" │ ", style=palette.text_muted)
        commands_text.append("/exit", style=f"bold {palette.error}")
        commands_text.append(" │ ", style=palette.text_muted)
        commands_text.append("/clear", style=f"bold {palette.warning}")
        commands_text.append(" │ ", style=palette.text_muted)
        commands_text.append("/model", style="bold #00FF88")  # Mint green

        content = Group(
            Align.center(info_text),
            Text(""),
            Align.center(commands_text),
        )

        # Title with status - neon green branding
        title = Text()
        title.append("◢", style="bold #00FF88")  # Mint green corner
        title.append(" HCode AI Agent ", style="bold #39FF14")  # Neon green brand
        title.append("◣", style="bold #00FF88")  # Mint green corner
        title.append("  ◉ ", style="bold #39FF14")  # Neon green dot
        title.append("ONLINE", style="bold #39FF14")  # Neon green status

        return Panel(
            content,
            title=title,
            border_style="bold #39FF14",  # Neon green border
            padding=(1, 2),
        )


# ═══════════════════════════════════════════════════════════════════════
# MESSAGE PANELS
# ═══════════════════════════════════════════════════════════════════════


class UserMessagePanel:
    """Panel for user messages."""

    def __init__(self, content: str, timestamp: Optional[datetime] = None):
        self.content = content
        self.timestamp = timestamp or datetime.now()

    def render(self) -> Group:
        """Render user message."""
        palette = get_palette()

        header = Text()
        header.append("◆ ", style=f"bold {palette.secondary}")
        header.append("You", style=f"bold {palette.primary}")
        header.append(f"  {self.timestamp.strftime('%H:%M')}", style=palette.text_muted)

        body = Padding(Text(self.content), (0, 0, 0, 2))

        return Group(header, body)


class AIMessagePanel:
    """Panel for AI responses."""

    def __init__(
        self,
        content: str,
        thinking: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.content = content
        self.thinking = thinking
        self.timestamp = timestamp or datetime.now()

    def render(self) -> Group:
        """Render AI message."""
        palette = get_palette()
        elements = []

        # Thinking section (if present)
        if self.thinking:
            thinking_header = Text()
            thinking_header.append("◊ ", style=f"bold {palette.warning}")
            thinking_header.append("Thinking", style=f"italic {palette.warning}")
            elements.append(thinking_header)
            elements.append(Padding(Text(self.thinking, style=palette.text_muted), (0, 0, 0, 2)))
            elements.append(Text(""))

        # Main response
        header = Text()
        header.append("◈ ", style="bold #00FF88")  # Mint green icon
        header.append("HCode", style="bold #39FF14")  # Neon green brand
        header.append(f"  {self.timestamp.strftime('%H:%M')}", style=palette.text_muted)
        elements.append(header)

        # Content (render as markdown if it looks like markdown)
        if "```" in self.content or self.content.startswith("#"):
            body = Markdown(self.content, code_theme="dracula")
        else:
            body = Text(self.content)

        elements.append(Padding(body, (0, 0, 0, 2)))

        return Group(*elements)


# ═══════════════════════════════════════════════════════════════════════
# TOOL EXECUTION PANEL
# ═══════════════════════════════════════════════════════════════════════


class ToolPanel:
    """Panel for tool execution display."""

    def __init__(
        self,
        tool_name: str,
        tool_input: str,
        tool_output: Optional[str] = None,
        status: str = "running",  # running, success, error
        duration: Optional[float] = None,
    ):
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.tool_output = tool_output
        self.status = status
        self.duration = duration

    def render(self) -> Panel:
        """Render tool panel."""
        palette = get_palette()

        status_icons = {
            "running": ("◐", palette.warning),
            "success": ("✔", palette.success),
            "error": ("✖", palette.error),
        }
        icon, color = status_icons.get(self.status, status_icons["running"])

        # Title
        title = Text()
        title.append(f"{icon} ", style=f"bold {color}")
        title.append(Icons.get_tool_icon(self.tool_name), style=palette.accent)
        title.append(f" {self.tool_name}", style=f"bold {palette.accent}")

        if self.duration:
            title.append(f" ({self.duration:.2f}s)", style=palette.text_muted)

        # Content
        content_parts = []

        # Input preview
        input_preview = self.tool_input[:100]
        if len(self.tool_input) > 100:
            input_preview += "..."
        input_text = Text()
        input_text.append("Input: ", style=palette.text_muted)
        input_text.append(input_preview, style=palette.text_secondary)
        content_parts.append(input_text)

        # Output (if available)
        if self.tool_output:
            content_parts.append(Text(""))
            output_preview = self.tool_output[:200]
            if len(self.tool_output) > 200:
                output_preview += "..."
            output_text = Text()
            output_text.append("Output: ", style=palette.text_muted)
            output_text.append(output_preview, style=palette.text_primary)
            content_parts.append(output_text)

        return Panel(
            Group(*content_parts),
            title=title,
            border_style=color,
            padding=(0, 1),
        )


# ═══════════════════════════════════════════════════════════════════════
# ERROR PANEL
# ═══════════════════════════════════════════════════════════════════════


class ErrorPanel:
    """Panel for error messages."""

    def __init__(
        self,
        message: str,
        details: Optional[str] = None,
        error_type: str = "Error",
    ):
        self.message = message
        self.details = details
        self.error_type = error_type

    def render(self) -> Panel:
        """Render error panel."""
        palette = get_palette()

        content_parts = [Text(self.message, style=palette.error)]

        if self.details:
            content_parts.append(Text(""))
            content_parts.append(Text(self.details, style=palette.text_muted))

        title = Text()
        title.append("✖ ", style=f"bold {palette.error}")
        title.append(self.error_type, style=f"bold {palette.error}")

        return Panel(
            Group(*content_parts),
            title=title,
            border_style=palette.error,
            padding=(0, 2),
        )


# ═══════════════════════════════════════════════════════════════════════
# SUCCESS PANEL
# ═══════════════════════════════════════════════════════════════════════


class SuccessPanel:
    """Panel for success messages."""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details

    def render(self) -> Panel:
        """Render success panel."""
        palette = get_palette()

        content_parts = [Text(self.message, style=palette.success)]

        if self.details:
            content_parts.append(Text(""))
            content_parts.append(Text(self.details, style=palette.text_secondary))

        title = Text()
        title.append("✔ ", style=f"bold {palette.success}")
        title.append("Success", style=f"bold {palette.success}")

        return Panel(
            Group(*content_parts),
            title=title,
            border_style=palette.success,
            padding=(0, 2),
        )


# ═══════════════════════════════════════════════════════════════════════
# INFO PANEL
# ═══════════════════════════════════════════════════════════════════════


class InfoPanel:
    """Panel for informational messages."""

    def __init__(
        self,
        title: str,
        content: RenderableType,
        icon: str = "ℹ",
    ):
        self.title = title
        self.content = content
        self.icon = icon

    def render(self) -> Panel:
        """Render info panel."""
        palette = get_palette()

        title_text = Text()
        title_text.append(f"{self.icon} ", style=f"bold {palette.info}")
        title_text.append(self.title, style=f"bold {palette.info}")

        return Panel(
            self.content,
            title=title_text,
            border_style=palette.info,
            padding=(0, 2),
        )


# ═══════════════════════════════════════════════════════════════════════
# FILE TREE PANEL
# ═══════════════════════════════════════════════════════════════════════


class FileTreePanel:
    """Panel displaying file tree."""

    def __init__(
        self,
        root_name: str,
        files: List[str],
        show_icons: bool = True,
    ):
        self.root_name = root_name
        self.files = files
        self.show_icons = show_icons

    def render(self) -> Panel:
        """Render file tree panel."""
        palette = get_palette()

        # Build tree
        tree = Tree(
            f"[{palette.primary}]{Icons.FOLDER} {self.root_name}[/]",
            guide_style=palette.border_default,
        )

        # Group files by directory
        dirs: Dict[str, Any] = {}
        for filepath in sorted(self.files):
            parts = filepath.replace("\\", "/").split("/")
            current = dirs

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            filename = parts[-1]
            current[filename] = None

        def add_nodes(parent: Tree, structure: Dict) -> None:
            for name, children in sorted(structure.items()):
                if children is None:
                    icon = Icons.get_file_icon(name) if self.show_icons else ""
                    parent.add(f"[{palette.text_secondary}]{icon} {name}[/]")
                else:
                    icon = Icons.FOLDER if self.show_icons else ""
                    branch = parent.add(f"[{palette.primary}]{icon} {name}[/]")
                    add_nodes(branch, children)

        add_nodes(tree, dirs)

        return Panel(
            tree,
            title=f"[{palette.accent}]◈ Files[/]",
            border_style=palette.border_default,
            padding=(0, 1),
        )


# ═══════════════════════════════════════════════════════════════════════
# STATS PANEL
# ═══════════════════════════════════════════════════════════════════════


class StatsPanel:
    """Panel displaying statistics."""

    def __init__(
        self,
        title: str,
        stats: List[Tuple[str, str, Optional[str]]],  # (label, value, color)
    ):
        self.title = title
        self.stats = stats

    def render(self) -> Panel:
        """Render stats panel."""
        palette = get_palette()

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
        )
        table.add_column("Label", style=palette.text_muted)
        table.add_column("Value", justify="right")

        for label, value, color in self.stats:
            table.add_row(
                label,
                Text(value, style=f"bold {color or palette.primary}"),
            )

        return Panel(
            table,
            title=f"[{palette.accent}]◈ {self.title}[/]",
            border_style=palette.border_default,
            padding=(0, 1),
        )


# ═══════════════════════════════════════════════════════════════════════
# HELP PANEL
# ═══════════════════════════════════════════════════════════════════════


class HelpPanel:
    """Panel displaying help information."""

    def __init__(
        self,
        commands: List[Tuple[str, str]],  # (command, description)
        title: str = "Help",
    ):
        self.commands = commands
        self.title = title

    def render(self) -> Panel:
        """Render help panel."""
        palette = get_palette()

        table = Table(
            show_header=True,
            header_style=f"bold {palette.secondary}",
            box=SIMPLE,
            padding=(0, 2),
        )
        table.add_column("Command", style=f"bold {palette.primary}")
        table.add_column("Description", style=palette.text_secondary)

        for command, description in self.commands:
            table.add_row(command, description)

        return Panel(
            table,
            title=f"[{palette.accent}]◈ {self.title}[/]",
            border_style=palette.border_default,
            padding=(0, 1),
        )


# ═══════════════════════════════════════════════════════════════════════
# TOKEN USAGE PANEL
# ═══════════════════════════════════════════════════════════════════════


class TokenUsagePanel:
    """Panel displaying token usage."""

    def __init__(
        self,
        input_tokens: int,
        output_tokens: int,
        elapsed_time: Optional[float] = None,
    ):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.elapsed_time = elapsed_time

    def render(self) -> Text:
        """Render token usage (inline, not panel)."""
        palette = get_palette()
        self.input_tokens + self.output_tokens

        text = Text()
        text.append("◈ ", style=f"bold {palette.secondary}")
        text.append(f"{self.input_tokens:,}", style=f"bold {palette.primary}")
        text.append(" in │ ", style=palette.text_muted)
        text.append(f"{self.output_tokens:,}", style=f"bold {palette.secondary}")
        text.append(" out", style=palette.text_muted)

        if self.elapsed_time:
            text.append(" │ ", style=palette.text_muted)
            text.append(f"⚡ {self.elapsed_time:.2f}s", style=f"bold {palette.warning}")

        return text


# ═══════════════════════════════════════════════════════════════════════
# DIFF DISPLAY - Claude Code Style
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class DiffLine:
    """A single line in a diff."""

    line_number_old: Optional[int]  # Line number in old file (None for additions)
    line_number_new: Optional[int]  # Line number in new file (None for deletions)
    content: str
    change_type: str  # 'context', 'addition', 'deletion', 'separator'


class DiffDisplay:
    """
    Claude Code-style diff display.

    Shows file changes with:
    - Line numbers for both old and new versions
    - Colored additions (green) and deletions (red)
    - Context lines around changes
    - Statistics summary (lines added/removed)
    """

    CONTEXT_LINES = 3

    @staticmethod
    def compute_diff(old_content: str, new_content: str, context_lines: int = 3) -> List[DiffLine]:
        """Compute diff between old and new content."""
        import difflib
        import re

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=context_lines))

        result = []
        old_line_num = 0
        new_line_num = 0

        i = 0
        while i < len(diff):
            line = diff[i]

            if line.startswith("@@"):
                match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if match:
                    old_line_num = int(match.group(1)) - 1
                    new_line_num = int(match.group(2)) - 1

                if result:
                    result.append(DiffLine(None, None, "...", "separator"))

            elif line.startswith("---") or line.startswith("+++"):
                pass
            elif line.startswith("-"):
                old_line_num += 1
                result.append(DiffLine(old_line_num, None, line[1:].rstrip("\n\r"), "deletion"))
            elif line.startswith("+"):
                new_line_num += 1
                result.append(DiffLine(None, new_line_num, line[1:].rstrip("\n\r"), "addition"))
            elif line.startswith(" "):
                old_line_num += 1
                new_line_num += 1
                result.append(
                    DiffLine(old_line_num, new_line_num, line[1:].rstrip("\n\r"), "context")
                )

            i += 1

        return result

    @staticmethod
    def render(
        filename: str,
        old_content: str,
        new_content: str,
        context_lines: int = 3,
        show_stats: bool = True,
        language: str = None,
    ) -> Panel:
        """Render a Claude Code-style diff panel."""
        palette = get_palette()

        # Auto-detect language from filename
        if language is None:
            ext_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".jsx": "jsx",
                ".tsx": "tsx",
                ".html": "html",
                ".css": "css",
                ".json": "json",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".md": "markdown",
                ".rs": "rust",
                ".go": "go",
                ".java": "java",
                ".c": "c",
                ".cpp": "cpp",
                ".h": "c",
                ".hpp": "cpp",
                ".rb": "ruby",
                ".php": "php",
                ".sh": "bash",
                ".sql": "sql",
                ".xml": "xml",
            }
            ext = os.path.splitext(filename)[1].lower()
            language = ext_map.get(ext, "text")

        # Compute diff
        diff_lines = DiffDisplay.compute_diff(old_content, new_content, context_lines)

        if not diff_lines:
            return Panel(
                Text("No changes", style=palette.text_muted),
                title=f"[{palette.text_secondary}]{Icons.get_file_icon(filename)} {filename}[/]",
                border_style=palette.border_default,
                box=ROUNDED,
                padding=(0, 1),
            )

        # Calculate statistics
        additions = sum(1 for d in diff_lines if d.change_type == "addition")
        deletions = sum(1 for d in diff_lines if d.change_type == "deletion")

        lines = []

        # Stats header
        if show_stats:
            stats_text = Text()
            stats_text.append(" +", style=palette.diff_added)
            stats_text.append(f" {additions} ", style=palette.diff_added)
            stats_text.append(" -", style=palette.diff_removed)
            stats_text.append(f" {deletions} ", style=palette.diff_removed)
            lines.append(stats_text)
            lines.append(Text(""))

        # Calculate max line number width
        max_old = max((d.line_number_old or 0) for d in diff_lines)
        max_new = max((d.line_number_new or 0) for d in diff_lines)
        ln_width = max(len(str(max_old)), len(str(max_new)), 3)

        # Render each diff line
        for diff_line in diff_lines:
            line_text = Text()

            if diff_line.change_type == "separator":
                line_text.append(f"{'─' * (ln_width * 2 + 5)}", style=palette.text_muted)
            elif diff_line.change_type == "deletion":
                old_ln = str(diff_line.line_number_old).rjust(ln_width)
                new_ln = " " * ln_width
                line_text.append(f" {old_ln} ", style=palette.text_muted)
                line_text.append(f" {new_ln} ", style=f"dim {palette.text_muted}")
                line_text.append(" - ", style=f"bold {palette.diff_removed}")
                line_text.append(diff_line.content, style=palette.diff_removed)
            elif diff_line.change_type == "addition":
                old_ln = " " * ln_width
                new_ln = str(diff_line.line_number_new).rjust(ln_width)
                line_text.append(f" {old_ln} ", style=f"dim {palette.text_muted}")
                line_text.append(f" {new_ln} ", style=palette.text_muted)
                line_text.append(" + ", style=f"bold {palette.diff_added}")
                line_text.append(diff_line.content, style=palette.diff_added)
            else:
                old_ln = (
                    str(diff_line.line_number_old).rjust(ln_width)
                    if diff_line.line_number_old
                    else " " * ln_width
                )
                new_ln = (
                    str(diff_line.line_number_new).rjust(ln_width)
                    if diff_line.line_number_new
                    else " " * ln_width
                )
                line_text.append(f" {old_ln} ", style=palette.text_muted)
                line_text.append(f" {new_ln} ", style=palette.text_muted)
                line_text.append("   ", style=palette.text_muted)
                line_text.append(diff_line.content, style=palette.text_secondary)

            lines.append(line_text)

        content = Group(*lines)
        file_icon = Icons.get_file_icon(filename)
        title_text = f"[{palette.text_secondary}]{file_icon} {filename}[/]"

        return Panel(
            content,
            title=title_text,
            border_style=palette.border_default,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def render_simple(
        filename: str,
        additions: List[str] = None,
        deletions: List[str] = None,
        context: List[str] = None,
    ) -> Panel:
        """Render simple diff display."""
        palette = get_palette()
        lines = []

        if context:
            for line in context:
                text = Text(f"  {line}")
                text.stylize(palette.text_muted)
                lines.append(text)

        if deletions:
            for line in deletions:
                text = Text(f"- {line}")
                text.stylize(palette.diff_removed)
                lines.append(text)

        if additions:
            for line in additions:
                text = Text(f"+ {line}")
                text.stylize(palette.diff_added)
                lines.append(text)

        content = Group(*lines) if lines else Text("No changes", style=palette.text_muted)
        file_icon = Icons.get_file_icon(filename)

        return Panel(
            content,
            title=f"[{palette.text_secondary}]{file_icon} {filename}[/]",
            border_style=palette.border_default,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def render_inline(old_string: str, new_string: str) -> Text:
        """Render inline diff for small changes."""
        palette = get_palette()
        text = Text()
        text.append(old_string, style=f"strike {palette.diff_removed}")
        text.append(" → ", style=palette.text_muted)
        text.append(new_string, style=f"bold {palette.diff_added}")
        return text


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def create_separator(label: Optional[str] = None, width: int = 60) -> Rule:
    """Create a styled separator."""
    palette = get_palette()
    if label:
        return Rule(label, style=palette.border_default)
    return Rule(style=palette.border_default)


def create_status_bar(
    status: str,
    model: str = "",
    tokens: int = 0,
) -> Text:
    """Create a status bar."""
    palette = get_palette()

    status_configs = {
        "ready": ("◉", palette.success, "Ready"),
        "thinking": ("◐", palette.warning, "Thinking"),
        "executing": ("▶", palette.info, "Executing"),
        "error": ("✖", palette.error, "Error"),
    }

    icon, color, label = status_configs.get(status, status_configs["ready"])

    text = Text()
    text.append(f" {icon} ", style=f"bold {color}")
    text.append(label, style=color)

    if model:
        text.append(f" │ ", style=palette.text_muted)
        text.append(model, style=palette.info)

    if tokens > 0:
        text.append(f" │ ", style=palette.text_muted)
        text.append(f"{tokens:,} tokens", style=palette.text_muted)

    return text
