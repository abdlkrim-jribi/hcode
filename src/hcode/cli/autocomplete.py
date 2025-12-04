"""
HCode Smart Autocomplete System

Provides intelligent command and text completion with:
- Slash command suggestions
- Context-aware completions
- History-based suggestions
- Smart phrase completion
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory, Suggestion
from prompt_toolkit.completion import (
    Completer,
    Completion,
    merge_completers,
)
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style


# ═══════════════════════════════════════════════════════════════════════
# COMMAND DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Command:
    """Represents a slash command."""

    name: str
    description: str
    aliases: List[str] = field(default_factory=list)
    category: str = "general"
    usage: str = ""
    examples: List[str] = field(default_factory=list)


# Built-in commands
BUILTIN_COMMANDS: List[Command] = [
    Command(
        name="/help",
        description="Show available commands and help",
        aliases=["/h", "/?"],
        category="system",
        usage="/help [command]",
        examples=["/help", "/help stats"],
    ),
    Command(
        name="/exit",
        description="Exit the chat session",
        aliases=["/quit", "/q", "/bye"],
        category="system",
    ),
    Command(
        name="/clear",
        description="Clear conversation history",
        aliases=["/cls", "/reset"],
        category="system",
    ),
    Command(
        name="/stats",
        description="Show session statistics (tokens, cost)",
        aliases=["/status", "/info"],
        category="system",
    ),
    Command(
        name="/export",
        description="Export conversation to file",
        aliases=["/save"],
        category="system",
        usage="/export [filename]",
    ),
    Command(
        name="/model",
        description="Switch AI model",
        aliases=["/m"],
        category="config",
        usage="/model <model_name>",
        examples=["/model gpt-4", "/model claude-3"],
    ),
    Command(
        name="/provider",
        description="Switch AI provider",
        aliases=["/p"],
        category="config",
        usage="/provider <anthropic|openai>",
    ),
    Command(
        name="/theme",
        description="Change UI theme",
        category="config",
        usage="/theme <theme_name>",
        examples=["/theme cyberpunk", "/theme matrix", "/theme frost"],
    ),
    Command(
        name="/undo",
        description="Undo last action",
        aliases=["/u"],
        category="editing",
    ),
    Command(
        name="/redo",
        description="Redo last undone action",
        category="editing",
    ),
    Command(
        name="/diff",
        description="Show pending changes",
        category="editing",
    ),
    Command(
        name="/commit",
        description="Commit pending changes",
        category="editing",
        usage="/commit [message]",
    ),
    Command(
        name="/run",
        description="Run a shell command",
        aliases=["/exec", "/!"],
        category="tools",
        usage="/run <command>",
        examples=["/run npm test", "/run python script.py"],
    ),
    Command(
        name="/read",
        description="Read a file",
        aliases=["/cat", "/view"],
        category="tools",
        usage="/read <filepath>",
    ),
    Command(
        name="/write",
        description="Write to a file",
        category="tools",
        usage="/write <filepath>",
    ),
    Command(
        name="/search",
        description="Search in codebase",
        aliases=["/find", "/grep"],
        category="tools",
        usage="/search <pattern>",
    ),
    Command(
        name="/web",
        description="Search the web",
        aliases=["/google"],
        category="tools",
        usage="/web <query>",
    ),
    Command(
        name="/todo",
        description="Manage todo list",
        aliases=["/tasks"],
        category="productivity",
        usage="/todo [add|remove|list]",
    ),
    Command(
        name="/context",
        description="Show current context",
        aliases=["/ctx"],
        category="debug",
    ),
    Command(
        name="/debug",
        description="Toggle debug mode",
        category="debug",
    ),
    Command(
        name="/memory",
        description="Show memory usage",
        category="debug",
    ),
    Command(
        name="/compact",
        description="Compact conversation history",
        category="system",
    ),
]


# ═══════════════════════════════════════════════════════════════════════
# SMART PHRASE COMPLETIONS
# ═══════════════════════════════════════════════════════════════════════

SMART_PHRASES: Dict[str, List[str]] = {
    # Common coding requests
    "create": [
        "create a function that",
        "create a class for",
        "create a REST API endpoint for",
        "create a test for",
        "create a component for",
    ],
    "add": [
        "add error handling to",
        "add logging to",
        "add tests for",
        "add documentation to",
        "add validation for",
        "add a feature that",
    ],
    "fix": [
        "fix the bug in",
        "fix the error",
        "fix the failing test",
        "fix the type error",
        "fix the import issue",
    ],
    "refactor": [
        "refactor this code to",
        "refactor for better performance",
        "refactor to use async/await",
        "refactor to follow best practices",
    ],
    "explain": [
        "explain this code",
        "explain how this works",
        "explain the error",
        "explain the architecture",
    ],
    "implement": [
        "implement a function that",
        "implement authentication",
        "implement error handling",
        "implement caching for",
        "implement pagination for",
    ],
    "optimize": [
        "optimize this code for performance",
        "optimize the database queries",
        "optimize memory usage",
        "optimize the algorithm",
    ],
    "update": [
        "update the dependencies",
        "update the configuration",
        "update the documentation",
        "update the tests",
    ],
    "remove": [
        "remove unused code",
        "remove deprecated features",
        "remove console.log statements",
    ],
    "write": [
        "write a test for",
        "write documentation for",
        "write a function that",
        "write a script that",
    ],
    "debug": [
        "debug this issue",
        "debug the failing test",
        "debug the error",
    ],
    "analyze": [
        "analyze this code",
        "analyze the performance",
        "analyze for security issues",
        "analyze the architecture",
    ],
    "review": [
        "review this code",
        "review for best practices",
        "review for security",
    ],
    "convert": [
        "convert this to TypeScript",
        "convert this to async/await",
        "convert to a class component",
        "convert to a functional component",
    ],
    "generate": [
        "generate a README",
        "generate tests for",
        "generate documentation for",
        "generate a migration for",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# COMMAND COMPLETER
# ═══════════════════════════════════════════════════════════════════════


class CommandCompleter(Completer):
    """Completer for slash commands with rich metadata."""

    def __init__(self, commands: Optional[List[Command]] = None):
        self.commands = commands or BUILTIN_COMMANDS
        self._build_lookup()

    def _build_lookup(self):
        """Build command lookup tables."""
        self.command_map: Dict[str, Command] = {}
        for cmd in self.commands:
            self.command_map[cmd.name] = cmd
            for alias in cmd.aliases:
                self.command_map[alias] = cmd

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Generate command completions."""
        text = document.text_before_cursor

        # Only complete if starting with /
        if not text.startswith("/"):
            return

        # Get the word being typed
        word = text.lstrip("/")

        # Find matching commands
        for cmd in self.commands:
            # Check main command name
            if cmd.name[1:].startswith(word):  # Remove leading /
                yield Completion(
                    cmd.name,
                    start_position=-len(text),
                    display=HTML(f"<b>{cmd.name}</b>"),
                    display_meta=HTML(f'<style fg="ansicyan">{cmd.description}</style>'),
                )

            # Check aliases
            for alias in cmd.aliases:
                if alias[1:].startswith(word) and alias != cmd.name:
                    yield Completion(
                        alias,
                        start_position=-len(text),
                        display=HTML(f"<i>{alias}</i>"),
                        display_meta=HTML(f'<style fg="ansimagenta">→ {cmd.name}</style>'),
                    )


