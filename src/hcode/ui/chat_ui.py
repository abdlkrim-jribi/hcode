"""
HCode Futuristic Interactive Chat Interface
Beautiful, responsive chat experience.
"""
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.rule import Rule
from rich.align import Align
from rich.padding import Padding
from rich.live import Live
from rich.box import ROUNDED, DOUBLE, HEAVY
from typing import Optional, AsyncIterator, List, Callable, Any
from datetime import datetime
from pathlib import Path
import asyncio
import time

from .theme import ThemeEngine, ThemeMode, get_theme, get_palette
from .components import CyberPanel, StatusIndicator, TokenCounter
from .animations import ThinkingAnimation, StreamingText
from .panels import (
    WelcomePanel,
    UserMessagePanel,
    AIMessagePanel,
    ToolPanel,
    ErrorPanel,
    SuccessPanel,
    TokenUsagePanel,
)


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

    async def stream_ai_response(
        self,
        token_stream: AsyncIterator[str],
    ) -> str:
        """Stream AI response with live rendering."""
        palette = get_palette()
        full_response = []

        with Live(
            Text("▌", style=f"bold {palette.primary}"),
            console=self.console,
            refresh_per_second=30,
            vertical_overflow="visible",
        ) as live:
            async for token in token_stream:
                full_response.append(token)
                current_text = "".join(full_response)

                # Render with cursor
                display = Text()
                display.append(current_text, style=palette.text_primary)
                display.append("▌", style=f"bold {palette.primary}")

                live.update(Padding(display, (0, 0, 0, 2)))

            # Final render without cursor
            final_text = "".join(full_response)
            live.update(Padding(
                self._render_response(final_text),
                (0, 0, 0, 2),
            ))

        return final_text

    def stream_ai_response_sync(
        self,
        token_iterator: Any,
    ) -> str:
        """Stream AI response synchronously."""
        palette = get_palette()
        full_response = []

        with Live(
            Text("▌", style=f"bold {palette.primary}"),
            console=self.console,
            refresh_per_second=30,
            vertical_overflow="visible",
        ) as live:
            for token in token_iterator:
                full_response.append(token)
                current_text = "".join(full_response)

                display = Text()
                display.append(current_text, style=palette.text_primary)
                display.append("▌", style=f"bold {palette.primary}")

                live.update(Padding(display, (0, 0, 0, 2)))

            final_text = "".join(full_response)
            live.update(Padding(
                self._render_response(final_text),
                (0, 0, 0, 2),
            ))

        return final_text

    def _render_response(self, text: str) -> RenderableType:
        """Render response with markdown and syntax highlighting."""
        if "```" in text or text.startswith("#"):
            return Markdown(text, code_theme="dracula")
        return Text(text)

    def display_ai_message(self, content: str, thinking: Optional[str] = None) -> None:
        """Display complete AI message."""
        panel = AIMessagePanel(content, thinking)
        self.console.print(panel.render())
        self.console.print()

    def display_token_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        elapsed_time: Optional[float] = None,
    ) -> None:
        """Display token usage stats."""
        usage = TokenUsagePanel(input_tokens, output_tokens, elapsed_time)
        self.console.print(Padding(usage.render(), (1, 0, 0, 2)))
        self.console.print()

    def display_tool_execution(
        self,
        tool_name: str,
        tool_input: str,
        tool_output: Optional[str] = None,
        status: str = "running",
        duration: Optional[float] = None,
    ) -> None:
        """Display tool execution with futuristic styling."""
        panel = ToolPanel(tool_name, tool_input, tool_output, status, duration)
        self.console.print(Padding(panel.render(), (0, 0, 0, 2)))

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

    def display_warning(self, message: str) -> None:
        """Display warning message."""
        palette = get_palette()

        text = Text()
        text.append("⚠ ", style=f"bold {palette.warning}")
        text.append(message, style=palette.warning)

        self.console.print(text)
        self.console.print()

    def display_separator(self, label: Optional[str] = None) -> None:
        """Display a futuristic separator."""
        palette = get_palette()

        if label:
            self.console.print(Rule(label, style=palette.text_muted))
        else:
            self.console.print(Rule(style=palette.text_muted, characters="─"))

    def display_goodbye(self) -> None:
        """Display goodbye message."""
        palette = get_palette()

        text = Text()
        text.append("\n◈ ", style=f"bold {palette.secondary}")
        text.append("Session ended. ", style=palette.text_primary)
        text.append("See you next time!", style=f"italic {palette.primary}")

        self.console.print(text)

    def get_input_prompt(self, label: str = "You") -> Text:
        """Get styled input prompt text."""
        palette = get_palette()

        text = Text()
        text.append("◆ ", style=f"bold {palette.secondary}")
        text.append(f"{label} ", style=f"bold {palette.primary}")
        text.append("› ", style=palette.primary)

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

