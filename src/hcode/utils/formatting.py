"""
Rich Terminal UI Formatting Utilities.

Provides beautiful terminal output with syntax highlighting, markdown rendering,
spinners, progress indicators, and colored status messages.
"""

from __future__ import annotations

import os
import platform
from contextlib import contextmanager
from enum import Enum
from typing import Any, Generator

from rich import box
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Platform detection for emoji support
IS_WINDOWS = platform.system() == "Windows"

SUPPORTS_EMOJI = not IS_WINDOWS or "WT_SESSION" in os.environ


class StatusType(Enum):
    """Status message types."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


# Emoji/icon mappings with fallbacks
ICONS = {
    "success": "" if SUPPORTS_EMOJI else "+",
    "error": "" if SUPPORTS_EMOJI else "X",
    "warning": "" if SUPPORTS_EMOJI else "!",
    "info": "" if SUPPORTS_EMOJI else "i",
    "debug": "" if SUPPORTS_EMOJI else "D",
    "rocket": "" if SUPPORTS_EMOJI else ">",
    "robot": "" if SUPPORTS_EMOJI else "[AI]",
    "tool": "" if SUPPORTS_EMOJI else "[T]",
    "search": "" if SUPPORTS_EMOJI else "?",
    "fire": "" if SUPPORTS_EMOJI else "*",
    "sparkles": "" if SUPPORTS_EMOJI else "*",
    "check": "" if SUPPORTS_EMOJI else "[+]",
    "cross": "" if SUPPORTS_EMOJI else "[X]",
    "clock": "" if SUPPORTS_EMOJI else "[T]",
    "money": "" if SUPPORTS_EMOJI else "$",
    "file": "" if SUPPORTS_EMOJI else "[F]",
    "folder": "" if SUPPORTS_EMOJI else "[D]",
    "code": "" if SUPPORTS_EMOJI else "<>",
    "terminal": "" if SUPPORTS_EMOJI else ">_",
    "thinking": "" if SUPPORTS_EMOJI else "...",
    "wave": "" if SUPPORTS_EMOJI else "o/",
    "lightning": "" if SUPPORTS_EMOJI else "!",
}

# Custom theme for HCode
HCODE_THEME = Theme(
    {
        "hcode.success": "bold green",
        "hcode.error": "bold red",
        "hcode.warning": "bold yellow",
        "hcode.info": "bold cyan",
        "hcode.debug": "dim",
        "hcode.prompt": "bold cyan",
        "hcode.response": "green",
        "hcode.code": "bright_white on grey23",
        "hcode.filename": "bold blue",
        "hcode.line_number": "dim cyan",
        "hcode.token_count": "dim magenta",
        "hcode.cost": "dim green",
    }
)

# Global console instance
console = Console(theme=HCODE_THEME)


def get_icon(name: str) -> str:
    """Get icon/emoji with fallback for terminal compatibility."""
    return ICONS.get(name, "")


def format_status(message: str, status: StatusType, prefix: bool = True) -> Text:
    """
    Format a status message with appropriate styling.

    Args:
        message: The message to format
        status: Type of status message
        prefix: Whether to include icon prefix

    Returns:
        Rich Text object with styling
    """
    styles = {
        StatusType.SUCCESS: ("hcode.success", "success"),
        StatusType.ERROR: ("hcode.error", "error"),
        StatusType.WARNING: ("hcode.warning", "warning"),
        StatusType.INFO: ("hcode.info", "info"),
        StatusType.DEBUG: ("hcode.debug", "debug"),
    }

    style, icon_name = styles[status]
    text = Text()

    if prefix:
        text.append(f"{get_icon(icon_name)} ", style=style)

    text.append(message, style=style)
    return text


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(format_status(message, StatusType.SUCCESS))


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(format_status(message, StatusType.ERROR))


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(format_status(message, StatusType.WARNING))


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(format_status(message, StatusType.INFO))


def print_debug(message: str) -> None:
    """Print a debug message."""
    console.print(format_status(message, StatusType.DEBUG))


def render_code(
    code: str,
    language: str = "python",
    line_numbers: bool = True,
    start_line: int = 1,
    highlight_lines: set[int] | None = None,
    theme: str = "monokai",
) -> Syntax:
    """
    Render code with syntax highlighting.

    Args:
        code: Source code to render
        language: Programming language for highlighting
        line_numbers: Show line numbers
        start_line: Starting line number
        highlight_lines: Set of line numbers to highlight
        theme: Syntax highlighting theme

    Returns:
        Rich Syntax object
    """
    return Syntax(
        code,
        language,
        line_numbers=line_numbers,
        start_line=start_line,
        highlight_lines=highlight_lines,
        theme=theme,
        word_wrap=True,
    )


def render_markdown(content: str) -> Markdown:
    """
    Render markdown content.

    Args:
        content: Markdown text to render

    Returns:
        Rich Markdown object
    """
    return Markdown(content)


def render_panel(
    content: Any,
    title: str | None = None,
    subtitle: str | None = None,
    border_style: str = "blue",
    expand: bool = True,
) -> Panel:
    """
    Render content in a styled panel.

    Args:
        content: Content to display in panel
        title: Panel title
        subtitle: Panel subtitle
        border_style: Border color/style
        expand: Whether panel should expand to full width

    Returns:
        Rich Panel object
    """
    return Panel(
        content,
        title=title,
        subtitle=subtitle,
        border_style=border_style,
        expand=expand,
        box=box.ROUNDED,
    )


def create_table(
    title: str | None = None,
    columns: list[tuple[str, str]] | None = None,
    box_style: Any = box.ROUNDED,
) -> Table:
    """
    Create a styled table.

    Args:
        title: Table title
        columns: List of (name, style) tuples for columns
        box_style: Rich box style

    Returns:
        Rich Table object
    """
    table = Table(title=title, box=box_style)

    if columns:
        for name, style in columns:
            table.add_column(name, style=style)

    return table


def create_progress(
    description: str = "Working...",
    show_spinner: bool = True,
    transient: bool = False,
) -> Progress:
    """
    Create a progress bar/spinner.

    Args:
        description: Task description
        show_spinner: Whether to show spinner
        transient: Remove when complete

    Returns:
        Rich Progress object
    """
    columns = []

    if show_spinner and not IS_WINDOWS:
        columns.append(SpinnerColumn())

    columns.extend(
        [
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        ]
    )

    return Progress(
        *columns,
        console=console,
        transient=transient,
    )


@contextmanager
def spinner(message: str = "Working...") -> Generator[None, None, None]:
    """
    Context manager for showing a spinner during operations.

    Args:
        message: Message to show with spinner

    Usage:
        with spinner("Loading..."):
            do_something()
    """
    if IS_WINDOWS:
        console.print(f"[dim]{message}[/dim]")
        yield
        return

    with console.status(message, spinner="dots"):
        yield


@contextmanager
def live_display(renderable: Any, refresh_rate: int = 10) -> Generator[Live, None, None]:
    """
    Context manager for live-updating display.

    Args:
        renderable: Initial content to display
        refresh_rate: Refresh rate per second

    Yields:
        Live object for updating
    """
    with Live(renderable, console=console, refresh_per_second=refresh_rate) as live:
        yield live


def format_tokens(input_tokens: int, output_tokens: int, show_total: bool = True) -> Text:
    """
    Format token usage display.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        show_total: Whether to show total

    Returns:
        Formatted Text object
    """
    text = Text()
    text.append("tokens: ", style="dim")
    text.append(f"{input_tokens:,}", style="cyan")
    text.append(" in | ", style="dim")
    text.append(f"{output_tokens:,}", style="green")
    text.append(" out", style="dim")

    if show_total:
        text.append(" | ", style="dim")
        text.append(f"{input_tokens + output_tokens:,}", style="magenta")
        text.append(" total", style="dim")

    return text


def format_cost(cost: float, currency: str = "$") -> Text:
    """
    Format cost display.

    Args:
        cost: Cost in dollars
        currency: Currency symbol

    Returns:
        Formatted Text object
    """
    text = Text()
    text.append(f"{currency}{cost:.4f}", style="hcode.cost")
    return text


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_file_path(path: str, max_length: int = 50) -> Text:
    """
    Format file path for display.

    Args:
        path: File path
        max_length: Maximum length before truncation

    Returns:
        Formatted Text object
    """
    text = Text()
    text.append(get_icon("file") + " ", style="dim")

    if len(path) > max_length:
        # Truncate from middle
        half = (max_length - 3) // 2
        path = f"{path[:half]}...{path[-half:]}"

    text.append(path, style="hcode.filename")
    return text


def format_diff_stats(additions: int, deletions: int) -> Text:
    """
    Format diff statistics.

    Args:
        additions: Number of lines added
        deletions: Number of lines removed

    Returns:
        Formatted Text object
    """
    text = Text()
    text.append(f"+{additions}", style="green")
    text.append(" / ", style="dim")
    text.append(f"-{deletions}", style="red")
    return text


def print_banner(version: str = "1.0.0") -> None:
    """Print the HCode banner."""
    banner = f"""
