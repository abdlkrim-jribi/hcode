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


class FinishReason(Enum):
    """Reasons for generation stopping"""

    STOP = "stop"  # Natural completion
    LENGTH = "length"  # Hit max_tokens limit
    TOOL_CALLS = "tool_calls"  # Stopped for tool execution
    CONTENT_FILTER = "content_filter"  # Content filtered
    ERROR = "error"  # Error occurred


@dataclass
class ContinuationState:
    """State for tracking continuation across API calls"""

    original_request: str
    accumulated_response: str
    continuation_count: int
    total_input_tokens: int
    total_output_tokens: int
    is_complete: bool
    finish_reason: FinishReason

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens


class ContinuationManager:
    """
    Manages automatic continuation for long outputs.

    When a model response is truncated due to max_tokens, this manager
    automatically continues the generation by:
    1. Detecting truncation (finish_reason = "length")
    2. Adding a continuation prompt
    3. Merging responses seamlessly
    """

    # Markers that indicate incomplete output
    INCOMPLETE_MARKERS = [
        # Code blocks
        "```",  # Unclosed code block
        # HTML/XML tags
        "<",  # Unclosed tag
        # JSON/Objects
        "{",  # Unclosed brace
        "[",  # Unclosed bracket
        # Strings
        '"',  # Unclosed quote
        "'",  # Unclosed single quote
    ]

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
        self.state: Optional[ContinuationState] = None

        # Load truncation patterns from config
        self._truncation_patterns = config.truncation_patterns if config.truncation_patterns else []

    def _get_continuation_prompts(self) -> List[str]:
        """Get continuation prompts from external config"""
        from hcode.config.prompts import get_prompts_config

        return get_prompts_config().get_continuation_prompts()

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

    def get_continuation_prompt(self, continuation_count: int) -> str:
        """
        Get the appropriate continuation prompt from external config.

        Args:
            continuation_count: How many continuations we've done

        Returns:
            Continuation prompt string
        """
        # Get prompts from config
        prompts = self._get_continuation_prompts()
        # Rotate through prompts to avoid repetition
        idx = continuation_count % len(prompts)
        return prompts[idx]

    def merge_responses(self, responses: List[str]) -> str:
        """
        Merge multiple continuation responses into one coherent output.

        Args:
            responses: List of response strings

        Returns:
            Merged response
        """
        if not responses:
            return ""

        merged = responses[0]

        for response in responses[1:]:
            # Remove any "continuation" acknowledgment from the model
            cleaned = self._clean_continuation_response(response)

            # Check for overlap and merge
            merged = self._smart_merge(merged, cleaned)

        return merged

    def _clean_continuation_response(self, response: str) -> str:
        """
        Remove continuation acknowledgments from response.

        Args:
            response: Raw continuation response

        Returns:
            Cleaned response
        """
        # Common patterns models add when continuing
        cleanup_patterns = [
            "Continuing from where I left off:",
            "Continuing:",
            "Here's the continuation:",
            "Picking up where I left off:",
            "Resuming:",
            "...continuing...",
        ]

        cleaned = response.strip()

        for pattern in cleanup_patterns:
            if cleaned.lower().startswith(pattern.lower()):
                cleaned = cleaned[len(pattern) :].strip()

        return cleaned

    def _smart_merge(self, first: str, second: str) -> str:
        """
        Intelligently merge two strings, handling overlaps.

        Args:
            first: First string
            second: Second string

        Returns:
            Merged string
        """
        # Check for overlap at the boundary
        # Look for the last few words of first in the start of second

        first_words = first.split()
        second_words = second.split()

        if not first_words or not second_words:
            return first + second

        # Try to find overlap (up to 10 words)
        max_overlap = min(10, len(first_words), len(second_words))

        for overlap_size in range(max_overlap, 0, -1):
            first_end = first_words[-overlap_size:]
            second_start = second_words[:overlap_size]

            if first_end == second_start:
                # Found overlap, merge without duplication
                return " ".join(first_words + second_words[overlap_size:])

        # No overlap found, simple concatenation
        # Add appropriate separator based on context
        if first.rstrip().endswith((".", "!", "?", ":", ";")):
            return first.rstrip() + "\n" + second.lstrip()
        elif first.rstrip().endswith(","):
            return first.rstrip() + " " + second.lstrip()
        else:
            return first.rstrip() + " " + second.lstrip()


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

        self.available_input_tokens = max_context_tokens - reserve_output_tokens
