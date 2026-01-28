"""
Thinking block processing for Hcode agent.

This module handles parsing and display of <thinking> blocks from LLM responses.
Thinking blocks contain the model's structured reasoning process.
"""

import re
from typing import Optional, Tuple, Union

from rich.console import Console

from hcode.core.reasoning import ReasoningParser, StructuredReasoning


class ThinkingBlockProcessor:
    """
    Process and display <thinking> blocks from LLM responses.
    
    The thinking block contains the model's reasoning process, structured
    into phases like perception, comprehension, reasoning, decision, and verification.
    
    Attributes:
        console: Rich console for display output
        debug_mode: If True, show verbose thinking panels
    """

    def __init__(self, console: Console, debug_mode: bool = False):
        """
        Initialize the thinking block processor.
        
        Args:
            console: Rich console for output
            debug_mode: If True, show full verbose panels
        """
        self.console = console
        self.debug_mode = debug_mode
        self._parser = ReasoningParser()

    def parse(self, text: str) -> Tuple[Optional[StructuredReasoning], str]:
        """
        Parse a thinking block from model output.
        
        Uses the central ReasoningParser to extract structured reasoning
        from <thinking> tags in the response.
        
        Args:
            text: The model's response text
            
        Returns:
            Tuple of (StructuredReasoning or None, remaining text without thinking block)
        """
        if "<thinking>" not in text:
            return None, text

        # Extract content inside tags
        pattern = re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL | re.IGNORECASE)
        match = pattern.search(text)

        if match:
            thinking_content = match.group(1).strip()
            # Parse the structured reasoning
            reasoning = self._parser.parse(thinking_content)

            # Remove the thinking block from the text to get the response
            remaining_text = pattern.sub("", text).strip()

            return reasoning, remaining_text

        return None, text

    def is_valid(self, block: Optional[StructuredReasoning]) -> bool:
        """
        Check if thinking block has meaningful content.
        
        A valid thinking block should have at least one populated phase
        or sufficient raw content.
        
        Args:
            block: The parsed thinking block
            
        Returns:
            True if the block contains meaningful reasoning
        """
        if not block:
            return False
        return (
                block.perception.is_complete()
                or block.comprehension.is_complete()
                or block.decision.is_complete()
                or block.analysis.is_complete()
                or len(block.raw_content) > 20
        )

    def get_summary(self, block: StructuredReasoning) -> str:
        """
        Get a summary of the thinking content.
        
        Extracts the most relevant piece of information from the
        structured reasoning block.
        
        Args:
            block: The parsed thinking block
            
        Returns:
            Summary string (not truncated)
        """
        if block.decision.decision:
            return f"Decision: {block.decision.decision}"
        if block.reasoning.hypothesis:
            return f"Hypothesis: {block.reasoning.hypothesis}"
        if block.comprehension.core_understanding:
            return f"Understanding: {block.comprehension.core_understanding}"
        return block.raw_content if block.raw_content else "Empty thinking"

    def display(self, block: StructuredReasoning) -> None:
        """
        Display a thinking block with Hcode style.
        
        Uses the HcodeDisplay system for consistent formatting.
        In debug mode, shows full verbose panel.
        
        Args:
            block: The parsed thinking block to display
        """
        from hcode.ui.hcode_display import get_hcode_display

        # Get display instance
        hcode_display = get_hcode_display(self.console)

        # Determine primary phase from what is populated in the block
        primary_phase = self._determine_primary_phase(block)

        # Build clean thinking content without phase labels
        content = self._build_display_content(block)

        hcode_display.display_thinking_block(
            content=content,
            phase=primary_phase,
            collapsed=False  # Show thinking visibly
        )

        # Update task mode based on phase
        self._update_task_mode(hcode_display, primary_phase)

        # Add progress update from goal/understanding
        if block.comprehension.core_understanding:
            summary = block.comprehension.core_understanding.split('\n')[0].strip()
            # Remove bullet points
            if summary.startswith("- "):
                summary = summary[2:]
            if summary:
                hcode_display.add_progress(summary)

    def _determine_primary_phase(self, block: StructuredReasoning) -> str:
        """Determine the primary phase from the thinking block."""
        if block.verification.is_complete():
            return "VERIFICATION"
        elif block.decision.is_complete():
            return "DECISION"
        elif block.reasoning.is_complete():
            return "REASONING"
        elif block.analysis.is_complete():
            return "ANALYSIS"
        elif block.comprehension.is_complete():
            return "COMPREHENSION"
        else:
            return "THINKING"

    def _build_display_content(self, block: StructuredReasoning) -> str:
        """Build clean thinking content for display."""
        thinking_lines = []

        # Show raw content directly if available (preferred - cleanest output)
        if block.raw_content.strip():
            thinking_lines.append(block.raw_content.strip())
        else:
            # Fallback: combine phase content without labels
            if block.perception.observation:
                thinking_lines.append(block.perception.observation)

            if block.comprehension.core_understanding:
                thinking_lines.append(block.comprehension.core_understanding)

            if block.reasoning.hypothesis:
                thinking_lines.append(block.reasoning.hypothesis)

            if block.decision.decision:
                thinking_lines.append(block.decision.decision)

        # If nothing parsed, show raw content (first 500 chars)
        if not thinking_lines and block.raw_content:
            raw_preview = block.raw_content[:500].strip()
            thinking_lines.append(raw_preview)

        primary_phase = self._determine_primary_phase(block)
        return "\n".join(thinking_lines) if thinking_lines else f"Phase: {primary_phase}"

    def _update_task_mode(self, hcode_display, primary_phase: str) -> None:
        """Update task mode based on reasoning phase."""
        from hcode.ui.hcode_display import TaskMode

        if primary_phase:
            new_mode = None
            if primary_phase in ["PLANNING", "ANALYSIS", "COMPREHENSION", "PERCEPTION"]:
                new_mode = TaskMode.PLANNING
            elif primary_phase in ["EXECUTION", "REASONING", "DECISION"]:
                new_mode = TaskMode.EXECUTION
            elif primary_phase in ["VERIFICATION", "REFLECTION"]:
                new_mode = TaskMode.VERIFICATION

            if new_mode and hcode_display.current_mode and new_mode != hcode_display.current_mode:
                hcode_display.update_mode(new_mode)