class InteractivePrompt:
    """Interactive prompt with history and suggestions."""

    def __init__(self, chat: ChatInterface):
        self.chat = chat
        self.history: List[str] = []
        self.history_index = -1

    def prompt(self, label: str = "You") -> Optional[str]:
        """Get user input with styled prompt."""
        prompt_text = self.chat.get_input_prompt(label)
        self.chat.console.print(prompt_text, end="")

        try:
            user_input = input().strip()
            if user_input:
                self.history.append(user_input)
                self.history_index = -1
            return user_input if user_input else None
        except (KeyboardInterrupt, EOFError):
            return None

    def prompt_confirm(
        self,
        message: str,
        default: bool = True,
    ) -> bool:
        """Prompt for yes/no confirmation."""
        palette = get_palette()

        prompt = Text()
        prompt.append("◆ ", style=f"bold {palette.warning}")
        prompt.append(message, style=palette.text_primary)

        if default:
            prompt.append(" [Y/n] ", style=palette.text_muted)
        else:
            prompt.append(" [y/N] ", style=palette.text_muted)

        self.chat.console.print(prompt, end="")

        try:
            response = input().strip().lower()
            if not response:
                return default
            return response in ("y", "yes")
        except (KeyboardInterrupt, EOFError):
            return False


# ═══════════════════════════════════════════════════════════════════════
# CHAT SESSION
# ═══════════════════════════════════════════════════════════════════════

class ChatSession:
    """Complete chat session manager."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        provider: str = "Anthropic",
    ):
        self.model = model
        self.provider = provider
        self.chat = ChatInterface()
        self.prompt = InteractivePrompt(self.chat)
        self.running = False

    def start(self) -> None:
        """Start the chat session."""
        self.running = True
        self.chat.clear()
        self.chat.display_welcome(self.model, self.provider)

    def stop(self) -> None:
        """Stop the chat session."""
        self.running = False
        self.chat.display_goodbye()

    def process_command(self, command: str) -> bool:
        """Process a command. Returns True if handled."""
        cmd = command.lower().strip()

        if cmd in ("/exit", "/quit", "/q"):
            self.running = False
            return True

        if cmd == "/clear":
            self.chat.clear()
            self.chat.display_welcome(self.model, self.provider)
            return True

        if cmd == "/help":
            self._show_help()
            return True

        if cmd.startswith("/theme"):
            self._handle_theme_command(cmd)
            return True

        return False

    def _show_help(self) -> None:
        """Show help information."""
        palette = get_palette()

        commands = [
            ("/help", "Show this help message"),
            ("/exit", "Exit the chat"),
            ("/clear", "Clear the screen"),
            ("/theme <name>", "Switch theme (cyberpunk, matrix, etc.)"),
        ]

        from .panels import HelpPanel
        panel = HelpPanel(commands)
        self.chat.console.print(panel.render())
        self.chat.console.print()

    def _handle_theme_command(self, cmd: str) -> None:
        """Handle theme switching."""
        parts = cmd.split()
        if len(parts) > 1:
            theme_name = parts[1]
            try:
                new_mode = ThemeMode(theme_name)
                get_theme().switch_theme(new_mode)
                self.chat.display_success(f"Switched to {theme_name} theme")
            except ValueError:
                available = ", ".join([m.value for m in ThemeMode])
                self.chat.display_error(
                    f"Unknown theme: {theme_name}",
                    f"Available themes: {available}"
                )
        else:
            available = ", ".join([m.value for m in ThemeMode])
            self.chat.display_info(f"Available themes: {available}")


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
