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
        """Build structured markdown content for display."""
        sections = []

        # Safe icon getter
        try:
            from hcode.ui.icons import Icons
            search_icon = Icons.SEARCH
            brain_icon = Icons.BRAIN
            flash_icon = Icons.LIGHTNING
            gear_icon = Icons.GEAR
            idea_icon = Icons.STAR
            shield_icon = Icons.CHECK
        except ImportError:
            search_icon = "SEARCH"
            brain_icon = "BRAIN"
            flash_icon = "ANALYSIS"
            gear_icon = "REASONING"
            idea_icon = "DECISION"
            shield_icon = "VERIFY"

        # 1. Perception
        if block.perception.is_complete():
            sections.append(f"### {search_icon} Perception")
            if block.perception.observation:
                sections.append(f"**Observation:** {block.perception.observation}")
            if block.perception.implicit_needs:
                sections.append("**Implicit Needs:**")
                for need in block.perception.implicit_needs:
                    sections.append(f"- {need}")

        # 2. Comprehension
        if block.comprehension.is_complete():
            sections.append(f"### {brain_icon} Comprehension")
            if block.comprehension.core_understanding:
                sections.append(block.comprehension.core_understanding)
            if block.comprehension.assumptions:
                sections.append("**Assumptions:**")
                for assumption in block.comprehension.assumptions:
                    sections.append(f"- {assumption}")

        # 3. Analysis
        if block.analysis.is_complete():
            sections.append(f"### {flash_icon} Analysis")
            if block.analysis.decomposition:
                sections.append("**Decomposition:**")
                for step in block.analysis.decomposition:
                    sections.append(f"- {step}")
            if block.analysis.options:
                sections.append("**Options:**")
                for opt in block.analysis.options:
                    desc = opt.get('description', str(opt))
                    sections.append(f"- {desc}")

        # 4. Reasoning
        if block.reasoning.is_complete():
            sections.append(f"### {gear_icon} Reasoning")
            if block.reasoning.hypothesis:
                sections.append(f"**Hypothesis:** {block.reasoning.hypothesis}")
            if block.reasoning.logical_chain:
                pass
            if block.reasoning.evidence_for:
                sections.append("**Supporting Evidence:**")
                for ev in block.reasoning.evidence_for:
                    sections.append(f"- {ev}")

        # 5. Decision
        if block.decision.is_complete():
            sections.append(f"### {idea_icon} Decision")
            sections.append(f"**{block.decision.decision}**")
            if block.decision.justification:
                sections.append(f"_{block.decision.justification}_")
            if block.decision.action_items:
                sections.append("**Action Items:**")
                for item in block.decision.action_items:
                    sections.append(f"- {item}")

        # 6. Verification
        if block.verification.is_complete():
            sections.append(f"### {shield_icon} Verification")
            if block.verification.safety_check:
                sections.append(f"**Safety:** {block.verification.safety_check}")
            if block.verification.potential_issues:
                sections.append("**Risks:**")
                for risk in block.verification.potential_issues:
                    sections.append(f"- {risk}")

        # Fallback
        if not sections and block.raw_content:
            sections.append(block.raw_content.strip())
        elif len(sections) == 0:
            sections.append("_Processing..._")

        self._determine_primary_phase(block)
        return "\n\n".join(sections)

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
