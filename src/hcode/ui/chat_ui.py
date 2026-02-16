"""
HCode Futuristic Interactive Chat Interface
Beautiful, responsive chat experience.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.padding import Padding
from rich.text import Text

from hcode.ui.animations import ThinkingAnimation
from hcode.ui.panels import (
    WelcomePanel,
    UserMessagePanel,
)
from hcode.ui.theme import get_theme, get_palette


# ═══════════════════════════════════════════════════════════════════════
# CHAT INTERFACE
# ═══════════════════════════════════════════════════════════════════════


class ChatInterface:
    """Futuristic chat interface with rich visuals."""

    def __init__(
            self,
            console: Optional[Console] = None,
            history_file: Optional[Path] = None,
    ):
        self.theme = get_theme()
        self.console = console or self.theme.console
        self.history_file = history_file or Path.home() / ".hcode" / "history"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Message history for display
        self.messages: List[dict] = []

    def display_welcome(
            self,
            model: str = "claude-sonnet-4-20250514",
            provider: str = "Anthropic",
    ) -> None:
        """Display welcome panel with system info."""
        panel = WelcomePanel(model=model, provider=provider)
        self.console.print(panel.render())
        self.console.print()

    def display_user_message(self, message: str) -> None:
        """Display user message with styling."""
        panel = UserMessagePanel(message)
        self.console.print(panel.render())
        self.console.print()

    def display_ai_message_start(self) -> None:
        """Display AI message header before streaming."""
        palette = get_palette()

        header = Text()
        header.append("◈ ", style=f"bold {palette.secondary}")
        header.append("HCode", style=f"bold {palette.accent}")
        header.append(f"  {datetime.now().strftime('%H:%M')}", style=palette.text_muted)

        self.console.print(header)

    def clear(self) -> None:
        """Clear the console."""
        self.console.clear()


# ═══════════════════════════════════════════════════════════════════════
# THINKING CONTEXT
# ═══════════════════════════════════════════════════════════════════════


class ThinkingContext:
    """Context manager for thinking/processing state."""

    def __init__(self, chat: ChatInterface, message: str = "Thinking"):
        self.chat = chat
        self.message = message
        self.animation: Optional[ThinkingAnimation] = None

    def __enter__(self):
        self.animation = ThinkingAnimation(self.chat.console)
        self.animation.start()
        return self

    def __exit__(self, *args):
        if self.animation:
            self.animation.stop()

    def update(self, message: str) -> None:
        """Update the thinking message."""
        if self.animation:
            self.animation.messages = [message]


def create_chat() -> ChatInterface:
    """Create a new chat interface."""
    return ChatInterface()


def display_message(
        content: str,
        role: str = "ai",
        console: Optional[Console] = None,
) -> None:
    """Quick function to display a message."""
    chat = ChatInterface(console)

    if role == "user":
        chat.display_user_message(content)
    else:
        chat.display_ai_message_start()
        chat.console.print(Padding(Text(content), (0, 0, 0, 2)))
        chat.console.print()


def display_thinking(
        console: Optional[Console] = None,
        message: str = "Thinking",
) -> ThinkingContext:
    """Create a thinking context."""
    chat = ChatInterface(console)
    return ThinkingContext(chat, message)
