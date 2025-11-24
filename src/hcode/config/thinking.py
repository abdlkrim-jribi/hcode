"""
Thinking configuration for extended reasoning.

Matches Claude Code's thinking behavior for complex tasks.
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class ThinkingMode(Enum):
    """Thinking modes matching Claude Code"""
    DISABLED = "disabled"           # No extended thinking
    AUTO = "auto"                   # Automatically decide when to think
    ALWAYS = "always"               # Always use extended thinking
    ON_COMPLEX = "on_complex"       # Only for complex tasks


class ThinkingVisibility(Enum):
    """How thinking is displayed"""
    HIDDEN = "hidden"               # Don't show thinking
    SUMMARY = "summary"             # Show summary only
    STREAMING = "streaming"         # Stream thinking in real-time
    FULL = "full"                   # Show complete thinking after


@dataclass
class ThinkingConfig:
    """
    Configuration for extended thinking.

    Matches Claude Code's thinking behavior.
    """
    # Enable extended thinking
    enabled: bool = True

    # When to use extended thinking
    mode: ThinkingMode = ThinkingMode.AUTO

    # How to display thinking
    visibility: ThinkingVisibility = ThinkingVisibility.STREAMING

    # Token budget for thinking
    budget_tokens: int = 10000

    # Minimum tokens before showing thinking
    min_display_tokens: int = 100

    # Phrases that trigger extended thinking
    trigger_phrases: List[str] = field(default_factory=lambda: [
        "think carefully",
        "step by step",
        "think through",
        "analyze",
        "complex",
        "difficult",
        "tricky",
        "figure out",
        "reason about",
        "work through",
        "plan",
        "strategy",
        "architecture",
        "design",
        "refactor",
        "debug",
        "optimize",
        "security",
        "performance"
    ])

    # Complexity indicators that trigger thinking
    complexity_indicators: List[str] = field(default_factory=lambda: [
        "multiple files",
        "entire codebase",
        "refactor",
        "migration",
        "architecture",
        "system design",
        "integration",
        "security audit",
        "performance optimization",
        "bug that",
        "error in",
        "failing test",
        "implement feature"
    ])

    # Tool count threshold to trigger thinking
    tool_threshold: int = 3

    def should_think(self, message: str, estimated_tools: int = 0) -> bool:
        """
        Determine if extended thinking should be used.

        Args:
            message: User message
            estimated_tools: Estimated number of tool calls needed

        Returns:
            True if should use extended thinking
        """
        if self.mode == ThinkingMode.DISABLED:
            return False

        if self.mode == ThinkingMode.ALWAYS:
            return True

        message_lower = message.lower()

        # Check trigger phrases
        for phrase in self.trigger_phrases:
            if phrase in message_lower:
                return True

        # Check complexity indicators
        for indicator in self.complexity_indicators:
            if indicator in message_lower:
                return True

        # Check tool threshold
        if estimated_tools >= self.tool_threshold:
            return True

        # Check message length (long messages often need more thought)
        if len(message) > 500:
            return True

        return False
