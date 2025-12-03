"""
Legacy compatibility layer for cli.styles.components.

Re-exports component classes from the new hcode.ui module.
"""

from hcode.ui import (
    # Panels
    StyledPanel,
    TodoItem,
    TodoDisplay,
    Header,
    Footer,
    StatusLine,
    Prompt,
    Separator,
    progress_bar,

    # UI Components
    CyberPanel,
    MetricCard,
    CommandPalette,
    ProgressRing,
    TokenCounter,
    InfoCard,
    StatsRow,
    KeyboardShortcut,
    QuickActionBar,
    Timestamp,
    Badge,
    ToolExecution,

    # Panels from panels.py
    WelcomePanel,
    UserMessagePanel,
    AIMessagePanel,
    ToolPanel,
    ErrorPanel,
    SuccessPanel,
    InfoPanel,
    FileTreePanel,
    StatsPanel,
    HelpPanel,
    TokenUsagePanel,
    DiffLine,
    DiffDisplay,

    # Box styles
    CYBER_BOX,
    NEON_BOX,
    TECH_BOX,
    MODERN_BOX,
    ASCII_BOX,

    # Functions
    create_info_table,
    create_horizontal_rule,
    create_separator,
    create_status_bar,
)

__all__ = [
    # Panels
    "StyledPanel",
    "TodoItem",
    "TodoDisplay",
    "Header",
    "Footer",
    "StatusLine",
    "Prompt",
    "Separator",
    "progress_bar",

    # UI Components
    "CyberPanel",
    "MetricCard",
    "CommandPalette",
    "ProgressRing",
    "TokenCounter",
    "InfoCard",
    "StatsRow",
    "KeyboardShortcut",
    "QuickActionBar",
    "Timestamp",
    "Badge",
    "ToolExecution",

    # Panels
    "WelcomePanel",
    "UserMessagePanel",
    "AIMessagePanel",
    "ToolPanel",
    "ErrorPanel",
    "SuccessPanel",
    "InfoPanel",
    "FileTreePanel",
    "StatsPanel",
    "HelpPanel",
    "TokenUsagePanel",
    "DiffLine",
    "DiffDisplay",

    # Box styles
    "CYBER_BOX",
    "NEON_BOX",
    "TECH_BOX",
    "MODERN_BOX",
    "ASCII_BOX",

    # Functions
    "create_info_table",
    "create_horizontal_rule",
    "create_separator",
    "create_status_bar",
]