# ═══════════════════════════════════════════════════════════════════════
# SMART PHRASE COMPLETER
# ═══════════════════════════════════════════════════════════════════════


class SmartPhraseCompleter(Completer):
    """Completer for smart phrase suggestions."""

    def __init__(self, phrases: Optional[Dict[str, List[str]]] = None):
        self.phrases = phrases or SMART_PHRASES

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Generate phrase completions."""
        text = document.text_before_cursor.lower().strip()

        # Don't complete commands
        if text.startswith("/"):
            return

        # Don't complete very short inputs
        if len(text) < 2:
            return

        # Get last word
        words = text.split()
        if not words:
            return

        last_word = words[-1]

        # Find matching phrases
        for trigger, completions in self.phrases.items():
            if trigger.startswith(last_word):
                for phrase in completions:
                    # Calculate what to add
                    remaining = phrase[len(last_word) :] if phrase.startswith(last_word) else phrase

                    yield Completion(
                        remaining,
                        start_position=0,
                        display=HTML(f'<style fg="ansiyellow">{phrase}</style>'),
                        display_meta=HTML('<style fg="ansiblue">suggestion</style>'),
                    )


# ═══════════════════════════════════════════════════════════════════════
# FILE PATH COMPLETER
# ═══════════════════════════════════════════════════════════════════════


class FilePathCompleter(Completer):
    """Completer for file paths in the current project."""

    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = Path(root_dir or os.getcwd())
        self._cache: List[str] = []
        self._cache_time = 0

    def _scan_files(self, max_depth: int = 4) -> List[str]:
        """Scan project files."""
        files = []
        ignore_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

        def scan(path: Path, depth: int = 0):
            if depth > max_depth:
                return
            try:
                for item in path.iterdir():
                    if item.name.startswith(".") and item.name not in [".env", ".gitignore"]:
                        continue
                    if item.is_dir():
                        if item.name not in ignore_dirs:
                            scan(item, depth + 1)
                    else:
                        rel_path = str(item.relative_to(self.root_dir))
                        files.append(rel_path.replace("\\", "/"))
            except PermissionError:
                pass

        scan(self.root_dir)
        return files[:500]  # Limit results

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Generate file path completions."""
        text = document.text_before_cursor

        # Look for file path patterns
        # After commands like /read, /write, or when typing paths
        patterns = [
            r"/(?:read|write|cat|view|edit)\s+(\S*)$",
            r"(?:file|path)[:\s]+(\S*)$",
            r'"([^"]*)"$',
            r"'([^']*)'$",
        ]

        path_prefix = None
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                path_prefix = match.group(1)
                break

        if path_prefix is None:
            return

        # Refresh cache periodically
        import time

        if time.time() - self._cache_time > 30:
            self._cache = self._scan_files()
            self._cache_time = time.time()

        # Find matching files
        path_prefix_lower = path_prefix.lower()
        for filepath in self._cache:
            if path_prefix_lower in filepath.lower():
                yield Completion(
                    filepath,
                    start_position=-len(path_prefix),
                    display=HTML(f'<style fg="ansigreen">{filepath}</style>'),
                    display_meta=HTML('<style fg="ansiblue">file</style>'),
                )