[bold cyan]╦ ╦┌─┐┌─┐┌┬┐┌─┐[/bold cyan]
[bold cyan]╠═╣│  │ │ ││├┤ [/bold cyan]
[bold cyan]╩ ╩└─┘└─┘─┴┘└─┘[/bold cyan]
[dim]Universal AI Coding Assistant[/dim]
[dim]v{version} | Claude + GPT[/dim]
"""
    console.print(Panel(banner.strip(), border_style="cyan", box=box.DOUBLE))


def print_welcome_tips() -> None:
    """Print welcome tips."""
    tips = [
        f"[cyan]{get_icon('info')} Tip:[/cyan] Use [bold]--help[/bold] on any command for details",
        f"[cyan]{get_icon('info')} Tip:[/cyan] Press [bold]Ctrl+C[/bold] anytime to safely interrupt",
        f"[cyan]{get_icon('info')} Tip:[/cyan] Use [bold]--stream[/bold] for real-time responses",
        f"[cyan]{get_icon('info')} Tip:[/cyan] Try [bold]hcode chat[/bold] for interactive mode",
    ]
    console.print("\n".join(tips) + "\n")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def wrap_in_panel(
    content: str,
    title: str | None = None,
    status: StatusType = StatusType.INFO,
) -> Panel:
    """
    Wrap content in a status-colored panel.

    Args:
        content: Content to wrap
        title: Panel title
        status: Status type for coloring

    Returns:
        Rich Panel object
    """
    colors = {
        StatusType.SUCCESS: "green",
        StatusType.ERROR: "red",
        StatusType.WARNING: "yellow",
        StatusType.INFO: "blue",
        StatusType.DEBUG: "dim",
    }

    return Panel(
        content,
        title=f"[bold]{title}[/bold]" if title else None,
        border_style=colors[status],
        box=box.ROUNDED,
    )
