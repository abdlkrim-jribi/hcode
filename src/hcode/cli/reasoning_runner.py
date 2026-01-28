"""
Integrated Reasoning Runner for HCode CLI.

Combines enhanced reasoning with todo tracking and persistent display.
Provides a Claude Code-like experience with visible progress tracking.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from hcode.core.execution import (
    EnhancedThinkingMode,
    ThinkingResult,
    create_enhanced_thinking_manager,
)
from hcode.core.execution import FeedbackEntry
from hcode.core.todo import TodoManager, TodoItem
from hcode.ui.theme import get_palette, get_console
from hcode.ui.todo_display import (
    PersistentTodoDisplay,
    render_todo_panel,
    render_todo_status_line,
    TodoStatusBar,
)
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclass
class ReasoningRunnerConfig:
    """Configuration for the reasoning runner"""

    show_thinking: bool = True
    show_todo_panel: bool = True
    compact_todo: bool = False
    max_visible_todos: int = 5
    auto_update_todos: bool = True
    reasoning_mode: EnhancedThinkingMode = EnhancedThinkingMode.ADAPTIVE


class ReasoningRunner:
    """
    Integrated runner that combines reasoning, execution, and todo tracking.

    Provides a unified interface for:
    - Running tasks with enhanced reasoning
    - Automatically updating todo lists from reasoning
    - Displaying progress in real-time
    - Collecting execution feedback
    """

    def __init__(
        self,
        llm_client: Any = None,
        console: Optional[Console] = None,
            config: Optional[ReasoningRunnerConfig] = None,
    ):
        """
        Initialize the reasoning runner.

        Args:
            llm_client: LLM client for generating responses
            console: Rich console for display
            config: Runner configuration
        """
        self.llm_client = llm_client
        self.console = console or get_console()
        self.config = config or ReasoningRunnerConfig()

        # Initialize components
        self.todo_manager = TodoManager()
        self.thinking_manager = create_enhanced_thinking_manager(
            llm_client=llm_client, todo_manager=self.todo_manager
        )
        self.todo_display = PersistentTodoDisplay(
            console=self.console,
            max_visible=self.config.max_visible_todos,
            compact_mode=self.config.compact_todo,
        )

        # State
        self.current_result: Optional[ThinkingResult] = None
        self.execution_history: List[Dict[str, Any]] = []
        self.is_running = False

        # Listeners
        self.on_todo_update: List[Callable[[List[Dict[str, Any]]], None]] = []
        self.on_reasoning_complete: List[Callable[[ThinkingResult], None]] = []
        self.on_execution_feedback: List[Callable[[FeedbackEntry], None]] = []

        # Connect components
        self._setup_connections()

    def _setup_connections(self):
        """Set up connections between components"""
        # Connect todo manager to display
        self.todo_manager.add_listener(self._on_todos_changed)

        # Connect thinking manager to display
        self.thinking_manager.add_todo_listener(self._on_todos_from_reasoning)

    def _on_todos_changed(self, todos: List[TodoItem]):
        """Handle todo list changes"""
        todo_dicts = [
            {"content": t.content, "status": t.status.value, "activeForm": t.active_form}
            for t in todos
        ]
        self.todo_display.set_todos(todo_dicts)

        # Notify external listeners
        for listener in self.on_todo_update:
            try:
                listener(todo_dicts)
            except Exception:
                pass

    def _on_todos_from_reasoning(self, todos: List[Dict[str, Any]]):
        """Handle todos extracted from reasoning"""
        self.todo_display.set_todos(todos)

    def set_llm_client(self, client: Any):
        """Set the LLM client"""
        self.llm_client = client
        self.thinking_manager.set_llm_client(client)

    # =========================================================================
    # MAIN EXECUTION INTERFACE
    # =========================================================================

    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
            mode: Optional[EnhancedThinkingMode] = None,
    ) -> ThinkingResult:
        """
        Run a task with full reasoning and todo tracking.

        Args:
            task: The task to execute
            context: Additional context
            mode: Reasoning mode override

        Returns:
            ThinkingResult with reasoning and action items
        """
        self.is_running = True
        mode = mode or self.config.reasoning_mode

        # Start todo display if enabled
        if self.config.show_todo_panel:
            self.todo_display.start()

        try:
            # Perform reasoning
            result = await self.thinking_manager.think(prompt=task, mode=mode, context=context)

            self.current_result = result

            # Notify listeners
            for listener in self.on_reasoning_complete:
                try:
                    listener(result)
                except Exception:
                    pass

            return result

        finally:
            self.is_running = False

    def record_execution(
        self,
        tool_name: str,
        action: str,
        output: str,
        success: bool,
        error: Optional[str] = None,
            duration_ms: int = 0,
    ) -> FeedbackEntry:
        """
        Record an execution result.

        Args:
            tool_name: Name of the tool executed
            action: Description of the action
            output: Output from execution
            success: Whether execution succeeded
            error: Error message if failed
            duration_ms: Execution duration

        Returns:
            Feedback entry with analysis
        """
        feedback = self.thinking_manager.record_execution(
            tool_name=tool_name,
            action=action,
            output=output,
            success=success,
            error=error,
            duration_ms=duration_ms,
        )

        # Track in history
        self.execution_history.append(
            {
                "tool_name": tool_name,
                "action": action,
                "success": success,
                "timestamp": datetime.now().isoformat(),
                "feedback_type": feedback.feedback_type.value,
            }
        )

        # Advance todo if successful
        if success and self.config.auto_update_todos:
            self.todo_display.mark_current_complete()

        # Notify listeners
        for listener in self.on_execution_feedback:
            try:
                listener(feedback)
            except Exception:
                pass

        return feedback

    def complete_todo(self, content: Optional[str] = None):
        """
        Mark a todo as complete.

        Args:
            content: Specific todo content to complete (or current if None)
        """
        if content:
            # Find and complete specific todo
            todos = self.todo_manager.get_all()
            for i, todo in enumerate(todos):
                if todo.content == content:
                    self.todo_display.update_todo(i, "completed")
                    break
        else:
            # Complete current
            self.todo_display.mark_current_complete()

    def add_todo(self, content: str, active_form: Optional[str] = None):
        """
        Add a new todo item.

        Args:
            content: Todo content
            active_form: Active form text
        """
        self.todo_display.add_todo(content, active_form)

    def stop_display(self):
        """Stop the todo display"""
        if self.todo_display:
            self.todo_display.stop()

    # =========================================================================
    # DISPLAY METHODS
    # =========================================================================

    def render_status(self) -> Text:
        """Render current status as text"""
        todos = self.todo_manager.get_all()
        return render_todo_status_line(
            [
                {"content": t.content, "status": t.status.value, "activeForm": t.active_form}
                for t in todos
            ]
        )

    def render_panel(self) -> Panel:
        """Render todo panel"""
        todos = self.todo_manager.get_all()
        return render_todo_panel(
            [
                {"content": t.content, "status": t.status.value, "activeForm": t.active_form}
                for t in todos
            ]
        )

    def get_progress(self) -> Dict[str, Any]:
        """Get progress statistics"""
        return self.todo_display.get_progress()

    def display_summary(self):
        """Display execution summary"""
        palette = get_palette()
        progress = self.get_progress()

        # Create summary table
        table = Table(
            title="Execution Summary", box=box.ROUNDED, border_style=palette.border_default
        )
        table.add_column("Metric", style=palette.text_secondary)
        table.add_column("Value", style=f"bold {palette.primary}")

        table.add_row("Total Tasks", str(progress["total"]))
        table.add_row("Completed", str(progress["completed"]))
        table.add_row("In Progress", str(progress["in_progress"]))
        table.add_row("Pending", str(progress["pending"]))
        table.add_row("Progress", f"{progress['percentage']:.1f}%")

        if self.current_result:
            table.add_row("Confidence", f"{self.current_result.confidence:.0%}")
            if self.current_result.quality_metrics:
                table.add_row(
                    "Quality Score", f"{self.current_result.quality_metrics.get('overall', 0):.2f}"
                )

        self.console.print(table)


class ChatReasoningRunner:
    """
    Chat-mode reasoning runner with persistent todo display.

    Designed for interactive chat sessions where todos are displayed
    persistently at the bottom of the screen.
    """

    def __init__(self, llm_client: Any = None, console: Optional[Console] = None):
        self.llm_client = llm_client
        self.console = console or get_console()
        self.palette = get_palette()

        # Components
        self.todo_manager = TodoManager()
        self.thinking_manager = create_enhanced_thinking_manager(
            llm_client=llm_client, todo_manager=self.todo_manager
        )
        self.todo_bar = TodoStatusBar()

        # State
        self.todos: List[Dict[str, Any]] = []
        self.show_todos = True

    def set_llm_client(self, client: Any):
        """Set the LLM client"""
        self.llm_client = client
        self.thinking_manager.set_llm_client(client)

    def update_todos(self, todos: List[Dict[str, Any]]):
        """Update the todo list"""
        self.todos = todos

        # Sync with todo manager
        self.todo_manager.batch_update(todos)

    def add_todo(self, content: str, active_form: Optional[str] = None):
        """Add a todo item"""
        new_todo = {"content": content, "status": "pending", "activeForm": active_form or content}

        # If this is the first pending and no in_progress, make it in_progress
        has_in_progress = any(t.get("status") == "in_progress" for t in self.todos)
        if not has_in_progress:
            new_todo["status"] = "in_progress"

        self.todos.append(new_todo)
        self.todo_manager.batch_update(self.todos)

    def complete_current(self):
        """Complete the current in-progress todo"""
        for i, todo in enumerate(self.todos):
            if todo.get("status") == "in_progress":
                self.todos[i]["status"] = "completed"

                # Advance to next pending
                for j, next_todo in enumerate(self.todos[i + 1:], i + 1):
                    if next_todo.get("status") == "pending":
                        self.todos[j]["status"] = "in_progress"
                        break
                break

        self.todo_manager.batch_update(self.todos)

    def render_status_bar(self) -> Text:
        """Render the status bar for display at bottom"""
        if not self.todos or not self.show_todos:
            return Text("")

        total = len(self.todos)
        completed = sum(1 for t in self.todos if t.get("status") == "completed")
        current = next((t for t in self.todos if t.get("status") == "in_progress"), None)

        return self.todo_bar.render(
            completed=completed,
            total=total,
            current_task=current.get("activeForm") if current else None,
        )

    def render_full_panel(self) -> Panel:
        """Render full todo panel"""
        return render_todo_panel(self.todos)

    async def process_with_reasoning(
            self, task: str, context: Optional[Dict[str, Any]] = None
    ) -> ThinkingResult:
        """
        Process a task with reasoning and todo extraction.

        Args:
            task: The task to process
            context: Additional context

        Returns:
            ThinkingResult with reasoning and action items
        """
        result = await self.thinking_manager.think(
            prompt=task, mode=EnhancedThinkingMode.ADAPTIVE, context=context
        )

        # Update todos from result
        if result.action_items:
            self.todos = result.action_items
            self.todo_manager.batch_update(self.todos)

        return result

    def get_action_items(self) -> List[str]:
        """Get current action items as strings"""
        return [t.get("content", "") for t in self.todos if t.get("status") != "completed"]


# ═══════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def create_reasoning_runner(
    llm_client: Any = None,
    console: Optional[Console] = None,
    show_todos: bool = True,
        compact_todos: bool = False,
) -> ReasoningRunner:
    """
    Create a configured reasoning runner.

    Args:
        llm_client: LLM client
        console: Rich console
        show_todos: Whether to show todo panel
        compact_todos: Use compact todo display

    Returns:
        Configured ReasoningRunner
    """
    config = ReasoningRunnerConfig(show_todo_panel=show_todos, compact_todo=compact_todos)
    return ReasoningRunner(llm_client=llm_client, console=console, config=config)


def create_chat_reasoning_runner(
        llm_client: Any = None, console: Optional[Console] = None
) -> ChatReasoningRunner:
    """
    Create a chat-mode reasoning runner.

    Args:
        llm_client: LLM client
        console: Rich console

    Returns:
        Configured ChatReasoningRunner
    """
    return ChatReasoningRunner(llm_client=llm_client, console=console)
