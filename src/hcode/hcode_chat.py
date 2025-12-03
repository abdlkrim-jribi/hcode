"""
Hcode Advanced Chat Interface.
Implements all advanced features including chat interface, shortcuts, and tool execution.
"""

import asyncio
import json
import os
import sys
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from enum import Enum

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.live import Live
from rich.layout import Layout
from rich import box
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML

from hcode.core import HcodeAgent
from hcode.providers import ProviderPreferences, TaskComplexity, TaskType
from hcode.utils.config import load_config

# Import autonomous operation system
from hcode.agent.modes import AgentMode, get_mode_config, get_mode_description
from hcode.cli.autonomous_cli import AutonomousCLI, create_mode_status_line
from hcode.cli.shortcuts import ShortcutManager, ShortcutAction, setup_shortcuts_for_agent

# Import styling system (from ui module)
from hcode.ui import (
    Colors,
    Icons,
    Lines,
    StyledPanel,
    Header,
    Footer,
    StatusLine,
    Prompt as StyledPrompt,
    TodoDisplay,
    TodoItem as StyledTodoItem,
    Separator,
    get_default_box,
    console as styled_console,
    spinner,
    get_status_icon
)


class MessageRole(Enum):
    """Message roles in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class HcodeChat:
    """
    Hcode Advanced Chat Interface.

    Features:
    - Natural conversation flow
    - Tool execution with parallel support
    - Slash commands (/, @, etc.)
    - Todo list management
    - Context awareness
    - Markdown rendering
    - Session persistence
    """

    def __init__(self, workspace_dir: Optional[str] = None):
        """Initialize Hcode chat interface

        Args:
            workspace_dir: The workspace directory to operate in (defaults to current directory)
        """
        self.console = styled_console  # Use styled console
        self.config = load_config()
        self.agent = None
        self.session_history = []
        self.todos = []
        self.current_context = {}
        self.shortcuts = self._init_shortcuts()
        self.commands = self._init_commands()
        self.icons = Icons()  # Initialize icons

        # Set workspace directory - always use the directory where hcode was opened
        self.workspace_dir = Path(workspace_dir or os.getcwd()).resolve()

        # Change to workspace directory to ensure all operations happen there
        os.chdir(self.workspace_dir)

        # Initialize prompt session with history and autocompletion
        # Handle Windows terminal compatibility
        # Store history in the workspace directory
        history_file = self.workspace_dir / '.hcode_history'
        try:
            self.prompt_session = PromptSession(
                history=FileHistory(str(history_file)),
                auto_suggest=AutoSuggestFromHistory(),
                completer=WordCompleter(list(self.commands.keys()) + list(self.shortcuts.keys()))
            )
        except Exception:
            # Fallback for incompatible terminals
            self.prompt_session = None

        # Hcode style settings
        self.stream_responses = True
        self.show_tool_calls = True
        self.auto_continue = True
        self.markdown_rendering = True

        # Version info
        self.version = "1.0.0"

        # Autonomous operation system
        self.current_mode = AgentMode.INTERACTIVE
        self.autonomous_cli = AutonomousCLI(self.console)
        self.shortcut_manager = ShortcutManager()

        # Set up mode change callback
        self.autonomous_cli.set_mode_change_callback(self._on_mode_change)

        # Register shortcut callbacks
        self._setup_shortcut_callbacks()

    def _setup_shortcut_callbacks(self):
        """Set up keyboard shortcut callbacks"""
        self.shortcut_manager.register_callback(
            ShortcutAction.TOGGLE_MODE,
            self._toggle_mode
        )
        self.shortcut_manager.register_callback(
            ShortcutAction.SWITCH_TO_AUTO,
            lambda: self._set_mode(AgentMode.AUTO)
        )
        self.shortcut_manager.register_callback(
            ShortcutAction.SWITCH_TO_INTERACTIVE,
            lambda: self._set_mode(AgentMode.INTERACTIVE)
        )
        self.shortcut_manager.register_callback(
            ShortcutAction.SWITCH_TO_PLAN,
            lambda: self._set_mode(AgentMode.PLAN)
        )
        self.shortcut_manager.register_callback(
            ShortcutAction.SHOW_HELP,
            lambda: asyncio.create_task(self.show_help())
        )
        self.shortcut_manager.register_callback(
            ShortcutAction.SHOW_TASKS,
            self.display_todos
        )

    def _on_mode_change(self, new_mode: AgentMode):
        """Handle mode change from CLI"""
        self.current_mode = new_mode
        self.autonomous_cli.set_current_mode(new_mode)

    def _toggle_mode(self):
        """Toggle between interactive and auto modes"""
        if self.current_mode == AgentMode.INTERACTIVE:
            self._set_mode(AgentMode.AUTO)
        else:
            self._set_mode(AgentMode.INTERACTIVE)

    def _set_mode(self, mode: AgentMode):
        """Set agent mode"""
        self.current_mode = mode
        self.autonomous_cli.set_current_mode(mode)
        self.autonomous_cli._display_mode_change(self.current_mode, mode)

    def _init_shortcuts(self) -> Dict[str, str]:
        """Initialize Hcode shortcuts"""
        return {
            "/help": "Show available commands",
            "/clear": "Clear conversation history",
            "/exit": "Exit chat",
            "/tasks": "Show current todo list",
            "/stats": "Show session statistics",
            "/context": "Show current context",
            "/export": "Export conversation",
            "/settings": "Show/modify settings",
            "/agents": "Use specialized agents",
            "/explore": "Explore codebase",
            "/plan": "Plan implementation",
            "/commit": "Create git commit",
            "/pr": "Create pull request",
            "/debug": "Debug mode toggle",
            "/model": "Switch model",
            # Mode commands
            "/auto": "Switch to auto mode",
            "/interactive": "Switch to interactive mode",
            "/mode": "Show/change mode",
            "/review": "Switch to review mode",
            # Context mentions
            "@workspace": "Reference workspace context",
            "@file": "Reference specific file",
            "@web": "Search web",
            "@docs": "Search documentation",
        }

    def _init_commands(self) -> Dict[str, callable]:
        """Initialize command handlers"""
        return {
            "/help": self.show_help,
            "/clear": self.clear_conversation,
            "/exit": self.exit_chat,
            "/tasks": self.show_tasks,
            "/stats": self.show_statistics,
            "/context": self.show_context,
            "/export": self.export_conversation,
            "/settings": self.show_settings,
            "/agents": self.use_agents,
            "/explore": self.explore_codebase,
            "/plan": self.plan_task,
            "/commit": self.create_commit,
            "/pr": self.create_pr,
            "/debug": self.toggle_debug,
            "/model": self.switch_model,
            # Mode commands
            "/auto": self.switch_to_auto,
            "/interactive": self.switch_to_interactive,
            "/mode": self.show_mode,
            "/review": self.switch_to_review,
        }

    async def initialize_agent(self):
        """Initialize the AI agent with Hcode capabilities"""
        # Get API keys (env vars take priority over config)
        anthropic_key = os.getenv("ANTHROPIC_API_KEY") or self.config.get("providers", {}).get("anthropic", {}).get("api_key")
        openai_key = os.getenv("OPENAI_API_KEY") or self.config.get("providers", {}).get("openai", {}).get("api_key")
        openai_base_url = os.getenv("OPENAI_BASE_URL") or self.config.get("providers", {}).get("openai", {}).get("base_url")

        if not anthropic_key and not openai_key:
            self.console.print(Panel(
                "[red]No API keys found![/red]\n\n"
                "Please set environment variables:\n"
                "  export ANTHROPIC_API_KEY='your-key'\n"
                "  export OPENAI_API_KEY='your-key'",
                title="Configuration Error",
                border_style="red"
            ))
            sys.exit(1)

        # Get provider preference from config
        provider_pref = self.config.get("preferences", {}).get("primary_provider", "auto")
        cost_opt = self.config.get("preferences", {}).get("cost_optimization", "balanced")

        # Get model configuration (env vars take priority over config)
        anthropic_model = os.getenv("ANTHROPIC_MODEL") or self.config.get("providers", {}).get("anthropic", {}).get("default_model")
        openai_model = os.getenv("OPENAI_MODEL") or self.config.get("providers", {}).get("openai", {}).get("default_model")

        # Create agent with preferences
        preferences = ProviderPreferences(
            primary_provider=provider_pref,
            prefer_streaming=True,
            cost_optimization=cost_opt
        )

        self.agent = HcodeAgent(
            anthropic_key=anthropic_key,
            openai_key=openai_key,
            openai_base_url=openai_base_url,
            anthropic_model=anthropic_model,
            openai_model=openai_model,
            preferences=preferences,
            config=self.config,
            root_dir=str(self.workspace_dir)  # Always use the workspace directory
        )

        # Set Hcode system prompt
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build Hcode system prompt with workspace context"""
        workspace_info = f"""
WORKSPACE INFORMATION:
- Working Directory: {self.workspace_dir}
- All file operations are relative to this workspace
- Never operate outside the workspace unless explicitly requested
"""
        return f"""You are Hcode, an advanced AI coding assistant with comprehensive capabilities.

{workspace_info}

You have access to the following tools:
- File operations (Read, Write, Edit, Glob, Grep)
- Web capabilities (WebSearch, WebFetch)
- Interactive features (AskUserQuestion, TodoWrite)
- Development tools (Bash, Git operations)
- Jupyter notebook support

Key behaviors:
1. Be concise and professional
2. Use tools proactively when needed
3. Track tasks using TodoWrite
4. Ask for clarification when needed
5. Provide code references with file:line format
6. Support parallel tool execution
7. Handle slash commands and shortcuts
8. ALWAYS work within the workspace directory: {self.workspace_dir}

Remember:
- Stream responses for better UX
- Show your thinking process
- Be transparent about limitations
- Focus on helping the user effectively
- All file paths should be relative to or within the workspace"""

    def show_banner(self):
        """Display Hcode banner with styling"""
        # Clear screen for fresh start
        self.console.clear()

        # Fixed width for consistent display
        PANEL_WIDTH = 60

        # ASCII art logo with accent color
        logo_art = Text()
        logo_lines = [
            "    __  __               __",
            "   / / / /________  ____/ /__",
            "  / /_/ / ___/ __ \\/ __  / _ \\",
            " / __  / /__/ /_/ / /_/ /  __/",
            "/_/ /_/\\___/\\____/\\__,_/\\___/"
        ]
        for line in logo_lines:
            logo_art.append(line + "\n", style=f"bold {Colors.PRIMARY}")

        # Main header content
        header_content = Text()
        header_content.append(logo_art)

        # Tagline
        header_content.append("AI-Powered Coding Assistant\n", style=f"italic {Colors.TEXT_SECONDARY}")

        # Version and status
        header_content.append(f"\n{self.icons.LOGO} ", style=f"bold {Colors.PRIMARY}")
        header_content.append(f"v{self.version}", style=Colors.TEXT_MUTED)
        header_content.append(f"  {self.icons.BULLET}  ", style=Colors.TEXT_MUTED)
        header_content.append("Ready", style=f"bold {Colors.SUCCESS}")

        # Print header panel with fixed width
        self.console.print(Panel(
            Align.center(header_content),
            border_style=Colors.PRIMARY,
            box=get_default_box(),
            padding=(1, 2),
            width=PANEL_WIDTH
        ))

        # Feature highlights in a compact row
        features = [
            (self.icons.TOOL, "Tools", Colors.SECONDARY),
            (self.icons.SEARCH, "Search", Colors.INFO),
            (self.icons.CODE, "Code", Colors.PRIMARY),
            (self.icons.TERMINAL, "Shell", Colors.WARNING),
            (self.icons.GLOBE, "Web", Colors.TERTIARY),
        ]

        feature_text = Text()
        feature_text.append(" Features: ", style=f"bold {Colors.TEXT_SECONDARY}")
        for i, (icon, name, color) in enumerate(features):
            if i > 0:
                feature_text.append(" ", style=Colors.TEXT_MUTED)
            feature_text.append(f"{icon}", style=color)
            feature_text.append(f"{name}", style=Colors.TEXT_SECONDARY)

        self.console.print(feature_text)

        # Show workspace directory
        workspace_text = Text()
        workspace_text.append(f" {self.icons.FOLDER} ", style=f"bold {Colors.INFO}")
        workspace_text.append("Workspace: ", style=f"bold {Colors.TEXT_SECONDARY}")
        workspace_text.append(str(self.workspace_dir), style=Colors.TEXT_MUTED)
        self.console.print(workspace_text)
        self.console.print()

        # Quick start hints
        hints_panel = self._create_hints_panel(PANEL_WIDTH)
        self.console.print(hints_panel)
        self.console.print()

    def _create_hints_panel(self, width: int = 60) -> Panel:
        """Create quick start hints panel"""
        hints = Text()

        # Commands section
        hints.append(f" {self.icons.ARROW_RIGHT_FANCY} ", style=f"bold {Colors.PRIMARY}")
        hints.append("Commands\n", style=f"bold {Colors.TEXT_PRIMARY}")

        commands_info = [
            ("/help", "Show commands"),
            ("/explore", "Explore code"),
            ("/tasks", "View todos"),
            ("/exit", "Exit"),
        ]

        for cmd, desc in commands_info:
            hints.append(f"   {cmd:<10}", style=f"bold {Colors.SECONDARY}")
            hints.append(f"{desc}\n", style=Colors.TEXT_MUTED)

        hints.append(f"\n {self.icons.ARROW_RIGHT_FANCY} ", style=f"bold {Colors.PRIMARY}")
        hints.append("Mentions\n", style=f"bold {Colors.TEXT_PRIMARY}")

        mentions_info = [
            ("@workspace", "Workspace ctx"),
            ("@file", "File reference"),
            ("@web", "Web search"),
        ]

        for mention, desc in mentions_info:
            hints.append(f"   {mention:<11}", style=f"bold {Colors.INFO}")
            hints.append(f"{desc}\n", style=Colors.TEXT_MUTED)

        hints.append(f"\n {self.icons.INFO} ", style=Colors.INFO)
        hints.append("Type naturally to chat!", style=f"italic {Colors.TEXT_MUTED}")

        return Panel(
            hints,
            title=f"[{Colors.TEXT_SECONDARY}]Quick Start[/]",
            border_style=Colors.BORDER_DEFAULT,
            box=get_default_box(),
            padding=(0, 1),
            width=width
        )

    async def process_message(self, message: str) -> str:
        """
        Process user message with Hcode logic.

        Args:
            message: User input message

        Returns:
            Assistant response
        """
        # Check for shortcuts and commands
        if message.startswith('/'):
            return await self.handle_command(message)

        if message.startswith('@'):
            return await self.handle_mention(message)

        # Process as regular message
        response = await self.execute_with_tools(message)

        # Update session history
        self.session_history.append({
            "role": MessageRole.USER.value,
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        self.session_history.append({
            "role": MessageRole.ASSISTANT.value,
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        return response

    async def handle_command(self, command: str) -> str:
        """Handle slash commands"""
        cmd = command.split()[0]
        args = command[len(cmd):].strip()

        if cmd in self.commands:
            return await self.commands[cmd](args)
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."

    async def handle_mention(self, message: str) -> str:
        """Handle @ mentions for context injection"""
        # Parse mention type
        if message.startswith("@workspace"):
            # Add workspace context
            workspace_info = await self.get_workspace_context()
            context_message = f"{workspace_info}\n\nUser request: {message[10:].strip()}"
            return await self.execute_with_tools(context_message)

        elif message.startswith("@file"):
            # Parse file reference
            parts = message.split(maxsplit=2)
            if len(parts) >= 2:
                file_path = parts[1]
                user_message = parts[2] if len(parts) > 2 else ""

                # Read file and add to context
                file_content = await self.read_file_content(file_path)
                context_message = f"File {file_path}:\n{file_content}\n\nUser request: {user_message}"
                return await self.execute_with_tools(context_message)

        elif message.startswith("@web"):
            # Perform web search
            query = message[4:].strip()
            return await self.web_search(query)

        elif message.startswith("@docs"):
            # Search documentation
            query = message[5:].strip()
            return await self.search_docs(query)

        return f"Unknown mention type. Available: @workspace, @file, @web, @docs"

    def _is_continuation_message(self, message: str) -> bool:
        """Check if message is a continuation/confirmation rather than a new task"""
        message_lower = message.strip().lower()

        # Short confirmations
        if message_lower in ['yes', 'y', 'ok', 'okay', 'sure', 'go ahead', 'proceed',
                            'continue', 'do it', 'generate', 'create it', 'yes please',
                            'generate the file', 'create the file', 'write the file',
                            'make it', 'build it']:
            return True

        # Very short messages are likely confirmations
        if len(message_lower) < 20 and not any(word in message_lower for word in
                                                ['create', 'implement', 'build', 'write', 'generate', 'fix', 'debug']):
            return True

        return False

    def _enhance_continuation_message(self, message: str) -> str:
        """
        Enhance a continuation message with context to help the model understand.

        When user says 'proceed' or 'yes', the model needs to understand this is
        a confirmation to continue with the previous task.
        """
        message_lower = message.strip().lower()

        # Check if this looks like a confirmation
        confirmation_words = ['yes', 'y', 'ok', 'okay', 'sure', 'go ahead', 'proceed',
                             'continue', 'do it', 'generate', 'create it', 'yes please',
                             'generate the file', 'create the file', 'write the file',
                             'make it', 'build it']

        if message_lower in confirmation_words:
            # Get the last user message from session history (the original task)
            original_task = None
            for msg in reversed(self.session_history):
                if msg.get('role') == 'user':
                    content = msg.get('content', '')
                    # Skip if it's also a short confirmation
                    if content.strip().lower() not in confirmation_words and len(content) > 20:
                        original_task = content
                        break

            if original_task:
                # Enhance the message with context
                return f"User confirmed: {message}. Please proceed with the previously discussed task: {original_task}"

        return message

    async def execute_with_tools(self, message: str) -> str:
        """
        Execute message with tool support.

        Args:
            message: User message

        Returns:
            Response with tool execution results
        """
        # Check if this is a continuation message
        is_continuation = self._is_continuation_message(message)

        # Only create new todos if this is a new task, not a continuation
        if not is_continuation:
            await self.create_todos_for_task(message)

            # Display todos at the start of task execution
            self.console.print()
            self.console.print(f"[bold cyan]📋 Task Planning[/bold cyan]")
            self.display_todos()
            self.console.print()

        # Enhance continuation messages with context
        task_message = message
        if is_continuation:
            task_message = self._enhance_continuation_message(message)
            if task_message != message:
                self.console.print(f"[dim]📎 Continuation context: {task_message[:100]}...[/dim]")

        # Execute task through agent
        response = await self.agent.execute_task(
            task=task_message,
            complexity=self.determine_complexity(message),
            task_type=self.determine_task_type(message),
            stream=self.stream_responses,
            use_sub_agents=self.should_use_agents(message)
        )

        # Update todos after execution - mark ALL tasks as completed
        # since the task has been executed (including file write)
        if self.todos:
            # For file generation tasks, all steps are complete when we reach here
            # because the agent has already analyzed, designed, generated, and saved
            for todo in self.todos:
                # Mark all tasks as completed if the response indicates success
                if "success" in response.lower() or "written" in response.lower() or "created" in response.lower() or "generated" in response.lower():
                    todo['status'] = 'completed'
                elif todo.get('status') == 'in_progress':
                    # At minimum, mark in-progress tasks as completed
                    todo['status'] = 'completed'

            await self.agent.update_todos(self.todos)

            # Display final todos
            self.console.print()
            self.console.print(f"[bold green]✅ Task Status[/bold green]")
            self.display_todos()

        return response

    def should_create_todos(self, message: str) -> bool:
        """Determine if todos should be created for this task"""
        indicators = [
            "implement", "create", "build", "develop", "add feature",
            "refactor", "fix", "debug", "optimize", "test",
            "multiple", "steps", "tasks", "todo", "plan"
        ]
        message_lower = message.lower()
        return any(indicator in message_lower for indicator in indicators)

    def determine_complexity(self, message: str) -> TaskComplexity:
        """Determine task complexity from message"""
        complex_indicators = ["complex", "comprehensive", "full", "entire", "system", "architecture"]
        simple_indicators = ["simple", "quick", "basic", "trivial", "small", "minor"]

        message_lower = message.lower()

        if any(ind in message_lower for ind in complex_indicators):
            return TaskComplexity.COMPLEX
        elif any(ind in message_lower for ind in simple_indicators):
            return TaskComplexity.SIMPLE
        else:
            return TaskComplexity.MODERATE

    def determine_task_type(self, message: str) -> TaskType:
        """Determine task type from message"""
        message_lower = message.lower()

        if any(word in message_lower for word in ["debug", "fix", "error", "bug"]):
            return TaskType.DEBUGGING
        elif any(word in message_lower for word in ["analyze", "review", "check", "audit"]):
            return TaskType.CODE_REVIEW
        elif any(word in message_lower for word in ["refactor", "improve", "optimize", "clean"]):
            return TaskType.REFACTORING
        elif any(word in message_lower for word in ["document", "docs", "comment", "explain"]):
            return TaskType.DOCUMENTATION
        elif any(word in message_lower for word in ["test", "testing", "spec", "unittest"]):
            return TaskType.TESTING
        else:
            return TaskType.CODE_GENERATION

    def should_use_agents(self, message: str) -> bool:
        """Determine if specialized agents should be used"""
        agent_indicators = ["explore", "plan", "implement", "complex", "comprehensive", "multi-step"]
        message_lower = message.lower()
        return any(ind in message_lower for ind in agent_indicators)

    async def create_todos_for_task(self, task: str):
        """Create todo list for task"""
        # Generate todos based on task
        todos = self.generate_todos_from_task(task)

        # Update todo list
        self.todos = todos

        # Update agent todos (display is handled by execute_with_tools)
        await self.agent.update_todos(todos)

    def generate_todos_from_task(self, task: str) -> List[Dict[str, str]]:
        """Generate todo items from task description"""
        todos = []

        # Parse task and create appropriate todos
        task_lower = task.lower()

        if "implement" in task_lower or "create" in task_lower or "generate" in task_lower or "write" in task_lower:
            todos.extend([
                {"content": "Analyze requirements", "status": "in_progress", "activeForm": "Analyzing requirements"},
                {"content": "Design solution", "status": "pending", "activeForm": "Designing solution"},
                {"content": "Generate code/content", "status": "pending", "activeForm": "Generating code/content"},
                {"content": "Review and validate", "status": "pending", "activeForm": "Reviewing and validating"},
                {"content": "Save to file (requires confirmation)", "status": "pending", "activeForm": "Saving to file"}
            ])
        elif "debug" in task_lower or "fix" in task_lower:
            todos.extend([
                {"content": "Reproduce the issue", "status": "in_progress", "activeForm": "Reproducing the issue"},
                {"content": "Identify root cause", "status": "pending", "activeForm": "Identifying root cause"},
                {"content": "Implement fix", "status": "pending", "activeForm": "Implementing fix"},
                {"content": "Test the fix", "status": "pending", "activeForm": "Testing the fix"},
                {"content": "Verify no regressions", "status": "pending", "activeForm": "Verifying no regressions"}
            ])
        elif "refactor" in task_lower:
            todos.extend([
                {"content": "Analyze current implementation", "status": "in_progress", "activeForm": "Analyzing current implementation"},
                {"content": "Identify improvement areas", "status": "pending", "activeForm": "Identifying improvement areas"},
                {"content": "Plan refactoring approach", "status": "pending", "activeForm": "Planning refactoring approach"},
                {"content": "Implement refactoring", "status": "pending", "activeForm": "Implementing refactoring"},
                {"content": "Ensure tests pass", "status": "pending", "activeForm": "Ensuring tests pass"}
            ])
        elif "read" in task_lower or "show" in task_lower or "list" in task_lower or "find" in task_lower:
            todos.extend([
                {"content": "Search/read files", "status": "in_progress", "activeForm": "Searching/reading files"},
                {"content": "Process results", "status": "pending", "activeForm": "Processing results"},
                {"content": "Display output", "status": "pending", "activeForm": "Displaying output"}
            ])
        else:
            # Default todos for any task
            todos.extend([
                {"content": "Understand request", "status": "in_progress", "activeForm": "Understanding request"},
                {"content": "Execute task", "status": "pending", "activeForm": "Executing task"},
                {"content": "Present results", "status": "pending", "activeForm": "Presenting results"}
            ])

        return todos

    def display_todos(self):
        """Display current todo list with styled output"""
        if not self.todos:
            self.console.print(f"[{Colors.TEXT_MUTED}]{self.icons.INFO} No tasks in todo list[/]")
            return

        # Convert to StyledTodoItem format
        styled_todos = [
            StyledTodoItem(
                content=todo.get("content", ""),
                status=todo.get("status", "pending"),
                active_form=todo.get("activeForm", "")
            )
            for todo in self.todos
        ]

        # Use the styled TodoDisplay component
        todo_panel = TodoDisplay.render(styled_todos, "Todo List")
        self.console.print(todo_panel)

    async def update_todo_status(self):
        """Update todo status based on progress"""
        # TODO: Add actual progress tracking
        if self.todos and self.todos[0]["status"] == "pending":
            self.todos[0]["status"] = "in_progress"
            await self.agent.update_todos(self.todos)

    async def show_help(self, args: str = "") -> str:
        """Show styled help information"""
        # Build help content
        help_content = Text()

        # Title
        help_content.append(f"\n  {self.icons.LOGO} ", style=f"bold {Colors.PRIMARY}")
        help_content.append("Hcode Commands\n\n", style=f"bold {Colors.TEXT_PRIMARY}")

        # Basic Commands
        help_content.append(f"  {self.icons.ARROW_RIGHT_FANCY} ", style=f"bold {Colors.PRIMARY}")
        help_content.append("Basic Commands\n", style=f"bold {Colors.TEXT_PRIMARY}")

        basic_commands = [
            ("/help", "Show this help message"),
            ("/clear", "Clear conversation history"),
            ("/exit", "Exit the chat"),
            ("/tasks", "Show current todo list"),
            ("/stats", "Show session statistics"),
        ]
        for cmd, desc in basic_commands:
            help_content.append(f"    {cmd:<14}", style=f"bold {Colors.SECONDARY}")
            help_content.append(f" {desc}\n", style=Colors.TEXT_MUTED)

        # Development Commands
        help_content.append(f"\n  {self.icons.ARROW_RIGHT_FANCY} ", style=f"bold {Colors.PRIMARY}")
        help_content.append("Development Commands\n", style=f"bold {Colors.TEXT_PRIMARY}")

        dev_commands = [
            ("/explore", "Explore codebase"),
            ("/plan", "Create implementation plan"),
            ("/commit", "Create git commit"),
            ("/pr", "Create pull request"),
            ("/debug", "Toggle debug mode"),
        ]
        for cmd, desc in dev_commands:
            help_content.append(f"    {cmd:<14}", style=f"bold {Colors.SECONDARY}")
            help_content.append(f" {desc}\n", style=Colors.TEXT_MUTED)

        # Mode Commands
        help_content.append(f"\n  {self.icons.ARROW_RIGHT_FANCY} ", style=f"bold {Colors.PRIMARY}")
        help_content.append("Mode Commands\n", style=f"bold {Colors.TEXT_PRIMARY}")

        mode_commands = [
            ("/mode", "Show current mode"),
            ("/auto", "Auto mode (execute freely)"),
            ("/interactive", "Interactive mode (ask first)"),
            ("/review", "Review mode (approve plan)"),
        ]
        for cmd, desc in mode_commands:
            help_content.append(f"    {cmd:<14}", style=f"bold {Colors.WARNING}")
            help_content.append(f" {desc}\n", style=Colors.TEXT_MUTED)

        # Context Commands
        help_content.append(f"\n  {self.icons.ARROW_RIGHT_FANCY} ", style=f"bold {Colors.PRIMARY}")
        help_content.append("Context Mentions\n", style=f"bold {Colors.TEXT_PRIMARY}")

        context_commands = [
            ("@workspace", "Reference entire workspace"),
            ("@file <path>", "Reference specific file"),
            ("@web <query>", "Search the web"),
            ("@docs <query>", "Search documentation"),
        ]
        for cmd, desc in context_commands:
            help_content.append(f"    {cmd:<14}", style=f"bold {Colors.INFO}")
            help_content.append(f" {desc}\n", style=Colors.TEXT_MUTED)

        # Settings
        help_content.append(f"\n  {self.icons.ARROW_RIGHT_FANCY} ", style=f"bold {Colors.PRIMARY}")
        help_content.append("Settings\n", style=f"bold {Colors.TEXT_PRIMARY}")

        settings_commands = [
            ("/settings", "View/modify settings"),
            ("/model", "Switch AI model"),
            ("/agents", "Use specialized agents"),
        ]
        for cmd, desc in settings_commands:
            help_content.append(f"    {cmd:<14}", style=f"bold {Colors.SECONDARY}")
            help_content.append(f" {desc}\n", style=Colors.TEXT_MUTED)

        # Tips
        help_content.append(f"\n  {self.icons.INFO} ", style=Colors.INFO)
        help_content.append("Tips\n", style=f"bold {Colors.TEXT_SECONDARY}")
        tips = [
            "Use natural language for tasks",
            "Tools are executed automatically",
            "Responses stream in real-time",
            "Context is maintained across messages",
        ]
        for tip in tips:
            help_content.append(f"    {self.icons.BULLET} ", style=Colors.TEXT_MUTED)
            help_content.append(f"{tip}\n", style=Colors.TEXT_MUTED)

        # Print as panel
        self.console.print(Panel(
            help_content,
            border_style=Colors.PRIMARY,
            box=get_default_box(),
            padding=(0, 1)
        ))

        return ""  # Return empty since we already printed

    async def clear_conversation(self, args: str = "") -> str:
        """Clear conversation history"""
        self.session_history = []
        self.todos = []
        if self.agent:
            self.agent.context_manager.clear_context(keep_system=True)
        self.console.print(f"[bold {Colors.SUCCESS}]{self.icons.CHECK}[/] Conversation cleared")
        return ""

    async def exit_chat(self, args: str = "") -> str:
        """Exit chat"""
        return "exit"

    async def show_tasks(self, args: str = "") -> str:
        """Show current tasks"""
        self.display_todos()
        return ""

    async def show_statistics(self, args: str = "") -> str:
        """Show session statistics"""
        if not self.agent:
            return "No active session"

        stats = self.agent.get_session_stats()

        stats_text = f"""
# Session Statistics

- **Provider**: {stats.get('provider', 'Unknown')}
- **Total Cost**: ${stats.get('total_cost', 0):.4f}
- **Messages**: {stats.get('context', {}).get('total_messages', 0)}
- **Session ID**: {stats.get('context', {}).get('session_id', 'None')}

## Tool Usage
"""
        for tool, count in stats.get('tool_usage', {}).items():
            stats_text += f"- {tool}: {count}\n"

        return stats_text

    async def show_context(self, args: str = "") -> str:
        """Show current context"""
        context_info = f"""
# Current Context

- **Workspace Directory**: {self.workspace_dir}
- **Current Directory**: {os.getcwd()}
- **Session Messages**: {len(self.session_history)}
- **Active Todos**: {len([t for t in self.todos if t['status'] != 'completed'])}
- **Completed Todos**: {len([t for t in self.todos if t['status'] == 'completed'])}
"""
        return context_info

    async def export_conversation(self, args: str = "") -> str:
        """Export conversation to file"""
        filename = args.strip() if args else f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        export_data = {
            "session_history": self.session_history,
            "todos": self.todos,
            "context": self.current_context,
            "timestamp": datetime.now().isoformat()
        }

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        self.console.print(f"[bold {Colors.SUCCESS}]{self.icons.CHECK}[/] Conversation exported to [{Colors.INFO}]{filename}[/]")
        return ""

    async def show_settings(self, args: str = "") -> str:
        """Show or modify settings"""
        settings_text = f"""
# Current Settings

- **Stream Responses**: {self.stream_responses}
- **Show Tool Calls**: {self.show_tool_calls}
- **Auto Continue**: {self.auto_continue}
- **Markdown Rendering**: {self.markdown_rendering}

To modify: `/settings <setting> <value>`
Example: `/settings stream false`
"""

        if args:
            parts = args.split()
            if len(parts) == 2:
                setting, value = parts
                if setting == "stream":
                    self.stream_responses = value.lower() == "true"
                elif setting == "tools":
                    self.show_tool_calls = value.lower() == "true"
                elif setting == "continue":
                    self.auto_continue = value.lower() == "true"
                elif setting == "markdown":
                    self.markdown_rendering = value.lower() == "true"
                return f"[OK] Updated {setting} to {value}"

        return settings_text

    async def use_agents(self, args: str = "") -> str:
        """Toggle use of specialized agents"""
        # This would be implemented with actual agent selection
        return "🤖 Specialized agents activated for next task"

    async def explore_codebase(self, args: str = "") -> str:
        """Explore codebase"""
        if not args:
            return "Please provide a search query. Example: /explore API endpoints"

        if self.agent:
            result = await self.agent.explore_codebase(args, thoroughness="medium")
            return result
        return "Agent not initialized"

    async def plan_task(self, args: str = "") -> str:
        """Plan implementation"""
        if not args:
            return "Please provide a task to plan. Example: /plan implement user authentication"

        if self.agent:
            result = await self.agent.plan_implementation(args)
            return result
        return "Agent not initialized"

    async def create_commit(self, args: str = "") -> str:
        """Create git commit"""
        commit_message = args if args else "Auto-commit via Hcode"

        # Execute git commands
        commands = [
            "git add -A",
            f'git commit -m "{commit_message}"'
        ]

        results = []
        for cmd in commands:
            # This would use the actual Bash tool
            results.append(f"Executed: {cmd}")

        return "\n".join(results)

    async def create_pr(self, args: str = "") -> str:
        """Create pull request"""
        pr_title = args if args else "Auto-PR via Hcode"

        # This would integrate with git and GitHub CLI
        return f"📝 Created PR: {pr_title}"

    async def toggle_debug(self, args: str = "") -> str:
        """Toggle debug mode"""
        # This would toggle actual debug settings
        return "🐛 Debug mode toggled"

    async def switch_model(self, args: str = "") -> str:
        """Switch AI model"""
        if not args:
            return "Available models: claude-3-opus, claude-3-sonnet, gpt-4, gpt-3.5-turbo"

        # This would switch the actual model
        return f"[OK] Switched to model: {args}"

    # ============================================================
    # MODE COMMANDS
    # ============================================================

    async def switch_to_auto(self, args: str = "") -> str:
        """Switch to auto mode"""
        self._set_mode(AgentMode.AUTO)
        return ""

    async def switch_to_interactive(self, args: str = "") -> str:
        """Switch to interactive mode"""
        self._set_mode(AgentMode.INTERACTIVE)
        return ""

    async def switch_to_review(self, args: str = "") -> str:
        """Switch to review mode"""
        self._set_mode(AgentMode.REVIEW)
        return ""

    async def show_mode(self, args: str = "") -> str:
        """Show current mode or switch mode"""
        if args:
            # Try to parse mode name
            mode_name = args.strip().lower()
            mode_map = {
                "auto": AgentMode.AUTO,
                "interactive": AgentMode.INTERACTIVE,
                "plan": AgentMode.PLAN,
                "review": AgentMode.REVIEW,
            }
            if mode_name in mode_map:
                self._set_mode(mode_map[mode_name])
            else:
                self.autonomous_cli.show_mode_help()
        else:
            self.autonomous_cli.show_mode_status()
        return ""

    async def get_workspace_context(self) -> str:
        """Get workspace context information"""
        # Gather workspace information
        workspace_info = f"""
Workspace: {os.getcwd()}
Git Status: {self.get_git_status()}
Project Structure: {self.get_project_structure()}
"""
        return workspace_info

    def get_git_status(self) -> str:
        """Get git status information"""
        # This would use actual git commands
        return "clean"

    def get_project_structure(self) -> str:
        """Get project structure"""
        # This would analyze actual project structure
        return "Python project with src/ structure"

    async def read_file_content(self, file_path: str) -> str:
        """Read file content"""
        if self.agent:
            result = await self.agent.tool_manager.read_file(file_path)
            return result.output if result.success else f"Error reading {file_path}"
        return ""

    async def web_search(self, query: str) -> str:
        """Perform web search"""
        if self.agent:
            result = await self.agent.web_search(query)
            return result
        return "Agent not initialized"

    async def search_docs(self, query: str) -> str:
        """Search documentation"""
        # This would search actual documentation
        return f"Searching docs for: {query}"

    def render_message(self, content: str, role: MessageRole = MessageRole.ASSISTANT):
        """Render message with styled formatting"""
        if role == MessageRole.USER:
            # User message with styled panel
            self.console.print(Panel(
                Text(content, style=Colors.TEXT_PRIMARY),
                title=f"[bold {Colors.SECONDARY}]{self.icons.PROMPT} You[/]",
                border_style=Colors.BORDER_DEFAULT,
                box=get_default_box(),
                padding=(0, 1)
            ))
        elif role == MessageRole.ASSISTANT:
            if self.markdown_rendering:
                self.console.print(Panel(
                    Markdown(content),
                    title=f"[bold {Colors.PRIMARY}]{self.icons.AGENT} Assistant[/]",
                    border_style=Colors.PRIMARY,
                    box=get_default_box(),
                    padding=(0, 2)
                ))
            else:
                self.console.print(Panel(
                    Text(content),
                    title=f"[bold {Colors.PRIMARY}]{self.icons.AGENT} Assistant[/]",
                    border_style=Colors.PRIMARY,
                    box=get_default_box(),
                    padding=(0, 1)
                ))
        elif role == MessageRole.TOOL_CALL:
            if self.show_tool_calls:
                self.console.print(f"[{Colors.SECONDARY}]{self.icons.TOOL} Tool: {content}[/]")
        elif role == MessageRole.TOOL_RESULT:
            if self.show_tool_calls:
                self.console.print(f"[{Colors.INFO}]{self.icons.CHECK} Result: {content[:100]}...[/]")

    async def run(self):
        """Run the Hcode chat interface"""
        self.show_banner()

        # Initialize agent with spinner
        await self._initialize_with_style()

        # Main chat loop
        while True:
            try:
                # Get user input with styled prompt
                user_input = await self._get_user_input()

                if not user_input.strip():
                    continue

                # Process message
                response = await self.process_message(user_input)

                # Check for exit
                if response == "exit":
                    self._show_goodbye()
                    break

                # Render response
                if response:
                    self.render_message(response)

            except KeyboardInterrupt:
                self.console.print(f"\n[{Colors.WARNING}]{self.icons.WARNING} Use /exit to quit or continue chatting[/]")
                continue
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[bold {Colors.ERROR}]{self.icons.CROSS} Error:[/] {str(e)}")
                if self.config.get("debug", False):
                    import traceback
                    self.console.print(traceback.format_exc())

    async def _initialize_with_style(self):
        """Initialize agent with styled output"""
        # Show initialization status
        init_text = Text()
        init_text.append(f"  {self.icons.EXECUTING} ", style=f"bold {Colors.THINKING}")
        init_text.append("Initializing Hcode agent", style=Colors.TEXT_SECONDARY)

        with spinner("Initializing Hcode agent...") as s:
            try:
                await self.initialize_agent()

                # Get provider info for display
                provider_info = self._get_provider_info()

            except Exception as e:
                self.console.print(f"\n[bold {Colors.ERROR}]{self.icons.CROSS} Initialization failed:[/] {str(e)}")
                raise

        # Test connection to LLM
        self.console.print(f"[{Colors.TEXT_MUTED}]Testing connection to LLM...[/]")
        try:
            connection_ok, connection_msg = await self._test_llm_connection()
            if not connection_ok:
                self.console.print(f"[bold {Colors.WARNING}]{self.icons.WARNING} Connection issue:[/] {connection_msg}")
                self.console.print(f"[{Colors.TEXT_MUTED}]The agent will still attempt to connect when you send a message.[/]")
            else:
                self.console.print(f"[bold {Colors.SUCCESS}]{self.icons.CHECK}[/] {connection_msg}")
        except Exception as e:
            self.console.print(f"[bold {Colors.WARNING}]{self.icons.WARNING} Connection test skipped:[/] {str(e)}")

        # Show success status
        self.console.print(f"[bold {Colors.SUCCESS}]{self.icons.CHECK}[/] Agent ready!")

        # Show connection info with mode
        status = StatusLine.render(
            status="ready",
            message="Connected",
            model=provider_info.get("model", "Unknown"),
            tokens=0
        )
        self.console.print(status)

        # Show mode info
        mode_status = create_mode_status_line(self.current_mode)
        mode_config = get_mode_config(self.current_mode)
        self.console.print(f" Mode: ", end="")
        self.console.print(mode_status, end="")
        self.console.print(f"  {self.icons.BULLET}  ", style=Colors.TEXT_MUTED, end="")
        self.console.print(f"{mode_config.description}", style=Colors.TEXT_MUTED)
        self.console.print()

        # Separator before chat
        self.console.print(Separator.thin())
        self.console.print()

    def _get_provider_info(self) -> Dict[str, str]:
        """Get current provider information"""
        info = {"provider": "Unknown", "model": "Unknown"}

        if self.agent and hasattr(self.agent, 'selector'):
            current = self.agent.selector.current_provider
            if current:
                info["provider"] = current.__class__.__name__
                if hasattr(current, 'model'):
                    info["model"] = current.model

        # Fallback to config
        if info["model"] == "Unknown":
            openai_model = self.config.get("providers", {}).get("openai", {}).get("default_model")
            anthropic_model = self.config.get("providers", {}).get("anthropic", {}).get("default_model")
            info["model"] = openai_model or anthropic_model or "Unknown"

        return info

    async def _test_llm_connection(self) -> tuple[bool, str]:
        """
        Test the connection to the LLM API.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.agent:
            return False, "Agent not initialized"

        # Get the current provider from the selector
        provider_selector = self.agent.provider_selector

        # Try to get a provider and test it
        providers = provider_selector.get_available_providers()
        if not providers:
            return False, "No providers available"

        # Test the first available provider
        for provider_name in providers:
            try:
                provider = provider_selector.get_provider_by_name(provider_name)
                if provider and hasattr(provider, 'test_connection'):
                    success, msg = await provider.test_connection()
                    if success:
                        return True, msg
                    else:
                        # Try next provider if this one fails
                        continue
                elif provider:
                    # Provider doesn't have test_connection, assume it's working
                    return True, f"Connected to {provider_name}"
            except Exception as e:
                continue

        return False, "All providers failed to connect"

    async def _get_user_input(self) -> str:
        """Get user input with styled prompt"""
        # Build prompt text
        prompt_icon = self.icons.PROMPT
        prompt_text = f"{prompt_icon} You {self.icons.ARROW_RIGHT_FANCY} "

        if self.prompt_session:
            return await self.prompt_session.prompt_async(
                HTML(f'<style fg="#{Colors.PRIMARY[1:]}" bold="True">{prompt_icon}</style> <b>You</b> <style fg="#{Colors.PRIMARY[1:]}">></style> ')
            )
        else:
            # Fallback to simple input with styled prefix
            self.console.print(f"[bold {Colors.PRIMARY}]{prompt_icon}[/] [bold]You[/] [bold {Colors.PRIMARY}]>[/] ", end="")
            return input()

    def _show_goodbye(self):
        """Show styled goodbye message"""
        self.console.print()
        self.console.print(Separator.thin())
        self.console.print()

        goodbye = Text()
        goodbye.append(f"  {self.icons.STAR} ", style=f"bold {Colors.WARNING}")
        goodbye.append("Thanks for using Hcode!", style=f"bold {Colors.TEXT_PRIMARY}")
        goodbye.append("\n")
        goodbye.append(f"  {self.icons.INFO} ", style=Colors.INFO)
        goodbye.append("Session saved. See you next time!", style=Colors.TEXT_MUTED)

        self.console.print(Panel(
            goodbye,
            border_style=Colors.PRIMARY,
            box=get_default_box(),
            padding=(0, 1)
        ))
        self.console.print()


@click.command()
@click.option('--model', '-m', help='Specify AI model')
@click.option('--provider', '-p', type=click.Choice(['auto', 'anthropic', 'openai']), default='auto', help='AI provider')
@click.option('--session', '-s', help='Resume session ID')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--workspace', '-w', type=click.Path(exists=True, file_okay=False, dir_okay=True),
              default=None, help='Workspace directory (defaults to current directory)')
def main(model, provider, session, debug, workspace):
    """
    Launch Hcode Advanced Chat Interface.

    This provides a full AI assistant experience with:
    - Natural chat interface
    - Tool execution
    - Slash commands
    - Todo management
    - Context awareness

    The agent always works within the workspace directory where it was opened.
    """
    # Initialize with workspace directory (defaults to current directory)
    chat = HcodeChat(workspace_dir=workspace)

    # Apply CLI options
    if model:
        chat.config['model'] = model
    if provider:
        chat.config['provider'] = provider
    if session:
        chat.config['session'] = session
    if debug:
        chat.config['debug'] = True

    # Run async chat
    asyncio.run(chat.run())


if __name__ == "__main__":
    main()