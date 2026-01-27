"""
Compatibility layer for legacy CLI styles.

Provides backwards-compatible components for code that was using cli.styles.
"""

from dataclasses import dataclass
from typing import List, Optional

from rich.align import Align
from rich.box import ROUNDED
from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

from hcode.ui.icons import Icons as NewIcons
from hcode.ui.theme import get_palette


# ============================================================
# COLORS COMPATIBILITY
# ============================================================


class Colors:
    """Legacy color constants - maps to theme palette."""

    @staticmethod
    def _get(attr: str) -> str:
        palette = get_palette()
        return getattr(palette, attr, "#FFFFFF")

    # Primary colors
    PRIMARY = property(lambda self: get_palette().primary)
    SECONDARY = property(lambda self: get_palette().secondary)
    ACCENT = property(lambda self: get_palette().accent)

    # Status colors
    SUCCESS = property(lambda self: get_palette().success)
    ERROR = property(lambda self: get_palette().error)
    WARNING = property(lambda self: get_palette().warning)
    INFO = property(lambda self: get_palette().info)

    # Text colors
    TEXT_PRIMARY = property(lambda self: get_palette().text_primary)
    TEXT_SECONDARY = property(lambda self: get_palette().text_secondary)
    TEXT_MUTED = property(lambda self: get_palette().text_muted)

    # Other
    BORDER_DEFAULT = property(lambda self: get_palette().border_default)
    THINKING = property(lambda self: get_palette().secondary)


# Make it work as both class attributes and instance properties
Colors.PRIMARY = get_palette().primary
Colors.SECONDARY = get_palette().secondary
Colors.ACCENT = get_palette().accent
Colors.SUCCESS = get_palette().success
Colors.ERROR = get_palette().error
Colors.WARNING = get_palette().warning
Colors.INFO = get_palette().info
Colors.TEXT_PRIMARY = get_palette().text_primary
Colors.TEXT_SECONDARY = get_palette().text_secondary
Colors.TEXT_MUTED = get_palette().text_muted
Colors.BORDER_DEFAULT = get_palette().border_default
Colors.THINKING = get_palette().secondary
Colors.TERTIARY = get_palette().accent  # Alias for accent

# Todo status colors
Colors.TODO_PENDING = get_palette().text_muted
Colors.TODO_IN_PROGRESS = get_palette().warning
Colors.TODO_COMPLETED = get_palette().success
Colors.TODO_BLOCKED = get_palette().error
Colors.TODO_SKIPPED = get_palette().text_muted


# ============================================================
# LINES / BORDERS COMPATIBILITY
# ============================================================


class Lines:
    """Border line characters."""

    HORIZONTAL = "─"
    VERTICAL = "│"
    CORNER_TL = "╭"
    CORNER_TR = "╮"
    CORNER_BL = "╰"
    CORNER_BR = "╯"
    T_DOWN = "┬"
    T_UP = "┴"
    T_RIGHT = "├"
    T_LEFT = "┤"
    CROSS = "┼"
    DOUBLE_H = "═"
    DOUBLE_V = "║"


def get_default_box():
    """Return default box style."""
    return ROUNDED


# ============================================================
# STATUS ICONS
# ============================================================


def get_status_icon(status: str) -> str:
    """Get icon for status."""
    icons = NewIcons()
    status_map = {
        "success": icons.CHECK,
        "error": icons.ERROR,
        "warning": icons.WARNING,
        "info": icons.INFO,
        "running": icons.LOADING,
        "pending": icons.PENDING,
        "thinking": icons.THINKING,
    }
    return status_map.get(status.lower(), icons.INFO)


# ============================================================
# STYLED PANEL
# ============================================================