# ═══════════════════════════════════════════════════════════════════════
# HISTORY-BASED AUTO-SUGGEST
# ═══════════════════════════════════════════════════════════════════════


class SmartAutoSuggest(AutoSuggestFromHistory):
    """Enhanced auto-suggest with smart completions."""

    def __init__(self, phrases: Optional[Dict[str, List[str]]] = None):
        super().__init__()
        self.phrases = phrases or SMART_PHRASES

    def get_suggestion(self, buffer, document: Document) -> Optional[Suggestion]:
        """Get auto-suggestion."""
        text = document.text

        # First try history
        history_suggestion = super().get_suggestion(buffer, document)
        if history_suggestion:
            return history_suggestion

        # Then try smart phrases
        if len(text) >= 3:
            text_lower = text.lower()
            for trigger, completions in self.phrases.items():
                if text_lower.endswith(trigger):
                    # Suggest first completion
                    if completions:
                        suggestion = completions[0][len(trigger) :]
                        return Suggestion(suggestion)

        return None


# ═══════════════════════════════════════════════════════════════════════
# HCODE PROMPT STYLE
# ═══════════════════════════════════════════════════════════════════════


def get_hcode_style() -> Style:
    """Get the styled prompt theme."""
    return Style.from_dict(
        {
            # Completion menu
            "completion-menu": "bg:#1a1a2e #ffffff",
            "completion-menu.completion": "bg:#1a1a2e #00ffff",
            "completion-menu.completion.current": "bg:#00ffff #000000",
            "completion-menu.meta.completion": "bg:#1a1a2e #888888",
            "completion-menu.meta.completion.current": "bg:#00ffff #000000",
            # Scrollbar
            "scrollbar.background": "bg:#1a1a2e",
            "scrollbar.button": "bg:#00ffff",
            # Auto-suggestion (ghost text)
            "auto-suggestion": "#666666 italic",
            # Prompt
            "prompt": "#00ffff bold",
            "prompt.arg": "#ff00ff",
            # Input
            "": "#ffffff",  # Default text
            # Bottom toolbar
            "bottom-toolbar": "bg:#1a1a2e #888888",
            "bottom-toolbar.text": "#00ffff",
        }
    )


# ═══════════════════════════════════════════════════════════════════════
# HCODE PROMPT SESSION
# ═══════════════════════════════════════════════════════════════════════


