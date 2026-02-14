"""
HCode Futuristic UI Components
Custom panels, boxes, and interactive elements.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple, Dict

from rich.align import Align
from rich.box import Box, ROUNDED, SIMPLE
from rich.console import RenderableType, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from hcode.ui.theme import get_palette
from hcode.ui.icons import Icons

# ═══════════════════════════════════════════════════════════════════════
# CUSTOM BOX STYLES
# ═══════════════════════════════════════════════════════════════════════

# Futuristic double-edge box (8 lines required by Rich)
CYBER_BOX = Box("╔═╤╗\n" "║ │║\n" "╠═╪╣\n" "║ │║\n" "╠═╪╣\n" "╠═╪╣\n" "║ │║\n" "╚═╧╝\n")

# Neon glow simulation box
NEON_BOX = Box("▛▀▀▜\n" "▌  ▐\n" "▌──▐\n" "▌  ▐\n" "▌──▐\n" "▌──▐\n" "▌  ▐\n" "▙▄▄▟\n")

# Minimal tech box
TECH_BOX = Box("┏━┳┓\n" "┃ ┃┃\n" "┣━╋┫\n" "┃ ┃┃\n" "┣━╋┫\n" "┣━╋┫\n" "┃ ┃┃\n" "┗━┻┛\n")

# Rounded modern box
MODERN_BOX = Box("╭──╮\n" "│  │\n" "├──┤\n" "│  │\n" "├──┤\n" "├──┤\n" "│  │\n" "╰──╯\n")

# ASCII fallback box
ASCII_BOX = Box("+--+\n" "|  |\n" "+--+\n" "|  |\n" "+--+\n" "+--+\n" "|  |\n" "+--+\n")


# ═══════════════════════════════════════════════════════════════════════
# STATUS INDICATOR
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class StatusIndicator:
    """Futuristic status indicator with glow effect."""

    status: str
    color: str
    icon: str

    PRESETS = {
        "online": ("ONLINE", "#00FF00", Icons.ONLINE),
        "offline": ("OFFLINE", "#FF0000", Icons.OFFLINE),
        "loading": ("LOADING", "#FFFF00", Icons.LOADING),
        "error": ("ERROR", "#FF0055", Icons.ERROR),
        "success": ("SUCCESS", "#00FF88", Icons.SUCCESS),
        "warning": ("WARNING", "#FFB800", Icons.WARNING),
        "processing": ("PROCESSING", "#00FFFF", Icons.REFRESH),
        "ready": ("READY", "#00FFFF", Icons.PLAY),
        "thinking": ("THINKING", "#FFB800", Icons.THINKING),
        "paused": ("PAUSED", "#888888", Icons.PAUSE),
    }

    @classmethod
    def create(cls, preset: str) -> "StatusIndicator":
        """Create status indicator from preset name."""
        status, color, icon = cls.PRESETS.get(preset, cls.PRESETS["offline"])
        return cls(status, color, icon)

    def render(self) -> Text:
        """Render the status indicator as Rich Text."""
        text = Text()
        text.append(f"{self.icon} ", style=f"bold {self.color}")
        text.append(self.status, style=f"bold {self.color}")
        return text

    def render_compact(self) -> Text:
        """Render compact version (icon only)."""
        return Text(self.icon, style=f"bold {self.color}")


# ═══════════════════════════════════════════════════════════════════════
# CYBER PANEL
# ═══════════════════════════════════════════════════════════════════════


class CyberPanel:
    """Futuristic panel with customizable glow and styling."""

    def __init__(
        self,
        content: RenderableType,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        border_color: Optional[str] = None,
        glow_color: Optional[str] = None,
        box_style: Box = MODERN_BOX,
        status: Optional[str] = None,
        padding: Tuple[int, int] = (1, 2),
        width: Optional[int] = None,
    ):
        self.content = content
        self.title = title
        self.subtitle = subtitle
        self.border_color = border_color
        self.glow_color = glow_color
        self.box_style = box_style
        self.status = status
        self.padding = padding
        self.width = width

    def render(self) -> Panel:
        """Render the cyber panel."""
        palette = get_palette()
        border_color = self.border_color or palette.primary
        glow_color = self.glow_color or palette.secondary

        # Build title with optional status
        title_text = None
        if self.title:
            title_text = Text()
            title_text.append(Icons.DECO_LEFT, style=f"bold {glow_color}")
            title_text.append(f" {self.title} ", style=f"bold {border_color}")
            title_text.append(Icons.DECO_RIGHT, style=f"bold {glow_color}")

            if self.status:
                indicator = StatusIndicator.create(self.status)
                title_text.append("  ")
                title_text.append_text(indicator.render())

        # Build subtitle
        subtitle_text = None
        if self.subtitle:
            subtitle_text = Text(self.subtitle, style=f"italic {palette.text_muted}")

        return Panel(
            self.content,
            title=title_text,
            subtitle=subtitle_text,
            border_style=f"bold {border_color}",
            box=self.box_style,
            padding=self.padding,
            width=self.width,
        )


# ═══════════════════════════════════════════════════════════════════════
# METRIC CARD
# ═══════════════════════════════════════════════════════════════════════


class MetricCard:
    """Futuristic metric display card."""

    def __init__(
        self,
        label: str,
        value: str,
        icon: str = "●",
        trend: Optional[str] = None,  # "up", "down", "stable"
        color: Optional[str] = None,
        width: int = 20,
    ):
        self.label = label
        self.value = value
        self.icon = icon
        self.trend = trend
        self.color = color
        self.width = width

    def render(self) -> Panel:
        """Render the metric card."""
        palette = get_palette()
        color = self.color or palette.primary

        trend_icons = {
            "up": ("↑", palette.success),
            "down": ("↓", palette.error),
            "stable": ("→", palette.warning),
        }

        content = Text()
        content.append(f"{self.icon} ", style=f"bold {color}")
        content.append(f"{self.label}\n", style=f"bold {palette.text_muted}")
        content.append(f"{self.value}", style=f"bold {color}")

        if self.trend and self.trend in trend_icons:
            icon, trend_color = trend_icons[self.trend]
            content.append(f" {icon}", style=f"bold {trend_color}")

        return Panel(
            Align.center(content),
            border_style=f"{color}",
            box=ROUNDED,
            padding=(0, 1),
            width=self.width,
        )


# ═══════════════════════════════════════════════════════════════════════
# COMMAND PALETTE
# ═══════════════════════════════════════════════════════════════════════


class CommandPalette:
    """Futuristic command palette display."""

    def __init__(self, commands: List[Tuple[str, str, str]]):
        """
        Args:
            commands: List of (shortcut, command, description) tuples
        """
        self.commands = commands

    def render(self) -> Table:
        """Render the command palette."""
        palette = get_palette()

        table = Table(
            show_header=True,
            header_style=f"bold {palette.secondary}",
            border_style=palette.border_default,
            box=ROUNDED,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("⌨", style=f"bold {palette.warning}", width=8, justify="center")
        table.add_column("Command", style=f"bold {palette.primary}", width=15)
        table.add_column("Description", style=palette.text_secondary)

        for shortcut, command, description in self.commands:
            table.add_row(
                Text(shortcut, style=f"bold {palette.warning}"),
                Text(command, style=f"bold {palette.primary}"),
                Text(description, style=palette.text_secondary),
            )

        return table


# ═══════════════════════════════════════════════════════════════════════
# PROGRESS RING
# ═══════════════════════════════════════════════════════════════════════


class ProgressRing:
    """Futuristic circular progress indicator (ASCII representation)."""

    FRAMES = ["◜ ", " ◝", " ◞", "◟ "]  # Spinning
    COMPLETE_FRAMES = ["○", "◔", "◑", "◕", "●"]  # Fill animation

    @classmethod
    def spinning(cls, frame: int) -> str:
        """Get spinning frame."""
        return cls.FRAMES[frame % len(cls.FRAMES)]

    @classmethod
    def progress(cls, percentage: float) -> str:
        """Get progress frame based on percentage."""
        index = int((percentage / 100) * (len(cls.COMPLETE_FRAMES) - 1))
        return cls.COMPLETE_FRAMES[min(index, len(cls.COMPLETE_FRAMES) - 1)]

    @classmethod
    def render(cls, percentage: float, label: str = "") -> Text:
        """Render progress with label."""
        palette = get_palette()
        icon = cls.progress(percentage)

        text = Text()
        text.append(f"{icon} ", style=f"bold {palette.primary}")
        if label:
            text.append(f"{label} ", style=palette.text_secondary)
        text.append(f"{percentage:.0f}%", style=f"bold {palette.primary}")

        return text


# ═══════════════════════════════════════════════════════════════════════
# TOKEN COUNTER
# ═══════════════════════════════════════════════════════════════════════


class TokenCounter:
    """Futuristic token usage display."""

    def __init__(
        self,
        input_tokens: int,
        output_tokens: int,
        max_tokens: int = 100000,
    ):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.max_tokens = max_tokens

    def render(self) -> Text:
        """Render token counter."""
        palette = get_palette()
        total = self.input_tokens + self.output_tokens
        percentage = (total / self.max_tokens) * 100

        # Color based on usage
        if percentage < 50:
            color = palette.success
        elif percentage < 80:
            color = palette.warning
        else:
            color = palette.error

        text = Text()
        text.append("◈ ", style=f"bold {palette.secondary}")
        text.append(f"{self.input_tokens:,}", style=f"bold {palette.primary}")
        text.append(" in │ ", style=palette.text_muted)
        text.append(f"{self.output_tokens:,}", style=f"bold {palette.secondary}")
        text.append(" out │ ", style=palette.text_muted)
        text.append(f"{percentage:.1f}%", style=f"bold {color}")

        return text


# ═══════════════════════════════════════════════════════════════════════
# INFO CARD
# ═══════════════════════════════════════════════════════════════════════


class InfoCard:
    """Information display card with icon and content."""

    def __init__(
        self,
        title: str,
        content: str,
        icon: str = "ℹ",
        card_type: str = "info",  # info, success, warning, error
    ):
        self.title = title
        self.content = content
        self.icon = icon
        self.card_type = card_type

    def render(self) -> Panel:
        """Render the info card."""
        palette = get_palette()

        type_colors = {
            "info": palette.info,
            "success": palette.success,
            "warning": palette.warning,
            "error": palette.error,
        }
        color = type_colors.get(self.card_type, palette.info)

        header = Text()
        header.append(f"{self.icon} ", style=f"bold {color}")
        header.append(self.title, style=f"bold {color}")

        body = Text()
        body.append(self.content, style=palette.text_primary)

        content = Group(header, Text(""), body)

        return Panel(
            content,
            border_style=color,
            box=ROUNDED,
            padding=(1, 2),
        )


# ═══════════════════════════════════════════════════════════════════════
# STATS ROW
# ═══════════════════════════════════════════════════════════════════════


class StatsRow:
    """Horizontal row of stats/metrics."""

    def __init__(self, stats: List[Tuple[str, str, Optional[str]]]):
        """
        Args:
            stats: List of (label, value, optional_color) tuples
        """
        self.stats = stats

    def render(self) -> Text:
        """Render stats row."""
        palette = get_palette()

        text = Text()
        for i, (label, value, color) in enumerate(self.stats):
            if i > 0:
                text.append(" │ ", style=palette.text_muted)

            text.append(f"{label}: ", style=palette.text_muted)
            text.append(value, style=f"bold {color or palette.primary}")

        return text


# ═══════════════════════════════════════════════════════════════════════
# KEYBOARD SHORTCUT
# ═══════════════════════════════════════════════════════════════════════


class KeyboardShortcut:
    """Display keyboard shortcut in styled format."""

    def __init__(self, key: str, description: str):
        self.key = key
        self.description = description

    def render(self) -> Text:
        """Render keyboard shortcut."""
        palette = get_palette()

        text = Text()
        text.append(f" {self.key} ", style=f"bold {palette.bg_elevated} {palette.text_primary}")
        text.append(f" {self.description}", style=palette.text_secondary)

        return text


# ═══════════════════════════════════════════════════════════════════════
# QUICK ACTION BAR
# ═══════════════════════════════════════════════════════════════════════


class QuickActionBar:
    """Bar displaying available quick actions."""

    def __init__(self, actions: List[Tuple[str, str]]):
        """
        Args:
            actions: List of (key, action) tuples
        """
        self.actions = actions

    def render(self) -> Text:
        """Render action bar."""
        palette = get_palette()

        text = Text()
        for i, (key, action) in enumerate(self.actions):
            if i > 0:
                text.append("  ", style="")

            text.append(f"[{key}]", style=f"bold {palette.warning}")
            text.append(f" {action}", style=palette.text_muted)

        return text


# ═══════════════════════════════════════════════════════════════════════
# TIMESTAMP
# ═══════════════════════════════════════════════════════════════════════


class Timestamp:
    """Styled timestamp display."""

    def __init__(self, dt: Optional[datetime] = None, format_str: str = "%H:%M:%S"):
        self.dt = dt or datetime.now()
        self.format_str = format_str

    def render(self) -> Text:
        """Render timestamp."""
        palette = get_palette()

        text = Text()
        text.append(self.dt.strftime(self.format_str), style=palette.text_muted)

        return text


# ═══════════════════════════════════════════════════════════════════════
# BADGE
# ═══════════════════════════════════════════════════════════════════════


class Badge:
    """Small colored badge/tag."""

    def __init__(self, label: str, color: Optional[str] = None, icon: Optional[str] = None):
        self.label = label
        self.color = color
        self.icon = icon

    def render(self) -> Text:
        """Render badge."""
        palette = get_palette()
        color = self.color or palette.primary

        text = Text()
        text.append(" ", style="")
        if self.icon:
            text.append(f"{self.icon} ", style=f"bold {color}")
        text.append(self.label, style=f"bold {color}")
        text.append(" ", style="")

        return text


# ═══════════════════════════════════════════════════════════════════════
# TOOL EXECUTION DISPLAY
# ═══════════════════════════════════════════════════════════════════════


class ToolExecution:
    """Display for tool execution status."""

    def __init__(
        self,
        tool_name: str,
        tool_input: str = "",
        status: str = "running",
        duration: Optional[float] = None,
    ):
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.status = status
        self.duration = duration

    def render(self) -> Text:
        """Render tool execution display."""
        palette = get_palette()

        status_configs = {
            "running": ("◐", palette.warning),
            "success": ("✔", palette.success),
            "error": ("✖", palette.error),
            "pending": ("○", palette.text_muted),
        }

        icon, color = status_configs.get(self.status, status_configs["pending"])

        text = Text()
        text.append(f"{icon} ", style=f"bold {color}")
        text.append("Tool: ", style=palette.text_muted)
        text.append(self.tool_name, style=f"bold {palette.accent}")

        if self.tool_input:
            preview = self.tool_input[:50]
            if len(self.tool_input) > 50:
                preview += "..."
            text.append("\n")
            text.append(f"  └─ {preview}", style=palette.text_muted)

        if self.duration is not None:
            text.append(f" ({self.duration:.2f}s)", style=palette.text_muted)

        return text


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def create_info_table(data: Dict[str, str], title: Optional[str] = None) -> Table:
    """Create a simple info table from key-value pairs."""
    palette = get_palette()

    table = Table(
        show_header=bool(title),
        header_style=f"bold {palette.primary}",
        border_style=palette.border_default,
        box=SIMPLE,
        padding=(0, 1),
    )

    if title:
        table.add_column(title, style=palette.text_secondary)
        table.add_column("", style=palette.text_primary)
    else:
        table.add_column("", style=palette.text_secondary)
        table.add_column("", style=palette.text_primary)

    for key, value in data.items():
        table.add_row(key, value)

    return table


def create_horizontal_rule(width: int = 60, char: str = "─") -> Text:
    """Create a horizontal rule."""
    palette = get_palette()
    return Text(char * width, style=palette.border_default)
