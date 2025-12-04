"""
HCode Futuristic Animations and Loading Effects
Smooth, non-blocking terminal animations.
"""

from rich.console import Console
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.style import Style
from rich.panel import Panel
from rich.align import Align
from typing import Optional, Iterator, List, Callable, Any
import time
import asyncio
import threading
from contextlib import contextmanager
from dataclasses import dataclass

from .theme import get_theme, get_palette, ColorUtils


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
# ANIMATED MESSAGE
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class AnimatedMessage:
    """A message with animated components."""

    prefix_icon: str
    message: str
    suffix_frames: List[str]
    color: str = "#00FFFF"

    def render(self, frame: int) -> Text:
        """Render the animated message at a specific frame."""
        text = Text()
        text.append(f"{self.prefix_icon} ", style=f"bold {self.color}")
        text.append(self.message, style=f"{self.color}")
        text.append(
            f" {self.suffix_frames[frame % len(self.suffix_frames)]}", style=f"bold {self.color}"
        )
        return text


# ═══════════════════════════════════════════════════════════════════════
# CYBER PROGRESS
# ═══════════════════════════════════════════════════════════════════════


class CyberProgress:
    """Futuristic progress bar with custom styling."""

    def __init__(
        self,
        console: Console,
        description: str = "Processing",
        spinner_name: str = "neural",
        bar_color: Optional[str] = None,
        complete_color: Optional[str] = None,
    ):
        self.console = console
        self.description = description
        self.spinner_name = spinner_name
        self.bar_color = bar_color
        self.complete_color = complete_color

    @contextmanager
    def track(self, total: int):
        """Context manager for tracking progress."""
        palette = get_palette()
        bar_color = self.bar_color or palette.primary
        complete_color = self.complete_color or palette.success

        progress = Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn(f"[bold {bar_color}]{self.description}"),
            BarColumn(
                bar_width=40,
                style=f"{bar_color}",
                complete_style=f"bold {complete_color}",
                finished_style=f"bold {complete_color}",
            ),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        )

        with progress:
            task = progress.add_task(self.description, total=total)
            yield lambda advance=1: progress.update(task, advance=advance)


# ═══════════════════════════════════════════════════════════════════════
# STREAMING TEXT
# ═══════════════════════════════════════════════════════════════════════


class StreamingText:
    """Typewriter effect for streaming text output."""

    def __init__(
        self,
        console: Console,
        color: Optional[str] = None,
        speed: float = 0.02,
    ):
        self.console = console
        self.color = color
        self.speed = speed

    async def stream(self, text: str) -> None:
        """Stream text with typewriter effect (async)."""
        palette = get_palette()
        color = self.color or palette.text_primary

        for char in text:
            self.console.print(char, end="", style=color)
            await asyncio.sleep(self.speed)
        self.console.print()

    def stream_sync(self, text: str) -> None:
        """Synchronous version of stream."""
        palette = get_palette()
        color = self.color or palette.text_primary

        for char in text:
            self.console.print(char, end="", style=color)
            time.sleep(self.speed)
        self.console.print()

    def stream_words(self, text: str, word_delay: float = 0.05) -> None:
        """Stream text word by word."""
        palette = get_palette()
        color = self.color or palette.text_primary

        words = text.split()
        for i, word in enumerate(words):
            if i > 0:
                self.console.print(" ", end="")
            self.console.print(word, end="", style=color)
            time.sleep(word_delay)
        self.console.print()


# ═══════════════════════════════════════════════════════════════════════
# GLITCH EFFECT
# ═══════════════════════════════════════════════════════════════════════


