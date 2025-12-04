"""
Live Todo Bar - Real-time todo display that updates during agent execution.

This module provides an integrated todo display that receives updates via
the callback system, enabling Claude Code-style real-time todo updates
during agent execution.

Key Features:
- Receives todo updates via callback system (no polling)
- Integrates with Rich streaming output
- Uses ANSI positioning for persistent bottom display
- Thread-safe updates from async execution
"""

import sys
import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from rich.console import Console

from hcode.ui.todo_display import (
    ClaudeCodeTodoDisplay,
)
from hcode.tools.tool_callbacks import (
    ToolEvent,
    ToolEventType,
    get_callback_manager,
)


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

    # ANSI escape sequences for cursor positioning
    SAVE_CURSOR = "\033[s"
    RESTORE_CURSOR = "\033[u"
    CLEAR_LINE = "\033[2K"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"

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
                self.todos = list(event.todos)

            # Immediately render the update
            if self._active:
                self._render_status_bar()

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

        # Clear the status area
        self._clear_status_area()

    def _reserve_space(self) -> None:
        """Reserve space at the bottom of the terminal."""
        # Print newlines to create space
        for _ in range(self.height):
            print()

        # Move cursor back up
        sys.stdout.write(f"\033[{self.height}A")
        sys.stdout.flush()

    def _clear_status_area(self) -> None:
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

    def _update_loop(self) -> None:
        """Background thread to update the elapsed time display."""
        while not self._stop_event.is_set():
            if self._active and self.todos:
                self._render_status_bar()
            time.sleep(0.5)  # Update twice per second

    def _render_status_bar(self) -> None:
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

            # Render to string
            from io import StringIO

            string_buffer = StringIO()
            temp_console = Console(
                file=string_buffer,
                force_terminal=True,
                width=self.console.width or 120,
                no_color=False,
            )

            rendered = self.todo_display.render(
                self.todos,
                elapsed_seconds=elapsed,
                token_count=self.token_count,
                show_shortcuts=self.show_shortcuts,
            )
            temp_console.print(rendered)

            # Get lines
            output = string_buffer.getvalue()
            lines = output.split("\n")[: self.height]

            # Position and render
            sys.stdout.write(self.SAVE_CURSOR)

            for i, line in enumerate(lines):
                row = terminal_height - self.height + i + 1
                sys.stdout.write(f"\033[{row}H")
                sys.stdout.write(self.CLEAR_LINE)
                # Handle Windows encoding issues with Unicode characters
                try:
                    sys.stdout.write(line)
                except UnicodeEncodeError:
                    # Fallback: replace problematic Unicode with ASCII alternatives
                    safe_line = line.encode("ascii", "replace").decode("ascii")
                    sys.stdout.write(safe_line)

            sys.stdout.write(self.RESTORE_CURSOR)
            sys.stdout.flush()

    def update_todos(self, todos: List[Dict[str, Any]]) -> None:
        """
        Manually update todos (in addition to callback updates).

        Args:
            todos: The new todo list
        """
        with self._lock:
            self.todos = list(todos)

        if self._active:
            self._render_status_bar()

    def update_tokens(self, token_count: int) -> None:
        """
        Update the token count display.

        Args:
            token_count: Number of tokens used
        """
        with self._lock:
            self.token_count = token_count

    def reset_timer(self) -> None:
        """Reset the elapsed time to zero."""
        self.start_time = datetime.now()

    @property
    def is_active(self) -> bool:
        """Check if the bar is currently active."""
        return self._active

    def get_todos(self) -> List[Dict[str, Any]]:
        """Get the current todo list."""
        with self._lock:
            return list(self.todos)


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

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the todo bar when exiting context."""
        self.todo_bar.stop()
        return False

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