class StyledPanel:
    """Factory for creating styled panels - legacy compatibility."""

    @staticmethod
    def success(content: str, title: str = "Success") -> Panel:
        """Create success panel."""
        palette = get_palette()
        icons = NewIcons()
        return Panel(
            Text(content, style=f"bold {palette.success}"),
            title=f"[bold {palette.success}]{icons.CHECK} {title}[/]",
            border_style=palette.success,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def error(content: str, title: str = "Error") -> Panel:
        """Create error panel."""
        palette = get_palette()
        icons = NewIcons()
        return Panel(
            Text(content, style=palette.error),
            title=f"[bold {palette.error}]{icons.ERROR} {title}[/]",
            border_style=palette.error,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def warning(content: str, title: str = "Warning") -> Panel:
        """Create warning panel."""
        palette = get_palette()
        icons = NewIcons()
        return Panel(
            Text(content, style=palette.warning),
            title=f"[bold {palette.warning}]{icons.WARNING} {title}[/]",
            border_style=palette.warning,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def info(content: str, title: str = "Info") -> Panel:
        """Create info panel."""
        palette = get_palette()
        icons = NewIcons()
        return Panel(
            Text(content, style=palette.info),
            title=f"[{palette.info}]{icons.INFO} {title}[/]",
            border_style=palette.info,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def thinking(content: str, title: str = "Thinking") -> Panel:
        """Create thinking/processing panel."""
        palette = get_palette()
        icons = NewIcons()
        return Panel(
            Text(content, style=palette.secondary),
            title=f"[bold {palette.secondary}]{icons.THINKING} {title}[/]",
            border_style=palette.secondary,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def code(code: str, language: str = "python", title: str = "Code") -> Panel:
        """Create code panel with syntax highlighting."""
        palette = get_palette()
        icons = NewIcons()
        syntax = Syntax(code, language, theme="dracula", line_numbers=True, word_wrap=True)
        return Panel(
            syntax,
            title=f"[{palette.text_secondary}]{icons.CODE} {title}[/]",
            border_style=palette.border_default,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def agent(content: str, title: str = "Agent") -> Panel:
        """Create agent response panel."""
        palette = get_palette()
        icons = NewIcons()
        return Panel(
            Text(content),
            title=f"[bold {palette.primary}]{icons.AGENT} {title}[/]",
            border_style=palette.primary,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def user(content: str, title: str = "You") -> Panel:
        """Create user message panel."""
        palette = get_palette()
        icons = NewIcons()
        return Panel(
            Text(content, style=palette.text_secondary),
            title=f"[{palette.text_secondary}]{icons.USER} {title}[/]",
            border_style=palette.border_default,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def tool(content: str, tool_name: str) -> Panel:
        """Create tool execution panel."""
        palette = get_palette()
        icons = NewIcons()
        return Panel(
            Text(content, style=palette.text_secondary),
            title=f"[{palette.secondary}]{icons.TOOL} {tool_name}[/]",
            border_style=palette.secondary,
            box=ROUNDED,
            padding=(0, 1),
        )


# ============================================================
# TODO DISPLAY
# ============================================================


@dataclass
class TodoItem:
    """Represents a todo item."""

    content: str
    status: str = "pending"  # pending, in_progress, completed
    active_form: str = ""  # Present tense form of the task (e.g., "Running tests")

    def get_icon(self) -> str:
        icons = NewIcons()
        if self.status == "completed":
            return icons.SUCCESS
        elif self.status == "in_progress":
            return icons.LOADING
        return icons.PENDING

    def get_style(self) -> str:
        palette = get_palette()
        if self.status == "completed":
            return palette.success
        elif self.status == "in_progress":
            return palette.warning
        return palette.text_muted


class TodoDisplay:
    """Display for todo items - legacy compatibility."""

    @staticmethod
    def render(todos: List[TodoItem], title: str = "Tasks") -> Panel:
        """Render todo list as panel."""
        palette = get_palette()
        icons = NewIcons()

        if not todos:
            content = Text("No tasks", style=palette.text_muted)
        else:
            lines = []
            for todo in todos:
                line = Text()
                line.append(f"{todo.get_icon()} ", style=todo.get_style())
                line.append(todo.content, style=todo.get_style())
                lines.append(line)
            content = Group(*lines)

        return Panel(
            content,
            title=f"[{palette.primary}]{icons.TODO} {title}[/]",
            border_style=palette.border_default,
            box=ROUNDED,
            padding=(0, 1),
        )


# ============================================================
# HEADER / FOOTER / STATUS LINE
# ============================================================


class Header:
    """Application header display."""

    @staticmethod
    def render(
        title: str = "HCode",
        subtitle: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Panel:
        """Render header panel."""
        palette = get_palette()

        content = Text()
        content.append(title, style=f"bold {palette.primary}")
        if version:
            content.append(f" v{version}", style=palette.text_muted)
        if subtitle:
            content.append(f"\n{subtitle}", style=palette.text_secondary)

        return Panel(
            Align.center(content), border_style=palette.primary, box=ROUNDED, padding=(0, 2)
        )


class Footer:
    """Application footer display."""

    @staticmethod
    def render(
        left: str = "",
        center: str = "",
        right: str = "",
    ) -> Text:
        """Render footer text."""
        palette = get_palette()

        text = Text()
        if left:
            text.append(left, style=palette.text_muted)
        if center:
            text.append(f"  {center}  ", style=palette.text_secondary)
        if right:
            text.append(right, style=palette.text_muted)

        return text


class StatusLine:
    """Status line display."""

    @staticmethod
    def render(
        status: str = "Ready",
        icon: Optional[str] = None,
        details: Optional[str] = None,
        message: Optional[str] = None,
        model: Optional[str] = None,
        tokens: Optional[int] = None,
    ) -> Text:
        """Render status line with optional model and token info."""
        palette = get_palette()
        icons = NewIcons()

        text = Text()
        text.append(icon or icons.INFO, style=palette.primary)
        text.append(f" {status}", style=palette.text_primary)

        if message:
            text.append(f" - {message}", style=palette.text_muted)

        if details:
            text.append(f" - {details}", style=palette.text_muted)

        if model:
            text.append(f" │ ", style=palette.text_muted)
            text.append(f"Model: ", style=palette.text_muted)
            text.append(f"{model}", style=palette.secondary)

        if tokens is not None:
            text.append(f" │ ", style=palette.text_muted)
            text.append(f"Tokens: ", style=palette.text_muted)
            text.append(f"{tokens:,}", style=palette.primary)

        return text


# ============================================================
# PROMPT
# ============================================================


class Prompt:
    """Input prompt styling."""

    @staticmethod
    def render(label: str = "You", symbol: str = "❯") -> Text:
        """Render input prompt."""
        palette = get_palette()

        text = Text()
        text.append(f"{label} ", style=f"bold {palette.primary}")
        text.append(f"{symbol} ", style=palette.secondary)

        return text

    @staticmethod
    def get_string(label: str = "You", symbol: str = "❯") -> str:
        """Get prompt as plain string for input()."""
        return f"{label} {symbol} "


# ============================================================
# SEPARATOR
# ============================================================


class Separator:
    """Visual separator."""

    @staticmethod
    def render(label: Optional[str] = None, style: Optional[str] = None) -> Rule:
        """Render separator rule."""
        palette = get_palette()
        return Rule(title=label, style=style or palette.text_muted, characters="─")

    @staticmethod
    def thin(label: Optional[str] = None) -> Rule:
        """Render a thin separator."""
        palette = get_palette()
        return Rule(title=label, style=palette.text_muted, characters="─")

    @staticmethod
    def thick(label: Optional[str] = None) -> Rule:
        """Render a thick separator."""
        palette = get_palette()
        return Rule(title=label, style=palette.text_muted, characters="━")

    @staticmethod
    def double(label: Optional[str] = None) -> Rule:
        """Render a double-line separator."""
        palette = get_palette()
        return Rule(title=label, style=palette.text_muted, characters="═")


# ============================================================
# PROGRESS BAR
# ============================================================

from contextlib import contextmanager
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn


@contextmanager
def progress_bar(
    description: str = "Processing",
    total: Optional[int] = None,
):
    """Context manager for progress bar display."""
    palette = get_palette()

    with Progress(
        SpinnerColumn(style=palette.primary),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style=palette.primary, finished_style=palette.success),
        TaskProgressColumn(),
    ) as progress:
        if total:
            task = progress.add_task(description, total=total)
            yield progress, task
        else:
            task = progress.add_task(description)
            yield progress, task


# ============================================================
# SPINNER (Compatible wrapper)
# ============================================================


@contextmanager
def spinner(message: str = "Processing", spinner_type: str = "dots"):
    """
    Context manager for spinner animation.

    This is a compatibility wrapper that uses the global console.
    """
    from rich.console import Console

    palette = get_palette()
    console = Console()

    with console.status(
        f"[bold {palette.primary}]{message}",
        spinner=spinner_type,
        spinner_style=f"bold {palette.primary}",
    ):
        yield


@contextmanager
def thinking(message: str = "Thinking"):
    """
    Context manager for thinking animation.

    This is a compatibility wrapper that uses the global console.
    """
    from rich.console import Console
    from rich.live import Live
    import time
    import threading

    palette = get_palette()
    console = Console()
    icons = NewIcons()

    THINKING_ICONS = ["◐", "◓", "◑", "◒"]
    stop_event = threading.Event()
    live = None

    def animate():
        nonlocal live
        icon_index = 0
        while not stop_event.is_set():
            icon = THINKING_ICONS[icon_index % len(THINKING_ICONS)]
            text = Text()
            text.append(f" {icon} ", style=f"bold {palette.warning}")
            text.append(message, style=palette.warning)
            if live:
                live.update(text)
            icon_index += 1
            time.sleep(0.15)

    live = Live(
        Text(f" {THINKING_ICONS[0]} {message}", style=palette.warning),
        console=console,
        refresh_per_second=10,
        transient=True,
    )

    try:
        live.start()
        thread = threading.Thread(target=animate, daemon=True)
        thread.start()
        yield
    finally:
        stop_event.set()
        if live:
            live.stop()
