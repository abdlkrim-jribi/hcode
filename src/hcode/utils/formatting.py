"""Rich Terminal UI Formatting Utilities.

Provides beautiful terminal output with syntax highlighting, markdown rendering,
spinners, progress indicators, and colored status messages.

This module offers a collection of helper functions and classes to render
rich text, tables, panels, and other UI components in the terminal. It
leverages the `rich` library to provide a consistent and visually
appealing experience across platforms.

Example:
    from hcode.utils.formatting import print_success
    print_success("Operation completed")
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
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
IS_WINDOWS = platform.system() == 'Windows'
SUPPORTS_EMOJI = not IS_WINDOWS or 'WT_SESSION' in os.environ

class StatusType(Enum):
    """Enum representing status message types.

    Attributes:
        SUCCESS: Success status.
        ERROR: Error status.
        WARNING: Warning status.
        INFO: Info status.
        DEBUG: Debug status.
    """
    SUCCESS = 'success'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    DEBUG = 'debug'
ICONS = {'success': '' if SUPPORTS_EMOJI else '+', 'error': '' if SUPPORTS_EMOJI else 'X', 'warning': '' if SUPPORTS_EMOJI else '!', 'info': '' if SUPPORTS_EMOJI else 'i', 'debug': '' if SUPPORTS_EMOJI else 'D', 'rocket': '' if SUPPORTS_EMOJI else '>', 'robot': '' if SUPPORTS_EMOJI else '[AI]', 'tool': '' if SUPPORTS_EMOJI else '[T]', 'search': '' if SUPPORTS_EMOJI else '?', 'fire': '' if SUPPORTS_EMOJI else '*', 'sparkles': '' if SUPPORTS_EMOJI else '*', 'check': '' if SUPPORTS_EMOJI else '[+]', 'cross': '' if SUPPORTS_EMOJI else '[X]', 'clock': '' if SUPPORTS_EMOJI else '[T]', 'money': '' if SUPPORTS_EMOJI else '$', 'file': '' if SUPPORTS_EMOJI else '[F]', 'folder': '' if SUPPORTS_EMOJI else '[D]', 'code': '' if SUPPORTS_EMOJI else '<>', 'terminal': '' if SUPPORTS_EMOJI else '>_', 'thinking': '' if SUPPORTS_EMOJI else '...', 'wave': '' if SUPPORTS_EMOJI else 'o/', 'lightning': '' if SUPPORTS_EMOJI else '!'}
HCODE_THEME = Theme({'hcode.success': 'bold green', 'hcode.error': 'bold red', 'hcode.warning': 'bold yellow', 'hcode.info': 'bold cyan', 'hcode.debug': 'dim', 'hcode.prompt': 'bold cyan', 'hcode.response': 'green', 'hcode.code': 'bright_white on grey23', 'hcode.filename': 'bold blue', 'hcode.line_number': 'dim cyan', 'hcode.token_count': 'dim magenta', 'hcode.cost': 'dim green'})
console = Console(theme=HCODE_THEME)

def get_icon(name: str) -> str:
    """get_icon description.

Args:
    name: description

Returns:
    description

Raises:
    Exception description"""
    return ICONS.get(name, '')

def format_status(message: str, status: StatusType, prefix: bool=True) -> Text:
    """format_status description.

Args:
    message: description
    status: description
    prefix: description

Returns:
    description

Raises:
    Exception description"""
    styles = {StatusType.SUCCESS: ('hcode.success', 'success'), StatusType.ERROR: ('hcode.error', 'error'), StatusType.WARNING: ('hcode.warning', 'warning'), StatusType.INFO: ('hcode.info', 'info'), StatusType.DEBUG: ('hcode.debug', 'debug')}
    style, icon_name = styles[status]
    text = Text()
    if prefix:
        text.append(f'{get_icon(icon_name)} ', style=style)
    text.append(message, style=style)
    return text

def print_success(message: str) -> None:
    """Print a success message to the console.

Args:
    message (str): The message to display.

