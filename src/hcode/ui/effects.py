"""
HCode Special Visual Effects
Advanced terminal effects and visual enhancements.
"""

from rich.console import Console, RenderableType
from rich.text import Text
from rich.panel import Panel
from rich.live import Live
from rich.align import Align
from rich.style import Style
from typing import List, Optional, Callable, Any
import random
import time
import asyncio
import threading
from dataclasses import dataclass

from .theme import get_palette, get_theme, ColorUtils


# ═══════════════════════════════════════════════════════════════════════
# MATRIX RAIN EFFECT
# ═══════════════════════════════════════════════════════════════════════


class MatrixRain:
    """Matrix-style falling code rain effect."""

    CHARS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ0123456789"
    ASCII_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*"

    def __init__(
        self,
        console: Console,
        width: int = 60,
        height: int = 10,
        use_unicode: bool = True,
    ):
        self.console = console
        self.width = width
        self.height = height
        self.chars = self.CHARS if use_unicode else self.ASCII_CHARS
        self._stop_event = threading.Event()
        self._columns: List[int] = []

    def _init_columns(self) -> None:
        """Initialize column positions."""
        self._columns = [random.randint(-self.height, 0) for _ in range(self.width)]

    def _render_frame(self) -> Text:
        """Render a single frame of the matrix."""
        palette = get_palette()
        lines = []

        for row in range(self.height):
            line = Text()
            for col in range(self.width):
                col_pos = self._columns[col]

                if row == col_pos:
                    # Brightest (head of stream)
                    char = random.choice(self.chars)
                    line.append(char, style=f"bold #FFFFFF")
                elif row < col_pos and row > col_pos - 5:
                    # Bright trail
                    char = random.choice(self.chars)
                    fade = 1 - ((col_pos - row) / 5)
                    green = int(255 * fade)
                    line.append(char, style=f"#{0:02x}{green:02x}{0:02x}")
                elif row < col_pos:
                    # Dim trail
                    char = random.choice(self.chars)
                    line.append(char, style="#004400")
                else:
                    line.append(" ")

            lines.append(line)

        # Update column positions
        for i in range(len(self._columns)):
            self._columns[i] += 1
            if self._columns[i] > self.height + 5:
                self._columns[i] = random.randint(-10, 0)

        result = Text()
        for line in lines:
            result.append_text(line)
            result.append("\n")

        return result

    def run(self, duration: float = 3.0) -> None:
        """Run matrix rain for specified duration."""
        self._init_columns()
        end_time = time.time() + duration

        with Live(console=self.console, refresh_per_second=15, transient=True) as live:
            while time.time() < end_time:
                frame = self._render_frame()
                live.update(frame)
                time.sleep(0.05)


# ═══════════════════════════════════════════════════════════════════════
# SCAN LINE EFFECT
# ═══════════════════════════════════════════════════════════════════════


class ScanLine:
    """Horizontal scan line effect."""

    def __init__(
        self,
        console: Console,
        width: int = 60,
        message: str = "",
    ):
        self.console = console
        self.width = width
        self.message = message

    def run(self, duration: float = 2.0) -> None:
        """Run scan line effect."""
        palette = get_palette()
        steps = int(duration / 0.05)

        with Live(console=self.console, refresh_per_second=20, transient=True) as live:
            for i in range(steps):
                pos = i % self.width
                line = Text()

                for j in range(self.width):
                    if j == pos:
                        line.append("█", style=f"bold {palette.primary}")
                    elif abs(j - pos) < 3:
                        line.append("▓", style=palette.secondary)
                    elif abs(j - pos) < 5:
                        line.append("░", style=palette.text_muted)
                    else:
                        line.append(" ")

                if self.message:
                    msg = Text()
                    msg.append(f"\n{self.message}", style=palette.text_secondary)
                    live.update(Align.center(Text.assemble(line, msg)))
                else:
                    live.update(Align.center(line))

                time.sleep(0.05)


