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
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def create_horizontal_rule(width: int = 60, char: str = "─") -> Text:
    """Create a horizontal rule."""
    palette = get_palette()
    return Text(char * width, style=palette.border_default)
