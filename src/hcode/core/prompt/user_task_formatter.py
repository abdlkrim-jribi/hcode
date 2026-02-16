"""
User task formatting for Hcode agent.

This module handles formatting user tasks with output format instructions
and proper structure for the LLM.
"""

from typing import Optional

from hcode.config.core_prompts.core import CorePromptLoader


class UserTaskFormatter:
    """
    Format user tasks for LLM consumption.

    Wraps user tasks with appropriate instructions for output format,
    tool usage hints, and task completion expectations.
    """

    def __init__(self, include_output_format: bool = True):
        """
        Initialize the user task formatter.

        Args:
            include_output_format: Whether to include output format instructions
        """
        self.include_output_format = include_output_format
        self._loader = CorePromptLoader()

    @property
    def OUTPUT_FORMAT(self) -> str:
        """Get the output format instructions from config."""
        return self._loader.get_output_format("default")

    def format(self, task: str, context: Optional[str] = None) -> str:
        """
        Format a user task for the LLM.
        
        Args:
            task: The raw user task
            context: Optional additional context
            
        Returns:
            Formatted task string
        """
        formatted = f"<user_task>\n{task}\n</user_task>"

        if context:
            formatted = f"<context>\n{context}\n</context>\n\n{formatted}"

        if self.include_output_format:
            formatted = formatted + "\n\n" + self.OUTPUT_FORMAT

        return formatted
