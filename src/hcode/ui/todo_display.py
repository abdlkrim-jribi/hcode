"""
Persistent Todo Display Component for HCode CLI.

Provides a Claude Code-style persistent todo list that displays at the
bottom of the terminal to track agent progress in real-time.
"""

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.box import ROUNDED, SIMPLE, MINIMAL
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.padding import Padding
from rich.rule import Rule
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import time

from .theme import get_palette, get_theme


class TodoDisplayStatus(Enum):
    """Status indicators for todo items"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class DisplayTodoItem:
    """Todo item for display purposes"""
    content: str
    status: TodoDisplayStatus = TodoDisplayStatus.PENDING
    active_form: str = ""
    index: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def get_display_text(self) -> str:
        """Get the text to display based on status"""
        if self.status == TodoDisplayStatus.IN_PROGRESS:
            return self.active_form or self.content
        return self.content

    def get_duration(self) -> Optional[float]:
        """Get duration in seconds if applicable"""
        if self.start_time:
            end = self.end_time or datetime.now()
            return (end - self.start_time).total_seconds()
        return None


class TodoDisplayRenderer:
    """
    Renders todo list in Claude Code style.

    Displays:
    - Current task with animation
    - Progress bar
    - Completed/pending counts
    - Time elapsed
    """

    # Status icons and colors
    STATUS_CONFIG = {
        TodoDisplayStatus.PENDING: ("○", "dim white"),
        TodoDisplayStatus.IN_PROGRESS: ("◐", "bold yellow"),
        TodoDisplayStatus.COMPLETED: ("●", "bold green"),
        TodoDisplayStatus.BLOCKED: ("⊗", "bold red"),
        TodoDisplayStatus.SKIPPED: ("⊘", "dim"),
    }

    # Animation frames for in-progress
    PROGRESS_FRAMES = ["◐", "◓", "◑", "◒"]

    def __init__(self, max_visible: int = 5):
        """
        Initialize renderer.

        Args:
            max_visible: Maximum number of todos to show
        """
        self.max_visible = max_visible
        self.animation_frame = 0
        self.palette = get_palette()

    def render(
        self,
        todos: List[DisplayTodoItem],
        show_all: bool = False,
        compact: bool = False
    ) -> RenderableType:
        """
        Render the todo list.

        Args:
            todos: List of todo items
            show_all: Show all items (not just visible)
            compact: Use compact single-line format

        Returns:
            Rich renderable
        """
        if not todos:
            return Text("No tasks", style="dim")

        if compact:
            return self._render_compact(todos)

        return self._render_full(todos, show_all)

    def _render_compact(self, todos: List[DisplayTodoItem]) -> Text:
        """Render compact single-line format"""
        text = Text()

        # Count by status
        completed = sum(1 for t in todos if t.status == TodoDisplayStatus.COMPLETED)
        in_progress = sum(1 for t in todos if t.status == TodoDisplayStatus.IN_PROGRESS)
        total = len(todos)

        # Progress indicator
        text.append("Tasks: ", style="dim")
        text.append(f"{completed}/{total}", style="bold cyan")

        # Current task
        current = next((t for t in todos if t.status == TodoDisplayStatus.IN_PROGRESS), None)
        if current:
            frame = self.PROGRESS_FRAMES[self.animation_frame % len(self.PROGRESS_FRAMES)]
            text.append(f"  {frame} ", style="bold yellow")
            display_text = current.get_display_text()
            if len(display_text) > 40:
                display_text = display_text[:37] + "..."
            text.append(display_text, style="yellow")

        return text

    def _render_full(
        self,
        todos: List[DisplayTodoItem],
        show_all: bool
    ) -> Panel:
        """Render full todo panel"""
        # Separate by status
        completed = [t for t in todos if t.status == TodoDisplayStatus.COMPLETED]
        in_progress = [t for t in todos if t.status == TodoDisplayStatus.IN_PROGRESS]
        pending = [t for t in todos if t.status == TodoDisplayStatus.PENDING]
        other = [t for t in todos if t.status in [TodoDisplayStatus.BLOCKED, TodoDisplayStatus.SKIPPED]]

        # Build display list - prioritize in_progress and pending
        display_todos = in_progress + pending + other

        if not show_all and len(display_todos) > self.max_visible:
            display_todos = display_todos[:self.max_visible]

        # Create content
        lines = []

        # Progress bar
        total = len(todos)
        done = len(completed)
        progress_pct = (done / total * 100) if total > 0 else 0

        progress_line = self._render_progress_bar(done, total, progress_pct)
        lines.append(progress_line)
        lines.append(Text(""))

        # Todo items
        for todo in display_todos:
            line = self._render_todo_item(todo)
            lines.append(line)

        # Show completed count if any hidden
        hidden_completed = len(completed)
        if hidden_completed > 0 and not show_all:
            lines.append(Text(""))
            lines.append(Text(
                f"  ● {hidden_completed} completed",
                style="dim green"
            ))

        # Show remaining count if truncated
        remaining = len(todos) - len(display_todos) - hidden_completed
        if remaining > 0:
            lines.append(Text(f"  ... and {remaining} more", style="dim"))

        content = Group(*lines)

        # Create panel
        title = self._render_title(done, total)

        return Panel(
            content,
            title=title,
            border_style=self.palette.border_default,
            box=ROUNDED,
            padding=(0, 1),
        )

    def _render_progress_bar(
        self,
        done: int,
        total: int,
        percentage: float
    ) -> Text:
        """Render progress bar"""
        bar_width = 30
        filled = int(bar_width * percentage / 100)
        empty = bar_width - filled

        text = Text()
        text.append("  ")

        # Progress bar
        text.append("▓" * filled, style="bold green")
        text.append("░" * empty, style="dim")

        text.append(f"  {percentage:.0f}%", style="bold cyan")
        text.append(f"  ({done}/{total})", style="dim")

        return text

    def _render_todo_item(self, todo: DisplayTodoItem) -> Text:
        """Render a single todo item"""
        icon, color = self.STATUS_CONFIG.get(
            todo.status,
            self.STATUS_CONFIG[TodoDisplayStatus.PENDING]
        )

        # Animate in-progress items
        if todo.status == TodoDisplayStatus.IN_PROGRESS:
            icon = self.PROGRESS_FRAMES[self.animation_frame % len(self.PROGRESS_FRAMES)]

        text = Text()
        text.append(f"  {icon} ", style=color)

        display_text = todo.get_display_text()
        text.append(display_text, style=color.replace("bold ", "") if "bold" in color else color)

        # Show duration for in-progress
        if todo.status == TodoDisplayStatus.IN_PROGRESS:
            duration = todo.get_duration()
            if duration:
                text.append(f" ({duration:.1f}s)", style="dim")

        return text

    def _render_title(self, done: int, total: int) -> Text:
        """Render panel title"""
        title = Text()
        title.append("◈ ", style=f"bold {self.palette.secondary}")
        title.append("Tasks", style=f"bold {self.palette.primary}")
        title.append(f" [{done}/{total}]", style="dim")
        return title

    def advance_animation(self):
        """Advance animation frame"""
        self.animation_frame += 1


class PersistentTodoDisplay:
    """
    Persistent todo display that stays at the bottom of the terminal.

    Uses Rich's Live display to maintain a persistent view that
    updates in real-time as tasks progress.
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        max_visible: int = 5,
        refresh_rate: float = 4.0,  # Refreshes per second
        compact_mode: bool = False
    ):
        """
        Initialize persistent display.

        Args:
            console: Rich console instance
            max_visible: Max items to show
            refresh_rate: How often to refresh display
            compact_mode: Use compact single-line format
        """
        self.console = console or Console()
        self.renderer = TodoDisplayRenderer(max_visible=max_visible)
        self.refresh_rate = refresh_rate
        self.compact_mode = compact_mode

        self.todos: List[DisplayTodoItem] = []
        self.live: Optional[Live] = None
        self._running = False
        self._lock = threading.Lock()

        # Listeners for external integration
        self.update_listeners: List[Callable[[List[DisplayTodoItem]], None]] = []

    def add_listener(self, listener: Callable[[List[DisplayTodoItem]], None]):
        """Add update listener"""
        self.update_listeners.append(listener)

    def _notify_listeners(self):
        """Notify all listeners of update"""
        for listener in self.update_listeners:
            try:
                listener(self.todos)
            except Exception:
                pass

    def start(self):
        """Start the persistent display"""
        if self._running:
            return

        self._running = True

        # Create live display
        self.live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=self.refresh_rate,
            transient=False,
            vertical_overflow="visible"
        )
        self.live.start()

        # Start animation thread
        self._animation_thread = threading.Thread(
            target=self._animation_loop,
            daemon=True
        )
        self._animation_thread.start()

    def stop(self):
        """Stop the persistent display"""
        self._running = False

        if self.live:
            self.live.stop()
            self.live = None

    def _animation_loop(self):
        """Background thread for animations"""
        while self._running:
            time.sleep(0.25)  # 4 FPS for animation
            self.renderer.advance_animation()
            self._update_display()

    def _render(self) -> RenderableType:
        """Render current state"""
        with self._lock:
            return self.renderer.render(
                self.todos,
                show_all=False,
                compact=self.compact_mode
            )

    def _update_display(self):
        """Update the live display"""
        if self.live and self._running:
            try:
                self.live.update(self._render())
            except Exception:
                pass  # Ignore display errors

    def set_todos(self, todos: List[Dict[str, Any]]):
        """
        Set todos from dictionary list.

        Args:
            todos: List of todo dictionaries with content, status, activeForm
        """
        with self._lock:
            self.todos = []
            for i, todo_data in enumerate(todos):
                status_str = todo_data.get("status", "pending")
                try:
                    status = TodoDisplayStatus(status_str)
                except ValueError:
                    status = TodoDisplayStatus.PENDING

                item = DisplayTodoItem(
                    content=todo_data.get("content", ""),
                    status=status,
                    active_form=todo_data.get("activeForm", ""),
                    index=i
                )

                # Set start time for in-progress
                if status == TodoDisplayStatus.IN_PROGRESS:
                    item.start_time = datetime.now()

                self.todos.append(item)

        self._update_display()
        self._notify_listeners()

    def update_todo(self, index: int, status: str, active_form: Optional[str] = None):
        """
        Update a specific todo.

        Args:
            index: Todo index
            status: New status
            active_form: Optional new active form
        """
        with self._lock:
            if 0 <= index < len(self.todos):
                todo = self.todos[index]

                old_status = todo.status
                try:
                    todo.status = TodoDisplayStatus(status)
                except ValueError:
                    pass

                if active_form:
                    todo.active_form = active_form

                # Track timing
                if todo.status == TodoDisplayStatus.IN_PROGRESS and old_status != TodoDisplayStatus.IN_PROGRESS:
                    todo.start_time = datetime.now()
                elif todo.status == TodoDisplayStatus.COMPLETED and old_status == TodoDisplayStatus.IN_PROGRESS:
                    todo.end_time = datetime.now()

        self._update_display()
        self._notify_listeners()

    def add_todo(self, content: str, active_form: Optional[str] = None, status: str = "pending"):
        """
        Add a new todo.

        Args:
            content: Todo content
            active_form: Active form text
            status: Initial status
        """
        with self._lock:
            try:
                status_enum = TodoDisplayStatus(status)
            except ValueError:
                status_enum = TodoDisplayStatus.PENDING

            item = DisplayTodoItem(
                content=content,
                status=status_enum,
                active_form=active_form or content,
                index=len(self.todos)
            )

            if status_enum == TodoDisplayStatus.IN_PROGRESS:
                item.start_time = datetime.now()

            self.todos.append(item)

        self._update_display()
        self._notify_listeners()

    def mark_current_complete(self):
        """Mark the current in-progress todo as complete and advance to next"""
        with self._lock:
            # Find current in-progress
            for i, todo in enumerate(self.todos):
                if todo.status == TodoDisplayStatus.IN_PROGRESS:
                    todo.status = TodoDisplayStatus.COMPLETED
                    todo.end_time = datetime.now()

                    # Find next pending and mark in-progress
                    for next_todo in self.todos[i + 1:]:
                        if next_todo.status == TodoDisplayStatus.PENDING:
                            next_todo.status = TodoDisplayStatus.IN_PROGRESS
                            next_todo.start_time = datetime.now()
                            break
                    break

        self._update_display()
        self._notify_listeners()

    def clear(self):
        """Clear all todos"""
        with self._lock:
            self.todos = []

        self._update_display()
        self._notify_listeners()

    def get_progress(self) -> Dict[str, Any]:
        """Get progress statistics"""
        with self._lock:
            total = len(self.todos)
            completed = sum(1 for t in self.todos if t.status == TodoDisplayStatus.COMPLETED)
            in_progress = sum(1 for t in self.todos if t.status == TodoDisplayStatus.IN_PROGRESS)
            pending = sum(1 for t in self.todos if t.status == TodoDisplayStatus.PENDING)

            current = next(
                (t for t in self.todos if t.status == TodoDisplayStatus.IN_PROGRESS),
                None
            )

            return {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "pending": pending,
                "percentage": (completed / total * 100) if total > 0 else 0,
                "current_task": current.get_display_text() if current else None
            }