class HCodePrompt:
    """
    Interactive prompt with smart completions for HCode.

    Features:
    - Slash command completion with descriptions
    - Smart phrase suggestions
    - File path completion
    - History-based auto-suggest
    - Keyboard shortcuts
    """

    def __init__(
        self,
        history_file: Optional[str] = None,
        enable_history: bool = True,
        enable_suggestions: bool = True,
        enable_file_completion: bool = True,
        custom_commands: Optional[List[Command]] = None,
    ):
        # Build completers
        completers = [
            CommandCompleter(custom_commands),
            SmartPhraseCompleter(),
        ]

        if enable_file_completion:
            completers.append(FilePathCompleter())

        # Merge completers
        self.completer = merge_completers(completers)

        # Setup history
        if enable_history and history_file:
            history_path = Path(history_file)
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self.history = FileHistory(str(history_path))
        else:
            self.history = InMemoryHistory()

        # Auto-suggest
        self.auto_suggest = SmartAutoSuggest() if enable_suggestions else None

        # Key bindings
        self.key_bindings = self._create_key_bindings()

        # Create session
        self.session: Optional[PromptSession] = None

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings."""
        kb = KeyBindings()

        @kb.add(Keys.Tab)
        def _(event):
            """Tab to complete."""
            buff = event.app.current_buffer
            if buff.complete_state:
                buff.complete_next()
            else:
                buff.start_completion(select_first=True)

        @kb.add(Keys.ControlSpace)
        def _(event):
            """Ctrl+Space to trigger completion."""
            buff = event.app.current_buffer
            buff.start_completion(select_first=False)

        @kb.add(Keys.Escape)
        def _(event):
            """Escape to cancel completion."""
            buff = event.app.current_buffer
            if buff.complete_state:
                buff.cancel_completion()

        return kb

    def _get_prompt_message(self, message_count: int = 0) -> FormattedText:
        """Get formatted prompt message."""
        return FormattedText(
            [
                ("class:prompt", f"You [{message_count}]: "),
            ]
        )

    def _get_bottom_toolbar(self) -> str:
        """Get bottom toolbar text."""
        return HTML(
            "<b>Tab</b>: Complete  |  "
            "<b>Ctrl+Space</b>: Show suggestions  |  "
            "<b>↑↓</b>: Navigate  |  "
            "<b>/help</b>: Commands"
        )

    def create_session(self) -> PromptSession:
        """Create and return a prompt session."""
        self.session = PromptSession(
            completer=self.completer,
            history=self.history,
            auto_suggest=self.auto_suggest,
            key_bindings=self.key_bindings,
            style=get_hcode_style(),
            complete_while_typing=True,
            complete_in_thread=True,
            bottom_toolbar=self._get_bottom_toolbar,
            mouse_support=True,
            wrap_lines=True,
        )
        return self.session

    def prompt(self, message: str = "You: ", message_count: int = 0, **kwargs) -> str:
        """
        Show prompt and get user input with completions.

        Args:
            message: Custom prompt message (ignored if using formatted)
            message_count: Message counter for prompt
            **kwargs: Additional arguments to pass to prompt

        Returns:
            User input string
        """
        if self.session is None:
            self.create_session()

        return self.session.prompt(self._get_prompt_message(message_count), **kwargs)


# ═══════════════════════════════════════════════════════════════════════
# QUICK ACCESS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def create_hcode_prompt(
    history_file: Optional[str] = None,
    enable_suggestions: bool = True,
) -> HCodePrompt:
    """Create an HCode prompt with default settings."""
    # Default history file in user's home
    if history_file is None:
        history_file = str(Path.home() / ".hcode" / "history.txt")

    return HCodePrompt(
        history_file=history_file,
        enable_history=True,
        enable_suggestions=enable_suggestions,
        enable_file_completion=True,
    )


def get_all_commands() -> List[Command]:
    """Get list of all available commands."""
    return BUILTIN_COMMANDS.copy()


def get_command_help(command_name: str) -> Optional[str]:
    """Get help text for a specific command."""
    for cmd in BUILTIN_COMMANDS:
        if cmd.name == command_name or command_name in cmd.aliases:
            help_text = f"{cmd.name}: {cmd.description}\n"
            if cmd.usage:
                help_text += f"Usage: {cmd.usage}\n"
            if cmd.aliases:
                help_text += f"Aliases: {', '.join(cmd.aliases)}\n"
            if cmd.examples:
                help_text += f"Examples:\n"
                for ex in cmd.examples:
                    help_text += f"  {ex}\n"
            return help_text
    return None
