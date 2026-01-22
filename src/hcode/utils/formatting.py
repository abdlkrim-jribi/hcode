

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
from rich.text import Text
from rich.theme import Theme

IS_WINDOWS = platform.system() == "Windows"
SUPPORTS_EMOJI = not IS_WINDOWS or "WT_SESSION" in os.environ


class StatusType(Enum):
    """Enum representing status message types.

    Attributes:
        SUCCESS: Success status.
        ERROR: Error status.
        WARNING: Warning status.
        INFO: Info status.
        DEBUG: Debug status.
    """

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

# Icon mapping for different status types and UI elements
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
console = Console(theme=HCODE_THEME)


def get_icon(name: str) -> str:
    """Return the icon string for a given name.

    Args:
        name (str): The symbolic name of the icon (e.g., ``"success"``).

    Returns:
        str: The corresponding icon character or an empty string if not found.
    """


    return ICONS.get(name, "")


def format_status(message: str, status: StatusType, prefix: bool = True) -> Text:
    """Format a status message with appropriate styling and optional prefix.

    Args:
        message (str): The message text to display.
        status (StatusType): The status enum indicating the message type (e.g., SUCCESS, ERROR).
        prefix (bool, optional): Whether to prepend the status icon. Defaults to True.

    Returns:
        Text: A Rich `Text` object with the styled message ready for console output.
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
    """Print a success message to the console.

    Args:
        message: The success message to display.

    Returns:
        None

    Raises:
        None
    """
    console.print(format_status(message, StatusType.SUCCESS))


def print_error(message: str) -> None:
    """Print an error message to the console.

    Args:
        message: The error message to display.

    Returns:
        None

    Raises:
        None
    """
    console.print(format_status(message, StatusType.ERROR))


def print_warning(message: str) -> None:
    """Print a warning message to the console.

    Args:
        message: The warning message to display.

    Returns:
        None

    Raises:
        None
    """
    console.print(format_status(message, StatusType.WARNING))


def print_info(message: str) -> None:
    """Print an informational message to the console.

    Args:
        message: The informational message to display.

    Returns:
        None

    Raises:
        None
    """
    console.print(format_status(message, StatusType.INFO))


def print_debug(message: str) -> None:
    """Print a debug message to the console.

    Args:
        message: The debug message to display.

    Returns:
        None

    Raises:
        None
    """
    console.print(format_status(message, StatusType.DEBUG))


def render_code(
    code: str,
    language: str = "python",
    line_numbers: bool = True,
    start_line: int = 1,
    highlight_lines: set[int] | None = None,
    theme: str = "monokai",
) -> Syntax:
    """Render source code as a ``rich`` ``Syntax`` object.

    Args:
        code: The source code string.
        language: The programming language for syntax highlighting.
        line_numbers: Whether to show line numbers.
        start_line: The starting line number.
        highlight_lines: Optional set of line numbers to highlight.
        theme: The colour theme to use.

    Returns:
        A ``Syntax`` object ready for printing.

    Raises:
        None
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
    """Render a markdown string as a ``rich`` ``Markdown`` object.

    Args:
        content: The markdown text to render.

    Returns:
        A ``Markdown`` object.

    Raises:
        None
    """
    return Markdown(content)


def render_panel(
    content: Any,
    title: str | None = None,
    subtitle: str | None = None,
    border_style: str = "blue",
    expand: bool = True,
) -> Panel:
    """Wrap content in a styled ``rich`` ``Panel``.

    Args:
        content: The renderable content to place inside the panel.
        title: Optional panel title.
        subtitle: Optional panel subtitle.
        border_style: Colour/style for the border.
        expand: Whether the panel should expand to fill width.

    Returns:
        A ``Panel`` object.

    Raises:
        None
    """
    return Panel(
        content,
        title=title,
        subtitle=subtitle,
        border_style=border_style,
        expand=expand,
        box=box.ROUNDED,
    )