# ============================================================================
# Module-level convenience functions (backward compatibility)
# ============================================================================

def parse_thinking_block(text: str) -> Tuple[Optional[StructuredReasoning], str]:
    """
    Parse a thinking block from model output using the central ReasoningParser.
    
    This is a module-level function for backward compatibility.
    Consider using ThinkingBlockProcessor class for new code.
    
    Args:
        text: The model's response text
        
    Returns:
        Tuple of (StructuredReasoning or None, remaining text without thinking block)
    """
    if "<thinking>" not in text:
        return None, text

    parser = ReasoningParser()

    # Extract content inside tags
    pattern = re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL | re.IGNORECASE)
    match = pattern.search(text)

    if match:
        thinking_content = match.group(1).strip()
        # Parse the structured reasoning
        reasoning = parser.parse(thinking_content)

        # Remove the thinking block from the text to get the response
        remaining_text = pattern.sub("", text).strip()

        return reasoning, remaining_text

    return None, text


def is_valid_thinking(block: Optional[StructuredReasoning]) -> bool:
    """Check if thinking block has meaningful content."""
    if not block:
        return False
    return (
            block.perception.is_complete()
            or block.comprehension.is_complete()
            or block.decision.is_complete()
            or block.analysis.is_complete()
            or len(block.raw_content) > 20
    )


def get_thinking_summary(block: StructuredReasoning) -> str:
    """Get a summary of the thinking (no truncation)."""
    if block.decision.decision:
        return f"Decision: {block.decision.decision}"
    if block.reasoning.hypothesis:
        return f"Hypothesis: {block.reasoning.hypothesis}"
    if block.comprehension.core_understanding:
        return f"Understanding: {block.comprehension.core_understanding}"
    return block.raw_content if block.raw_content else "Empty thinking"


def format_thinking_display(
        block: Union[StructuredReasoning], console: Console, debug_mode: bool = False
) -> None:
    """
    Display a thinking block with Hcode style.
    
    This is a module-level function for backward compatibility.
    Consider using ThinkingBlockProcessor class for new code.
    
    Args:
        block: The parsed thinking block (StructuredReasoning)
        console: Rich console for output
        debug_mode: If True, show full verbose panel
    """
    processor = ThinkingBlockProcessor(console, debug_mode=debug_mode)
    processor.display(block)
