"""
HCode Futuristic Interactive Chat Interface
Beautiful, responsive chat experience.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, AsyncIterator, List, Any

from rich.console import Console, RenderableType
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding
from rich.rule import Rule
from rich.text import Text

from hcode.ui.animations import ThinkingAnimation
from hcode.ui.panels import (
    WelcomePanel,
    UserMessagePanel,
    AIMessagePanel,
    ToolPanel,
    ErrorPanel,
    SuccessPanel,
    TokenUsagePanel,
)
from hcode.ui.theme import ThemeMode, get_theme, get_palette


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







    def display_error(self, message: str, details: Optional[str] = None) -> None:
        """Display error message with styling."""
        panel = ErrorPanel(message, details)
        self.console.print(panel.render())
        self.console.print()

    def display_success(self, message: str, details: Optional[str] = None) -> None:
        """Display success message."""
        panel = SuccessPanel(message, details)
        self.console.print(panel.render())
        self.console.print()

    def display_info(self, message: str) -> None:
        """Display info message."""
        palette = get_palette()

        text = Text()
        text.append("ℹ ", style=f"bold {palette.info}")
        text.append(message, style=palette.info)

        self.console.print(text)
        self.console.print()



    def display_goodbye(self) -> None:
        """Display goodbye message."""
        palette = get_palette()

        text = Text()
        text.append("\n◈ ", style=f"bold {palette.secondary}")
        text.append("Session ended. ", style=palette.text_primary)
        text.append("See you next time!", style=f"italic {palette.primary}")

        self.console.print(text)

    def get_input_prompt(self, label: str = "You") -> Text:
        """Get styled input prompt text (Floating Input)."""
        palette = get_palette()
        from hcode.ui.icons import Icons
        icons = Icons()
        
        text = Text()
        # Lambda icon in Cyan
        text.append(f"{icons.PROMPT_LAMBDA} ", style=f"bold {palette.primary}")
        
        # We can drop the label for a cleaner look or keep it minimal
        # Design spec: "Prefix: A colored lambda λ"
        # Let's keep label but make it subtle if needed, or just Lambda?
        # "Floating Input: For User Ask, characterized by a colored prefix (λ) and an underlined input area."
        # Use Lambda + Label for clarity
        text.append(f"{label} ", style=f"bold {palette.secondary}")
        
        return text

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


# ═══════════════════════════════════════════════════════════════════════
# INTERACTIVE PROMPT
# ═══════════════════════════════════════════════════════════════════════




# ═══════════════════════════════════════════════════════════════════════
# QUICK CHAT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


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
