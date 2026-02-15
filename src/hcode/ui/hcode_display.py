"""
Hcode-Style Display Manager for Hcode Agent.

Provides Claude Code/Hcode style reasoning display with:
- "Thought for Xs" timer header
- Task boundary display with mode status
- Progress updates with numbered steps
- File tracking (edited/viewed)
- Collapsible thinking blocks
- Phase-by-phase reasoning display
"""

import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict

from rich import box
from rich.console import Console, Group
from rich.live import Live
# from rich.rule import Rule
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Import theme system
try:
    from . import get_palette, Icons, get_console
except ImportError:
    from hcode.ui import get_palette, Icons, get_console


class TaskMode(Enum):
    """Agent operation modes matching Hcode phases."""
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


class HcodeDisplay:
    """
    Hcode/Claude Code style display manager.
    
    Provides real-time display of agent thinking and progress
    with the distinctive Hcode visual style.
    
    Usage:
        display = HcodeDisplay(console)
        
        with display.task_context("Implementing Feature", TaskMode.PLANNING):
            with display.thinking_context():
                # Agent thinking...
                display.add_progress("Exploring codebase structure")
                display.track_file("main.py", FileAction.VIEWED)
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize Hcode display manager."""
        self.console = console or get_console()
        self._palette = get_palette()
        self._icons = Icons()
        
        # Task state
        self.current_task: Optional[str] = None
        self.current_mode: Optional[TaskMode] = None
        self.task_start_time: Optional[float] = None
        
        # Thinking state
        # Thinking state
        self.thinking_start_time: Optional[float] = None
        
        # Progress tracking
        self.progress_updates: List[ProgressUpdate] = []
        self.tracked_files: Dict[str, TrackedFile] = {}
        self._progress_counter = 0
        
        # Display state
        self._thinking_stop_event = threading.Event()
        self._thinking_thread: Optional[threading.Thread] = None
        self._thinking_live: Optional[Live] = None

        
    def reset(self):
        """Reset all state for a new task."""
        self.current_task = None
        self.current_mode = None
        self.task_start_time = None
        self.thinking_start_time = None
        self.progress_updates = []
        self.tracked_files = {}
        self._progress_counter = 0
        
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
                text = Text(f"  {summary}", style=self._palette.text_muted)
                self.console.print(text)
                
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
        Start the thinking timer.
        
        Prints a modern styled 'Thinking...' message with neon green accents.
        """
        self.thinking_start_time = time.time()
        self._thinking_stop_event.clear()
        
        # Modern neon green styled thinking indicator
        text = Text()
        text.append("\n  ", style="")
        text.append(f"{self._icons.LOGO} ", style="bold #00FF88")  # Mint green icon
        text.append("Thinking", style="bold #39FF14")  # Neon green
        text.append(f" {self._icons.LOADING}", style="bold #00FFAA")  # Animated-styled spinner
        self.console.print(text)
        
    def end_thinking(self) -> float:
        """
        End thinking timer and show final duration with modern styling.
        
        Returns:
            Duration in seconds
        """
        self._thinking_stop_event.set()
        
        duration = 0.0
        if self.thinking_start_time:
            duration = time.time() - self.thinking_start_time
            
            # Modern neon green "Thought for Xs" message
            final_text = Text()
            final_text.append("  ", style="")
            final_text.append(f"{self._icons.CYBER_DOT} ", style="bold #39FF14")  # Neon green dot
            final_text.append("Thought for ", style=self._palette.text_muted)
            final_text.append(f"{duration:.0f}s", style="bold #39FF14")  # Neon green duration
            self.console.print(final_text)
            
        self.thinking_start_time = None
        return duration
        
            
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
        
            
            
    # =========================================================================
    # INTEGRATED DISPLAY
    # =========================================================================

    def display_thinking_block(
        self,
        content: str,
        phase: Optional[str] = None,
        collapsed: bool = False,
    ) -> None:
        """
        Display a thinking block with modern neon green styling.

        Shows thinking with a visible indicator, phase badge, and content.

        Args:
            content: The thinking content
            phase: Optional phase name (e.g., "PLANNING", "EXECUTION")
            collapsed: Whether to show collapsed (summary only)
        """
        if not content:
            return

        # Calculate thinking duration if available
        duration_str = ""
        if self.thinking_start_time:
            duration = time.time() - self.thinking_start_time
            duration_str = f" • {duration:.1f}s"

        # Content processing
        if collapsed:
            # Show just first line as summary
            lines = content.strip().split('\n')
            display_content = lines[0] + ("..." if len(lines) > 1 else "")
        else:
            display_content = content.strip()

        # Build Title
        title = Text()
        title.append("Thinking", style="thinking.title")
        
        if phase:
            phase_colors = {
                "PLANNING": "#00DDFF",      # Cyan
                "EXECUTION": "#39FF14",     # Neon green
                "VERIFICATION": "#FFCC00",  # Gold
                "DECISION": "#FF00FF",      # Magenta
                "ANALYSIS": "#00DDFF",      # Cyan match
                "COMPREHENSION": "#00DDFF", # Cyan match
                "REASONING": "#39FF14",     # Green match
            }
            p_color = phase_colors.get(phase, "#39FF14")
            title.append(f" ({phase})", style=f"bold {p_color}")
        
        if duration_str:
            title.append(duration_str, style="thinking.metadata")

        # Create Grid Layout (Borderless with Gutter)
        grid = Table.grid(padding=(0, 1))
        # Column 1: Gutter
        grid.add_column(style="thinking.gutter", width=2, justify="center")
        # Column 2: Content
        grid.add_column(style="thinking.content")
        
        # Determine Icon
        
        # Row 1: Header
        grid.add_row("▍", title)
        
        # Row 2: Content (if any)
        if content:
            # Add a spacer row
            grid.add_row("▍", "")
            
            if collapsed:
                lines = content.strip().split('\n')
                display_content = lines[0] + ("..." if len(lines) > 1 else "")
                grid.add_row("▍", Text(display_content, style="thinking.metadata"))
            else:
                # Render content as Markdown but we need to potentially process line by line
                # for the gutter to persist. Alternatively, we can nest a table.
                # For simplicity and "airiness", let's indent the content.
                
                # We can't easily put Markdown in a single cell and have the gutter on the left 
                # for every line unless we split it.
                # But a simple indentation logic is often cleaner for "airy" design.
                
                # Let's try rendering Markdown in the second column.
                # Rich Tables handle multiline content in cells automatically.
                md_content = Markdown(content.strip())
                grid.add_row("▍", md_content)

        # Footer / Spacer
        # grid.add_row("▍", "") 
        
        self.console.print()
        self.console.print(grid)
        self.console.print()


    # =========================================================================
    # LIVE COMMAND DISPLAY
    # =========================================================================
    
    @contextmanager
    def live_command_context(self, command: str):
        """
        Context manager for live command output streaming.
        """
        buffer = deque(maxlen=5)
        
        def generate_panel(content_lines, is_done=False):
            # HCode "Gutter" Style for Executing Commands
            # ┃ Executing command...
            # ┃ stdout...
            
            # Colors
            gutter_color = "#FF5F00" # Orange for execution/bash-like
            if is_done:
                gutter_color = "#39FF14" # Green for done? Or keep orange?
                # Actually typically execution is orange/yellow then success is green.
            
            gutter = f"[{gutter_color}]┃[/]" # Gutter symbol
            
            # Header
            header = Text()
            header.append("┃ ", style=f"{gutter_color}")
            header.append("Executing ", style=f"bold {gutter_color}")
            
            # Truncate command
            cmd_display = command
            if len(cmd_display) > 60:
                cmd_display = cmd_display[:57] + "..."
            header.append(cmd_display, style="white")
            
            if not is_done:
                header.append(f" {self._icons.LOADING}", style=f"bold {gutter_color}")
                
            # Content
            # Join content lines
            # Limit to last 10 lines for "pane" effect without scrolling too much in Live
            visible_lines = content_lines[-10:] if len(content_lines) > 10 else content_lines
            content_text = Text()
            for line in visible_lines:
                # Add gutter to each line
                content_text.append(f"{gutter}   ", style="")
                content_text.append(line, style="dim white")
                if not line.endswith("\n"):
                    content_text.append("\n")
            
            # Assemble Group/Layout
            # using Group to stack Header + Content
            return Group(header, content_text)

        # Initial render
        with Live(generate_panel([]), console=self.console, refresh_per_second=10) as live:
            
            # Create a simple interface to update the buffer
            class UpdateInterface:
                def update(self, text: str):
                    # Handle newlines properly
                    buffer.append(text)
                    live.update(generate_panel(buffer))
                    
            yield UpdateInterface()
            
            # Final update
            live.update(generate_panel(buffer, is_done=True))

    def display_tool_result(self, tool_name: str, content: str, status: str = "success") -> None:
        """
        Display static tool result in a styled panel.
        
        Args:
            tool_name: Name of the tool (LS, GLOB, etc)
            content: The content/output data
            status: Status for coloring (success, error, warning)
        """
        status_colors = {
            "success": "#39FF14",  # Neon Green
            "error": "#FF0055",    # Neon Red
            "warning": "#FFCC00",  # Gold
        }
        color = status_colors.get(status, "#39FF14")
        
        # Build Title
        title = Text()
        title.append(f"{self._icons.LOGO} ", style=f"bold #00FF88")
        title.append(f"{tool_name} Result", style=f"bold {color}")
        
        # Create Panel
        panel = Panel(
            Text(content, style=self._palette.text_muted if status == "success" else color),
            title=title,
            title_align="left",
            border_style=color,
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True
        )
        
        self.console.print()
        self.console.print(panel)
        self.console.print()

# Singleton instance for global access
_display_instance: Optional[HcodeDisplay] = None


def get_hcode_display(console: Optional[Console] = None) -> HcodeDisplay:
    """Get or create the global HcodeDisplay instance."""
    global _display_instance
    if _display_instance is None:
        _display_instance = HcodeDisplay(console)
    return _display_instance


def reset_display() -> None:
    """Reset the global display instance."""
    global _display_instance
    if _display_instance:
        _display_instance.reset()


__all__ = [
    "HcodeDisplay",
    "TaskMode",
    "FileAction",
    "ProgressUpdate",
    "TrackedFile",
    "get_hcode_display",
    "reset_display",
]
