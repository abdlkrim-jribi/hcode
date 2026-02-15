"""
Compatibility layer for legacy CLI styles.

Provides backwards-compatible components for code that was using cli.styles.
"""

import threading
import time
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.text import Text

from hcode.ui.icons import Icons as NewIcons
from hcode.ui.theme import get_palette


# ============================================================
# ANIMATION WRAPPERS
# ============================================================


@contextmanager
def spinner(message: str = "Processing", spinner_type: str = "dots"):
    """
    Context manager for spinner animation.

    This is a compatibility wrapper that uses the global console.
    """
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
    palette = get_palette()
    console = Console()
    NewIcons()

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
