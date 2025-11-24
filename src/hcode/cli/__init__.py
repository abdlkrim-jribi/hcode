"""
CLI components for Hcode.

Includes display, styling, and interactive features.
"""

from .display import AgentDisplay

# Import styles submodule for easy access
from . import styles
from .styles import (
    Colors,
    Icons,
    StyledPanel,
    console,
    spinner,
    thinking,
    progress_bar
)

# Import autonomous CLI components
from .autonomous_cli import AutonomousCLI, create_mode_status_line
from .shortcuts import (
    ShortcutManager,
    ShortcutAction,
    KeyBinding,
    setup_shortcuts_for_agent
)

__all__ = [
    'AgentDisplay',
    'styles',
    'Colors',
    'Icons',
    'StyledPanel',
    'console',
    'spinner',
    'thinking',
    'progress_bar',
    # Autonomous CLI
    'AutonomousCLI',
    'create_mode_status_line',
    # Shortcuts
    'ShortcutManager',
    'ShortcutAction',
    'KeyBinding',
    'setup_shortcuts_for_agent',
]
