"""
Color system for Hcode CLI.

Base accent color: #08CB00 (Vibrant Green)
Creates a cohesive, professional terminal experience.
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from enum import Enum


# ============================================================
# PLATFORM DETECTION
# ============================================================

IS_WINDOWS = sys.platform == "win32"

# Check if terminal supports Unicode
def supports_unicode() -> bool:
    """Check if terminal supports Unicode"""
    if IS_WINDOWS:
        # Check for Windows Terminal or ConEmu
        return (
            os.environ.get("WT_SESSION") is not None or
            os.environ.get("ConEmuANSI") == "ON" or
            os.environ.get("TERM_PROGRAM") == "vscode"
        )
    return True


# ============================================================
# COLOR UTILITIES
# ============================================================

class ColorUtils:
    """Utility functions for color manipulation"""

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex to RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex"""
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def lighten(hex_color: str, factor: float) -> str:
        """Lighten a color by factor (0-1)"""
        r, g, b = ColorUtils.hex_to_rgb(hex_color)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return ColorUtils.rgb_to_hex(r, g, b)

    @staticmethod
    def darken(hex_color: str, factor: float) -> str:
        """Darken a color by factor (0-1)"""
        r, g, b = ColorUtils.hex_to_rgb(hex_color)
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        return ColorUtils.rgb_to_hex(r, g, b)


# ============================================================
# COLOR DEFINITIONS
# ============================================================

