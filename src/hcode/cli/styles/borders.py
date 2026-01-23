"""
Legacy compatibility layer for cli.styles.borders.

Re-exports border-related components from the new hcode.ui module.
"""

from rich.box import ROUNDED, DOUBLE, HEAVY, SIMPLE

from hcode.ui import Lines, Borders, get_default_box
from hcode.ui.components import CYBER_BOX, NEON_BOX, TECH_BOX, MODERN_BOX, ASCII_BOX


class BoxStyle:
    """Legacy BoxStyle class - provides box style constants."""

    ROUNDED = ROUNDED
    DOUBLE = DOUBLE
    HEAVY = HEAVY
    SIMPLE = SIMPLE
    CYBER = CYBER_BOX
    NEON = NEON_BOX
    TECH = TECH_BOX
    MODERN = MODERN_BOX
    ASCII = ASCII_BOX


class BoxChars:
    """Legacy BoxChars class - provides box drawing characters."""

    HORIZONTAL = "─"
    VERTICAL = "│"
    CORNER_TL = "╭"
    CORNER_TR = "╮"
    CORNER_BL = "╰"
    CORNER_BR = "╯"
    T_DOWN = "┬"
    T_UP = "┴"
    T_RIGHT = "├"
    T_LEFT = "┤"
    CROSS = "┼"
    DOUBLE_H = "═"
    DOUBLE_V = "║"


__all__ = [
    "Lines",
    "Borders",
    "BoxStyle",
    "BoxChars",
    "get_default_box",
    "CYBER_BOX",
    "NEON_BOX",
    "TECH_BOX",
    "MODERN_BOX",
    "ASCII_BOX",
]
