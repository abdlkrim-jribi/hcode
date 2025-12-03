"""
Legacy compatibility layer for cli.styles.

This module re-exports all components from the new hcode.ui module
to maintain backwards compatibility with existing code.
"""

# Re-export everything from the ui module
from hcode.ui import (
    # Colors
    Colors,

    # Icons
    Icons,
    Emoji,
    Borders,

    # Components
    StyledPanel,
    TodoItem,
    TodoDisplay,
    Header,
    Footer,
    StatusLine,
    Prompt,
    Separator,
    progress_bar,

    # Box styles
    get_default_box,
    Lines,
    get_status_icon,

    # Console
    console,
    get_console,

    # Animations
    spinner,
    thinking,
    loading,

    # Panels
    DiffLine,
    DiffDisplay,
)

__all__ = [
    # Colors
    "Colors",

    # Icons
    "Icons",
    "Emoji",
    "Borders",

    # Components
    "StyledPanel",
    "TodoItem",
    "TodoDisplay",
    "Header",
    "Footer",
    "StatusLine",
    "Prompt",
    "Separator",
    "progress_bar",

    # Box styles
    "get_default_box",
    "Lines",
    "get_status_icon",

    # Console
    "console",
    "get_console",

    # Animations
    "spinner",
    "thinking",
    "loading",

    # Panels
    "DiffLine",
    "DiffDisplay",
]