@dataclass(frozen=True)
class ColorScheme:
    """Complete color scheme for the CLI"""

    # ─────────────────────────────────────────────────────────
    # PRIMARY COLORS (Based on #08CB00)
    # ─────────────────────────────────────────────────────────

    # Main accent - the vibrant green
    PRIMARY: str = "#08CB00"
    PRIMARY_LIGHT: str = "#4AE044"
    PRIMARY_LIGHTER: str = "#7AEF75"
    PRIMARY_DARK: str = "#069E00"
    PRIMARY_DARKER: str = "#047000"

    # Secondary accent - complementary blue
    SECONDARY: str = "#00A8CB"
    SECONDARY_LIGHT: str = "#44C8E0"
    SECONDARY_DARK: str = "#007A9E"

    # Tertiary - warm accent for highlights
    TERTIARY: str = "#CB8F00"
    TERTIARY_LIGHT: str = "#E0B544"

    # ─────────────────────────────────────────────────────────
    # SEMANTIC COLORS
    # ─────────────────────────────────────────────────────────

    # Success (uses primary green)
    SUCCESS: str = "#08CB00"
    SUCCESS_LIGHT: str = "#4AE044"
    SUCCESS_BG: str = "#0A2E08"

    # Error
    ERROR: str = "#FF3B3B"
    ERROR_LIGHT: str = "#FF6B6B"
    ERROR_DARK: str = "#CC2F2F"
    ERROR_BG: str = "#2E0A0A"

    # Warning
    WARNING: str = "#FFB800"
    WARNING_LIGHT: str = "#FFCC44"
    WARNING_DARK: str = "#CC9300"
    WARNING_BG: str = "#2E2508"

    # Info
    INFO: str = "#00A8CB"
    INFO_LIGHT: str = "#44C8E0"
    INFO_BG: str = "#082A2E"

    # ─────────────────────────────────────────────────────────
    # BACKGROUND COLORS (Dark Theme)
    # ─────────────────────────────────────────────────────────

    # Main backgrounds
    BG_PRIMARY: str = "#0D0D0D"      # Deepest background
    BG_SECONDARY: str = "#141414"    # Slightly lighter
    BG_TERTIARY: str = "#1A1A1A"     # Cards, panels
    BG_ELEVATED: str = "#212121"     # Elevated elements
    BG_HOVER: str = "#2A2A2A"        # Hover states

    # Special backgrounds
    BG_CODE: str = "#0F0F0F"         # Code blocks
    BG_INPUT: str = "#181818"        # Input fields
    BG_SELECTION: str = "#0A3D08"    # Selection (green tinted)
    BG_HIGHLIGHT: str = "#1A3318"    # Highlighted lines

    # ─────────────────────────────────────────────────────────
    # TEXT COLORS
    # ─────────────────────────────────────────────────────────

    # Primary text
    TEXT_PRIMARY: str = "#FFFFFF"
    TEXT_SECONDARY: str = "#A0A0A0"
    TEXT_TERTIARY: str = "#707070"
    TEXT_MUTED: str = "#505050"
    TEXT_DISABLED: str = "#404040"

    # Special text
    TEXT_ACCENT: str = "#08CB00"     # Accent colored text
    TEXT_LINK: str = "#00A8CB"       # Links
    TEXT_CODE: str = "#E0E0E0"       # Code text

    # ─────────────────────────────────────────────────────────
    # BORDER COLORS
    # ─────────────────────────────────────────────────────────

    BORDER_DEFAULT: str = "#2A2A2A"
    BORDER_LIGHT: str = "#3A3A3A"
    BORDER_FOCUS: str = "#08CB00"
    BORDER_ERROR: str = "#FF3B3B"
    BORDER_SUCCESS: str = "#08CB00"

    # ─────────────────────────────────────────────────────────
    # SYNTAX HIGHLIGHTING
    # ─────────────────────────────────────────────────────────

    SYNTAX_KEYWORD: str = "#FF79C6"      # Pink - keywords
    SYNTAX_STRING: str = "#08CB00"       # Green - strings
    SYNTAX_NUMBER: str = "#BD93F9"       # Purple - numbers
    SYNTAX_FUNCTION: str = "#50FA7B"     # Bright green - functions
    SYNTAX_CLASS: str = "#8BE9FD"        # Cyan - classes
    SYNTAX_COMMENT: str = "#6272A4"      # Gray-blue - comments
    SYNTAX_OPERATOR: str = "#FF79C6"     # Pink - operators
    SYNTAX_VARIABLE: str = "#F8F8F2"     # White - variables
    SYNTAX_CONSTANT: str = "#BD93F9"     # Purple - constants
    SYNTAX_PARAMETER: str = "#FFB86C"    # Orange - parameters
    SYNTAX_TYPE: str = "#8BE9FD"         # Cyan - types
    SYNTAX_DECORATOR: str = "#FFB86C"    # Orange - decorators

    # ─────────────────────────────────────────────────────────
    # SPECIAL PURPOSE
    # ─────────────────────────────────────────────────────────

    # Agent states
    THINKING: str = "#CB8F00"         # Amber for thinking
    EXECUTING: str = "#08CB00"        # Green for executing
    WAITING: str = "#00A8CB"          # Blue for waiting

    # Todo states
    TODO_PENDING: str = "#505050"
    TODO_IN_PROGRESS: str = "#00A8CB"
    TODO_COMPLETED: str = "#08CB00"
    TODO_BLOCKED: str = "#FF3B3B"
    TODO_SKIPPED: str = "#707070"

    # Progress
    PROGRESS_BAR: str = "#08CB00"
    PROGRESS_BG: str = "#2A2A2A"
    PROGRESS_TEXT: str = "#FFFFFF"

    # Diff colors
    DIFF_ADDED: str = "#08CB00"
    DIFF_ADDED_BG: str = "#0A2E08"
    DIFF_REMOVED: str = "#FF3B3B"
    DIFF_REMOVED_BG: str = "#2E0A0A"
    DIFF_CHANGED: str = "#FFB800"
    DIFF_CHANGED_BG: str = "#2E2508"


@dataclass(frozen=True)
class LightColorScheme(ColorScheme):
    """Light theme color scheme"""

    # Primary colors stay the same
    PRIMARY: str = "#08CB00"
    PRIMARY_LIGHT: str = "#4AE044"
    PRIMARY_DARK: str = "#069E00"

    # Backgrounds - inverted
    BG_PRIMARY: str = "#FFFFFF"
    BG_SECONDARY: str = "#F8F8F8"
    BG_TERTIARY: str = "#F0F0F0"
    BG_ELEVATED: str = "#FFFFFF"
    BG_CODE: str = "#F5F5F5"
    BG_INPUT: str = "#FAFAFA"
    BG_SELECTION: str = "#D4F5D0"
    BG_HIGHLIGHT: str = "#E8F5E6"

    # Text - inverted
    TEXT_PRIMARY: str = "#1A1A1A"
    TEXT_SECONDARY: str = "#505050"
    TEXT_TERTIARY: str = "#707070"
    TEXT_MUTED: str = "#909090"
    TEXT_CODE: str = "#1A1A1A"

    # Borders
    BORDER_DEFAULT: str = "#E0E0E0"
    BORDER_LIGHT: str = "#EEEEEE"
    BORDER_FOCUS: str = "#08CB00"


