"""
Persistent Todo Display Component for HCode CLI.

Provides a Claude Code-style persistent todo list that displays at the
bottom of the terminal to track agent progress in real-time.

Claude Code Style:
✶ Writing integration tests… (esc to interrupt · ctrl+t to hide todos · 3m 21s · ↓ 9.5k tokens)
 ⎿  ☒ Fix Rich markup escaping in Edit tool display
    ☒ Fix long line handling in Edit tool display
    ☐ Write more integration tests for Edit tool
"""

import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable

from rich.box import ROUNDED
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from hcode.ui.theme import get_palette

# ═══════════════════════════════════════════════════════════════════════
# CLAUDE CODE STYLE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

# Checkbox characters (Claude Code style)
CHECKBOX_CHECKED = "☒"
CHECKBOX_UNCHECKED = "☐"
CHECKBOX_IN_PROGRESS = "☐"  # In-progress shown with sparkle header instead

# Icons
ICON_SPARKLE = "✶"
ICON_BRANCH = "⎿"


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
        self, todos: List[DisplayTodoItem], show_all: bool = False, compact: bool = False
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
        sum(1 for t in todos if t.status == TodoDisplayStatus.IN_PROGRESS)
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

    def _render_full(self, todos: List[DisplayTodoItem], show_all: bool) -> Panel:
        """Render full todo panel"""
        # Separate by status
        completed = [t for t in todos if t.status == TodoDisplayStatus.COMPLETED]
        in_progress = [t for t in todos if t.status == TodoDisplayStatus.IN_PROGRESS]
        pending = [t for t in todos if t.status == TodoDisplayStatus.PENDING]
        other = [
            t for t in todos if t.status in [TodoDisplayStatus.BLOCKED, TodoDisplayStatus.SKIPPED]
        ]

        # Build display list - prioritize in_progress and pending
        display_todos = in_progress + pending + other

        if not show_all and len(display_todos) > self.max_visible:
            display_todos = display_todos[: self.max_visible]

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
            lines.append(Text(f"  ● {hidden_completed} completed", style="dim green"))

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

    def _render_progress_bar(self, done: int, total: int, percentage: float) -> Text:
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
            todo.status, self.STATUS_CONFIG[TodoDisplayStatus.PENDING]
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
        compact_mode: bool = False,
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
            vertical_overflow="visible",
        )
        self.live.start()

        # Start animation thread
        self._animation_thread = threading.Thread(target=self._animation_loop, daemon=True)
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
            return self.renderer.render(self.todos, show_all=False, compact=self.compact_mode)

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
                    index=i,
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
                if (
                    todo.status == TodoDisplayStatus.IN_PROGRESS
                    and old_status != TodoDisplayStatus.IN_PROGRESS
                ):
                    todo.start_time = datetime.now()
                elif (
                    todo.status == TodoDisplayStatus.COMPLETED
                    and old_status == TodoDisplayStatus.IN_PROGRESS
                ):
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
                index=len(self.todos),
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
                    for next_todo in self.todos[i + 1 :]:
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
                (t for t in self.todos if t.status == TodoDisplayStatus.IN_PROGRESS), None
            )

            return {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "pending": pending,
                "percentage": (completed / total * 100) if total > 0 else 0,
                "current_task": current.get_display_text() if current else None,
            }


class TodoStatusBar:
    """
    Simple status bar showing todo progress.

    For use when full panel is not needed.
    """

    def __init__(self):
        self.palette = get_palette()

    def render(self, completed: int, total: int, current_task: Optional[str] = None) -> Text:
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
    console: Optional[Console] = None, compact: bool = False
) -> PersistentTodoDisplay:
    """Create a new todo display instance"""
    return PersistentTodoDisplay(console=console, compact_mode=compact)


def render_todo_panel(todos: List[Dict[str, Any]], max_visible: int = 5) -> Panel:
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
            index=i,
        )
        display_items.append(item)

    return renderer.render(display_items, show_all=False, compact=False)


def render_todo_status_line(todos: List[Dict[str, Any]]) -> Text:
    """
    Render a single-line todo status.

    Args:
        todos: List of todo dictionaries

    Returns:
        Rich Text
    """
    total = len(todos)
    completed = sum(1 for t in todos if t.get("status") == "completed")
    current = next((t for t in todos if t.get("status") == "in_progress"), None)

    bar = TodoStatusBar()
    return bar.render(
        completed=completed,
        total=total,
        current_task=current.get("activeForm") or current.get("content") if current else None,
    )


# ═══════════════════════════════════════════════════════════════════════
# CLAUDE CODE STYLE TODO DISPLAY
# ═══════════════════════════════════════════════════════════════════════


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




def print_claude_code_todos(
    todos: List[Dict[str, Any]],
    console: Optional[Console] = None,
    elapsed_seconds: float = 0,
    token_count: int = 0,
    show_shortcuts: bool = True,
):
    """
    Print todos in Claude Code style.

    Convenience function for printing without creating a display instance.
    """
    display = ClaudeCodeTodoDisplay(console or Console())
    display.print(todos, elapsed_seconds, token_count, show_shortcuts)


# ═══════════════════════════════════════════════════════════════════════
# PERSISTENT BOTTOM STATUS BAR (Claude Code style)
# ═══════════════════════════════════════════════════════════════════════


