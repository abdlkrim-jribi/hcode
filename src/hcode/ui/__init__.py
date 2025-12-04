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

from .theme import (
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

# ═══════════════════════════════════════════════════════════════════════
# BANNER EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from .banners import (
    # Logo constants
    LOGO_CYBER,
    LOGO_NEON,
    LOGO_MINIMAL,
    LOGO_GLITCH,
    LOGO_FUTURISTIC,
    LOGO_SMALL,
    LOGO_TECH,
    LOGO_BLOCK,

    # Functions
    create_banner,
    create_animated_banner,
    create_gradient_text,
    create_vertical_gradient_text,
    create_rainbow_text,
    create_section_header,
    create_subsection_header,
    create_divider,
    create_glow_text,
    create_neon_box,
    display_welcome,
    display_startup_animation,
    quick_banner,
    status_banner,
    get_cyberpunk_gradient,
)

# ═══════════════════════════════════════════════════════════════════════
# COMPONENT EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from .components import (
    # Box styles
    CYBER_BOX,
    NEON_BOX,
    TECH_BOX,
    MODERN_BOX,
    ASCII_BOX,

    # Classes
    StatusIndicator,
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

    # Functions
    create_info_table,
    create_horizontal_rule,
)

# ═══════════════════════════════════════════════════════════════════════
# ANIMATION EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from .animations import (
    # Spinner definitions
    CYBER_SPINNERS,

    # Classes
    AnimatedMessage,
    CyberProgress,
    StreamingText,
    GlitchEffect,
    ThinkingAnimation,
    WaveAnimation,
    PulsingText,
    Countdown,
    LoadingDots,

    # Context managers
    spinner,
    thinking,
    loading,

    # Functions
    countdown,
)

# ═══════════════════════════════════════════════════════════════════════
# ICON EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from .icons import (
    # Classes
    Icons,
    Emoji,
    Borders,

    # Constants
    USE_UNICODE,
    IS_WINDOWS,

    # Functions
    supports_unicode,
)

# ═══════════════════════════════════════════════════════════════════════
# SYNTAX HIGHLIGHTING EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from .syntax import (
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

# ═══════════════════════════════════════════════════════════════════════
# EFFECTS EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from .effects import (
    # Classes
    MatrixRain,
    ScanLine,
    PulseEffect,
    RevealEffect,
    ScrambleEffect,
    BorderGlow,
    ParticleBurst,

    # Functions
    matrix_rain,
    scan_line,
    pulse_text,
    reveal_text,
    scramble_text,
    particle_burst,
)

# ═══════════════════════════════════════════════════════════════════════
# PANEL EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from .panels import (
    # Classes
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

    # Functions
    create_separator,
    create_status_bar,
)

# ═══════════════════════════════════════════════════════════════════════
# CONSOLE INSTANCE
# ═══════════════════════════════════════════════════════════════════════

# Create a global console instance for convenience
from rich.console import Console as _Console
console = _Console()

# ═══════════════════════════════════════════════════════════════════════
# CHAT UI EXPORTS
# ═══════════════════════════════════════════════════════════════════════

from .chat_ui import (
    # Classes
    ChatInterface,
    ThinkingContext,
    InteractivePrompt,
    ChatSession,

    # Functions
    create_chat,
    display_message,
    display_thinking,
)

# ═══════════════════════════════════════════════════════════════════════
# TODO DISPLAY EXPORTS (Enhanced persistent display)
# ═══════════════════════════════════════════════════════════════════════

from .todo_display import (
    # Classes
    TodoDisplayStatus,
    DisplayTodoItem,
    TodoDisplayRenderer,
    PersistentTodoDisplay,
    TodoStatusBar,

    # Functions
    create_todo_display,
    render_todo_panel,
    render_todo_status_line,
)

# ═══════════════════════════════════════════════════════════════════════
# LIVE TODO BAR EXPORTS (Real-time updates via callbacks)
# ═══════════════════════════════════════════════════════════════════════

from .live_todo_bar import (
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
    "create_animated_banner",
    "create_gradient_text",
    "create_vertical_gradient_text",
    "create_rainbow_text",
    "create_section_header",
    "create_subsection_header",
    "create_divider",
    "create_glow_text",
    "create_neon_box",
    "display_welcome",
    "display_startup_animation",
    "quick_banner",
    "status_banner",
    "get_cyberpunk_gradient",

    # Components
    "CYBER_BOX",
    "NEON_BOX",
    "TECH_BOX",
    "MODERN_BOX",
    "ASCII_BOX",
    "StatusIndicator",
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
    "create_info_table",
    "create_horizontal_rule",

    # Animations
    "CYBER_SPINNERS",
    "AnimatedMessage",
    "CyberProgress",
    "StreamingText",
    "GlitchEffect",
    "ThinkingAnimation",
    "WaveAnimation",
    "PulsingText",
    "Countdown",
    "LoadingDots",
    "spinner",
    "thinking",
    "loading",
    "countdown",

    # Icons
    "Icons",
    "Emoji",
    "Borders",
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

    # Effects
    "MatrixRain",
    "ScanLine",
    "PulseEffect",
    "RevealEffect",
    "ScrambleEffect",
    "BorderGlow",
    "ParticleBurst",
    "matrix_rain",
    "scan_line",
    "pulse_text",
    "reveal_text",
    "scramble_text",
    "particle_burst",

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
    "create_separator",
    "create_status_bar",

    # Console
    "console",

    # Chat UI
    "ChatInterface",
    "ThinkingContext",
    "InteractivePrompt",
    "ChatSession",
    "create_chat",
    "display_message",
    "display_thinking",

    # Todo Display (Enhanced)
    "TodoDisplayStatus",
    "DisplayTodoItem",
    "TodoDisplayRenderer",
    "PersistentTodoDisplay",
    "TodoStatusBar",
    "create_todo_display",
    "render_todo_panel",
    "render_todo_status_line",

    # Live Todo Bar (Real-time updates)
    "LiveTodoBar",
    "StreamingTodoIntegration",
    "get_live_todo_bar",
    "start_live_todos",
    "stop_live_todos",
    "get_current_todos",
]

# ═══════════════════════════════════════════════════════════════════════
# COMPATIBILITY LAYER (Legacy cli.styles support)
# ═══════════════════════════════════════════════════════════════════════

from .compat import (
    # Colors
    Colors,

    # Borders
    Lines,
    get_default_box,

    # Status
    get_status_icon,

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

    # Animations (compatible wrappers)
    spinner,
    thinking,
)

# Update __all__ with compat exports
__all__.extend([
    "Colors",
    "Lines",
    "get_default_box",
    "get_status_icon",
    "StyledPanel",
    "TodoItem",
    "TodoDisplay",
    "Header",
    "Footer",
    "StatusLine",
    "Prompt",
    "Separator",
    "progress_bar",
    "spinner",
    "thinking",
])

# ═══════════════════════════════════════════════════════════════════════
# VERSION
# ═══════════════════════════════════════════════════════════════════════

__version__ = "1.0.0"