# ═══════════════════════════════════════════════════════════════════════
# PULSE EFFECT
# ═══════════════════════════════════════════════════════════════════════


class PulseEffect:
    """Pulsing glow effect on text."""

    def __init__(
        self,
        console: Console,
        text: str,
        base_color: Optional[str] = None,
        glow_color: Optional[str] = None,
    ):
        self.console = console
        self.text = text
        palette = get_palette()
        self.base_color = base_color or palette.primary
        self.glow_color = glow_color or palette.secondary

    def run(self, cycles: int = 3, cycle_duration: float = 0.5) -> None:
        """Run pulse effect."""
        steps_per_cycle = 10
        step_duration = cycle_duration / steps_per_cycle

        with Live(console=self.console, refresh_per_second=20, transient=True) as live:
            for _ in range(cycles):
                # Pulse up
                for i in range(steps_per_cycle):
                    factor = i / steps_per_cycle
                    color = ColorUtils.blend(self.base_color, self.glow_color, factor)
                    live.update(Text(self.text, style=f"bold {color}"))
                    time.sleep(step_duration)

                # Pulse down
                for i in range(steps_per_cycle):
                    factor = 1 - (i / steps_per_cycle)
                    color = ColorUtils.blend(self.base_color, self.glow_color, factor)
                    live.update(Text(self.text, style=f"bold {color}"))
                    time.sleep(step_duration)


# ═══════════════════════════════════════════════════════════════════════
# REVEAL EFFECT
# ═══════════════════════════════════════════════════════════════════════


class RevealEffect:
    """Character-by-character reveal effect."""

    def __init__(
        self,
        console: Console,
        text: str,
        reveal_char: str = "█",
    ):
        self.console = console
        self.text = text
        self.reveal_char = reveal_char

    def run(self, duration: float = 1.0) -> None:
        """Run reveal effect."""
        palette = get_palette()
        text_length = len(self.text)
        step_duration = duration / text_length

        with Live(console=self.console, refresh_per_second=30, transient=True) as live:
            for i in range(text_length + 1):
                revealed = self.text[:i]
                hidden = self.reveal_char * (text_length - i)

                display = Text()
                display.append(revealed, style=f"bold {palette.primary}")
                display.append(hidden, style=palette.text_muted)

                live.update(display)
                time.sleep(step_duration)


# ═══════════════════════════════════════════════════════════════════════
# SCRAMBLE EFFECT
# ═══════════════════════════════════════════════════════════════════════


class ScrambleEffect:
    """Text scramble/decode effect."""

    SCRAMBLE_CHARS = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(
        self,
        console: Console,
        text: str,
    ):
        self.console = console
        self.text = text

    def run(self, duration: float = 1.5) -> None:
        """Run scramble effect."""
        palette = get_palette()
        text_length = len(self.text)
        steps = int(duration / 0.03)
        chars_per_step = text_length / steps

        revealed = [False] * text_length
        reveal_count = 0

        with Live(console=self.console, refresh_per_second=30, transient=True) as live:
            for step in range(steps + text_length):
                display = Text()

                # Reveal more characters
                chars_to_reveal = int(step * chars_per_step) - reveal_count
                for _ in range(chars_to_reveal):
                    # Find unrevealed character
                    candidates = [i for i, r in enumerate(revealed) if not r]
                    if candidates:
                        idx = random.choice(candidates)
                        revealed[idx] = True
                        reveal_count += 1

                # Build display string
                for i, char in enumerate(self.text):
                    if revealed[i]:
                        display.append(char, style=f"bold {palette.primary}")
                    elif char == " ":
                        display.append(" ")
                    else:
                        display.append(random.choice(self.SCRAMBLE_CHARS), style=palette.text_muted)

                live.update(display)
                time.sleep(0.03)