class PersistentStatusBar:
    """
    A persistent status bar that stays at the bottom of the terminal.

    Uses ANSI escape sequences to create a sticky footer that updates
    in real-time while allowing normal output to scroll above it.

    Usage:
        status_bar = PersistentStatusBar()
        status_bar.start()

        # Update todos anytime
        status_bar.update_todos(todos_list)

        # Normal prints work above the status bar
        print("This scrolls above")

        status_bar.stop()
    """

    # ANSI escape sequences
    SAVE_CURSOR = "\033[s"
    RESTORE_CURSOR = "\033[u"
    MOVE_TO_BOTTOM = "\033[{row}H"  # Move to specific row
    CLEAR_LINE = "\033[2K"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"

    def __init__(self, console: Optional[Console] = None, height: int = 5):
        """
        Initialize persistent status bar.

        Args:
            console: Rich console instance
            height: Number of lines to reserve for status bar
        """
        self.console = console or Console()
        self.height = height
        self.todos: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.token_count: int = 0
        self._active = False
        self._lock = threading.Lock()
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.todo_display = ClaudeCodeTodoDisplay(self.console)

    def start(self):
        """Start the persistent status bar."""
        if self._active:
            return

        self._active = True
        self._stop_event.clear()
        self.start_time = datetime.now()

        # Reserve space at bottom
        self._reserve_space()

        # Start update thread for animations
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()

    def stop(self):
        """Stop the persistent status bar."""
        self._active = False
        self._stop_event.set()

        if self._update_thread:
            self._update_thread.join(timeout=1.0)

        # Clear the status bar area
        self._clear_status_area()

    def _reserve_space(self):
        """Reserve space at the bottom of the terminal for the status bar."""
        # Print newlines to create space
        for _ in range(self.height):
            print()

        # Move cursor back up
        sys.stdout.write(f"\033[{self.height}A")
        sys.stdout.flush()

    def _clear_status_area(self):
        """Clear the status bar area."""
        terminal_height = self._get_terminal_height()

        sys.stdout.write(self.SAVE_CURSOR)
        for i in range(self.height):
            row = terminal_height - self.height + i + 1
            sys.stdout.write(f"\033[{row}H")
            sys.stdout.write(self.CLEAR_LINE)
        sys.stdout.write(self.RESTORE_CURSOR)
        sys.stdout.flush()

    def _get_terminal_height(self) -> int:
        """Get terminal height."""
        try:
            import shutil

            return shutil.get_terminal_size().lines
        except Exception:
            return 24  # Default

    def _update_loop(self):
        """Background thread to update the status bar."""
        while not self._stop_event.is_set():
            self._render_status_bar()
            time.sleep(0.25)  # Update 4 times per second

    def _render_status_bar(self):
        """Render the status bar at the bottom of the terminal."""
        if not self._active:
            return

        with self._lock:
            if not self.todos:
                return

            terminal_height = self._get_terminal_height()

            # Calculate elapsed time
            elapsed = 0.0
            if self.start_time:
                elapsed = (datetime.now() - self.start_time).total_seconds()

            # Render the todo display to a string
            from io import StringIO

            string_buffer = StringIO()
            temp_console = Console(
                file=string_buffer, force_terminal=True, width=self.console.width or 120
            )

            # Render todos
            rendered = self.todo_display.render(
                self.todos,
                elapsed_seconds=elapsed,
                token_count=self.token_count,
                show_shortcuts=True,
            )
            temp_console.print(rendered)

            # Get the rendered lines
            output = string_buffer.getvalue()
            lines = output.split("\n")[: self.height]

            # Save cursor, move to bottom, render, restore cursor
            sys.stdout.write(self.SAVE_CURSOR)

            for i, line in enumerate(lines):
                row = terminal_height - self.height + i + 1
                sys.stdout.write(f"\033[{row}H")
                sys.stdout.write(self.CLEAR_LINE)
                sys.stdout.write(line)

            sys.stdout.write(self.RESTORE_CURSOR)
            sys.stdout.flush()

    def update_todos(self, todos: List[Dict[str, Any]]):
        """Update the todo list."""
        with self._lock:
            self.todos = todos
        self._render_status_bar()

    def update_tokens(self, token_count: int):
        """Update the token count."""
        with self._lock:
            self.token_count = token_count



class LiveTodoBar:
    """
    Alternative implementation using Rich's Live display.

    Better integration with Rich but may conflict with other Live displays.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.todos: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.token_count: int = 0
        self.live: Optional[Live] = None
        self._lock = threading.Lock()
        self.todo_display = ClaudeCodeTodoDisplay(self.console)

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit."""
        self.stop()

    def start(self):
        """Start the live display."""
        self.start_time = datetime.now()
        self.live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
            vertical_overflow="visible",
        )
        self.live.start()

    def stop(self):
        """Stop the live display."""
        if self.live:
            self.live.stop()
            self.live = None

    def _render(self) -> Text:
        """Render the current state."""
        if not self.todos:
            return Text("")

        elapsed = 0.0
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()

        return self.todo_display.render(
            self.todos, elapsed_seconds=elapsed, token_count=self.token_count, show_shortcuts=True
        )

    def update(self):
        """Force update the display."""
        if self.live:
            self.live.update(self._render())

    def update_todos(self, todos: List[Dict[str, Any]]):
        """Update todos and refresh display."""
        with self._lock:
            self.todos = todos
        self.update()

    def update_tokens(self, token_count: int):
        """Update token count."""
        with self._lock:
            self.token_count = token_count
        self.update()


# Global functions removed as they were unused
