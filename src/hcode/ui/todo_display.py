"""
Persistent Todo Display Component for HCode CLI.

Provides a Claude Code-style persistent todo list that displays at the
bottom of the terminal to track agent progress in real-time.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.text import Text

from hcode.ui.theme import get_palette

# ═══════════════════════════════════════════════════════════════════════
# CLAUDE CODE STYLE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

# Checkbox characters (Claude Code style)
CHECKBOX_CHECKED = "☒"
CHECKBOX_UNCHECKED = "☐"

# Icons
ICON_SPARKLE = "✶"
ICON_BRANCH = "⎿"


class ClaudeCodeTodoDisplay:
    """
    Claude Code-style todo display with persistent bottom bar.

    Displays like:
    ✶ Writing integration tests… (esc to interrupt · ctrl+t to hide todos · 3m 21s · ↓ 9.5k tokens)
     ⎿  ☒ Fix Rich markup escaping in Edit tool display
        ☒ Fix long line handling in Edit tool display
        ☐ Write more integration tests for Edit tool
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.palette = get_palette()
        self.start_time: Optional[datetime] = None
        self.token_count: int = 0

    def format_duration(self, seconds: float) -> str:
        """Format duration as Xm Ys or Xs."""
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"

    def format_tokens(self, tokens: int) -> str:
        """Format token count with K suffix if large."""
        if tokens >= 1000:
            return f"{tokens / 1000:.1f}k"
        return str(tokens)

    def render(
            self,
            todos: List[Dict[str, Any]],
            elapsed_seconds: float = 0,
            token_count: int = 0,
            show_shortcuts: bool = True,
    ) -> Text:
        """
        Render Claude Code-style todo display.

        Args:
            todos: List of todo dictionaries with content, status, activeForm
            elapsed_seconds: Time elapsed since start
            token_count: Number of tokens used
            show_shortcuts: Whether to show keyboard shortcuts

        Returns:
            Rich Text object for printing
        """
        if not todos:
            return Text("", style="dim")

        text = Text()

        # Find current in-progress task
        current_task = next((t for t in todos if t.get("status") == "in_progress"), None)

        # Header line with sparkle and active task
        if current_task:
            active_text = current_task.get("activeForm") or current_task.get("content", "Working…")
            text.append(f"{ICON_SPARKLE} ")
            text.append(f"{active_text}… ")
        else:
            # All done or no in-progress
            completed = sum(1 for t in todos if t.get("status") == "completed")
            if completed == len(todos):
                text.append(f"{ICON_SPARKLE} ")
                text.append("All tasks completed ")
            else:
                text.append(f"{ICON_SPARKLE} ")
                text.append("Ready ")

        # Status info in parentheses
        status_parts = []
        if show_shortcuts:
            status_parts.append("esc to interrupt")
            status_parts.append("ctrl+t to hide todos")
        if elapsed_seconds > 0:
            status_parts.append(self.format_duration(elapsed_seconds))
        if token_count > 0:
            status_parts.append(f"↓ {self.format_tokens(token_count)} tokens")

        if status_parts:
            text.append("(", style="dim")
            text.append(" · ".join(status_parts), style="dim")
            text.append(")", style="dim")

        text.append("\n")

        # Todo items with branch connector
        text.append(f" {ICON_BRANCH}  ")

        for i, todo in enumerate(todos):
            if i > 0:
                text.append("\n    ")  # Indent continuation lines

            status = todo.get("status", "pending")
            content = todo.get("content", "")

            if status == "completed":
                text.append(f"{CHECKBOX_CHECKED} ")
                text.append(content)
            elif status == "in_progress":
                text.append(f"{CHECKBOX_UNCHECKED} ")
                text.append(content)
            else:  # pending
                text.append(f"{CHECKBOX_UNCHECKED} ", style="dim")
                text.append(content, style="dim")

        return text

    def print(
            self,
            todos: List[Dict[str, Any]],
            elapsed_seconds: float = 0,
            token_count: int = 0,
            show_shortcuts: bool = True,
    ):
        """Print the todo display to console."""
        rendered = self.render(todos, elapsed_seconds, token_count, show_shortcuts)
        self.console.print(rendered)
