"""
CLI components for Hcode.

Includes display, styling, interactive features, and reasoning integration.
"""

from hcode.cli.display import AgentDisplay
# Import reasoning runner for integrated todo tracking
from hcode.cli.reasoning_runner import (
    ReasoningRunner,
    ReasoningRunnerConfig,
    ChatReasoningRunner,
    create_reasoning_runner,
    create_chat_reasoning_runner,
)
from hcode.cli.shortcuts import ShortcutManager, ShortcutAction, KeyBinding, setup_shortcuts_for_agent
# Import UI module (replaces old styles)
from hcode.ui import Colors, Icons, StyledPanel, console, spinner, thinking, progress_bar

__all__ = [
    "AgentDisplay",
    "Colors",
    "Icons",
    "StyledPanel",
    "console",
    "spinner",
    "thinking",
    "progress_bar",
    # Shortcuts
    "ShortcutManager",
    "ShortcutAction",
    "KeyBinding",
    "setup_shortcuts_for_agent",
    # Reasoning Runner
    "ReasoningRunner",
    "ReasoningRunnerConfig",
    "ChatReasoningRunner",
    "create_reasoning_runner",
    "create_chat_reasoning_runner",
]
