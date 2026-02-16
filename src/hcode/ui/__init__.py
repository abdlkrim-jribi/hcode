"""
HCode Futuristic UI/UX Design System

A comprehensive cyberpunk-themed terminal UI library featuring:
- 7 distinct themes (Cyberpunk, Neon Nights, Matrix, Synthwave, Frost, Minimal, Hacker)
- Custom ASCII art banners with gradient effects
- Advanced animations and loading effects
- Specialized panels for different content types
- Syntax highlighting with cyberpunk styling
- Interactive chat interface
- Special visual effects (Matrix rain, glitch, pulse, etc.)

Example Usage:
    from hcode.ui import (
        get_console,
        set_theme,
        ThemeMode,
        create_banner,
        ChatInterface,
        CyberPanel,
        highlight_code,
    )

    # Set theme
    set_theme(ThemeMode.CYBERPUNK)

    # Get themed console
    console = get_console()

    # Display banner
    console.print(create_banner())

    # Create chat interface
    chat = ChatInterface()
    chat.display_welcome()
"""

# ═══════════════════════════════════════════════════════════════════════
# THEME EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from hcode.ui.animations import (
    # Spinner definitions
    CYBER_SPINNERS,
    # Classes
    ThinkingAnimation,
    Countdown,
    LoadingDots,
    # Context managers
    # Functions
    countdown,
)
from hcode.ui.banners import (
    # Logo constants
    LOGO_CYBER,
    LOGO_NEON,
    LOGO_MINIMAL,
    LOGO_GLITCH,
    LOGO_FUTURISTIC,
    LOGO_SMALL,
    LOGO_TECH,
    LOGO_BLOCK,
    create_banner,
)
from hcode.ui.components import (
    # Box styles
    CYBER_BOX,
    NEON_BOX,
    TECH_BOX,
    MODERN_BOX,
    ASCII_BOX,
    # Classes
    StatusIndicator,
    CyberPanel,
    # Functions
    create_horizontal_rule,
)

from hcode.ui.icons import (
    # Classes
    Icons,
    Emoji,
    # Constants
    USE_UNICODE,
    IS_WINDOWS,
    # Functions
    supports_unicode,
)
from hcode.ui.panels import (
    # Classes
    WelcomePanel,
    UserMessagePanel,
    AIMessagePanel,
    ToolPanel,
    ErrorPanel,
    SuccessPanel,
    InfoPanel,
    InfoPanel,
    DiffLine,
    DiffDisplay,
    # Functions
)
from hcode.ui.syntax import (
    # Classes
    CyberSyntax,
    DiffHighlighter,
    CodeBlock,
    # Functions
    highlight_code,
    highlight_file,
    inline_code,
    diff_text,
    detect_language,
    # Constants
    EXTENSION_TO_LANGUAGE,
    CYBERPUNK_TOKENS,
)
from hcode.ui.theme import (
    # Enums
    ThemeMode,
    # Classes
    ColorPalette,
    ColorUtils,
    ThemeEngine,
    # Functions
    get_theme,
    set_theme,
    get_console,
    get_palette,
    # Theme definitions
    THEMES,
)
# Create a global console instance for convenience
from rich.console import Console as _Console

# ═══════════════════════════════════════════════════════════════════════hcode.ui
# BANNER EXPORTS
# ═══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
# COMPONENT EXPORTS
# ═══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
# ANIMATION EXPORTS
# ═══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
# ICON EXPORTS
# ═══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
# SYNTAX HIGHLIGHTING EXPORTS
# ═══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
# EFFECTS EXPORTS
# ═══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
# PANEL EXPORTS
# ═══════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════
# CONSOLE INSTANCE
# ═══════════════════════════════════════════════════════════════════════

console = _Console()

# ═══════════════════════════════════════════════════════════════════════
# CHAT UI EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from hcode.ui.chat_ui import (
    # Classes
    ChatInterface,
    ThinkingContext,
    # Functions
    create_chat,
    display_message,
    display_thinking,
)

# ═══════════════════════════════════════════════════════════════════════
# TODO DISPLAY EXPORTS (Enhanced persistent display)
# ═══════════════════════════════════════════════════════════════════════

from hcode.ui.todo_display import (
    # Classes
    ClaudeCodeTodoDisplay,
)

# ═══════════════════════════════════════════════════════════════════════
# LIVE TODO BAR EXPORTS (Real-time updates via callbacks)
# ═══════════════════════════════════════════════════════════════════════

from hcode.ui.live_todo_bar import (
    # Classes
    LiveTodoBar,
    StreamingTodoIntegration,
    # Functions
    get_live_todo_bar,
    start_live_todos,
    stop_live_todos,
    get_current_todos,
)

# ═══════════════════════════════════════════════════════════════════════
# HCODE DISPLAY EXPORTS (Claude Code style reasoning display)
# ═══════════════════════════════════════════════════════════════════════

from hcode.ui.hcode_display import (
    # Classes
    HcodeDisplay,
    TaskMode,
    FileAction,
    ProgressUpdate,
    TrackedFile,
    # Functions
    get_hcode_display,
    reset_display,
)


# ═══════════════════════════════════════════════════════════════════════
# ALL EXPORTS
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    # Theme
    "ThemeMode",
    "ColorPalette",
    "ColorUtils",
    "ThemeEngine",
    "get_theme",
    "set_theme",
    "get_console",
    "get_palette",
    "THEMES",
    # Banners
    "LOGO_CYBER",
    "LOGO_NEON",
    "LOGO_MINIMAL",
    "LOGO_GLITCH",
    "LOGO_FUTURISTIC",
    "LOGO_SMALL",
    "LOGO_TECH",
    "LOGO_BLOCK",
    "create_banner",
    # Components
    "CYBER_BOX",
    "NEON_BOX",
    "TECH_BOX",
    "MODERN_BOX",
    "ASCII_BOX",
    "StatusIndicator",
    "CyberPanel",
    "create_horizontal_rule",
    # Animations
    "CYBER_SPINNERS",
    "ThinkingAnimation",
    "Countdown",
    "LoadingDots",
    "countdown",
    # Icons
    "Icons",
    "Emoji",
    "USE_UNICODE",
    "IS_WINDOWS",
    "supports_unicode",
    # Syntax
    "CyberSyntax",
    "DiffHighlighter",
    "CodeBlock",
    "highlight_code",
    "highlight_file",
    "inline_code",
    "diff_text",
    "detect_language",
    "EXTENSION_TO_LANGUAGE",
    "CYBERPUNK_TOKENS",
    # Panels
    "WelcomePanel",
    "UserMessagePanel",
    "AIMessagePanel",
    "ToolPanel",
    "ErrorPanel",
    "SuccessPanel",
    "InfoPanel",
    "DiffLine",
    "DiffDisplay",
    # Console
    "console",
    # Chat UI
    "ChatInterface",
    "ThinkingContext",
    "ThinkingContext",
    "create_chat",
    "display_message",
    "display_thinking",
    # Todo Display (Enhanced)
    "ClaudeCodeTodoDisplay",
    # Live Todo Bar (Real-time updates)
    "LiveTodoBar",
    "StreamingTodoIntegration",
    "get_live_todo_bar",
    "start_live_todos",
    "stop_live_todos",
    "get_current_todos",
    # Hcode Display (Claude Code style)
    "HcodeDisplay",
    "TaskMode",
    "FileAction",
    "ProgressUpdate",
    "TrackedFile",
    "get_hcode_display",
    "reset_display",
]





# ═══════════════════════════════════════════════════════════════════════
# VERSION
# ═══════════════════════════════════════════════════════════════════════

__version__ = "1.0.0"