Returns:
    None

Raises:
    None"""
    console.print(format_status(message, StatusType.SUCCESS))

def print_error(message: str) -> None:
    """print_error description.

Args:
    message: description

Returns:
    description

Raises:
    Exception description"""
    console.print(format_status(message, StatusType.ERROR))

def print_warning(message: str) -> None:
    """print_warning description.

Args:
    message: description

Returns:
    description

Raises:
    Exception description"""
    console.print(format_status(message, StatusType.WARNING))

def print_info(message: str) -> None:
    """print_info description.

Args:
    message: description

Returns:
    description

Raises:
    Exception description"""
    console.print(format_status(message, StatusType.INFO))

def print_debug(message: str) -> None:
    """print_debug description.

Args:
    message: description

Returns:
    description

Raises:
    Exception description"""
    console.print(format_status(message, StatusType.DEBUG))

def render_code(code: str, language: str='python', line_numbers: bool=True, start_line: int=1, highlight_lines: set[int] | None=None, theme: str='monokai') -> Syntax:
    """render_code description.

Args:
    code: description
    language: description
    line_numbers: description
    start_line: description
    highlight_lines: description
    theme: description

Returns:
    description

Raises:
    Exception description"""
    return Syntax(code, language, line_numbers=line_numbers, start_line=start_line, highlight_lines=highlight_lines, theme=theme, word_wrap=True)

def render_markdown(content: str) -> Markdown:
    """render_markdown description.

Args:
    content: description

Returns:
    description

Raises:
    Exception description"""
    return Markdown(content)

def render_panel(content: Any, title: str | None=None, subtitle: str | None=None, border_style: str='blue', expand: bool=True) -> Panel:
    """render_panel description.

Args:
    content: description
    title: description
    subtitle: description
    border_style: description
    expand: description

Returns:
    description

Raises:
    Exception description"""
    return Panel(content, title=title, subtitle=subtitle, border_style=border_style, expand=expand, box=box.ROUNDED)

def create_table(title: str | None=None, columns: list[tuple[str, str]] | None=None, box_style: Any=box.ROUNDED) -> Table:
    """create_table description.

Args:
    title: description
    columns: description
    box_style: description

Returns:
    description

Raises:
    Exception description"""
    table = Table(title=title, box=box_style)
    if columns:
        for name, style in columns:
            table.add_column(name, style=style)
    return table

def create_progress(description: str='Working...', show_spinner: bool=True, transient: bool=False) -> Progress:
    """create_progress description.

Args:
    description: description
    show_spinner: description
    transient: description

Returns:
    description

Raises:
    Exception description"""
    columns = []
    if show_spinner and (not IS_WINDOWS):
        columns.append(SpinnerColumn())
    columns.extend([TextColumn('[progress.description]{task.description}'), BarColumn(), TaskProgressColumn(), TimeElapsedColumn()])
    return Progress(*columns, console=console, transient=transient)

@contextmanager
def spinner(message: str='Working...') -> Generator[None, None, None]:
    """spinner description.

Args:
    message: description

Returns:
    description

Raises:
    Exception description"""
    if IS_WINDOWS:
        console.print(f'[dim]{message}[/dim]')
        yield
        return
    with console.status(message, spinner='dots'):
        yield

@contextmanager
def live_display(renderable: Any, refresh_rate: int=10) -> Generator[Live, None, None]:
    """live_display description.

Args:
    renderable: description
    refresh_rate: description

Returns:
    description

Raises:
    Exception description"""
    with Live(renderable, console=console, refresh_per_second=refresh_rate) as live:
        yield live

def format_tokens(input_tokens: int, output_tokens: int, show_total: bool=True) -> Text:
    """format_tokens description.

Args:
    input_tokens: description
    output_tokens: description
    show_total: description

Returns:
    description

