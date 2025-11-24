"""
Box drawing characters and border styles for Hcode CLI.
Uses Unicode box drawing for clean, modern appearance.
"""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple
import sys

from rich.box import Box


# ============================================================
# PLATFORM DETECTION
# ============================================================

IS_WINDOWS = sys.platform == "win32"


# ============================================================
# BOX DRAWING CHARACTERS
# ============================================================

class BoxChars(NamedTuple):
    """Box drawing character set"""
    # Corners
    top_left: str
    top_right: str
    bottom_left: str
    bottom_right: str

    # Edges
    horizontal: str
    vertical: str

    # T-junctions
    top_tee: str
    bottom_tee: str
    left_tee: str
    right_tee: str

    # Cross
    cross: str


# ============================================================
# PREDEFINED BOX STYLES
# ============================================================

class BoxStyle(Enum):
    """Available box styles"""

    # Rounded (default for modern terminals)
    ROUNDED = BoxChars(
        top_left="╭",
        top_right="╮",
        bottom_left="╰",
        bottom_right="╯",
        horizontal="─",
        vertical="│",
        top_tee="┬",
        bottom_tee="┴",
        left_tee="├",
        right_tee="┤",
        cross="┼"
    )

    # Sharp corners
    SHARP = BoxChars(
        top_left="┌",
        top_right="┐",
        bottom_left="└",
        bottom_right="┘",
        horizontal="─",
        vertical="│",
        top_tee="┬",
        bottom_tee="┴",
        left_tee="├",
        right_tee="┤",
        cross="┼"
    )

    # Double line
    DOUBLE = BoxChars(
        top_left="╔",
        top_right="╗",
        bottom_left="╚",
        bottom_right="╝",
        horizontal="═",
        vertical="║",
        top_tee="╦",
        bottom_tee="╩",
        left_tee="╠",
        right_tee="╣",
        cross="╬"
    )

    # Simple ASCII fallback
    ASCII = BoxChars(
        top_left="+",
        top_right="+",
        bottom_left="+",
        bottom_right="+",
        horizontal="-",
        vertical="|",
        top_tee="+",
        bottom_tee="+",
        left_tee="+",
        right_tee="+",
        cross="+"
    )

    # Minimal
    MINIMAL = BoxChars(
        top_left=" ",
        top_right=" ",
        bottom_left=" ",
        bottom_right=" ",
        horizontal=" ",
        vertical="|",
        top_tee=" ",
        bottom_tee=" ",
        left_tee="|",
        right_tee="|",
        cross="|"
    )


# ============================================================
# CUSTOM RICH BOXES
# ============================================================

# Hcode style rounded box (Claude Code-like)
HCODE_BOX = Box(
    "╭──╮\n"
    "│  │\n"
    "├──┤\n"
    "│  │\n"
    "├──┤\n"
    "├──┤\n"
    "│  │\n"
    "╰──╯\n"
)

# Simple box for Windows compatibility
SIMPLE_BOX = Box(
    "+--+\n"
    "|  |\n"
    "+--+\n"
    "|  |\n"
    "+--+\n"
    "+--+\n"
    "|  |\n"
    "+--+\n"
)

# Minimal box (just vertical lines)
MINIMAL_BOX = Box(
    "    \n"
    "|  |\n"
    "|  |\n"
    "|  |\n"
    "|  |\n"
    "|  |\n"
    "|  |\n"
    "    \n"
)


def get_default_box() -> Box:
    """Get default box style based on platform"""
    # For Windows without proper Unicode support, use simple box
    if IS_WINDOWS:
        import os
        # Check for modern Windows Terminal
        if os.environ.get("WT_SESSION") or os.environ.get("TERM_PROGRAM") == "vscode":
            return HCODE_BOX
        return SIMPLE_BOX
    return HCODE_BOX


# ============================================================
# LINE DRAWING UTILITIES
# ============================================================

class Lines:
    """Common line patterns"""

    # Horizontal lines
    THIN = "-" if IS_WINDOWS else "─"
    THICK = "=" if IS_WINDOWS else "━"
    DOUBLE = "=" if IS_WINDOWS else "═"
    DOTTED = "." if IS_WINDOWS else "┄"
    DASHED = "-" if IS_WINDOWS else "┅"

    # Vertical lines
    THIN_V = "|" if IS_WINDOWS else "│"
    THICK_V = "|" if IS_WINDOWS else "┃"
    DOUBLE_V = "|" if IS_WINDOWS else "║"

    # Arrows (Windows-safe)
    ARROW_RIGHT = "->" if IS_WINDOWS else "→"
    ARROW_LEFT = "<-" if IS_WINDOWS else "←"
    ARROW_UP = "^" if IS_WINDOWS else "↑"
    ARROW_DOWN = "v" if IS_WINDOWS else "↓"
    ARROW_RIGHT_BOLD = "=>" if IS_WINDOWS else "➜"
    ARROW_RIGHT_FANCY = ">" if IS_WINDOWS else "❯"
    ARROW_RIGHT_DOUBLE = ">>" if IS_WINDOWS else "»"

    # Bullets (Windows-safe)
    BULLET = "*" if IS_WINDOWS else "•"
    BULLET_HOLLOW = "o" if IS_WINDOWS else "◦"
    BULLET_SQUARE = "#" if IS_WINDOWS else "▪"
    BULLET_DIAMOND = "*" if IS_WINDOWS else "◆"
    BULLET_TRIANGLE = ">" if IS_WINDOWS else "▸"

    @classmethod
    def horizontal(cls, width: int, style: str = "thin") -> str:
        """Create horizontal line"""
        chars = {
            "thin": cls.THIN,
            "thick": cls.THICK,
            "double": cls.DOUBLE,
            "dotted": cls.DOTTED,
            "dashed": cls.DASHED
        }
        return chars.get(style, cls.THIN) * width

    @classmethod
    def separator(cls, width: int = 50, style: str = "thin", label: str = "") -> str:
        """Create separator with optional label"""
        char = {
            "thin": cls.THIN,
            "thick": cls.THICK,
            "double": cls.DOUBLE
        }.get(style, cls.THIN)

        if label:
            label = f" {label} "
            side_len = (width - len(label)) // 2
            return f"{char * side_len}{label}{char * (width - side_len - len(label))}"

        return char * width
