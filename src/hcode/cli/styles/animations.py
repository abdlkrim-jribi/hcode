"""
Animation utilities for Hcode CLI.

Provides spinners, progress animations, and typing effects.
"""

import sys
import time
import threading
from typing import List, Optional, Callable, Iterator
from dataclasses import dataclass
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn

from .colors import Colors
from .icons import Spinners, Icons


# ============================================================
# CONSOLE
# ============================================================

console = Console()


# ============================================================
# SPINNER ANIMATION
# ============================================================

class AnimatedSpinner:
    """Animated spinner for long-running operations"""

    def __init__(
        self,
        message: str = "Processing",
        spinner_type: str = "dots",
        style: str = None
    ):
        self.message = message
        self.spinner_type = spinner_type
        self.style = style or Colors.PRIMARY
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._live: Optional[Live] = None

    def _get_frames(self) -> List[str]:
        """Get spinner frames"""
        spinners = {
            "dots": Spinners.DOTS,
            "line": Spinners.LINE,
            "arc": Spinners.ARC,
            "circle": Spinners.CIRCLE,
            "bounce": Spinners.BOUNCE,
            "pulse": Spinners.PULSE,
            "braille": Spinners.BRAILLE,
            "elegant": Spinners.ELEGANT,
            "simple": Spinners.SIMPLE,
            "growing": Spinners.GROWING,
        }
        return spinners.get(self.spinner_type, Spinners.DEFAULT)

    def start(self):
        """Start spinner animation"""
        self._stop_event.clear()

        spinner = Spinner("dots", text=self.message, style=self.style)
        self._live = Live(spinner, console=console, refresh_per_second=10, transient=True)
        self._live.start()

    def stop(self, final_message: str = None):
        """Stop spinner animation"""
        self._stop_event.set()
        if self._live:
            self._live.stop()
            self._live = None

        if final_message:
            console.print(f"[{Colors.SUCCESS}]{Icons().CHECK}[/] {final_message}")

    def update(self, message: str):
        """Update spinner message"""
        if self._live:
            spinner = Spinner("dots", text=message, style=self.style)
            self._live.update(spinner)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


@contextmanager
def spinner(message: str = "Processing", spinner_type: str = "dots"):
    """Context manager for spinner animation"""
    s = AnimatedSpinner(message, spinner_type)
    s.start()
    try:
        yield s
    finally:
        s.stop()


# ============================================================
# TYPING ANIMATION
# ============================================================

class TypingAnimation:
    """Typing effect for text output"""

    def __init__(
        self,
        text: str,
        speed: float = 0.03,
        style: str = None
    ):
        self.text = text
        self.speed = speed
        self.style = style

    def play(self):
        """Play typing animation"""
        for char in self.text:
            if self.style:
                console.print(f"[{self.style}]{char}[/]", end="")
            else:
                console.print(char, end="")
            sys.stdout.flush()
            time.sleep(self.speed)
        console.print()

    @staticmethod
    def stream(text_iterator: Iterator[str], style: str = None):
        """Stream text with typing effect"""
        for chunk in text_iterator:
            if style:
                console.print(f"[{style}]{chunk}[/]", end="")
            else:
                console.print(chunk, end="")
            sys.stdout.flush()
        console.print()


def type_text(text: str, speed: float = 0.03, style: str = None):
    """Convenience function for typing animation"""
    TypingAnimation(text, speed, style).play()


# ============================================================
# PROGRESS ANIMATION
# ============================================================

class ProgressAnimation:
    """Animated progress bar"""

    def __init__(
        self,
        total: int = 100,
        description: str = "Progress",
        bar_width: int = 40
    ):
        self.total = total
        self.description = description
        self.bar_width = bar_width
        self._progress: Optional[Progress] = None
        self._task_id = None

    def start(self):
        """Start progress animation"""
        from rich.progress import BarColumn, TaskProgressColumn

        self._progress = Progress(
            SpinnerColumn(),
            TextColumn(f"[{Colors.TEXT_SECONDARY}]{{task.description}}[/]"),
            BarColumn(
                complete_style=Colors.PRIMARY,
                finished_style=Colors.SUCCESS,
                bar_width=self.bar_width
            ),
            TaskProgressColumn(),
            console=console,
            transient=True
        )
        self._progress.start()
        self._task_id = self._progress.add_task(self.description, total=self.total)

    def update(self, advance: int = 1, description: str = None):
        """Update progress"""
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id,
                advance=advance,
                description=description or self.description
            )

    def set(self, completed: int):
        """Set progress to specific value"""
        if self._progress and self._task_id is not None:
            self._progress.update(self._task_id, completed=completed)

    def stop(self):
        """Stop progress animation"""
        if self._progress:
            self._progress.stop()
            self._progress = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


@contextmanager
def progress_bar(total: int = 100, description: str = "Progress"):
    """Context manager for progress bar"""
    p = ProgressAnimation(total, description)
    p.start()
    try:
        yield p
    finally:
        p.stop()


# ============================================================
# PULSING TEXT
# ============================================================

