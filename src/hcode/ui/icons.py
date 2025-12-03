"""
HCode Icon System
Nerd Font and Unicode icons for the UI.
"""
import os
import sys
from enum import Enum
from typing import Dict, Optional


# ═══════════════════════════════════════════════════════════════════════
# PLATFORM DETECTION
# ═══════════════════════════════════════════════════════════════════════

IS_WINDOWS = sys.platform == "win32"


def supports_unicode() -> bool:
    """Check if terminal supports Unicode."""
    if IS_WINDOWS:
        return (
            os.environ.get("WT_SESSION") is not None or
            os.environ.get("ConEmuANSI") == "ON" or
            os.environ.get("TERM_PROGRAM") == "vscode"
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
    CROSS = "✖" if USE_UNICODE else "[X]"  # Alias for ERROR
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

    TODO_PENDING = "○" if USE_UNICODE else "[ ]"
    TODO_IN_PROGRESS = "◐" if USE_UNICODE else "[~]"
    TODO_COMPLETED = "✔" if USE_UNICODE else "[X]"
    TODO_BLOCKED = "✖" if USE_UNICODE else "[!]"
    TODO_SKIPPED = "◌" if USE_UNICODE else "[-]"
    CIRCLE_EMPTY = "○" if USE_UNICODE else "( )"
    SQUARE_FILLED = "■" if USE_UNICODE else "[#]"
    TODO = "☐" if USE_UNICODE else "[ ]"

    # ═══════════════════════════════════════════════════════════════
    # ACTION ICONS
    # ═══════════════════════════════════════════════════════════════

    PLAY = "▶" if USE_UNICODE else "[>]"
    PAUSE = "⏸" if USE_UNICODE else "[||]"
    STOP = "⏹" if USE_UNICODE else "[#]"
    REFRESH = "⟳" if USE_UNICODE else "[R]"
    SAVE = "💾" if USE_UNICODE else "[S]"
    DELETE = "🗑" if USE_UNICODE else "[D]"
    EDIT = "✎" if USE_UNICODE else "[E]"
    COPY = "📋" if USE_UNICODE else "[C]"
    SEARCH = "🔍" if USE_UNICODE else "[?]"

    # ═══════════════════════════════════════════════════════════════
    # FILE ICONS
    # ═══════════════════════════════════════════════════════════════

    FILE = "📄" if USE_UNICODE else "[F]"
    FOLDER = "📁" if USE_UNICODE else "[D]"
    FOLDER_OPEN = "📂" if USE_UNICODE else "[D]"
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
    DATABASE = "🗃" if USE_UNICODE else "[DB]"

    # ═══════════════════════════════════════════════════════════════
    # COMMUNICATION
    # ═══════════════════════════════════════════════════════════════

    USER = "👤" if USE_UNICODE else "[U]"
    MESSAGE = "💬" if USE_UNICODE else "[M]"
    SEND = "➤" if USE_UNICODE else "[>]"
    THINKING = "💭" if USE_UNICODE else "[...]"
    AGENT = "🤖" if USE_UNICODE else "[AI]"
    PROMPT = "❯" if USE_UNICODE else ">"

    # ═══════════════════════════════════════════════════════════════
    # BRANDING / UI
    # ═══════════════════════════════════════════════════════════════

    LOGO = "◈" if USE_UNICODE else "[H]"
    TOOL = "⚙" if USE_UNICODE else "[T]"
    CODE = "📝" if USE_UNICODE else "[<>]"
    FOLDER = "📁" if USE_UNICODE else "[D]"
    GLOBE = "🌐" if USE_UNICODE else "[W]"
    ARROW_RIGHT_FANCY = "❯" if USE_UNICODE else ">"
    STAR = "★" if USE_UNICODE else "*"

    # ═══════════════════════════════════════════════════════════════
    # DECORATIVE
    # ═══════════════════════════════════════════════════════════════

    DIAMOND = "◆" if USE_UNICODE else "<>"
    DIAMOND_SMALL = "◈" if USE_UNICODE else "<>"
    DIAMOND_EMPTY = "◇" if USE_UNICODE else "<>"
    STAR = "★" if USE_UNICODE else "*"
    STAR_EMPTY = "☆" if USE_UNICODE else "*"
    BULLET = "•" if USE_UNICODE else "*"
    BULLET_HOLLOW = "◦" if USE_UNICODE else "o"

    # ═══════════════════════════════════════════════════════════════
    # ARROWS
    # ═══════════════════════════════════════════════════════════════

    ARROW_RIGHT = "→" if USE_UNICODE else "->"
    ARROW_LEFT = "←" if USE_UNICODE else "<-"
    ARROW_UP = "↑" if USE_UNICODE else "^"
    ARROW_DOWN = "↓" if USE_UNICODE else "v"
    ARROW_RIGHT_BOLD = "➜" if USE_UNICODE else "=>"
    CHEVRON_RIGHT = "›" if USE_UNICODE else ">"
    CHEVRON_LEFT = "‹" if USE_UNICODE else "<"
    DOUBLE_ARROW_RIGHT = "»" if USE_UNICODE else ">>"
    DOUBLE_ARROW_LEFT = "«" if USE_UNICODE else "<<"

    # ═══════════════════════════════════════════════════════════════
    # BOX DRAWING
    # ═══════════════════════════════════════════════════════════════

    BOX_TL = "╭" if USE_UNICODE else "+"
    BOX_TR = "╮" if USE_UNICODE else "+"
    BOX_BL = "╰" if USE_UNICODE else "+"
    BOX_BR = "╯" if USE_UNICODE else "+"
    BOX_H = "─" if USE_UNICODE else "-"
    BOX_V = "│" if USE_UNICODE else "|"
    BOX_CROSS = "┼" if USE_UNICODE else "+"

    # ═══════════════════════════════════════════════════════════════
    # PROGRESS
    # ═══════════════════════════════════════════════════════════════

    PROGRESS_FULL = "█" if USE_UNICODE else "#"
    PROGRESS_SEVEN = "▓" if USE_UNICODE else "="
    PROGRESS_HALF = "▒" if USE_UNICODE else "-"
    PROGRESS_LIGHT = "░" if USE_UNICODE else "."
    PROGRESS_EMPTY = "·" if USE_UNICODE else " "

    # ═══════════════════════════════════════════════════════════════
    # TECH/CYBER SPECIFIC
    # ═══════════════════════════════════════════════════════════════

    CYBER_DOT = "◉" if USE_UNICODE else "(*)"
    CYBER_RING = "○" if USE_UNICODE else "()"
    CIRCUIT_H = "═" if USE_UNICODE else "="
    CIRCUIT_V = "║" if USE_UNICODE else "|"
    NODE = "◎" if USE_UNICODE else "@"
    PULSE = "●" if USE_UNICODE else "*"
    GLOW = "◈" if USE_UNICODE else "<>"

    # ═══════════════════════════════════════════════════════════════
    # SPINNER FRAMES
    # ═══════════════════════════════════════════════════════════════

    SPINNER_ORBIT = ["◐", "◓", "◑", "◒"] if USE_UNICODE else ["-", "\\", "|", "/"]
    SPINNER_DOTS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"] if USE_UNICODE else [".", "..", "...", ".."]
    SPINNER_PULSE = ["●", "◉", "○", "◉"] if USE_UNICODE else ["#", "=", "-", "="]

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
    def get_status_icon(cls, status: str) -> str:
        """Get icon for status."""
        status_map = {
            "success": cls.SUCCESS,
            "error": cls.ERROR,
            "warning": cls.WARNING,
            "info": cls.INFO,
            "loading": cls.LOADING,
            "online": cls.ONLINE,
            "offline": cls.OFFLINE,
            "pending": cls.PENDING,
            "complete": cls.COMPLETE,
            "ready": cls.ONLINE,
            "thinking": cls.LOADING,
        }
        return status_map.get(status.lower(), cls.BULLET)

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

    # Single line
    SINGLE_H = "─" if USE_UNICODE else "-"
    SINGLE_V = "│" if USE_UNICODE else "|"
    SINGLE_TL = "┌" if USE_UNICODE else "+"
    SINGLE_TR = "┐" if USE_UNICODE else "+"
    SINGLE_BL = "└" if USE_UNICODE else "+"
    SINGLE_BR = "┘" if USE_UNICODE else "+"

    # Standard aliases (for compatibility)
    HORIZONTAL = SINGLE_H
    VERTICAL = SINGLE_V
    CORNER_TL = SINGLE_TL
    CORNER_TR = SINGLE_TR
    CORNER_BL = SINGLE_BL
    CORNER_BR = SINGLE_BR

    # Double line
    DOUBLE_H = "═" if USE_UNICODE else "="
    DOUBLE_V = "║" if USE_UNICODE else "|"
    DOUBLE_TL = "╔" if USE_UNICODE else "+"
    DOUBLE_TR = "╗" if USE_UNICODE else "+"
    DOUBLE_BL = "╚" if USE_UNICODE else "+"
    DOUBLE_BR = "╝" if USE_UNICODE else "+"

    # Rounded
    ROUND_TL = "╭" if USE_UNICODE else "+"
    ROUND_TR = "╮" if USE_UNICODE else "+"
    ROUND_BL = "╰" if USE_UNICODE else "+"
    ROUND_BR = "╯" if USE_UNICODE else "+"

    # Thick
    THICK_H = "━" if USE_UNICODE else "="
    THICK_V = "┃" if USE_UNICODE else "|"

    @classmethod
    def horizontal_line(cls, width: int, style: str = "single") -> str:
        """Create horizontal line."""
        chars = {
            "single": cls.SINGLE_H,
            "double": cls.DOUBLE_H,
            "thick": cls.THICK_H,
        }
        return chars.get(style, cls.SINGLE_H) * width

    @classmethod
    def create_box(cls, width: int, height: int, style: str = "rounded") -> str:
        """Create a box of specified dimensions."""
        if style == "rounded":
            tl, tr, bl, br = cls.ROUND_TL, cls.ROUND_TR, cls.ROUND_BL, cls.ROUND_BR
            h, v = cls.SINGLE_H, cls.SINGLE_V
        elif style == "double":
            tl, tr, bl, br = cls.DOUBLE_TL, cls.DOUBLE_TR, cls.DOUBLE_BL, cls.DOUBLE_BR
            h, v = cls.DOUBLE_H, cls.DOUBLE_V
        else:
            tl, tr, bl, br = cls.SINGLE_TL, cls.SINGLE_TR, cls.SINGLE_BL, cls.SINGLE_BR
            h, v = cls.SINGLE_H, cls.SINGLE_V

        top = tl + (h * (width - 2)) + tr
        mid = v + (" " * (width - 2)) + v
        bot = bl + (h * (width - 2)) + br

        lines = [top]
        for _ in range(height - 2):
            lines.append(mid)
        lines.append(bot)

        return "\n".join(lines)
