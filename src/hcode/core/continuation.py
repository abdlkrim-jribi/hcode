"""
Automatic continuation system for Hcode.

Handles long outputs by automatically continuing generation when:
1. Model output is truncated (finish_reason = "length")
2. Context is about to exceed limits

Similar to Claude Code's seamless long-form generation.
"""

import asyncio
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


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
        from ..config.prompts import get_models_config

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
        from ..config.prompts import get_prompts_config

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

        if len(responses) == 1:
            return responses[0]

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

    def create_state(self, original_request: str) -> ContinuationState:
        """
        Create initial continuation state.

        Args:
            original_request: The original user request

        Returns:
            New ContinuationState
        """
        self.state = ContinuationState(
            original_request=original_request,
            accumulated_response="",
            continuation_count=0,
            total_input_tokens=0,
            total_output_tokens=0,
            is_complete=False,
            finish_reason=FinishReason.STOP,
        )
        return self.state

    def update_state(
        self, response_text: str, finish_reason: str, input_tokens: int, output_tokens: int
    ) -> ContinuationState:
        """
        Update continuation state after a response.

        Args:
            response_text: The response text
            finish_reason: Finish reason from API
            input_tokens: Input tokens used
            output_tokens: Output tokens generated

        Returns:
            Updated state
        """
        if not self.state:
            raise ValueError("No continuation state. Call create_state first.")

        # Update accumulated response
        if self.state.accumulated_response:
            self.state.accumulated_response = self.merge_responses(
                [self.state.accumulated_response, response_text]
            )
        else:
            self.state.accumulated_response = response_text

        self.state.continuation_count += 1
        self.state.total_input_tokens += input_tokens
        self.state.total_output_tokens += output_tokens

        # Determine if complete
        if finish_reason == "length":
            self.state.finish_reason = FinishReason.LENGTH
            self.state.is_complete = False
        elif finish_reason == "tool_calls":
            self.state.finish_reason = FinishReason.TOOL_CALLS
            self.state.is_complete = False  # Tool calls need processing
        else:
            self.state.finish_reason = FinishReason.STOP
            self.state.is_complete = True

        # Check limits
        if self.state.continuation_count >= self.max_continuations:
            self.state.is_complete = True
            if self.console:
                self.console.print(
                    f"[yellow]⚠ Reached max continuations ({self.max_continuations})[/yellow]"
                )

        if self.state.total_tokens >= self.max_total_tokens:
            self.state.is_complete = True
            if self.console:
                self.console.print(
                    f"[yellow]⚠ Reached max total tokens ({self.max_total_tokens:,})[/yellow]"
                )

        return self.state

    def get_continuation_messages(self, context_messages: List[Any]) -> List[Any]:
        """
        Get messages for continuation request.

        Args:
            context_messages: Current context messages

        Returns:
            Messages with continuation prompt added
        """
        if not self.state:
            return context_messages

        from ..providers import Message

        # Add the accumulated response as assistant message
        messages = list(context_messages)

        if self.state.accumulated_response:
            messages.append(Message(role="assistant", content=self.state.accumulated_response))

        # Add continuation prompt
        continuation_prompt = self.get_continuation_prompt(self.state.continuation_count)
        messages.append(Message(role="user", content=continuation_prompt))

        return messages

    def display_continuation_status(self):
        """Display current continuation status"""
        if not self.state or not self.console:
            return

        self.console.print(
            f"[dim]↳ Continuation {self.state.continuation_count} "
            f"({self.state.total_output_tokens:,} tokens generated)[/dim]"
        )


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

    def calculate_token_budget(
        self, system_tokens: int, history_tokens: int, new_message_tokens: int
    ) -> Dict[str, int]:
        """
        Calculate token budget allocation.

        Args:
            system_tokens: Tokens in system prompt
            history_tokens: Tokens in conversation history
            new_message_tokens: Tokens in new user message

        Returns:
            Budget allocation dictionary
        """
        total_input = system_tokens + history_tokens + new_message_tokens
        remaining = self.available_input_tokens - total_input

        return {
            "system": system_tokens,
            "history": history_tokens,
            "new_message": new_message_tokens,
            "total_input": total_input,
            "available": self.available_input_tokens,
            "remaining": remaining,
            "output_reserved": self.reserve_output_tokens,
            "needs_truncation": remaining < 0,
        }

    def needs_summarization(self, current_tokens: int) -> bool:
        """
        Check if context needs summarization.

        Args:
            current_tokens: Current total tokens

        Returns:
            True if summarization is needed
        """
        threshold_tokens = self.available_input_tokens * self.summarization_threshold
        return current_tokens >= threshold_tokens

    def get_safe_max_tokens(self, current_input_tokens: int) -> int:
        """
        Get safe max_tokens for output.

        Args:
            current_input_tokens: Current input token count

        Returns:
            Safe max_tokens value
        """
        remaining = self.max_context_tokens - current_input_tokens

        # Leave some buffer
        safe_max = min(remaining - 100, self.reserve_output_tokens)

        return max(safe_max, 1000)  # Minimum 1000 tokens for output
