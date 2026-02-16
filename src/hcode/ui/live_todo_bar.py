"""
Live Todo Bar - Real-time todo display that updates during agent execution.

This module provides an integrated todo display that receives updates via
the callback system, enabling Claude Code-style real-time todo updates
during agent execution.

Key Features:
- Receives todo updates via callback system (no polling)
- Integrates with Rich streaming output
- Uses Rich controls for persistent bottom display causing no interference
- Thread-safe updates from async execution
- Cross-platform support via Rich
"""

import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from rich.console import Console, ConsoleOptions, RenderResult
from rich.control import Control
from rich.segment import ControlType

# Global write lock to coordinate streaming output and todo bar updates
_stdout_write_lock = threading.RLock()

from hcode.ui.todo_display import (
    ClaudeCodeTodoDisplay,
)
from hcode.tools.core.tool_callbacks import (
    ToolEvent,
    ToolEventType,
    get_callback_manager,
)

from rich.segment import Segment


class RawControl:
    """Wrapper for raw ANSI control codes."""

    def __init__(self, code: str):
        self.code = code
        self.code = code

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield Segment(self.code, is_control=True)


class LiveTodoBar:
    """
    Real-time todo bar that updates automatically during agent execution.

    Uses the callback system to receive todo updates immediately when
    TodoWrite is called, rather than waiting for task completion.

    Usage:
        bar = LiveTodoBar(console)
        bar.start()  # Start listening for updates

        # Agent execution happens here - todos update automatically
        result = await agent.execute_task(...)

        bar.stop()  # Stop and cleanup
    """

    def __init__(
            self, console: Optional[Console] = None, height: int = 6, show_shortcuts: bool = True
    ):
        """
        Initialize live todo bar.

        Args:
            console: Rich console instance
            height: Number of lines to reserve for todo display
            show_shortcuts: Whether to show keyboard shortcuts
        """
        self.console = console or Console()
        self.height = height
        self.show_shortcuts = show_shortcuts

        # State
        self.todos: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.token_count: int = 0
        self._active = False
        self._paused = False
        self._lock = threading.Lock()

        # Display components
        self.todo_display = ClaudeCodeTodoDisplay(self.console)

        # Callback management
        self._callback_manager = get_callback_manager()
        self._callback_registered = False

        # Update thread for elapsed time
        self._stop_event = threading.Event()
        self._update_thread: Optional[threading.Thread] = None

    def _on_todo_update(self, event: ToolEvent) -> None:
        """
        Handle todo update events from the callback system.

        Called automatically when TodoWrite tool is executed.

        Args:
            event: The todo update event
        """
        if event.todos is not None:
            with self._lock:
                # Check if todos actually changed
                self.todos = list(event.todos)

            # DISABLED: Printing on each todo update causes duplication on Windows
            # Todos are shown only at task completion via print_final_status()
            # if todos_changed and self._active and not self._paused:
            #     self._print_simple_status()

    def start(self) -> None:
        """
        Start the live todo bar.

        Registers for callback events and starts the update thread.
        """
        if self._active:
            return

        self._active = True
        self._stop_event.clear()
        self.start_time = datetime.now()

        # Register callback
        if not self._callback_registered:
            self._callback_manager.register(ToolEventType.TODO_UPDATE, self._on_todo_update)
            self._callback_registered = True

        # Reserve space at bottom
        self._reserve_space()

        # Start update thread for elapsed time animation
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()

    def stop(self) -> None:
        """
        Stop the live todo bar.

        Unregisters callbacks and cleans up display.
        """
        # Print final todo status before stopping (only once)
        if not getattr(self, '_final_printed', False):
            self.print_final_status()
            self._final_printed = True

        self._active = False
        self._stop_event.set()

        # Wait for update thread
        if self._update_thread:
            self._update_thread.join(timeout=1.0)
            self._update_thread = None

        # Unregister callback
        if self._callback_registered:
            self._callback_manager.unregister(ToolEventType.TODO_UPDATE, self._on_todo_update)
            self._callback_registered = False

        # NOTE: Don't clear status area here - it would erase the final status we just printed

    def print_final_status(self) -> None:
        """Print the final todo status (called when task completes)."""
        with self._lock:
            # DEBUG: Always show todo count
            todo_count = len(self.todos)
            if todo_count == 0:
                # Show message that no todos were created
                self.console.print("\n[dim]No todos created for this task[/dim]")
                return

            # Calculate elapsed time
            elapsed = 0.0
            if self.start_time:
                elapsed = (datetime.now() - self.start_time).total_seconds()

            try:
                # Render todos
                rendered = self.todo_display.render(
                    self.todos,
                    elapsed_seconds=elapsed,
                    token_count=self.token_count,
                    show_shortcuts=False,  # Don't show shortcuts in final status
                )

                # Print with separators for visibility
                self.console.print("\n" + "─" * 70)
                self.console.print(rendered)
                self.console.print("─" * 70 + "\n")
            except Exception:
                # Fallback: simple print if rendering fails
                self.console.print(f"\n[dim]Task completed with {len(self.todos)} todos[/dim]\n")

    def _reserve_space(self) -> None:
        """Reserve space at the bottom of the terminal."""
        with _stdout_write_lock:
            # Print newlines to create space
            self.console.print("\n" * self.height, end="")

            # Move cursor back up using Rich control
            self.console.control(Control.move(0, -self.height))

    def _clear_status_area(self) -> None:
        """Clear the status bar area."""
        with _stdout_write_lock:
            # We use standard ANSI codes wrapped in Rich Control for maximum compatibility
            # Save cursor, move to bottom area, clear lines, restore cursor

            terminal_height = self.console.height

            # Create control sequence
            controls = [
                RawControl("\033[s"),  # Save cursor
            ]

            for i in range(self.height):
                row = terminal_height - self.height + i
                controls.append(Control.move_to(0, row))
                controls.append(Control((ControlType.ERASE_IN_LINE, 2)))  # Clear whole line

            controls.append(RawControl("\033[u"))  # Restore cursor

            self.console.control(*controls)

    def update_todos(self, todos: List[Dict[str, Any]]) -> None:
        """
        Manually update todos (in addition to callback updates).

        Args:
            todos: The new todo list
        """
        with self._lock:
            self.todos = list(todos)

        # DISABLED: Causes duplication on Windows
        # if self._active:
        #     self._render_status_bar()

        with self._lock:
            self.token_count = token_count

    def _update_loop(self) -> None:
        """Background loop for time-based animation (seconds elapsed)."""
        while not self._stop_event.is_set():
            if self._active:
                # We can trigger a re-render here if we want live clock
                # but for Windows stability we keep it minimal
                pass
            time.sleep(1.0)

    def _render_status_bar(self) -> None:
        """Render the status bar area."""
        if not self._active or self._paused:
            return

        with self._lock:
            try:
                # Calculate elapsed
                elapsed = 0.0
                if self.start_time:
                    elapsed = (datetime.now() - self.start_time).total_seconds()

                # Render todos
                rendered = self.todo_display.render(
                    self.todos,
                    elapsed_seconds=elapsed,
                    token_count=self.token_count,
                    show_shortcuts=self.show_shortcuts,
                )

                # Clear and print
                self._clear_status_area()
                with _stdout_write_lock:
                    terminal_height = self.console.height
                    self.console.control(Control.move_to(0, terminal_height - self.height))
                    self.console.print(rendered, end="")
            except Exception:
                pass

    @property
    def is_active(self) -> bool:
        """Check if the bar is currently active."""
        return self._active

    def get_todos(self) -> List[Dict[str, Any]]:
        """Get the current todo list."""
        with self._lock:
            return list(self.todos)

    def pause(self) -> None:
        """Pause todo updates (e.g. during streaming)."""
        self._paused = True

    def resume(self) -> None:
        """Resume todo updates."""
        self._paused = False
        if self._active:
            self._render_status_bar()


