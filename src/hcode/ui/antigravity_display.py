"""
Antigravity-Style Display Manager for Hcode Agent.

Provides Claude Code/Antigravity style reasoning display with:
- "Thought for Xs" timer header
- Task boundary display with mode status
- Progress updates with numbered steps
- File tracking (edited/viewed)
- Collapsible thinking blocks
- Phase-by-phase reasoning display
"""

import time
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.padding import Padding
from rich.rule import Rule
from rich.markdown import Markdown

# Import theme system
try:
    from . import get_palette, Icons, get_console
except ImportError:
    from hcode.ui import get_palette, Icons, get_console


class TaskMode(Enum):
    """Agent operation modes matching Antigravity phases."""
    PLANNING = "PLANNING"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"


class FileAction(Enum):
    """File operation actions."""
    EDITED = "Edited"
    VIEWED = "Viewed"
    CREATED = "Created"
    DELETED = "Deleted"


@dataclass
class ProgressUpdate:
    """A single progress update."""
    number: int
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    completed: bool = False


@dataclass 
class TrackedFile:
    """A tracked file operation."""
    filename: str
    action: FileAction
    timestamp: datetime = field(default_factory=datetime.now)


class AntigravityDisplay:
    """
    Antigravity/Claude Code style display manager.
    
    Provides real-time display of agent thinking and progress
    with the distinctive Antigravity visual style.
    
    Usage:
        display = AntigravityDisplay(console)
        
        with display.task_context("Implementing Feature", TaskMode.PLANNING):
            with display.thinking_context():
                # Agent thinking...
                display.add_progress("Exploring codebase structure")
                display.track_file("main.py", FileAction.VIEWED)
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize Antigravity display manager."""
        self.console = console or get_console()
        self._palette = get_palette()
        self._icons = Icons()
        
        # Task state
        self.current_task: Optional[str] = None
        self.current_mode: Optional[TaskMode] = None
        self.task_start_time: Optional[float] = None
        
        # Thinking state
        self.thinking_start_time: Optional[float] = None
        self._thinking_live: Optional[Live] = None
        self._thinking_stop_event = threading.Event()
        self._thinking_thread: Optional[threading.Thread] = None
        
        # Progress tracking
        self.progress_updates: List[ProgressUpdate] = []
        self.tracked_files: Dict[str, TrackedFile] = {}
        self._progress_counter = 0
        
        # Display state
        self._task_displayed = False
        
    def reset(self):
        """Reset all state for a new task."""
        self.current_task = None
        self.current_mode = None
        self.task_start_time = None
        self.thinking_start_time = None
        self.progress_updates = []
        self.tracked_files = {}
        self._progress_counter = 0
        self._task_displayed = False
        
    # =========================================================================
    # TASK BOUNDARY DISPLAY
    # =========================================================================
    
    def start_task(self, task_name: str, mode: TaskMode = TaskMode.PLANNING) -> None:
        """
        Display task boundary header.
        
        Shows:
        - Task name with mode indicator
        - Mode-specific color styling
        """
        self.reset()
        self.current_task = task_name
        self.current_mode = mode
        self.task_start_time = time.time()
        
        # Mode colors
        mode_colors = {
            TaskMode.PLANNING: self._palette.info,
            TaskMode.EXECUTION: self._palette.success,
            TaskMode.VERIFICATION: self._palette.warning,
        }
        color = mode_colors.get(mode, self._palette.primary)
        
        # Display task header
        self.console.print()
        
        # Task name with mode badge
        header = Text()
        header.append(f"{self._icons.BULLET} ", style=f"bold {color}")
        header.append(task_name, style=f"bold {self._palette.text_primary}")
        
        self.console.print(header)
        
        # Mode indicator
        mode_text = Text()
        mode_text.append(f"  Mode: ", style=self._palette.text_muted)
        mode_text.append(mode.value, style=f"bold {color}")
        self.console.print(mode_text)
        
        self._task_displayed = True
        
    def update_mode(self, mode: TaskMode) -> None:
        """Update the current task mode."""
        self.current_mode = mode
        
        mode_colors = {
            TaskMode.PLANNING: self._palette.info,
            TaskMode.EXECUTION: self._palette.success,
            TaskMode.VERIFICATION: self._palette.warning,
        }
        color = mode_colors.get(mode, self._palette.primary)
        
        self.console.print()
        mode_text = Text()
        mode_text.append(f"  → Switched to: ", style=self._palette.text_muted)
        mode_text.append(mode.value, style=f"bold {color}")
        self.console.print(mode_text)
        
    def end_task(self, summary: Optional[str] = None) -> None:
        """End current task and show summary."""
        if self.task_start_time:
            duration = time.time() - self.task_start_time
            
            self.console.print()
            end_text = Text()
            end_text.append(f"✓ ", style=f"bold {self._palette.success}")
            end_text.append(f"Task completed ", style=self._palette.text_primary)
            end_text.append(f"({duration:.1f}s)", style=self._palette.text_muted)
            self.console.print(end_text)
            
            if summary:
                self.console.print(f"  {summary}", style=self._palette.text_muted)
                
    @contextmanager
    def task_context(self, task_name: str, mode: TaskMode = TaskMode.PLANNING):
        """Context manager for task boundaries."""
        self.start_task(task_name, mode)
        try:
            yield self
        finally:
            self.end_task()
            
    # =========================================================================
    # THINKING DISPLAY ("Thought for Xs")
    # =========================================================================
    
    def start_thinking(self) -> None:
        """
        Start the "Thought for Xs" animated timer.
        
        Shows a live-updating timer that counts up while the agent thinks.
        """
        self.thinking_start_time = time.time()
        self._thinking_stop_event.clear()
        
        self.console.print()
        
        def animate_thinking():
            """Animation thread for thinking timer."""
            icons = ["◐", "◓", "◑", "◒"]
            icon_idx = 0
            
            while not self._thinking_stop_event.is_set():
                elapsed = time.time() - self.thinking_start_time
                icon = icons[icon_idx % len(icons)]
                
                text = Text()
                text.append(f" {icon} ", style=f"bold {self._palette.warning}")
                text.append("Thought for ", style=self._palette.text_muted)
                text.append(f"{elapsed:.0f}s", style=f"bold {self._palette.warning}")
                
                if self._thinking_live:
                    self._thinking_live.update(text)
                    
                icon_idx += 1
                time.sleep(0.15)
        
        # Start live display
        initial_text = Text()
        initial_text.append(" ◐ ", style=f"bold {self._palette.warning}")
        initial_text.append("Thought for ", style=self._palette.text_muted)
        initial_text.append("0s", style=f"bold {self._palette.warning}")
        
        self._thinking_live = Live(
            initial_text,
            console=self.console,
            refresh_per_second=10,
            transient=True,
        )
        self._thinking_live.start()
        
        self._thinking_thread = threading.Thread(target=animate_thinking, daemon=True)
        self._thinking_thread.start()
        
    def end_thinking(self) -> float:
        """
        End thinking timer and show final duration.
        
        Returns:
            Duration in seconds
        """
        self._thinking_stop_event.set()
        
        if self._thinking_live:
            self._thinking_live.stop()
            self._thinking_live = None
            
        duration = 0.0
        if self.thinking_start_time:
            duration = time.time() - self.thinking_start_time
            
            # Show final "Thought for Xs" message
            final_text = Text()
            final_text.append("💡 ", style=f"bold {self._palette.info}")
            final_text.append("Thought for ", style=self._palette.text_muted)
            final_text.append(f"{duration:.0f}s", style=f"bold {self._palette.info}")
            self.console.print(final_text)
            
        self.thinking_start_time = None
        return duration
        
    @contextmanager
    def thinking_context(self):
        """Context manager for thinking display."""
        self.start_thinking()
        try:
            yield
        finally:
            self.end_thinking()
            
    # =========================================================================
    # PROGRESS UPDATES
    # =========================================================================
    
    def add_progress(self, message: str) -> int:
        """
        Add a numbered progress update.
        
        Args:
            message: Progress message to display
            
        Returns:
            Progress update number
        """
        self._progress_counter += 1
        update = ProgressUpdate(
            number=self._progress_counter,
            message=message,
        )
        self.progress_updates.append(update)
        
        # Display the progress update
        progress_text = Text()
        progress_text.append(f"  {self._progress_counter}. ", style=f"bold {self._palette.secondary}")
        progress_text.append(message, style=self._palette.text_primary)
        self.console.print(progress_text)
        
        return self._progress_counter
        
    def complete_progress(self, number: int) -> None:
        """Mark a progress update as completed."""
        for update in self.progress_updates:
            if update.number == number:
                update.completed = True
                break
                
    def show_progress_summary(self) -> None:
        """Show summary of all progress updates."""
        if not self.progress_updates:
            return
            
        self.console.print()
        self.console.print("Progress Updates", style=f"bold {self._palette.info}")
        
        for update in self.progress_updates:
            icon = "✓" if update.completed else "○"
            style = self._palette.success if update.completed else self._palette.text_muted
            self.console.print(f"  {icon} {update.number}. {update.message}", style=style)
            
    # =========================================================================
    # FILE TRACKING
    # =========================================================================
    
    def track_file(self, filename: str, action: FileAction) -> None:
        """
        Track a file operation.
        
        Args:
            filename: Name or path of the file
            action: What was done to the file
        """
        self.tracked_files[filename] = TrackedFile(
            filename=filename,
            action=action,
        )
        
    def show_files_edited(self) -> None:
        """Display list of edited files."""
        edited = [f for f in self.tracked_files.values() 
                  if f.action in (FileAction.EDITED, FileAction.CREATED)]
        
        if not edited:
            return
            
        self.console.print()
        header = Text()
        header.append("Files Edited", style=f"bold {self._palette.warning}")
        self.console.print(header)
        
        for file in edited:
            file_text = Text()
            file_text.append(f"  • ", style=self._palette.warning)
            file_text.append(file.filename, style=self._palette.text_primary)
            self.console.print(file_text)
            
    def show_files_explored(self) -> None:
        """Display list of viewed/explored files."""
        viewed = [f for f in self.tracked_files.values() 
                  if f.action == FileAction.VIEWED]
        
        if not viewed:
            return
            
        self.console.print()
        header = Text()
        header.append("Files Explored", style=f"bold {self._palette.info}")
        self.console.print(header)
        
        for file in viewed:
            file_text = Text()
            file_text.append(f"  • ", style=self._palette.info)
            file_text.append(file.filename, style=self._palette.text_muted)
            self.console.print(file_text)
            
    # =========================================================================
    # INTEGRATED DISPLAY
    # =========================================================================
    
    def show_task_summary(self) -> None:
        """
        Show complete task summary with all tracked information.
        
        Displays:
        - Files edited
        - Progress updates
        - Duration
        """
        self.console.print()
        self.console.print(Rule(style=self._palette.border_default))
        
        # Show files
        self.show_files_edited()
        self.show_files_explored()
        
        # Show progress summary
        if self.progress_updates:
            self.show_progress_summary()
            
        self.console.print()
        
    def display_thinking_block(
        self,
        content: str,
        phase: Optional[str] = None,
        collapsed: bool = True,
    ) -> None:
        """
        Display a thinking block in Antigravity style.
        
        Args:
            content: The thinking content
            phase: Optional phase name (e.g., "PERCEPTION", "DECISION")
            collapsed: Whether to show collapsed (summary only)
        """
        if collapsed:
            # Show just a summary line
            summary = content.split('\n')[0][:80]
            if len(content) > 80:
                summary += "..."
                
            thinking_text = Text()
            thinking_text.append("◊ ", style=f"bold {self._palette.warning}")
            if phase:
                thinking_text.append(f"[{phase}] ", style=f"italic {self._palette.secondary}")
            thinking_text.append(summary, style=self._palette.text_muted)
            self.console.print(thinking_text)
        else:
            # Show full thinking block
            panel = Panel(
                Markdown(content) if "```" in content else Text(content),
                title=f"◊ Thinking{f' - {phase}' if phase else ''}",
                title_align="left",
                border_style=self._palette.warning,
                padding=(0, 1),
            )
            self.console.print(panel)


# Singleton instance for global access
_display_instance: Optional[AntigravityDisplay] = None


def get_antigravity_display(console: Optional[Console] = None) -> AntigravityDisplay:
    """Get or create the global AntigravityDisplay instance."""
    global _display_instance
    if _display_instance is None:
        _display_instance = AntigravityDisplay(console)
    return _display_instance


def reset_display() -> None:
    """Reset the global display instance."""
    global _display_instance
    if _display_instance:
        _display_instance.reset()


__all__ = [
    "AntigravityDisplay",
    "TaskMode",
    "FileAction",
    "ProgressUpdate",
    "TrackedFile",
    "get_antigravity_display",
    "reset_display",
]