# ═══════════════════════════════════════════════════════════════════════
# BORDER GLOW EFFECT
# ═══════════════════════════════════════════════════════════════════════


class BorderGlow:
    """Animated glowing border effect."""

    def __init__(
        self,
        console: Console,
        content: RenderableType,
        width: int = 60,
    ):
        self.console = console
        self.content = content
        self.width = width

    def run(self, duration: float = 2.0) -> None:
        """Run border glow effect."""
        palette = get_palette()
        colors = [
            palette.primary,
            palette.secondary,
            palette.accent,
            palette.success,
            palette.warning,
        ]

        steps = int(duration / 0.1)

        with Live(console=self.console, refresh_per_second=10, transient=True) as live:
            for i in range(steps):
                color = colors[i % len(colors)]
                panel = Panel(
                    self.content,
                    border_style=f"bold {color}",
                    width=self.width,
                )
                live.update(panel)
                time.sleep(0.1)


# ═══════════════════════════════════════════════════════════════════════
# PARTICLE BURST EFFECT
# ═══════════════════════════════════════════════════════════════════════


class ParticleBurst:
    """Particle burst animation."""

    PARTICLES = ["*", ".", "·", "°", "✦", "✧", "⋆"]

    def __init__(
        self,
        console: Console,
        center_text: str = "",
        width: int = 40,
        height: int = 10,
    ):
        self.console = console
        self.center_text = center_text
        self.width = width
        self.height = height

    def run(self, duration: float = 1.5) -> None:
        """Run particle burst effect."""
        palette = get_palette()
        steps = int(duration / 0.05)

        # Generate particles
        num_particles = 30
        particles = []
        for _ in range(num_particles):
            angle = random.uniform(0, 6.28)  # 2*pi
            speed = random.uniform(0.5, 2)
            particles.append(
                {
                    "x": self.width // 2,
                    "y": self.height // 2,
                    "vx": speed * (angle - 3.14),  # cos approximation
                    "vy": speed * (angle - 1.57),  # sin approximation
                    "char": random.choice(self.PARTICLES),
                    "life": 1.0,
                }
            )

        with Live(console=self.console, refresh_per_second=20, transient=True) as live:
            for step in range(steps):
                # Create frame
                frame = [[" " for _ in range(self.width)] for _ in range(self.height)]

                # Update and draw particles
                for p in particles:
                    if p["life"] > 0:
                        x, y = int(p["x"]), int(p["y"])
                        if 0 <= x < self.width and 0 <= y < self.height:
                            frame[y][x] = p["char"]

                        # Update position
                        p["x"] += p["vx"]
                        p["y"] += p["vy"]
                        p["life"] -= 0.05

                # Build display
                text = Text()
                for row in frame:
                    for char in row:
                        if char != " ":
                            text.append(char, style=f"bold {palette.primary}")
                        else:
                            text.append(char)
                    text.append("\n")

                live.update(Align.center(text))
                time.sleep(0.05)


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def matrix_rain(console: Console, duration: float = 3.0, width: int = 60, height: int = 10) -> None:
    """Quick matrix rain effect."""
    MatrixRain(console, width, height).run(duration)


def scan_line(console: Console, message: str = "", duration: float = 2.0) -> None:
    """Quick scan line effect."""
    ScanLine(console, message=message).run(duration)


def pulse_text(console: Console, text: str, cycles: int = 3) -> None:
    """Quick pulse effect."""
    PulseEffect(console, text).run(cycles)


def reveal_text(console: Console, text: str, duration: float = 1.0) -> None:
    """Quick reveal effect."""
    RevealEffect(console, text).run(duration)


def scramble_text(console: Console, text: str, duration: float = 1.5) -> None:
    """Quick scramble effect."""
    ScrambleEffect(console, text).run(duration)


def particle_burst(console: Console, text: str = "", duration: float = 1.5) -> None:
    """Quick particle burst effect."""
    ParticleBurst(console, text).run(duration)