class StreamingTodoIntegration:
    """
    Integration helper for combining streaming output with todo bar.

    Provides methods to coordinate Rich streaming output with the
    persistent todo bar at the bottom.

    Usage:
        integration = StreamingTodoIntegration(console)

        with integration:
            # Streaming and todos work together
            async for chunk in stream_result:
                print(chunk, end="", flush=True)
            # Todo bar updates automatically via callbacks
    """

    def __init__(self, console: Optional[Console] = None, height: int = 6):
        """
        Initialize streaming integration.

        Args:
            console: Rich console instance
            height: Height of todo bar area
        """
        self.console = console or Console()
        self.todo_bar = LiveTodoBar(console=self.console, height=height)

    def __enter__(self):
        """Start the todo bar when entering context."""
        self.todo_bar.start()
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Stop the todo bar when exiting context."""
        self.todo_bar.stop()

    def start(self) -> None:
        """Start the integration (alternative to context manager)."""
        self.todo_bar.start()

    def stop(self) -> None:
        """Stop the integration."""
        self.todo_bar.stop()

    def get_todos(self) -> List[Dict[str, Any]]:
        """Get the current todo list."""
        return self.todo_bar.get_todos()

    def update_tokens(self, count: int) -> None:
        """Update token count."""
        self.todo_bar.update_tokens(count)


# Convenience functions

_global_live_bar: Optional[LiveTodoBar] = None


def get_live_todo_bar(console: Optional[Console] = None) -> LiveTodoBar:
    """
    Get or create the global live todo bar instance.

    Args:
        console: Optional console instance

    Returns:
        The global LiveTodoBar instance
    """
    global _global_live_bar
    if _global_live_bar is None:
        _global_live_bar = LiveTodoBar(console)
    return _global_live_bar


def start_live_todos(console: Optional[Console] = None) -> LiveTodoBar:
    """
    Start the global live todo bar.

    Args:
        console: Optional console instance

    Returns:
        The started LiveTodoBar
    """
    bar = get_live_todo_bar(console)
    bar.start()
    return bar


def stop_live_todos() -> None:
    """Stop the global live todo bar."""
    global _global_live_bar
    if _global_live_bar:
        _global_live_bar.stop()


def get_current_todos() -> List[Dict[str, Any]]:
    """Get todos from the global live bar."""
    global _global_live_bar
    if _global_live_bar:
        return _global_live_bar.get_todos()
    return []


def get_stdout_lock():
    """
    Get the global stdout write lock.

    Use this lock when writing to stdout to prevent interference
    with the live todo bar's ANSI positioning codes.

    Returns:
        The global stdout write lock

    Example:
        from hcode.ui.live_todo_bar import get_stdout_lock

        with get_stdout_lock():
            print("This won't interfere with todo bar", flush=True)
    """
    return _stdout_write_lock
