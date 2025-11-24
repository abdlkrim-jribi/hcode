"""
Icons and symbols for Hcode CLI.
Windows-compatible icon set with fallbacks.
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict


# ============================================================
# PLATFORM DETECTION
# ============================================================

IS_WINDOWS = sys.platform == "win32"

def supports_unicode() -> bool:
    """Check if terminal supports Unicode"""
    if IS_WINDOWS:
        return (
            os.environ.get("WT_SESSION") is not None or
            os.environ.get("ConEmuANSI") == "ON" or
            os.environ.get("TERM_PROGRAM") == "vscode"
        )
    return True

USE_UNICODE = supports_unicode()


# ============================================================
# ICON SETS
# ============================================================

@dataclass(frozen=True)
class Icons:
    """Complete icon set for the CLI - Windows compatible"""

    # ─────────────────────────────────────────────────────────
    # STATUS ICONS
    # ─────────────────────────────────────────────────────────

    # Checkmarks
    CHECK: str = "[OK]" if not USE_UNICODE else "✓"
    CHECK_BOLD: str = "[OK]" if not USE_UNICODE else "✔"
    CHECK_BOX: str = "[X]" if not USE_UNICODE else "☑"

    # Crosses
    CROSS: str = "[X]" if not USE_UNICODE else "✗"
    CROSS_BOLD: str = "[X]" if not USE_UNICODE else "✘"

    # Circles
    CIRCLE_EMPTY: str = "( )" if not USE_UNICODE else "○"
    CIRCLE_FILLED: str = "(*)" if not USE_UNICODE else "●"
    CIRCLE_HALF: str = "(~)" if not USE_UNICODE else "◐"
    CIRCLE_DOT: str = "(.)" if not USE_UNICODE else "⊙"

    # Squares
    SQUARE_EMPTY: str = "[ ]" if not USE_UNICODE else "☐"
    SQUARE_FILLED: str = "[#]" if not USE_UNICODE else "■"
    SQUARE_SMALL: str = "[.]" if not USE_UNICODE else "▪"

    # ─────────────────────────────────────────────────────────
    # TODO STATUS ICONS
    # ─────────────────────────────────────────────────────────

    TODO_PENDING: str = "[ ]" if not USE_UNICODE else "○"
    TODO_IN_PROGRESS: str = "[~]" if not USE_UNICODE else "◐"
    TODO_COMPLETED: str = "[X]" if not USE_UNICODE else "●"
    TODO_BLOCKED: str = "[!]" if not USE_UNICODE else "⊘"
    TODO_SKIPPED: str = "[-]" if not USE_UNICODE else "◌"

    # ─────────────────────────────────────────────────────────
    # AGENT STATE ICONS
    # ─────────────────────────────────────────────────────────

    THINKING: str = "[...]" if not USE_UNICODE else "◊"
    THINKING_ALT: str = "[?]" if not USE_UNICODE else "◇"
    EXECUTING: str = "[>]" if not USE_UNICODE else "▶"
    WAITING: str = "[.]" if not USE_UNICODE else "◌"
    COMPLETE: str = "[OK]" if not USE_UNICODE else "✓"
    ERROR: str = "[ERR]" if not USE_UNICODE else "✗"
    WARNING: str = "[!]" if not USE_UNICODE else "⚠"
    INFO: str = "[i]" if not USE_UNICODE else "ℹ"

    # ─────────────────────────────────────────────────────────
    # TOOL ICONS
    # ─────────────────────────────────────────────────────────

    TOOL: str = "[T]" if not USE_UNICODE else "◈"
    TOOL_ALT: str = "[*]" if not USE_UNICODE else "◆"
    FILE: str = "[F]" if not USE_UNICODE else "◇"
    FOLDER: str = "[D]" if not USE_UNICODE else "▷"
    CODE: str = "[<>]" if not USE_UNICODE else "◈"
    TERMINAL: str = "[>_]" if not USE_UNICODE else "▣"
    SEARCH: str = "[?]" if not USE_UNICODE else "◎"
    EDIT: str = "[E]" if not USE_UNICODE else "◇"
    DELETE: str = "[X]" if not USE_UNICODE else "⊗"
    GLOBE: str = "[W]" if not USE_UNICODE else "◉"
    DATABASE: str = "[DB]" if not USE_UNICODE else "▤"
    KEY: str = "[K]" if not USE_UNICODE else "◇"
    LOCK: str = "[L]" if not USE_UNICODE else "▣"
    UNLOCK: str = "[U]" if not USE_UNICODE else "▢"

    # ─────────────────────────────────────────────────────────
    # ARROWS & POINTERS
    # ─────────────────────────────────────────────────────────

    ARROW_RIGHT: str = "->" if not USE_UNICODE else "→"
    ARROW_LEFT: str = "<-" if not USE_UNICODE else "←"
    ARROW_UP: str = "^" if not USE_UNICODE else "↑"
    ARROW_DOWN: str = "v" if not USE_UNICODE else "↓"
    ARROW_RIGHT_BOLD: str = "=>" if not USE_UNICODE else "➜"
    ARROW_RIGHT_FANCY: str = ">" if not USE_UNICODE else "❯"
    ARROW_DOUBLE_RIGHT: str = ">>" if not USE_UNICODE else "»"
    ARROW_DOUBLE_LEFT: str = "<<" if not USE_UNICODE else "«"
    CHEVRON_RIGHT: str = ">" if not USE_UNICODE else "›"
    CHEVRON_LEFT: str = "<" if not USE_UNICODE else "‹"
    POINTER: str = ">" if not USE_UNICODE else "▶"
    POINTER_SMALL: str = ">" if not USE_UNICODE else "▸"

    # ─────────────────────────────────────────────────────────
    # PROGRESS INDICATORS
    # ─────────────────────────────────────────────────────────

    PROGRESS_EMPTY: str = "-" if not USE_UNICODE else "░"
    PROGRESS_PARTIAL: str = "=" if not USE_UNICODE else "▒"
    PROGRESS_FULL: str = "#" if not USE_UNICODE else "█"
    PROGRESS_START: str = "[" if not USE_UNICODE else "▐"
    PROGRESS_END: str = "]" if not USE_UNICODE else "▌"

    # Progress bar characters
    BAR_START: str = "[" if not USE_UNICODE else "╺"
    BAR_MID: str = "=" if not USE_UNICODE else "━"
    BAR_END: str = "]" if not USE_UNICODE else "╸"
    BAR_EMPTY: str = "-" if not USE_UNICODE else "─"

    # ─────────────────────────────────────────────────────────
    # MODE ICONS
    # ─────────────────────────────────────────────────────────

    LIGHTNING: str = "[!]" if not USE_UNICODE else "⚡"
    LIGHTNING_ALT: str = "[>]" if not USE_UNICODE else "↯"
    AUTO: str = "[A]" if not USE_UNICODE else "⚡"
    INTERACTIVE: str = "[I]" if not USE_UNICODE else "◈"
    PLAN: str = "[P]" if not USE_UNICODE else "▣"
    REVIEW: str = "[R]" if not USE_UNICODE else "◎"
    TASK: str = "[T]" if not USE_UNICODE else "▣"

    # ─────────────────────────────────────────────────────────
    # MISC SYMBOLS
    # ─────────────────────────────────────────────────────────

    STAR: str = "*" if not USE_UNICODE else "★"
    STAR_EMPTY: str = "*" if not USE_UNICODE else "☆"
    HEART: str = "<3" if not USE_UNICODE else "♥"
    DIAMOND: str = "<>" if not USE_UNICODE else "◆"
    DIAMOND_EMPTY: str = "<>" if not USE_UNICODE else "◇"
    BULLET: str = "*" if not USE_UNICODE else "•"
    ELLIPSIS: str = "..." if not USE_UNICODE else "…"
    INFINITY: str = "oo" if not USE_UNICODE else "∞"

    # ─────────────────────────────────────────────────────────
    # SPECIAL CHARACTERS
    # ─────────────────────────────────────────────────────────

    PROMPT: str = ">" if not USE_UNICODE else "❯"
    PROMPT_CONTINUE: str = "." if not USE_UNICODE else "·"
    PROMPT_ERROR: str = "!" if not USE_UNICODE else "✗"

    # Tree structure
    TREE_BRANCH: str = "+" if not USE_UNICODE else "├"
    TREE_LAST: str = "`" if not USE_UNICODE else "└"
    TREE_PIPE: str = "|" if not USE_UNICODE else "│"
    TREE_SPACE: str = " "

    # Git-style
    BRANCH: str = "@" if not USE_UNICODE else "⎇"
    COMMIT: str = "*" if not USE_UNICODE else "●"
    MERGE: str = "+" if not USE_UNICODE else "⊕"

    # ─────────────────────────────────────────────────────────
    # BRAND / IDENTITY
    # ─────────────────────────────────────────────────────────

    LOGO: str = "[H]" if not USE_UNICODE else "◈"
    LOGO_ALT: str = "[H]" if not USE_UNICODE else "⬡"
    AGENT: str = "[A]" if not USE_UNICODE else "◈"
    HCODE: str = "[H]" if not USE_UNICODE else "◈"


# ============================================================
# SPINNER ANIMATIONS
# ============================================================

class Spinners:
    """Spinner animation frames"""

    # Simple spinner (works everywhere)
    SIMPLE = ["-", "\\", "|", "/"]

    # Dots spinner (Unicode)
    DOTS = [".", "..", "...", ".."] if not USE_UNICODE else ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    # Line spinner
    LINE = ["-", "\\", "|", "/"]

    # Arc spinner
    ARC = [".", "o", "O", "o"] if not USE_UNICODE else ["◜", "◠", "◝", "◞", "◡", "◟"]

    # Circle spinner
    CIRCLE = ["()", "(o)", "(O)", "(o)"] if not USE_UNICODE else ["◐", "◓", "◑", "◒"]

    # Bounce spinner
    BOUNCE = [".", "o", ".", " "] if not USE_UNICODE else ["⠁", "⠂", "⠄", "⠂"]

    # Pulse spinner
    PULSE = ["#", "=", "-", "="] if not USE_UNICODE else ["█", "▓", "▒", "░", "▒", "▓"]

    # Growing dots
    GROWING = [".", "..", "...", ".."]

    # Braille dots (smoother animation)
    BRAILLE = DOTS if not USE_UNICODE else ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    # Elegant minimal
    ELEGANT = [". ", " .", " .", ". "] if not USE_UNICODE else ["◜ ", " ◝", " ◞", "◟ "]

    # Default
    DEFAULT = SIMPLE if not USE_UNICODE else DOTS


# ============================================================
# ICON HELPER FUNCTIONS
# ============================================================

def get_status_icon(status: str, style: str = "unicode") -> str:
    """Get appropriate icon for a status"""
    icons = Icons()

    mapping = {
        "pending": icons.TODO_PENDING,
        "in_progress": icons.TODO_IN_PROGRESS,
        "completed": icons.TODO_COMPLETED,
        "blocked": icons.TODO_BLOCKED,
        "skipped": icons.TODO_SKIPPED,
        "success": icons.CHECK,
        "error": icons.CROSS,
        "warning": icons.WARNING,
        "info": icons.INFO,
    }

    return mapping.get(status, icons.CIRCLE_EMPTY)


def get_file_icon(filename: str) -> str:
    """Get icon based on file extension"""
    icons = Icons()

    ext_mapping = {
        ".py": icons.CODE,
        ".js": icons.CODE,
        ".ts": icons.CODE,
        ".jsx": icons.CODE,
        ".tsx": icons.CODE,
        ".html": icons.GLOBE,
        ".css": icons.FILE,
        ".json": icons.FILE,
        ".yaml": icons.FILE,
        ".yml": icons.FILE,
        ".md": icons.FILE,
        ".txt": icons.FILE,
        ".sh": icons.TERMINAL,
        ".bash": icons.TERMINAL,
        ".sql": icons.DATABASE,
        ".env": icons.KEY,
    }

    ext = os.path.splitext(filename.lower())[1]
    return ext_mapping.get(ext, icons.FILE)


def get_tool_icon(tool_name: str) -> str:
    """Get icon for a tool"""
    icons = Icons()

    tool_mapping = {
        "read": icons.FILE,
        "write": icons.EDIT,
        "edit": icons.EDIT,
        "glob": icons.SEARCH,
        "grep": icons.SEARCH,
        "bash": icons.TERMINAL,
        "webfetch": icons.GLOBE,
        "websearch": icons.GLOBE,
        "todowrite": icons.SQUARE_FILLED,
        "task": icons.AGENT,
    }

    return tool_mapping.get(tool_name.lower(), icons.TOOL)
