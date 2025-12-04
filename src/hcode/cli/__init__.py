"""
CLI components for Hcode.

Includes display, styling, interactive features, and reasoning integration.
"""

from .display import AgentDisplay

# Import UI module (replaces old styles)
from ..ui import (
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

# Import reasoning runner for integrated todo tracking
from .reasoning_runner import (
    ReasoningRunner,
    ReasoningRunnerConfig,
    ChatReasoningRunner,
    create_reasoning_runner,
    create_chat_reasoning_runner,
)

__all__ = [
    'AgentDisplay',
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
    # Reasoning Runner
    'ReasoningRunner',
    'ReasoningRunnerConfig',
    'ChatReasoningRunner',
    'create_reasoning_runner',
    'create_chat_reasoning_runner',
]
