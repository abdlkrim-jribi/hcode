"""
Thinking Display Manager for HCode Agent.

Displays agent's thinking and reasoning in real-time with Claude Code-style formatting.
Shows "Thought for Xs" timer, reasoning phases, and progress updates.
"""

import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..agent.reasoning import ReasoningPhase


class ThinkingDisplayManager:
    """
    Manages real-time display of agent thinking and reasoning.
    
    Features:
    - Live "Thought for Xs" timer
    - Phase-by-phase reasoning display
    - Progress indicators with checkmarks
    - Rich formatted output
    """
    
    # Phase display configuration
    PHASE_NAMES = {
        ReasoningPhase.PERCEPTION: "Perception",
        ReasoningPhase.COMPREHENSION: "Comprehension",
        ReasoningPhase.ANALYSIS: "Analysis",
        ReasoningPhase.REASONING: "Reasoning",
        ReasoningPhase.CHANGE_IMPACT: "Change Impact",
        ReasoningPhase.DECISION: "Decision",
        ReasoningPhase.PRE_EXECUTION_REVIEW: "Pre-Execution Review",
        ReasoningPhase.VERIFICATION: "Verification",
    }
    
    PHASE_ICONS = {
        ReasoningPhase.PERCEPTION: "👁️",
        ReasoningPhase.COMPREHENSION: "🧠",
        ReasoningPhase.ANALYSIS: "🔍",
        ReasoningPhase.REASONING: "💭",
        ReasoningPhase.CHANGE_IMPACT: "⚡",
        ReasoningPhase.DECISION: "✨",
        ReasoningPhase.PRE_EXECUTION_REVIEW: "📋",
        ReasoningPhase.VERIFICATION: "✅",
    }
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize thinking display manager.
        
        Args:
            console: Rich console for output (creates if None)
        """
        self.console = console or Console()
        self.start_time: Optional[float] = None
        self.completed_phases: set = set()
        self.current_phase: Optional[ReasoningPhase] = None
    
    def start_thinking(self, message: str = "Thinking...") -> None:
        """
        Show start of thinking with simple message.
        
        Args:
            message: Message to display
        """
        self.start_time = time.time()
        self.console.print()
        self.console.print(f"🧠 {message}", style="dim italic")
        self.console.print()
    
    @contextmanager
    def show_thinking_timer(self):
        """
        Context manager to show "Thought for Xs" timer.
        
        Usage:
            with thinking_mgr.show_thinking_timer():
                # Do reasoning...
                pass
        """
        self.start_time = time.time()
        
        # Show initial message
        self.console.print()
        self.console.print("🧠 Thinking...", style="dim italic")
        
        try:
            yield
        finally:
            # Show completion time
            if self.start_time:
                duration = time.time() - self.start_time
                self.console.print()
                self.console.print(
                    f"💡 Thought for {duration:.1f}s",
                    style="dim italic"
                )
    
    def show_phase_start(self, phase: ReasoningPhase) -> None:
        """
        Display start of a reasoning phase.
        
        Args:
            phase: Reasoning phase starting
        """
        self.current_phase = phase
        
        icon = self.PHASE_ICONS.get(phase, "•")
        name = self.PHASE_NAMES.get(phase, phase.value)
        
        # Create phase header
        self.console.print()
        self.console.print(
            f"┌─ {icon} Phase: {name} " + "─" * (40 - len(name)),
            style="blue"
        )
    
    def show_phase_complete(
        self,
        phase: ReasoningPhase,
        output: Any,
        show_details: bool = True
    ) -> None:
        """
        Display completion of a reasoning phase.
        
        Args:
            phase: Reasoning phase completed
            output: Phase output (PerceptionOutput, ComprehensionOutput, etc.)
            show_details: Whether to show phase details
        """
        self.completed_phases.add(phase)
        
        if show_details and output:
            # Extract key information from output
            details = self._extract_phase_details(phase, output)
            
            for detail in details:
                self.console.print(f"│ ✓ {detail}", style="dim")
        
        # Close phase box
        self.console.print("└" + "─" * 45, style="blue")
    
    def show_completion(self, duration: float) -> None:
        """
        Show thinking completion message.
        
        Args:
            duration: Thinking duration in seconds
        """
        self.console.print()
        self.console.print(
            f"✓ Thinking complete ({duration:.1f}s)",
            style="bold green"
        )
        self.console.print()
    
    def show_phase_summary(self) -> None:
        """Show summary of completed phases."""
        if not self.completed_phases:
            return
        
        table = Table(title="Reasoning Phases", show_header=False)
        
        for phase in self.PHASE_NAMES.keys():
            icon = self.PHASE_ICONS.get(phase, "•")
            name = self.PHASE_NAMES.get(phase, phase.value)
            status = "✓" if phase in self.completed_phases else "○"
            
            style = "green" if phase in self.completed_phases else "dim"
            table.add_row(f"{status} {icon} {name}", style=style)
        
        self.console.print(table)
    
    def _extract_phase_details(
        self,
        phase: ReasoningPhase,
        output: Any
    ) -> list[str]:
        """
        Extract key details from phase output for display.
        
        Args:
            phase: Reasoning phase
            output: Phase output object
            
        Returns:
            List of detail strings to display
        """
        details = []
        
        try:
            if phase == ReasoningPhase.PERCEPTION and hasattr(output, 'observation'):
                if output.observation:
                    details.append(f"Observation: {output.observation}")
                if output.implicit_needs:
                    details.append(f"Identified {len(output.implicit_needs)} implicit needs")

            elif phase == ReasoningPhase.COMPREHENSION and hasattr(output, 'core_understanding'):
                if output.core_understanding:
                    details.append(f"Understanding: {output.core_understanding}")
                if output.assumptions:
                    details.append(f"{len(output.assumptions)} assumptions made")

            elif phase == ReasoningPhase.ANALYSIS and hasattr(output, 'decomposition'):
                if output.decomposition:
                    details.append(f"Broke into {len(output.decomposition)} steps")
                if output.options:
                    details.append(f"Identified {len(output.options)} options")

            elif phase == ReasoningPhase.DECISION and hasattr(output, 'decision'):
                if output.decision:
                    details.append(f"Decision: {output.decision}")
                if hasattr(output, 'confidence'):
                    details.append(f"Confidence: {output.confidence:.0%}")
            
            elif phase == ReasoningPhase.CHANGE_IMPACT and hasattr(output, 'files_affected'):
                if output.files_affected:
                    details.append(f"{len(output.files_affected)} files affected")
                if output.breaking_changes:
                    details.append(f"⚠️  {len(output.breaking_changes)} breaking changes")
            
            elif phase == ReasoningPhase.VERIFICATION and hasattr(output, 'validation_steps'):
                if output.validation_steps:
                    details.append(f"{len(output.validation_steps)} validation steps")
                if hasattr(output, 'ready_to_execute'):
                    status = "Ready" if output.ready_to_execute else "Not ready"
                    details.append(f"Status: {status}")
        
        except Exception:
            # If extraction fails, just show generic completion
            details.append("Phase completed")
        
        return details if details else ["Phase completed"]


def display_task_boundary(
    task_name: str,
    mode: str,
    console: Optional[Console] = None
) -> None:
    """
    Display task boundary header.
    
    Args:
        task_name: Name of the task
        mode: Agent mode (PLANNING/EXECUTION/VERIFICATION)
        console: Rich console for output
    """
    console = console or Console()
    
    mode_colors = {
        "PLANNING": "blue",
        "planning": "blue",
        "EXECUTION": "green",
        "execution": "green",
        "VERIFICATION": "yellow",
        "verification": "yellow",
    }
    
    color = mode_colors.get(mode, "white")
    
    console.print()
    console.print("━" * 60, style=color)
    console.print(f"Task: {task_name}", style=f"bold {color}")
    console.print(f"Mode: {mode.upper()}", style=color)
    console.print("━" * 60, style=color)
    console.print()


def display_reasoning_summary(
    reasoning: Any,
    console: Optional[Console] = None
) -> None:
    """
    Display summary of reasoning results.
    
    Args:
        reasoning: StructuredReasoning object
        console: Rich console for output
    """
    console = console or Console()
    
    # Build summary content
    content_parts = []
    
    # Decision
    if hasattr(reasoning, 'decision') and reasoning.decision.decision:
        content_parts.append(
            f"[bold]Decision:[/bold] {reasoning.decision.decision}"
        )
    
    # Action items
    if hasattr(reasoning, 'decision') and reasoning.decision.action_items:
        items = reasoning.decision.action_items[:5]  # Limit to 5
        items_str = "\n".join(f"  • {item}" for item in items)
        content_parts.append(f"[bold]Action Items:[/bold]\n{items_str}")
    
    # Confidence
    if hasattr(reasoning, 'get_confidence'):
        conf = reasoning.get_confidence()
        content_parts.append(f"[bold]Confidence:[/bold] {conf:.0%}")
    
    # Files affected
    if hasattr(reasoning, 'change_impact') and reasoning.change_impact.files_affected:
        num_files = len(reasoning.change_impact.files_affected)
        content_parts.append(f"[bold]Files Affected:[/bold] {num_files}")
    
    # Create panel
    if content_parts:
        panel = Panel(
            "\n\n".join(content_parts),
            title="💡 Reasoning Summary",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(panel)
        console.print()


class SimpleThinkingDisplay:
    """
    Minimal thinking display matching Claude Code style.

    Shows thinking as plain inline text without decoration.
    No boxes, no phase names, no colors, no icons (except 💭 for collapsed).
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize simple thinking display.

        Args:
            console: Rich console for output (creates if None)
        """
        self.console = console or Console()

    def show_thinking(self, content: str):
        """
        Display thinking inline as plain text.

        Args:
            content: The thinking content
        """
        if not content:
            return

        self.console.print()
        # Just print plain text, slightly dimmed
        for line in content.split('\n'):
            if line.strip():
                self.console.print(line, style="dim")
        self.console.print()

    def show_thinking_collapsed(self):
        """Display collapsed thinking indicator."""
        self.console.print("💭 Thinking...", style="dim italic")

    def show_thinking_block(self, content: str):
        """
        Display a block of thinking without any formatting.

        Args:
            content: The thinking content block
        """
        self.show_thinking(content)


__all__ = [
    "ThinkingDisplayManager",
    "SimpleThinkingDisplay",
    "display_task_boundary",
    "display_reasoning_summary",
]
