"""
Rich terminal display for agent execution.

Shows thinking progress and todo status in real-time.
Uses Claude Code-like styling.
"""

from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box

from ..agent.thinking import ThinkingBlock, ThinkingPhase
from ..agent.todo import TodoItem, TodoStatus
from ..config.thinking import ThinkingVisibility

# Import UI system
from ..ui import (
    Colors,
    Icons,
    StyledPanel,
    TodoDisplay,
    TodoItem as StyledTodoItem,
    get_default_box,
    console as styled_console
)


class AgentDisplay:
    """
    Rich terminal display for agent execution.

    Shows thinking and todos with Claude Code-like styling.
    In normal mode, thinking is hidden (Claude Code style).
    In debug mode, thinking is shown based on visibility setting.
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        visibility: ThinkingVisibility = ThinkingVisibility.STREAMING,
        debug_mode: bool = False
    ):
        """
        Initialize display.

        Args:
            console: Rich console instance
            visibility: How to show thinking (only used in debug mode)
            debug_mode: If False (default), thinking is hidden. If True, uses visibility setting.
        """
        self.console = console or styled_console
        self.debug_mode = debug_mode
        # In normal mode, hide thinking. In debug mode, use the specified visibility.
        self.visibility = visibility if debug_mode else ThinkingVisibility.HIDDEN
        self.current_thinking: Optional[ThinkingBlock] = None
        self.todos: List[TodoItem] = []
        self.live: Optional[Live] = None
        self.icons = Icons()

    def start_live_display(self) -> None:
        """Start live display mode"""
        layout = self._create_layout()
        self.live = Live(
            layout,
            console=self.console,
            refresh_per_second=4,
            screen=False
        )
        self.live.start()

    def stop_live_display(self) -> None:
        """Stop live display mode"""
        if self.live:
            self.live.stop()
            self.live = None

    def _create_layout(self) -> Layout:
        """Create display layout"""
        layout = Layout()
        layout.split_column(
            Layout(name="thinking", size=10),
            Layout(name="todos", size=15)
        )
        return layout

    def update_display(self) -> None:
        """Update live display"""
        if not self.live:
            return

        layout = self._create_layout()

        # Update thinking panel
        thinking_panel = self._create_thinking_panel()
        layout["thinking"].update(thinking_panel)

        # Update todos panel
        todos_panel = self._create_todos_panel()
        layout["todos"].update(todos_panel)

        self.live.update(layout)

    def on_thinking_block(self, block: ThinkingBlock) -> None:
        """
        Handle new thinking block.

        Args:
            block: Thinking block
        """
        self.current_thinking = block

        if self.visibility == ThinkingVisibility.HIDDEN:
            return

        if self.visibility == ThinkingVisibility.STREAMING:
            # Show in real-time
            if self.live:
                self.update_display()
            else:
                self._print_thinking_block(block)

        elif self.visibility == ThinkingVisibility.SUMMARY:
            # Show summary only
            self._print_thinking_summary(block)

    def on_todos_update(self, todos: List[TodoItem]) -> None:
        """
        Handle todos update.

        Args:
            todos: Updated todo list
        """
        self.todos = todos

        if self.live:
            self.update_display()
        else:
            self._print_todos()

    def _create_thinking_panel(self) -> Panel:
        """Create thinking panel with styled colors"""
        if not self.current_thinking:
            content = Text("No active thinking", style=Colors.TEXT_MUTED)
        else:
            phase = self.current_thinking.phase.value.upper()
            content = Text()
            content.append(f"Phase: ", style=f"bold {Colors.THINKING}")
            content.append(f"{phase}\n\n", style=Colors.THINKING)

            if self.visibility == ThinkingVisibility.FULL:
                content.append(self.current_thinking.content)
            else:
                content.append(self.current_thinking.summary or self.current_thinking.content[:200])

            # Show tokens and time
            content.append(f"\n\n", style=Colors.TEXT_MUTED)
            content.append(f"Tokens: {self.current_thinking.tokens_used} | ", style=Colors.TEXT_MUTED)
            content.append(f"Time: {self.current_thinking.duration_ms}ms", style=Colors.TEXT_MUTED)

        return Panel(
            content,
            title=f"[bold {Colors.THINKING}]{self.icons.THINKING} Thinking[/]",
            border_style=Colors.THINKING,
            box=get_default_box()
        )

    def _create_todos_panel(self) -> Panel:
        """Create todos panel with styled colors"""
        if not self.todos:
            content = Text("No todos yet", style=Colors.TEXT_MUTED)
            return Panel(
                content,
                title=f"[{Colors.PRIMARY}]{self.icons.CHECK} Tasks[/]",
                border_style=Colors.PRIMARY,
                box=get_default_box()
            )

        table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
        table.add_column("Status", width=3)
        table.add_column("Task", ratio=1)

        for todo in self.todos:
            # Status icon and color - using new color system
            status_config = {
                TodoStatus.PENDING: (self.icons.TODO_PENDING, Colors.TODO_PENDING),
                TodoStatus.IN_PROGRESS: (self.icons.TODO_IN_PROGRESS, Colors.TODO_IN_PROGRESS),
                TodoStatus.COMPLETED: (self.icons.TODO_COMPLETED, Colors.TODO_COMPLETED),
                TodoStatus.BLOCKED: (self.icons.TODO_BLOCKED, Colors.TODO_BLOCKED),
                TodoStatus.SKIPPED: (self.icons.TODO_SKIPPED, Colors.TODO_SKIPPED)
            }

            icon, color = status_config.get(todo.status, (self.icons.CIRCLE_EMPTY, Colors.TEXT_MUTED))

            # Use active form if in progress
            if todo.status == TodoStatus.IN_PROGRESS:
                task_text = todo.active_form or todo.content
            else:
                task_text = todo.content

            table.add_row(
                Text(icon, style=color),
                Text(task_text, style=f"bold {color}" if todo.status == TodoStatus.IN_PROGRESS else color)
            )

        # Add progress bar
        completed = sum(1 for t in self.todos if t.status == TodoStatus.COMPLETED)
        total = len(self.todos)

        return Panel(
            table,
            title=f"[{Colors.PRIMARY}]{self.icons.CHECK} Tasks ({completed}/{total})[/]",
            border_style=Colors.PRIMARY,
            box=get_default_box()
        )

    def _print_thinking_block(self, block: ThinkingBlock) -> None:
        """Print thinking block (non-live mode)"""
        phase = block.phase.value.upper()
        self.console.print(f"\n[bold {Colors.THINKING}]{self.icons.THINKING} THINKING: {phase}[/]")
        self.console.print(Panel(
            block.summary or block.content[:200],
            border_style=Colors.THINKING,
            box=get_default_box()
        ))

    def _print_thinking_summary(self, block: ThinkingBlock) -> None:
        """Print thinking summary"""
        phase = block.phase.value.title()
        self.console.print(f"[{Colors.THINKING}]{self.icons.BULLET} {phase}:[/] {block.summary}")

    def _print_todos(self) -> None:
        """Print todos (non-live mode)"""
        self.console.print(f"\n[bold {Colors.PRIMARY}]{self.icons.SQUARE_FILLED} TASKS:[/]")

        for todo in self.todos:
            status_config = {
                TodoStatus.PENDING: (self.icons.TODO_PENDING, Colors.TODO_PENDING),
                TodoStatus.IN_PROGRESS: (self.icons.TODO_IN_PROGRESS, Colors.TODO_IN_PROGRESS),
                TodoStatus.COMPLETED: (self.icons.TODO_COMPLETED, Colors.TODO_COMPLETED),
                TodoStatus.BLOCKED: (self.icons.TODO_BLOCKED, Colors.TODO_BLOCKED),
                TodoStatus.SKIPPED: (self.icons.TODO_SKIPPED, Colors.TODO_SKIPPED)
            }

            icon, color = status_config.get(todo.status, (self.icons.CIRCLE_EMPTY, Colors.TEXT_MUTED))

            if todo.status == TodoStatus.IN_PROGRESS:
                task_text = todo.active_form or todo.content
            else:
                task_text = todo.content

            self.console.print(f"[{color}]{icon} {task_text}[/]")

    def print_error(self, message: str) -> None:
        """Print error message"""
        self.console.print(f"[bold {Colors.ERROR}]{self.icons.CROSS} Error:[/] {message}")

    def print_success(self, message: str) -> None:
        """Print success message"""
        self.console.print(f"[bold {Colors.SUCCESS}]{self.icons.CHECK}[/] {message}")

    def print_info(self, message: str) -> None:
        """Print info message"""
        self.console.print(f"[{Colors.INFO}]{self.icons.INFO}[/] {message}")

    def print_warning(self, message: str) -> None:
        """Print warning message"""
        self.console.print(f"[bold {Colors.WARNING}]{self.icons.WARNING}[/] {message}")

    def print_thinking_summary(self, blocks: List[ThinkingBlock]) -> None:
        """
        Print summary of all thinking blocks.

        Args:
            blocks: List of thinking blocks
        """
        if not blocks:
            return

        self.console.print(f"\n[bold {Colors.THINKING}]{self.icons.THINKING} Thinking Summary:[/]")

        for block in blocks:
            phase = block.phase.value.title()
            self.console.print(f"[{Colors.THINKING}]{self.icons.BULLET} {phase}:[/] {block.summary}")

        total_tokens = sum(b.tokens_used for b in blocks)
        total_time = sum(b.duration_ms for b in blocks)

        self.console.print(
            f"\n[{Colors.TEXT_MUTED}]Total: {total_tokens} tokens, {total_time/1000:.1f}s[/]"
        )

    def print_final_todos(self) -> None:
        """Print final todo summary"""
        if not self.todos:
            return

        completed = sum(1 for t in self.todos if t.status == TodoStatus.COMPLETED)
        total = len(self.todos)

        self.console.print(f"\n[bold {Colors.SUCCESS}]{self.icons.CHECK} Completed {completed}/{total} tasks[/]")

        # Show any incomplete tasks
        incomplete = [
            t for t in self.todos
            if t.status not in [TodoStatus.COMPLETED, TodoStatus.SKIPPED]
        ]

        if incomplete:
            self.console.print(f"\n[{Colors.WARNING}]Remaining tasks:[/]")
            for todo in incomplete:
                status_name = todo.status.value.replace('_', ' ').title()
                self.console.print(f"  {self.icons.BULLET} [{status_name}] {todo.content}")
