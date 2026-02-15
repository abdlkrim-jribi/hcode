"""
HCode Futuristic Theme Engine
Supports multiple themes with smooth color transitions and glow effects.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple, List

from rich.console import Console
from rich.style import Style
from rich.theme import Theme


class ThemeMode(Enum):
    """Available futuristic theme modes."""

    CYBERPUNK = "cyberpunk"
    NEON_NIGHTS = "neon_nights"
    MATRIX = "matrix"
    SYNTHWAVE = "synthwave"
    FROST = "frost"
    MINIMAL = "minimal"
    HACKER = "hacker"
    NEON_GREEN = "neon_green"  # Signature HCODE theme


@dataclass
class ColorPalette:
    """Futuristic color palette with gradients and glow effects."""

    # ═══════════════════════════════════════════════════════════════
    # PRIMARY COLORS
    # ═══════════════════════════════════════════════════════════════

    primary: str = "#00FFFF"  # Cyan neon
    secondary: str = "#FF00FF"  # Magenta neon
    accent: str = "#FFFF00"  # Electric yellow

    # ═══════════════════════════════════════════════════════════════
    # BACKGROUND LAYERS
    # ═══════════════════════════════════════════════════════════════

    bg_dark: str = "#0D0D0D"  # Deep black
    bg_medium: str = "#1A1A2E"  # Dark blue-black
    bg_light: str = "#16213E"  # Navy accent
    bg_elevated: str = "#1F1F3D"  # Elevated surfaces


    # ═══════════════════════════════════════════════════════════════
    # SEMANTIC COLORS
    # ═══════════════════════════════════════════════════════════════

    success: str = "#00FF88"  # Neon green
    error: str = "#FF0055"  # Hot pink/red
    warning: str = "#FFB800"  # Amber
    info: str = "#00D4FF"  # Sky cyan

    # ═══════════════════════════════════════════════════════════════
    # TEXT COLORS
    # ═══════════════════════════════════════════════════════════════

    text_primary: str = "#FFFFFF"  # Pure white
    text_secondary: str = "#B8B8B8"  # Soft gray
    text_muted: str = "#6B6B6B"  # Muted gray
    text_glow: str = "#00FFFF"  # Glowing cyan
    text_highlight: str = "#FF00FF"  # Highlight magenta
    text_dim: str = "#BBBBBB"  # Brighter dim gray for visibility

    # ═══════════════════════════════════════════════════════════════
    # SPECIAL EFFECTS
    # ═══════════════════════════════════════════════════════════════

    gradient_start: str = "#FF00FF"  # Magenta
    gradient_mid: str = "#8000FF"  # Purple
    gradient_end: str = "#00FFFF"  # Cyan
    glow_color: str = "#00FFFF"  # Glow effect color
    border_glow: str = "#FF00FF"  # Border glow
    pulse_color: str = "#00FF88"  # Pulse effect

    # ═══════════════════════════════════════════════════════════════
    # CODE SYNTAX
    # ═══════════════════════════════════════════════════════════════

    code_keyword: str = "#FF79C6"  # Pink
    code_string: str = "#F1FA8C"  # Yellow
    code_function: str = "#50FA7B"  # Green
    code_comment: str = "#6272A4"  # Muted blue
    code_number: str = "#BD93F9"  # Purple
    code_operator: str = "#FF79C6"  # Pink
    code_class: str = "#8BE9FD"  # Cyan
    code_variable: str = "#F8F8F2"  # White
    code_constant: str = "#BD93F9"  # Purple
    code_parameter: str = "#FFB86C"  # Orange

    # ═══════════════════════════════════════════════════════════════
    # DIFF COLORS
    # ═══════════════════════════════════════════════════════════════

    diff_added: str = "#00FF88"
    diff_removed: str = "#FF0055"
    diff_changed: str = "#FFB800"

    # ═══════════════════════════════════════════════════════════════
    # BORDER COLORS
    # ═══════════════════════════════════════════════════════════════

    border_default: str = "#333344"
    border_focus: str = "#00FFFF"
    border_dim: str = "#666666"  # Visible dim border


# ═══════════════════════════════════════════════════════════════════════
# PREDEFINED THEMES
# ═══════════════════════════════════════════════════════════════════════

THEMES: Dict[ThemeMode, ColorPalette] = {
    ThemeMode.CYBERPUNK: ColorPalette(
        primary="#00FFFF",
        secondary="#FF00FF",
        accent="#FFFF00",
        bg_dark="#0D0D0D",
        bg_medium="#1A1A2E",
        bg_light="#16213E",
        success="#00FF88",
        error="#FF0055",
        warning="#FFB800",
        gradient_start="#FF00FF",
        gradient_end="#00FFFF",
        glow_color="#00FFFF",
        border_glow="#FF00FF",
        text_dim="#AAAAAA",
        border_dim="#555555",
    ),
    ThemeMode.NEON_NIGHTS: ColorPalette(
        primary="#F72585",
        secondary="#7209B7",
        accent="#4CC9F0",
        bg_dark="#10002B",
        bg_medium="#240046",
        bg_light="#3C096C",
        text_primary="#FFFFFF",
        text_secondary="#E0AAFF",
        success="#80ED99",
        error="#FF006E",
        warning="#FFD60A",
        gradient_start="#F72585",
        gradient_end="#4CC9F0",
        glow_color="#F72585",
        border_glow="#7209B7",
    ),
    ThemeMode.MATRIX: ColorPalette(
        primary="#00FF00",
        secondary="#008F11",
        accent="#00FF00",
        bg_dark="#000000",
        bg_medium="#0D0D0D",
        bg_light="#111111",
        text_primary="#00FF00",
        text_secondary="#008F11",
        text_muted="#004400",
        text_glow="#00FF00",
        success="#00FF00",
        error="#FF0000",
        warning="#FFFF00",
        gradient_start="#00FF00",
        gradient_end="#004400",
        glow_color="#00FF00",
        border_glow="#00FF00",
        code_keyword="#00FF00",
        code_string="#88FF88",
        code_function="#00FF00",
        code_comment="#006600",
        text_dim="#008F11",
        border_dim="#004400",
    ),
    ThemeMode.SYNTHWAVE: ColorPalette(
        primary="#FF6AD5",
        secondary="#C774E8",
        accent="#AD8CFF",
        bg_dark="#2D1B69",
        bg_medium="#1A1033",
        bg_light="#261447",
        text_primary="#FFFFFF",
        text_secondary="#E8B4E8",
        success="#94D0CC",
        error="#FF6B6B",
        warning="#FFE66D",
        gradient_start="#FF6AD5",
        gradient_end="#8795E8",
        glow_color="#FF6AD5",
        border_glow="#C774E8",
    ),
    ThemeMode.FROST: ColorPalette(
        primary="#88C0D0",
        secondary="#81A1C1",
        accent="#5E81AC",
        bg_dark="#2E3440",
        bg_medium="#3B4252",
        bg_light="#434C5E",
        text_primary="#ECEFF4",
        text_secondary="#D8DEE9",
        text_muted="#4C566A",
        success="#A3BE8C",
        error="#BF616A",
        warning="#EBCB8B",
        info="#88C0D0",
        gradient_start="#88C0D0",
        gradient_end="#5E81AC",
        glow_color="#88C0D0",
        border_glow="#81A1C1",
    ),
    ThemeMode.MINIMAL: ColorPalette(
        primary="#FFFFFF",
        secondary="#888888",
        accent="#00AAFF",
        bg_dark="#000000",
        bg_medium="#111111",
        bg_light="#1A1A1A",
        text_primary="#FFFFFF",
        text_secondary="#AAAAAA",
        text_muted="#666666",
        success="#00FF00",
        error="#FF0000",
        warning="#FFAA00",
        gradient_start="#FFFFFF",
        gradient_end="#888888",
        glow_color="#FFFFFF",
        border_glow="#444444",
    ),
    ThemeMode.HACKER: ColorPalette(
        primary="#20C20E",
        secondary="#0FFF50",
        accent="#39FF14",
        bg_dark="#000000",
        bg_medium="#0A0A0A",
        bg_light="#0F0F0F",
        text_primary="#20C20E",
        text_secondary="#15A005",
        text_muted="#0A5A03",
        text_glow="#39FF14",
        success="#39FF14",
        error="#FF0000",
        warning="#FFD700",
        gradient_start="#39FF14",
        gradient_end="#0FFF50",
        glow_color="#20C20E",
        border_glow="#0FFF50",
        code_keyword="#39FF14",
        code_string="#7FFF00",
        code_function="#00FF7F",
        code_comment="#2E8B57",
    ),
    # Signature HCODE theme - Modern neon green aesthetic
    # Signature HCODE theme - Electric Cyan & Slate Grey
    ThemeMode.NEON_GREEN: ColorPalette(
        primary="#00E5FF",       # Electric Cyan (Action/Progress)
        secondary="#708090",     # Muted Slate (Metadata/Borders)
        accent="#39FF14",        # Neon Green (Success/Additions - kept for compatibility/success)
        bg_dark="#1E1E1E",       # Deep Charcoal
        bg_medium="#252526",     # Slightly Lighter Charcoal
        bg_light="#2D2D30",      # Lightest Charcoal
        bg_elevated="#333333",   # Elevated Surface
        text_primary="#FFFFFF",  # Pure White
        text_secondary="#B0BEC5", # Light Blue-Grey
        text_muted="#708090",    # Muted Slate
        text_glow="#00E5FF",     # Electric Cyan Glow
        text_highlight="#39FF14", # Neon Green Highlight
        success="#39FF14",       # Neon Green
        error="#FF3355",         # Red
        warning="#FF5F00",       # Safety Orange
        info="#00E5FF",          # Electric Cyan
        gradient_start="#00E5FF", # Cyan
        gradient_mid="#9D00FF",   # Vivid Purple
        gradient_end="#39FF14",   # Neon Green
        glow_color="#00E5FF",    # Cyan Glow
        border_glow="#00E5FF",   # Cyan Border Glow
        pulse_color="#00E5FF",   # Cyan Pulse
        code_keyword="#FF5F00",   # Orange Keywords
        code_string="#39FF14",    # Green Strings
        code_function="#00E5FF",  # Cyan Functions
        code_comment="#708090",   # Slate Comments
        code_number="#9D00FF",    # Purple Numbers
        code_operator="#FFFFFF",  # White Operators
        code_class="#00E5FF",     # Cyan Classes
        code_variable="#B0BEC5",  # Blue-Grey Vars
        diff_added="#39FF14",     # Neon Green Added
        diff_removed="#FF3355",   # Red Removed
        border_default="#708090", # Slate Border
        border_focus="#00E5FF",   # Cyan Focus
        text_dim="#606060",       # Dim Grey
        border_dim="#404040",     # Dim Border
        # Special HCode Palette extras
        code_constant="#9D00FF",  # Purple Constants
        code_parameter="#FF5F00", # Orange Parameters
    ),
}


class ColorUtils:
    """Utility functions for color manipulation."""

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex color."""
        return f"#{r:02x}{g:02x}{b:02x}"


    @staticmethod
    def blend(color1: str, color2: str, factor: float = 0.5) -> str:
        """Blend two colors together."""
        r1, g1, b1 = ColorUtils.hex_to_rgb(color1)
        r2, g2, b2 = ColorUtils.hex_to_rgb(color2)
        r = int(r1 * (1 - factor) + r2 * factor)
        g = int(g1 * (1 - factor) + g2 * factor)
        b = int(b1 * (1 - factor) + b2 * factor)
        return ColorUtils.rgb_to_hex(r, g, b)