Raises:
    Exception description"""
    text = Text()
    text.append('tokens: ', style='dim')
    text.append(f'{input_tokens:,}', style='cyan')
    text.append(' in | ', style='dim')
    text.append(f'{output_tokens:,}', style='green')
    text.append(' out', style='dim')
    if show_total:
        text.append(' | ', style='dim')
        text.append(f'{input_tokens + output_tokens:,}', style='magenta')
        text.append(' total', style='dim')
    return text

def format_cost(cost: float, currency: str='$') -> Text:
    """format_cost description.

Args:
    cost: description
    currency: description

Returns:
    description

Raises:
    Exception description"""
    text = Text()
    text.append(f'{currency}{cost:.4f}', style='hcode.cost')
    return text

def format_duration(seconds: float) -> str:
    """format_duration description.

Args:
    seconds: description

Returns:
    description

Raises:
    Exception description"""
    if seconds < 1:
        return f'{seconds * 1000:.0f}ms'
    elif seconds < 60:
        return f'{seconds:.1f}s'
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f'{minutes}m {secs}s'
    else:
        hours = int(seconds // 3600)
        minutes = int(seconds % 3600 // 60)
        return f'{hours}h {minutes}m'

def format_file_path(path: str, max_length: int=50) -> Text:
    """format_file_path description.

Args:
    path: description
    max_length: description

Returns:
    description

Raises:
    Exception description"""
    text = Text()
    text.append(get_icon('file') + ' ', style='dim')
    if len(path) > max_length:
        half = (max_length - 3) // 2
        path = f'{path[:half]}...{path[-half:]}'
    text.append(path, style='hcode.filename')
    return text

def format_diff_stats(additions: int, deletions: int) -> Text:
    """format_diff_stats description.

Args:
    additions: description
    deletions: description

Returns:
    description

Raises:
    Exception description"""
    text = Text()
    text.append(f'+{additions}', style='green')
    text.append(' / ', style='dim')
    text.append(f'-{deletions}', style='red')
    return text

def print_banner(version: str='1.0.0') -> None:
    """print_banner description.

Args:
    version: description

Returns:
    description

Raises:
    Exception description"""
    banner = f'\n[bold cyan]╦ ╦┌─┐┌─┐┌┬┐┌─┐[/bold cyan]\n[bold cyan]╠═╣│  │ │ ││├┤ [/bold cyan]\n[bold cyan]╩ ╩└─┘└─┘─┴┘└─┘[/bold cyan]\n[dim]Universal AI Coding Assistant[/dim]\n[dim]v{version} | Claude + GPT[/dim]\n'
    console.print(Panel(banner.strip(), border_style='cyan', box=box.DOUBLE))

def print_welcome_tips() -> None:
    """print_welcome_tips description.

Args:
    None

Returns:
    description

Raises:
    Exception description"""
    tips = [f"[cyan]{get_icon('info')} Tip:[/cyan] Use [bold]--help[/bold] on any command for details", f"[cyan]{get_icon('info')} Tip:[/cyan] Press [bold]Ctrl+C[/bold] anytime to safely interrupt", f"[cyan]{get_icon('info')} Tip:[/cyan] Use [bold]--stream[/bold] for real-time responses", f"[cyan]{get_icon('info')} Tip:[/cyan] Try [bold]hcode chat[/bold] for interactive mode"]
    console.print('\n'.join(tips) + '\n')

def truncate_text(text: str, max_length: int=100, suffix: str='...') -> str:
    """truncate_text description.

Args:
    text: description
    max_length: description
    suffix: description

Returns:
    description

Raises:
    Exception description"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def wrap_in_panel(content: str, title: str | None=None, status: StatusType=StatusType.INFO) -> Panel:
    """wrap_in_panel description.

Args:
    content: description
    title: description
    status: description

Returns:
    description

Raises:
    Exception description"""
    colors = {StatusType.SUCCESS: 'green', StatusType.ERROR: 'red', StatusType.WARNING: 'yellow', StatusType.INFO: 'blue', StatusType.DEBUG: 'dim'}
    return Panel(content, title=f'[bold]{title}[/bold]' if title else None, border_style=colors[status], box=box.ROUNDED)