class GlitchEffect:
    """Apply glitch effect to text."""

    GLITCH_CHARS = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`░▒▓█"

    @classmethod
    def glitch_text(cls, text: str, intensity: float = 0.1) -> str:
        """Apply random glitch characters to text."""
        import random

        result = []
        for char in text:
            if random.random() < intensity and char != " ":
                result.append(random.choice(cls.GLITCH_CHARS))
            else:
                result.append(char)
        return "".join(result)

    @classmethod
    def animated_glitch(
        cls,
        console: Console,
        text: str,
        duration: float = 1.0,
        frames: int = 10,
    ) -> None:
        """Display text with animated glitch effect (sync)."""
        palette = get_palette()
        frame_duration = duration / frames

        with Live(console=console, refresh_per_second=20, transient=True) as live:
            # Glitch in
            for i in range(frames):
                intensity = 1.0 - (i / frames)
                glitched = cls.glitch_text(text, intensity)
                live.update(Text(glitched, style=f"bold {palette.primary}"))
                time.sleep(frame_duration)

            # Show clean text
            live.update(Text(text, style=f"bold {palette.primary}"))

    @classmethod
    async def animated_glitch_async(
        cls,
        console: Console,
        text: str,
        duration: float = 1.0,
        frames: int = 10,
    ) -> None:
        """Display text with animated glitch effect (async)."""
        palette = get_palette()
        frame_duration = duration / frames

        with Live(console=console, refresh_per_second=20, transient=True) as live:
            for i in range(frames):
                intensity = 1.0 - (i / frames)
                glitched = cls.glitch_text(text, intensity)
                live.update(Text(glitched, style=f"bold {palette.primary}"))
                await asyncio.sleep(frame_duration)

            live.update(Text(text, style=f"bold {palette.primary}"))


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

    @contextmanager
    def thinking(self, message: str = "Thinking"):
        """Context manager for thinking animation."""
        palette = get_palette()
        spinner_text = Text()
        spinner_text.append("◈ ", style=f"bold {palette.secondary}")
        spinner_text.append(f"{message}", style=f"bold {palette.primary}")

        with self.console.status(
            spinner_text,
            spinner="dots",
            spinner_style=f"bold {palette.primary}",
        ):
            yield


# ═══════════════════════════════════════════════════════════════════════
# WAVE ANIMATION
# ═══════════════════════════════════════════════════════════════════════


class WaveAnimation:
    """Wave animation for processing state."""

    WAVE_CHARS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"]

    def __init__(
        self,
        console: Console,
        width: int = 10,
        message: str = "",
    ):
        self.console = console
        self.width = width
        self.message = message
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start wave animation."""
        self._stop_event.clear()
        palette = get_palette()

        def animate():
            offset = 0
            while not self._stop_event.is_set():
                wave = ""
                for i in range(self.width):
                    char_idx = (i + offset) % len(self.WAVE_CHARS)
                    wave += self.WAVE_CHARS[char_idx]

                text = Text()
                if self.message:
                    text.append(f"{self.message} ", style=palette.text_secondary)
                text.append(wave, style=f"bold {palette.primary}")

                if self._live:
                    self._live.update(text)

                offset = (offset + 1) % len(self.WAVE_CHARS)
                time.sleep(0.1)

        self._live = Live(
            Text("", style=palette.primary),
            console=self.console,
            refresh_per_second=15,
            transient=True,
        )
        self._live.start()

        self._thread = threading.Thread(target=animate, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop wave animation."""
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
# PULSING TEXT
# ═══════════════════════════════════════════════════════════════════════


class PulsingText:
    """Text that pulses between colors."""

    def __init__(
        self,
        console: Console,
        text: str,
        colors: Optional[List[str]] = None,
        interval: float = 0.5,
    ):
        palette = get_palette()
        self.console = console
        self.text = text
        self.colors = colors or [palette.primary, palette.secondary]
        self.interval = interval
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start pulsing animation."""
        self._stop_event.clear()

        def animate():
            color_index = 0
            while not self._stop_event.is_set():
                color = self.colors[color_index % len(self.colors)]
                text = Text(self.text, style=f"bold {color}")
                if self._live:
                    self._live.update(text)
                color_index += 1
                time.sleep(self.interval)

        self._live = Live(
            Text(self.text, style=f"bold {self.colors[0]}"),
            console=self.console,
            refresh_per_second=4,
            transient=True,
        )
        self._live.start()

        self._thread = threading.Thread(target=animate, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop pulsing animation."""
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
# COUNTDOWN
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