class ThemeEngine:
    """Manages theme switching and Rich console styling."""

    _instance: Optional["ThemeEngine"] = None

    def __new__(cls, mode: ThemeMode = ThemeMode.CYBERPUNK):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, mode: ThemeMode = ThemeMode.CYBERPUNK):
        if self._initialized:
            return
        self._initialized = True
        self.mode = mode
        self.palette = THEMES[mode]
        self._console: Optional[Console] = None

    def get_rich_theme(self) -> Theme:
        """Generate Rich theme from current palette."""
        p = self.palette
        return Theme(
            {
                # ═══════════════════════════════════════════════════════
                # CORE STYLES
                # ═══════════════════════════════════════════════════════
                "primary": Style(color=p.primary, bold=True),
                "secondary": Style(color=p.secondary),
                "accent": Style(color=p.accent, bold=True),
                # ═══════════════════════════════════════════════════════
                # STATUS STYLES
                # ═══════════════════════════════════════════════════════
                "success": Style(color=p.success, bold=True),
                "error": Style(color=p.error, bold=True),
                "warning": Style(color=p.warning, bold=True),
                "info": Style(color=p.info),
                # ═══════════════════════════════════════════════════════
                # TEXT STYLES
                # ═══════════════════════════════════════════════════════
                "text": Style(color=p.text_primary),
                "text.muted": Style(color=p.text_muted),
                "text.secondary": Style(color=p.text_secondary),
                "text.glow": Style(color=p.text_glow, bold=True),
                "text.highlight": Style(color=p.text_highlight, bold=True),
                "text.dim": Style(color=p.text_dim),
                # ═══════════════════════════════════════════════════════
                # UI ELEMENTS
                # ═══════════════════════════════════════════════════════
                "panel.border": Style(color=p.primary),
                "panel.title": Style(color=p.accent, bold=True),
                "progress.bar": Style(color=p.primary),
                "progress.remaining": Style(color=p.bg_light),
                "progress.complete": Style(color=p.success),
                # ═══════════════════════════════════════════════════════
                # CODE HIGHLIGHTING
                # ═══════════════════════════════════════════════════════
                "code.keyword": Style(color=p.code_keyword, bold=True),
                "code.string": Style(color=p.code_string),
                "code.function": Style(color=p.code_function),
                "code.comment": Style(color=p.code_comment, italic=True),
                "code.number": Style(color=p.code_number),
                "code.operator": Style(color=p.code_operator),
                "code.class": Style(color=p.code_class, bold=True),
                "code.variable": Style(color=p.code_variable),
                "code.constant": Style(color=p.code_constant),
                "code.parameter": Style(color=p.code_parameter),
                # ═══════════════════════════════════════════════════════
                # DIFF STYLES
                # ═══════════════════════════════════════════════════════
                "diff.added": Style(color=p.diff_added),
                "diff.removed": Style(color=p.diff_removed),
                "diff.changed": Style(color=p.diff_changed),
                # ═══════════════════════════════════════════════════════
                # SPECIAL STYLES
                # ═══════════════════════════════════════════════════════
                "prompt": Style(color=p.primary, bold=True),
                "prompt.input": Style(color=p.text_primary),
                "ai.response": Style(color=p.text_primary),
                "ai.thinking": Style(color=p.warning, italic=True),
                "tool.name": Style(color=p.accent, bold=True),
                "tool.input": Style(color=p.text_secondary),
                "file.path": Style(color=p.secondary, underline=True),
                "file.name": Style(color=p.primary),
                "command": Style(color=p.warning, bold=True),
                # ═══════════════════════════════════════════════════════
                # BORDER STYLES
                # ═══════════════════════════════════════════════════════
                "border": Style(color=p.border_default),
                "border.focus": Style(color=p.border_focus, bold=True),
                "border.glow": Style(color=p.border_glow, bold=True),
                "border.dim": Style(color=p.border_dim),
                # ═══════════════════════════════════════════════════════
                # GRADIENT SIMULATION
                # ═══════════════════════════════════════════════════════
                "gradient.start": Style(color=p.gradient_start, bold=True),
                "gradient.mid": Style(color=p.gradient_mid, bold=True),
                "gradient.end": Style(color=p.gradient_end, bold=True),
                # ═══════════════════════════════════════════════════════
                # GLOW EFFECTS
                # ═══════════════════════════════════════════════════════
                "glow": Style(color=p.glow_color, bold=True),
                "pulse": Style(color=p.pulse_color, bold=True),
                # ═══════════════════════════════════════════════════════
                # THINKING BLOCK STYLES
                # ═══════════════════════════════════════════════════════
                "thinking.gutter": Style(color=p.primary, bold=True),
                "thinking.title": Style(color=p.text_primary, bold=True),
                "thinking.content": Style(color=p.text_secondary),
                "thinking.metadata": Style(color=p.text_muted, italic=True),
                "thinking.spinner": Style(color=p.accent, bold=True),
            }
        )

    @property
    def console(self) -> Console:
        """Get or create a console with the current theme."""
        if self._console is None:
            self._console = Console(theme=self.get_rich_theme())
        return self._console

    def switch_theme(self, mode: ThemeMode) -> None:
        """Switch to a different theme."""
        self.mode = mode
        self.palette = THEMES[mode]
        self._console = None  # Reset console with new theme





# ═══════════════════════════════════════════════════════════════════════
# GLOBAL THEME INSTANCE
# ═══════════════════════════════════════════════════════════════════════

_theme_engine: Optional[ThemeEngine] = None


def get_theme() -> ThemeEngine:
    """Get the global theme engine instance."""
    global _theme_engine
    if _theme_engine is None:
        _theme_engine = ThemeEngine()
    return _theme_engine


def set_theme(mode: ThemeMode) -> None:
    """Set the global theme mode."""
    get_theme().switch_theme(mode)


def get_console() -> Console:
    """Get the themed console instance."""
    return get_theme().console


def get_palette() -> ColorPalette:
    """Get the current color palette."""
    return get_theme().palette
