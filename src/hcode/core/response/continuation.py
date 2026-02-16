"""
Automatic continuation system for Hcode.

Handles long outputs by automatically continuing generation when:
1. Model output is truncated (finish_reason = "length")
2. Context is about to exceed limits

Similar to Claude Code's seamless long-form generation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any




class ContinuationManager:
    """
    Manages automatic continuation for long outputs.

    When a model response is truncated due to max_tokens, this manager
    automatically continues the generation by:
    1. Detecting truncation (finish_reason = "length")
    2. Adding a continuation prompt
    3. Merging responses seamlessly
    """


    def __init__(
        self,
        max_continuations: int = None,
        max_total_tokens: int = None,
        console: Optional[Any] = None,
    ):
        """
        Initialize ContinuationManager.

        Args:
            max_continuations: Maximum number of continuation attempts (from config if None)
            max_total_tokens: Maximum total tokens across all continuations (from config if None)
            console: Rich console for output
        """
        # Load from config if not provided
        from hcode.config.prompts import get_models_config

        config = get_models_config().get_continuation_config()

        self.max_continuations = (
            max_continuations if max_continuations is not None else config.max_continuations
        )
        self.max_total_tokens = (
            max_total_tokens if max_total_tokens is not None else config.max_total_tokens
        )
        self.console = console



    def should_continue(self, finish_reason: str, response_text: str) -> bool:
        """
        Determine if we should continue generation.

        Args:
            finish_reason: The finish reason from API
            response_text: The generated text

        Returns:
            True if we should continue
        """
        # Check finish reason
        if finish_reason == "length":
            return True

        # Check for incomplete markers at end of response
        response_stripped = response_text.rstrip()

        # Check for unclosed code blocks
        if response_stripped.count("```") % 2 == 1:
            return True

        # Check for obvious truncation patterns
        truncation_patterns = [
            # Mid-sentence truncation
            response_stripped.endswith(","),
            response_stripped.endswith(" and"),
            response_stripped.endswith(" or"),
            response_stripped.endswith(" the"),
            response_stripped.endswith(" a"),
            response_stripped.endswith(" an"),
            response_stripped.endswith(" to"),
            response_stripped.endswith(" is"),
            response_stripped.endswith(" are"),
            response_stripped.endswith(" was"),
            response_stripped.endswith(" were"),
            response_stripped.endswith(" will"),
            response_stripped.endswith(" be"),
            response_stripped.endswith(":"),
            # JSON truncation
            response_stripped.endswith('": "'),
            response_stripped.endswith('": {'),
            response_stripped.endswith('": ['),
        ]

        if any(truncation_patterns):
            return True

        return False




class ContextWindowManager:
    """
    Manages context window to prevent exceeding limits.

    Implements strategies like:
    1. Smart truncation based on importance
    2. Automatic summarization of old context
    3. Token budget allocation
    """

    def __init__(
        self,
        max_context_tokens: int = 128000,
        reserve_output_tokens: int = 4096,
        summarization_threshold: float = 0.8,
    ):
        """
        Initialize ContextWindowManager.

        Args:
            max_context_tokens: Maximum context window size
            reserve_output_tokens: Tokens to reserve for output
            summarization_threshold: Trigger summarization at this % of context
        """
        self.max_context_tokens = max_context_tokens
        self.reserve_output_tokens = reserve_output_tokens
        self.summarization_threshold = summarization_threshold