def create_progress(
    description: str = "Working...",
    show_spinner: bool = True,
    transient: bool = False,
) -> Progress:
    """Create a ``rich`` ``Progress`` bar.

    Args:
        description: Text displayed next to the progress bar.
        show_spinner: Whether to include a spinner column (disabled on Windows).
        transient: If ``True`` the progress bar disappears after completion.

    Returns:
        A ``Progress`` instance ready to be used as a context manager.

    Raises:
        None
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
    return Progress(*columns, console=console, transient=transient)


@contextmanager
def spinner(message: str = "Working...") -> Generator[None, None, None]:
    """Display a temporary spinner while a block of code runs.

    Args:
        message: Text to show next to the spinner.

    Yields:
        Nothing – the context manager handles the spinner lifecycle.

    Raises:
        None
    """
    with Live(
        render_panel(
            Text(message, style="bold"),
            border_style="green",
            title="",
        ),
        refresh_per_second=10,
    ) as live:
        try:
            yield
        finally:
            live.stop()


def print_tokens(
    input_tokens: int,
    output_tokens: int,
    show_total: bool = True,
) -> Text:
    """Format token usage statistics as a ``rich`` ``Text`` object.

    Args:
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        show_total: Whether to include the combined total.

    Returns:
        A ``Text`` object containing the formatted token counts.

    Raises:
        None
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
    """Format a monetary cost value.

    Args:
        cost: The numeric cost.
        currency: Currency symbol to prepend (default ``$``).

    Returns:
        A ``Text`` object with the formatted cost.

    Raises:
        None
    """
    text = Text()
    text.append(f"{currency}{cost:.4f}", style="hcode.cost")
    return text


def format_duration(seconds: float) -> str:
    """Convert a duration in seconds to a human‑readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        A string representing the duration in ms, s, m s, or h m.

    Raises:
        None
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


def format_file_path(path: str, max_length: int = 50) -> Text:
    """Truncate and style a file path for terminal display.

    Args:
        path: The full file path.
        max_length: Maximum length before truncation occurs.

    Returns:
        A ``Text`` object with the possibly truncated path.

    Raises:
        None
    """
    text = Text()
    text.append(get_icon("file") + " ", style="dim")
    if len(path) > max_length:
        half = (max_length - 3) // 2
        path = f"{path[:half]}...{path[-half:]}"
    text.append(path, style="hcode.filename")
    return text


def format_diff_stats(additions: int, deletions: int) -> Text:
    """Create a ``rich`` ``Text`` summary of diff statistics.

    Args:
        additions: Number of added lines.
        deletions: Number of removed lines.

    Returns:
        A ``Text`` object showing ``+`` additions and ``-`` deletions.

    Raises:
        None
    """
    text = Text()
    text.append(f"+{additions}", style="green")
    text.append(" / ", style="dim")
    text.append(f"-{deletions}", style="red")
    return text


def print_banner(version: str = "1.0.0") -> None:
    """Print a colourful ASCII banner with the given version.

    Args:
        version: The version string to display.

    Returns:
        None

    Raises:
        None
    """
    banner = (
        "\n[bold cyan]╦ ╦┌─┐┌─┐┌┬┐┌─┐[/bold cyan]\n"
        "[bold cyan]╠═╣│  │ │ ││├┤ [/bold cyan]\n"
        "[bold cyan]╩ ╩└─┘└─┘─┴┘└─┘[/bold cyan]\n"
        "[dim]Universal AI Coding Assistant[/dim]\n"
        f"[dim]v{version} | Claude + GPT[/dim]"
    )
    console.print(Panel(banner.strip(), border_style="cyan", box=box.DOUBLE))


def print_welcome_tips() -> None:
    """Print a short list of helpful usage tips.

    Returns:
        None

    Raises:
        None
    """
    tips = [
        f"[cyan]{get_icon('info')} Tip:[/cyan] Use [bold]--help[/bold] on any command for details",
        f"[cyan]{get_icon('info')} Tip:[/cyan] Press [bold]Ctrl+C[/bold] anytime to safely interrupt",
        f"[cyan]{get_icon('info')} Tip:[/cyan] Use [bold]--stream[/bold] for real‑time responses",
        f"[cyan]{get_icon('info')} Tip:[/cyan] Try [bold]hcode chat[/bold] for interactive mode",
    ]
    console.print("\n".join(tips) + "\n")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to a maximum length, adding a suffix if needed.

    Args:
        text: The original string.
        max_length: Maximum allowed length including the suffix.
        suffix: The string to append when truncation occurs.

    Returns:
        The possibly truncated string.

    Raises:
        None
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def wrap_in_panel(
    content: str,
    title: str | None = None,
    status: StatusType = StatusType.INFO,
) -> Panel:
    """Wrap text content in a coloured panel based on status.

    Args:
        content: The text to display inside the panel.
        title: Optional panel title.
        status: The status determining the border colour.

    Returns:
        A ``Panel`` object.

    Raises:
        None
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