class TodoStatusBar:
    """
    Simple status bar showing todo progress.

    For use when full panel is not needed.
    """

    def __init__(self):
        self.palette = get_palette()

    def render(
        self,
        completed: int,
        total: int,
        current_task: Optional[str] = None
    ) -> Text:
        """Render status bar"""
        text = Text()

        # Icon
        text.append("◈ ", style=f"bold {self.palette.secondary}")

        # Progress
        text.append(f"{completed}/{total}", style="bold cyan")
        text.append(" tasks", style="dim")

        # Current task
        if current_task:
            text.append("  │  ", style="dim")
            text.append("◐ ", style="bold yellow")

            if len(current_task) > 50:
                current_task = current_task[:47] + "..."
            text.append(current_task, style="yellow")

        return text


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION HELPERS
# ═══════════════════════════════════════════════════════════════════════

def create_todo_display(
    console: Optional[Console] = None,
    compact: bool = False
) -> PersistentTodoDisplay:
    """Create a new todo display instance"""
    return PersistentTodoDisplay(
        console=console,
        compact_mode=compact
    )


def render_todo_panel(
    todos: List[Dict[str, Any]],
    max_visible: int = 5
) -> Panel:
    """
    Render a static todo panel.

    Args:
        todos: List of todo dictionaries
        max_visible: Maximum items to show

    Returns:
        Rich Panel
    """
    renderer = TodoDisplayRenderer(max_visible=max_visible)

    display_items = []
    for i, todo_data in enumerate(todos):
        status_str = todo_data.get("status", "pending")
        try:
            status = TodoDisplayStatus(status_str)
        except ValueError:
            status = TodoDisplayStatus.PENDING

        item = DisplayTodoItem(
            content=todo_data.get("content", ""),
            status=status,
            active_form=todo_data.get("activeForm", ""),
            index=i
        )
        display_items.append(item)

    return renderer.render(display_items, show_all=False, compact=False)


def render_todo_status_line(
    todos: List[Dict[str, Any]]
) -> Text:
    """
    Render a single-line todo status.

    Args:
        todos: List of todo dictionaries

    Returns:
        Rich Text
    """
    total = len(todos)
    completed = sum(1 for t in todos if t.get("status") == "completed")
    current = next(
        (t for t in todos if t.get("status") == "in_progress"),
        None
    )

    bar = TodoStatusBar()
    return bar.render(
        completed=completed,
        total=total,
        current_task=current.get("activeForm") or current.get("content") if current else None
    )
