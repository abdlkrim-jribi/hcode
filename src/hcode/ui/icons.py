"""
HCode Icon System
Nerd Font and Unicode icons for the UI.
"""

import os
import sys

# ═══════════════════════════════════════════════════════════════════════
# PLATFORM DETECTION
# ═══════════════════════════════════════════════════════════════════════

IS_WINDOWS = sys.platform == "win32"


def supports_unicode() -> bool:
    """Check if terminal supports Unicode."""
    if IS_WINDOWS:
        # Check if encoding allows unicode
        if hasattr(sys.stdout, "encoding") and sys.stdout.encoding:
            encoding = sys.stdout.encoding.lower()
            if encoding in ("cp1252", "cp437", "mbcs"):
                return False

        return (
            os.environ.get("WT_SESSION") is not None
            or os.environ.get("ConEmuANSI") == "ON"
            or os.environ.get("TERM_PROGRAM") == "vscode"
        )
    return True


USE_UNICODE = supports_unicode()


# ═══════════════════════════════════════════════════════════════════════
# ICON DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════


class Icons:
    """Centralized icon definitions with Unicode fallbacks."""

    # ═══════════════════════════════════════════════════════════════
    # STATUS ICONS
    # ═══════════════════════════════════════════════════════════════

    SUCCESS = "✔" if USE_UNICODE else "[OK]"
    CHECK = "✔" if USE_UNICODE else "[OK]"  # Alias for SUCCESS
    ERROR = "✖" if USE_UNICODE else "[X]"
    WARNING = "⚠" if USE_UNICODE else "[!]"
    INFO = "ℹ" if USE_UNICODE else "[i]"
    LOADING = "◐" if USE_UNICODE else "[~]"
    ONLINE = "◉" if USE_UNICODE else "[*]"
    OFFLINE = "○" if USE_UNICODE else "[ ]"
    PENDING = "○" if USE_UNICODE else "[ ]"
    COMPLETE = "●" if USE_UNICODE else "[X]"
    EXECUTING = "◈" if USE_UNICODE else "[>]"

    # ═══════════════════════════════════════════════════════════════
    # TODO STATUS ICONS
    # ═══════════════════════════════════════════════════════════════


    # ═══════════════════════════════════════════════════════════════
    # ACTION ICONS
    # ═══════════════════════════════════════════════════════════════


    THINKING = "💭" if USE_UNICODE else "[...]"
    AGENT = "🤖" if USE_UNICODE else "[AI]"

    PLAY = "▶" if USE_UNICODE else "[>]"
    PAUSE = "⏸" if USE_UNICODE else "[||]"
    REFRESH = "⟳" if USE_UNICODE else "[R]"
    SEARCH = "🔍" if USE_UNICODE else "[?]"

    # ═══════════════════════════════════════════════════════════════
    # FILE ICONS
    # ═══════════════════════════════════════════════════════════════

    FILE = "📄" if USE_UNICODE else "[F]"
    EDIT = "✏️" if USE_UNICODE else "[E]"
    FOLDER = "📁" if USE_UNICODE else "[D]"

    CODE = "📝" if USE_UNICODE else "[<>]"
    IMAGE = "🖼" if USE_UNICODE else "[I]"
    CONFIG = "⚙" if USE_UNICODE else "[C]"

    # ═══════════════════════════════════════════════════════════════
    # AI/TECH ICONS
    # ═══════════════════════════════════════════════════════════════

    AI = "🤖" if USE_UNICODE else "[AI]"
    BRAIN = "🧠" if USE_UNICODE else "[B]"
    SPARKLE = "✨" if USE_UNICODE else "[*]"
    LIGHTNING = "⚡" if USE_UNICODE else "[!]"
    ROCKET = "🚀" if USE_UNICODE else "[^]"
    GEAR = "⚙" if USE_UNICODE else "[G]"
    TERMINAL = "🖥" if USE_UNICODE else "[T]"
    GLOBE = "🌐" if USE_UNICODE else "[W]"

    # ═══════════════════════════════════════════════════════════════
    # COMMUNICATION
    # ═══════════════════════════════════════════════════════════════


    MESSAGE = "💬" if USE_UNICODE else "[M]"

    # ═══════════════════════════════════════════════════════════════
    # BRANDING / UI
    # ═══════════════════════════════════════════════════════════════

    LOGO = "◈" if USE_UNICODE else "[H]"

    CODE = "📝" if USE_UNICODE else "[<>]"
    FOLDER = "📁" if USE_UNICODE else "[D]"
    GLOBE = "🌐" if USE_UNICODE else "[W]"
    STAR = "★" if USE_UNICODE else "*"
    
    # HCode Design System Specific
    GUTTER_BAR = "┃" if USE_UNICODE else "|"
    ICON_FILE_CIRCLE = "○" if USE_UNICODE else "[F]"
    ICON_DIR_CIRCLE = "●" if USE_UNICODE else "[D]"
    PROMPT_LAMBDA = "λ" if USE_UNICODE else ">"

    # CyberPanel Decorations
    DECO_LEFT = "◢" if USE_UNICODE else "["
    DECO_RIGHT = "◣" if USE_UNICODE else "]"


    # ═══════════════════════════════════════════════════════════════
    # DECORATIVE
    # ═══════════════════════════════════════════════════════════════

    BULLET = "•" if USE_UNICODE else "*"
    CYBER_DOT = "●" if USE_UNICODE else "*"




    # ═══════════════════════════════════════════════════════════════
    # BOX DRAWING
    # ═══════════════════════════════════════════════════════════════


    # ═══════════════════════════════════════════════════════════════
    # PROGRESS
    # ═══════════════════════════════════════════════════════════════


    # ═══════════════════════════════════════════════════════════════
    # SPINNER FRAMES
    # ═══════════════════════════════════════════════════════════════



    # ═══════════════════════════════════════════════════════════════
    # NERD FONT ICONS (for terminals with Nerd Fonts)
    # ═══════════════════════════════════════════════════════════════

    NERD = {
        "python": "" if USE_UNICODE else "[PY]",
        "javascript": "" if USE_UNICODE else "[JS]",
        "typescript": "" if USE_UNICODE else "[TS]",
        "rust": "" if USE_UNICODE else "[RS]",
        "go": "" if USE_UNICODE else "[GO]",
        "java": "" if USE_UNICODE else "[JV]",
        "cpp": "" if USE_UNICODE else "[C+]",
        "c": "" if USE_UNICODE else "[C]",
        "html": "" if USE_UNICODE else "[HT]",
        "css": "" if USE_UNICODE else "[CS]",
        "json": "" if USE_UNICODE else "[{}]",
        "yaml": "" if USE_UNICODE else "[YM]",
        "markdown": "" if USE_UNICODE else "[MD]",
        "git": "" if USE_UNICODE else "[GIT]",
        "docker": "" if USE_UNICODE else "[DK]",
        "terminal": "" if USE_UNICODE else "[>_]",
        "folder": "" if USE_UNICODE else "[D]",
        "file": "" if USE_UNICODE else "[F]",
        "settings": "" if USE_UNICODE else "[SET]",
        "search": "" if USE_UNICODE else "[?]",
        "check": "" if USE_UNICODE else "[OK]",
        "error": "" if USE_UNICODE else "[X]",
        "warning": "" if USE_UNICODE else "[!]",
        "info": "" if USE_UNICODE else "[i]",
    }

    @classmethod
    def get_file_icon(cls, filename: str) -> str:
        """Get icon based on file extension."""
        ext_map = {
            ".py": cls.NERD.get("python", cls.CODE),
            ".js": cls.NERD.get("javascript", cls.CODE),
            ".ts": cls.NERD.get("typescript", cls.CODE),
            ".jsx": cls.NERD.get("javascript", cls.CODE),
            ".tsx": cls.NERD.get("typescript", cls.CODE),
            ".rs": cls.NERD.get("rust", cls.CODE),
            ".go": cls.NERD.get("go", cls.CODE),
            ".java": cls.NERD.get("java", cls.CODE),
            ".cpp": cls.NERD.get("cpp", cls.CODE),
            ".c": cls.NERD.get("c", cls.CODE),
            ".h": cls.NERD.get("cpp", cls.CODE),
            ".hpp": cls.NERD.get("cpp", cls.CODE),
            ".html": cls.NERD.get("html", cls.CODE),
            ".css": cls.NERD.get("css", cls.CODE),
            ".scss": cls.NERD.get("css", cls.CODE),
            ".json": cls.NERD.get("json", cls.CONFIG),
            ".yaml": cls.NERD.get("yaml", cls.CONFIG),
            ".yml": cls.NERD.get("yaml", cls.CONFIG),
            ".toml": cls.CONFIG,
            ".md": cls.NERD.get("markdown", cls.FILE),
            ".txt": cls.FILE,
            ".log": cls.FILE,
            ".png": cls.IMAGE,
            ".jpg": cls.IMAGE,
            ".jpeg": cls.IMAGE,
            ".gif": cls.IMAGE,
            ".svg": cls.IMAGE,
            ".sh": cls.NERD.get("terminal", cls.TERMINAL),
            ".bash": cls.NERD.get("terminal", cls.TERMINAL),
            ".zsh": cls.NERD.get("terminal", cls.TERMINAL),
            ".dockerfile": cls.NERD.get("docker", cls.FILE),
        }

        ext = os.path.splitext(filename.lower())[1]
        return ext_map.get(ext, cls.FILE)


    @classmethod
    def get_tool_icon(cls, tool_name: str) -> str:
        """Get icon for tool."""
        tool_map = {
            "read": cls.FILE,
            "write": cls.EDIT,
            "edit": cls.EDIT,
            "glob": cls.SEARCH,
            "grep": cls.SEARCH,
            "bash": cls.TERMINAL,
            "webfetch": cls.GLOBE,
            "websearch": cls.GLOBE,
            "todowrite": cls.BULLET,
            "task": cls.AI,
        }
        return tool_map.get(tool_name.lower(), cls.GEAR)

    # ═══════════════════════════════════════════════════════════════
    # TOOL-SPECIFIC ICONS WITH ENHANCED VISIBILITY
    # ═══════════════════════════════════════════════════════════════






# ═══════════════════════════════════════════════════════════════════════
# EMOJI HELPER
# ═══════════════════════════════════════════════════════════════════════


class Emoji:
    """Emoji helper for consistent usage."""

    @staticmethod
    def status(status: str) -> str:
        """Get emoji for status."""
        status_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "loading": "⏳",
            "complete": "✨",
            "thinking": "🤔",
            "working": "⚙️",
            "rocket": "🚀",
            "fire": "🔥",
            "star": "⭐",
            "check": "✓",
            "cross": "✗",
        }
        return status_map.get(status.lower(), "•")

    @staticmethod
    def mood(mood: str) -> str:
        """Get emoji for mood/state."""
        mood_map = {
            "happy": "😊",
            "sad": "😢",
            "confused": "😕",
            "excited": "🎉",
            "thinking": "🤔",
            "sleeping": "😴",
            "working": "💪",
            "celebrating": "🎊",
        }
        return mood_map.get(mood.lower(), "🙂")


# ═══════════════════════════════════════════════════════════════════════
# DECORATIVE BORDERS
# ═══════════════════════════════════════════════════════════════════════


class Borders:
    """Decorative border characters."""

    pass



