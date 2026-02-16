"""
HCode Futuristic Animations and Loading Effects
Smooth, non-blocking terminal animations.
"""

import threading
import time
from contextlib import contextmanager
from typing import Optional, List

from rich.console import Console
from rich.live import Live
from rich.text import Text

from .theme import get_palette

# ═══════════════════════════════════════════════════════════════════════
# CUSTOM SPINNERS
# ═══════════════════════════════════════════════════════════════════════

CYBER_SPINNERS = {
    "pulse": {
        "frames": ["◉", "○", "◉", "○", "◉", "●", "◉", "●"],
        "interval": 120,
    },
    "data_flow": {
        "frames": [
            "▰▱▱▱▱▱▱",
            "▰▰▱▱▱▱▱",
            "▰▰▰▱▱▱▱",
            "▰▰▰▰▱▱▱",
            "▰▰▰▰▰▱▱",
            "▰▰▰▰▰▰▱",
            "▰▰▰▰▰▰▰",
            "▱▰▰▰▰▰▰",
            "▱▱▰▰▰▰▰",
            "▱▱▱▰▰▰▰",
            "▱▱▱▱▰▰▰",
            "▱▱▱▱▱▰▰",
            "▱▱▱▱▱▱▰",
            "▱▱▱▱▱▱▱",
        ],
        "interval": 80,
    },
    "neural": {
        "frames": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "interval": 80,
    },
    "quantum": {
        "frames": ["∙∙∙", "●∙∙", "∙●∙", "∙∙●", "∙●∙", "●∙∙"],
        "interval": 150,
    },
    "matrix": {
        "frames": ["█▓▒░", "▓▒░█", "▒░█▓", "░█▓▒"],
        "interval": 100,
    },
    "orbit": {
        "frames": ["◐", "◓", "◑", "◒"],
        "interval": 100,
    },
    "dna": {
        "frames": ["╔══╗", "║╔═╝", "╚╝╔╗", "══╚╝", "╔╗══", "╝╚═╗", "╔══╝", "╚══╗"],
        "interval": 100,
    },
    "cyber_scan": {
        "frames": [
            "[■□□□□□□□□□]",
            "[■■□□□□□□□□]",
            "[■■■□□□□□□□]",
            "[■■■■□□□□□□]",
            "[■■■■■□□□□□]",
            "[■■■■■■□□□□]",
            "[■■■■■■■□□□]",
            "[■■■■■■■■□□]",
            "[■■■■■■■■■□]",
            "[■■■■■■■■■■]",
            "[□■■■■■■■■■]",
            "[□□■■■■■■■■]",
            "[□□□■■■■■■■]",
            "[□□□□■■■■■■]",
            "[□□□□□■■■■■]",
            "[□□□□□□■■■■]",
            "[□□□□□□□■■■]",
            "[□□□□□□□□■■]",
            "[□□□□□□□□□■]",
            "[□□□□□□□□□□]",
        ],
        "interval": 50,
    },
    "neon_wave": {
        "frames": [
            "⣾⣽⣻⢿⡿⣟⣯⣷",
            "⣷⣾⣽⣻⢿⡿⣟⣯",
            "⣯⣷⣾⣽⣻⢿⡿⣟",
            "⣟⣯⣷⣾⣽⣻⢿⡿",
            "⡿⣟⣯⣷⣾⣽⣻⢿",
            "⢿⡿⣟⣯⣷⣾⣽⣻",
            "⣻⢿⡿⣟⣯⣷⣾⣽",
            "⣽⣻⢿⡿⣟⣯⣷⣾",
        ],
        "interval": 80,
    },
    "circuit": {
        "frames": [
            "◈───◈",
            "◈─◈─◈",
            "◈◈───",
            "─◈───",
            "──◈──",
            "───◈─",
            "───◈◈",
            "──◈─◈",
        ],
        "interval": 100,
    },
    "heartbeat": {
        "frames": ["♡", "♥", "♡", "♥", "♥", "♡"],
        "interval": 150,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# CYBER PROGRESS
# ═══════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════
# GLITCH EFFECT
# ═══════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════
# THINKING ANIMATION
# ═══════════════════════════════════════════════════════════════════════


class ThinkingAnimation:
    """AI thinking indicator with futuristic styling."""

    THINKING_MESSAGES = [
        "Analyzing...",
        "Processing...",
        "Thinking...",
        "Reasoning...",
        "Evaluating...",
        "Computing...",
        "Synthesizing...",
    ]

    THINKING_ICONS = ["◐", "◓", "◑", "◒"]

    def __init__(
            self,
            console: Console,
            style: str = "cyber",
            custom_messages: Optional[List[str]] = None,
    ):
        self.console = console
        self.style = style
        self.messages = custom_messages or self.THINKING_MESSAGES
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start thinking animation."""
        self._stop_event.clear()
        palette = get_palette()

        def animate():
            msg_index = 0
            icon_index = 0
            while not self._stop_event.is_set():
                message = self.messages[msg_index % len(self.messages)]
                icon = self.THINKING_ICONS[icon_index % len(self.THINKING_ICONS)]

                text = Text()
                text.append(f" {icon} ", style=f"bold {palette.warning}")
                text.append(message, style=palette.warning)

                if self._live:
                    self._live.update(text)

                icon_index += 1
                if icon_index % len(self.THINKING_ICONS) == 0:
                    msg_index += 1

                time.sleep(0.15)

        self._live = Live(
            Text(f" {self.THINKING_ICONS[0]} {self.messages[0]}", style=palette.warning),
            console=self.console,
            refresh_per_second=10,
            transient=True,
        )
        self._live.start()

        self._thread = threading.Thread(target=animate, daemon=True)
        self._thread.start()

    def stop(self, result_message: Optional[str] = None) -> None:
        """Stop thinking animation."""
        self._stop_event.set()
        if self._live:
            self._live.stop()
            self._live = None

        if result_message:
            palette = get_palette()
            self.console.print(f"[{palette.success}]✔[/] {result_message}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


# ═══════════════════════════════════════════════════════════════════════
# WAVE ANIMATION
# ═══════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════

class Countdown:
    """Countdown timer animation."""

    def __init__(
            self,
            console: Console,
            seconds: int,
            message: str = "Starting in",
    ):
        self.console = console
        self.seconds = seconds
        self.message = message

    def run(self) -> None:
        """Run countdown."""
        palette = get_palette()

        with Live(console=self.console, refresh_per_second=4, transient=True) as live:
            for remaining in range(self.seconds, 0, -1):
                text = Text()
                text.append(f"{self.message} ", style=palette.text_secondary)
                text.append(str(remaining), style=f"bold {palette.primary}")
                text.append("...", style=palette.text_muted)
                live.update(text)
                time.sleep(1)


# ═══════════════════════════════════════════════════════════════════════
# LOADING DOTS
# ═══════════════════════════════════════════════════════════════════════


class LoadingDots:
    """Animated loading dots."""

    def __init__(
            self,
            console: Console,
            message: str = "Loading",
            max_dots: int = 3,
    ):
        self.console = console
        self.message = message
        self.max_dots = max_dots
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start loading dots animation."""
        self._stop_event.clear()
        palette = get_palette()

        def animate():
            dots = 0
            while not self._stop_event.is_set():
                text = Text()
                text.append(self.message, style=palette.text_secondary)
                text.append("." * dots, style=f"bold {palette.primary}")
                text.append(" " * (self.max_dots - dots), style="")
                if self._live:
                    self._live.update(text)
                dots = (dots + 1) % (self.max_dots + 1)
                time.sleep(0.4)

        self._live = Live(
            Text(self.message, style=palette.text_secondary),
            console=self.console,
            refresh_per_second=4,
            transient=True,
        )
        self._live.start()

        self._thread = threading.Thread(target=animate, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop loading dots animation."""
        self._stop_event.set()
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


# ═══════════════════════════════════════════════════════════════════════
# HELPER CONTEXT MANAGERS
# ═══════════════════════════════════════════════════════════════════════


@contextmanager
def spinner(
        console: Console,
        message: str = "Processing",
        spinner_type: str = "dots",
):
    """Context manager for spinner animation."""
    palette = get_palette()

    with console.status(
            f"[bold {palette.primary}]{message}",
            spinner=spinner_type,
            spinner_style=f"bold {palette.primary}",
    ):
        yield


@contextmanager
def thinking(console: Console, message: str = "Thinking"):
    """Context manager for thinking animation."""
    anim = ThinkingAnimation(console)
    anim.start()
    try:
        yield anim
    finally:
        anim.stop()


@contextmanager
def loading(console: Console, message: str = "Loading"):
    """Context manager for loading animation."""
    dots = LoadingDots(console, message)
    dots.start()
    try:
        yield dots
    finally:
        dots.stop()


def countdown(console: Console, seconds: int, message: str = "Starting in") -> None:
    """Run countdown animation."""
    Countdown(console, seconds, message).run()
