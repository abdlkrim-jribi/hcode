"""
CLI styling system for Hcode.

Provides Claude Code-like terminal UI styling.
"""

from .colors import Colors, ThemeManager, Theme, ColorScheme, get_rich_theme
from .borders import BoxStyle, HCODE_BOX, Lines, get_default_box
from .icons import Icons, Spinners, get_status_icon, get_file_icon, get_tool_icon
from .components import (
    StyledPanel,
    TodoDisplay,
    TodoItem,
    StyledProgress,
    Header,
    Footer,
    StatusLine,
    Prompt,
    MessageDisplay,
    DiffDisplay,
    DiffLine,
    FileTree,
    Separator,
    LiveDisplay,
    console
)
from .animations import (
    AnimatedSpinner,
    spinner,
    TypingAnimation,
    type_text,
    ProgressAnimation,
    progress_bar,
    PulsingText,
    Countdown,
    countdown,
    LoadingDots,
    ThinkingAnimation,
    thinking,
    WaveAnimation
)

__all__ = [
    # Colors
    'Colors',
    'ThemeManager',
    'Theme',
    'ColorScheme',
    'get_rich_theme',

    # Borders
    'BoxStyle',
    'HCODE_BOX',
    'Lines',
    'get_default_box',

    # Icons
    'Icons',
    'Spinners',
    'get_status_icon',
    'get_file_icon',
    'get_tool_icon',

    # Components
    'StyledPanel',
    'TodoDisplay',
    'TodoItem',
    'StyledProgress',
    'Header',
    'Footer',
    'StatusLine',
    'Prompt',
    'MessageDisplay',
    'DiffDisplay',
    'DiffLine',
    'FileTree',
    'Separator',
    'LiveDisplay',
    'console',

    # Animations
    'AnimatedSpinner',
    'spinner',
    'TypingAnimation',
    'type_text',
    'ProgressAnimation',
    'progress_bar',
    'PulsingText',
    'Countdown',
    'countdown',
    'LoadingDots',
    'ThinkingAnimation',
    'thinking',
    'WaveAnimation'
]