class PulsingText:
    """Text that pulses between colors"""

    def __init__(
        self,
        text: str,
        colors: List[str] = None,
        interval: float = 0.5
    ):
        self.text = text
        self.colors = colors or [Colors.PRIMARY, Colors.PRIMARY_LIGHT]
        self.interval = interval
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None

    def start(self):
        """Start pulsing animation"""
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
            console=console,
            refresh_per_second=4,
            transient=True
        )
        self._live.start()

        self._thread = threading.Thread(target=animate, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop pulsing animation"""
        self._stop_event.set()
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


# ============================================================
# COUNTDOWN ANIMATION
# ============================================================

class Countdown:
    """Countdown timer animation"""

    def __init__(self, seconds: int, message: str = "Starting in"):
        self.seconds = seconds
        self.message = message

    def run(self):
        """Run countdown"""
        with Live(console=console, refresh_per_second=4, transient=True) as live:
            for remaining in range(self.seconds, 0, -1):
                text = Text()
                text.append(f"{self.message} ", style=Colors.TEXT_SECONDARY)
                text.append(str(remaining), style=f"bold {Colors.PRIMARY}")
                text.append("...", style=Colors.TEXT_MUTED)
                live.update(text)
                time.sleep(1)


def countdown(seconds: int, message: str = "Starting in"):
    """Run countdown animation"""
    Countdown(seconds, message).run()


# ============================================================
# LOADING DOTS
# ============================================================

class LoadingDots:
    """Animated loading dots"""

    def __init__(self, message: str = "Loading", max_dots: int = 3):
        self.message = message
        self.max_dots = max_dots
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None

    def start(self):
        """Start loading dots animation"""
        self._stop_event.clear()

        def animate():
            dots = 0
            while not self._stop_event.is_set():
                text = Text()
                text.append(self.message, style=Colors.TEXT_SECONDARY)
                text.append("." * dots, style=Colors.PRIMARY)
                text.append(" " * (self.max_dots - dots), style="")
                if self._live:
                    self._live.update(text)
                dots = (dots + 1) % (self.max_dots + 1)
                time.sleep(0.4)

        self._live = Live(
            Text(self.message, style=Colors.TEXT_SECONDARY),
            console=console,
            refresh_per_second=4,
            transient=True
        )
        self._live.start()

        self._thread = threading.Thread(target=animate, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop loading dots animation"""
        self._stop_event.set()
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


# ============================================================
# THINKING ANIMATION
# ============================================================

class ThinkingAnimation:
    """Thinking animation with rotating messages"""

    MESSAGES = [
        "Analyzing...",
        "Processing...",
        "Thinking...",
        "Reasoning...",
        "Evaluating...",
    ]

    def __init__(self, custom_messages: List[str] = None):
        self.messages = custom_messages or self.MESSAGES
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None

    def start(self):
        """Start thinking animation"""
        self._stop_event.clear()

        def animate():
            msg_index = 0
            while not self._stop_event.is_set():
                message = self.messages[msg_index % len(self.messages)]
                text = Text()
                text.append(f" {Icons().THINKING} ", style=f"bold {Colors.THINKING}")
                text.append(message, style=Colors.THINKING)
                if self._live:
                    self._live.update(text)
                msg_index += 1
                time.sleep(1.5)

        self._live = Live(
            Text(f" {Icons().THINKING} {self.messages[0]}", style=Colors.THINKING),
            console=console,
            refresh_per_second=2,
            transient=True
        )
        self._live.start()

        self._thread = threading.Thread(target=animate, daemon=True)
        self._thread.start()

    def stop(self, result_message: str = None):
        """Stop thinking animation"""
        self._stop_event.set()
        if self._live:
            self._live.stop()
            self._live = None

        if result_message:
            console.print(f"[{Colors.SUCCESS}]{Icons().CHECK}[/] {result_message}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


@contextmanager
def thinking(custom_messages: List[str] = None):
    """Context manager for thinking animation"""
    t = ThinkingAnimation(custom_messages)
    t.start()
    try:
        yield t
    finally:
        t.stop()


# ============================================================
# WAVE ANIMATION
# ============================================================

class WaveAnimation:
    """Wave animation for processing state"""

    WAVE_CHARS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"]
    WAVE_CHARS_ASCII = ["_", ".", "-", "=", "#", "=", "-", "."]

    def __init__(self, width: int = 10, message: str = ""):
        self.width = width
        self.message = message
        # Use ASCII chars on Windows without Unicode support
        from .icons import USE_UNICODE
        self.chars = self.WAVE_CHARS if USE_UNICODE else self.WAVE_CHARS_ASCII
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None

    def start(self):
        """Start wave animation"""
        self._stop_event.clear()

        def animate():
            offset = 0
            while not self._stop_event.is_set():
                wave = ""
                for i in range(self.width):
                    char_idx = (i + offset) % len(self.chars)
                    wave += self.chars[char_idx]

                text = Text()
                if self.message:
                    text.append(f"{self.message} ", style=Colors.TEXT_SECONDARY)
                text.append(wave, style=Colors.PRIMARY)

                if self._live:
                    self._live.update(text)

                offset = (offset + 1) % len(self.chars)
                time.sleep(0.1)

        self._live = Live(
            Text("", style=Colors.PRIMARY),
            console=console,
            refresh_per_second=15,
            transient=True
        )
        self._live.start()

        self._thread = threading.Thread(target=animate, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop wave animation"""
        self._stop_event.set()
        if self._live:
            self._live.stop()
            self._live = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