# ============================================================
# THEME MANAGEMENT
# ============================================================

class Theme(Enum):
    """Available themes"""
    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"


class ThemeManager:
    """Manages color themes"""

    _current_theme: Theme = Theme.DARK
    _dark_scheme: ColorScheme = ColorScheme()
    _light_scheme: ColorScheme = LightColorScheme()

    @classmethod
    def get_colors(cls) -> ColorScheme:
        """Get current color scheme"""
        if cls._current_theme == Theme.LIGHT:
            return cls._light_scheme
        return cls._dark_scheme

    @classmethod
    def set_theme(cls, theme: Theme):
        """Set current theme"""
        cls._current_theme = theme

    @classmethod
    def toggle_theme(cls):
        """Toggle between dark and light"""
        if cls._current_theme == Theme.DARK:
            cls._current_theme = Theme.LIGHT
        else:
            cls._current_theme = Theme.DARK

    @classmethod
    def get_current_theme(cls) -> Theme:
        """Get current theme"""
        return cls._current_theme


# ============================================================
# RICH STYLE DEFINITIONS
# ============================================================

def get_rich_theme() -> Dict[str, str]:
    """Get Rich library theme configuration"""
    c = ThemeManager.get_colors()

    return {
        # Base styles
        "primary": f"bold {c.PRIMARY}",
        "secondary": f"{c.SECONDARY}",
        "success": f"bold {c.SUCCESS}",
        "error": f"bold {c.ERROR}",
        "warning": f"bold {c.WARNING}",
        "info": f"{c.INFO}",

        # Text styles
        "text": f"{c.TEXT_PRIMARY}",
        "text.secondary": f"{c.TEXT_SECONDARY}",
        "text.muted": f"{c.TEXT_MUTED}",
        "text.accent": f"bold {c.TEXT_ACCENT}",

        # Code styles
        "code": f"{c.TEXT_CODE}",
        "code.keyword": f"bold {c.SYNTAX_KEYWORD}",
        "code.string": f"{c.SYNTAX_STRING}",
        "code.number": f"{c.SYNTAX_NUMBER}",
        "code.function": f"{c.SYNTAX_FUNCTION}",
        "code.class": f"bold {c.SYNTAX_CLASS}",
        "code.comment": f"italic {c.SYNTAX_COMMENT}",

        # UI elements
        "panel.border": f"{c.BORDER_DEFAULT}",
        "panel.title": f"bold {c.TEXT_PRIMARY}",
        "progress.bar": f"{c.PROGRESS_BAR}",
        "progress.complete": f"{c.PRIMARY}",

        # Status
        "status.thinking": f"bold {c.THINKING}",
        "status.executing": f"bold {c.EXECUTING}",
        "status.waiting": f"{c.WAITING}",
        "status.error": f"bold {c.ERROR}",
        "status.success": f"bold {c.SUCCESS}",

        # Todos
        "todo.pending": f"{c.TODO_PENDING}",
        "todo.in_progress": f"bold {c.TODO_IN_PROGRESS}",
        "todo.completed": f"{c.TODO_COMPLETED}",
        "todo.blocked": f"{c.TODO_BLOCKED}",

        # Diff
        "diff.added": f"{c.DIFF_ADDED}",
        "diff.removed": f"{c.DIFF_REMOVED}",
        "diff.changed": f"{c.DIFF_CHANGED}",

        # Special
        "prompt": f"bold {c.PRIMARY}",
        "prompt.arrow": f"{c.PRIMARY}",
        "header": f"bold {c.TEXT_PRIMARY}",
        "footer": f"{c.TEXT_MUTED}",
        "dim": f"dim {c.TEXT_MUTED}",
        "highlight": f"bold {c.PRIMARY}",
    }


# Convenience access
Colors = ThemeManager.get_colors()
