"""
Test automatic continuation system for long outputs.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hcode.core.continuation import (
    ContinuationManager,
    ContextWindowManager,
    ContinuationState,
    FinishReason
)


class TestContinuationManager:
    """Test the ContinuationManager class"""

    def test_initialization(self):
        """Test basic initialization"""
        manager = ContinuationManager()
        assert manager.max_continuations == 20
        assert manager.max_total_tokens == 200000
        assert manager.state is None

    def test_should_continue_on_length(self):
        """Test continuation detection on finish_reason=length"""
        manager = ContinuationManager()

        assert manager.should_continue("length", "any text") is True
        assert manager.should_continue("stop", "complete sentence.") is False

    def test_should_continue_unclosed_code_block(self):
        """Test detection of unclosed code blocks"""
        manager = ContinuationManager()

        # Unclosed code block should trigger continuation
        assert manager.should_continue("stop", "Here is code:\n```python\ndef foo():") is True

        # Closed code block should not
        assert manager.should_continue("stop", "Here is code:\n```python\ndef foo():\n    pass\n```") is False

    def test_should_continue_truncation_patterns(self):
        """Test detection of truncation patterns"""
        manager = ContinuationManager()

        # Mid-sentence truncation
        assert manager.should_continue("stop", "The function takes a") is True
        assert manager.should_continue("stop", "We need to and") is True
        assert manager.should_continue("stop", "This is the") is True
        assert manager.should_continue("stop", "Let me explain:") is True

        # Complete sentences should not continue
        assert manager.should_continue("stop", "This is complete.") is False
        assert manager.should_continue("stop", "Done!") is False

    def test_get_continuation_prompt(self):
        """Test continuation prompt rotation"""
        manager = ContinuationManager()

        prompts = [
            manager.get_continuation_prompt(0),
            manager.get_continuation_prompt(1),
            manager.get_continuation_prompt(2),
            manager.get_continuation_prompt(3),  # Should wrap around
        ]

        # Should have different prompts
        assert len(set(prompts[:3])) == 3
        # Should rotate
        assert prompts[0] == prompts[3]

    def test_merge_responses_simple(self):
        """Test simple response merging"""
        manager = ContinuationManager()

        responses = ["Hello world.", "This is more content."]
        merged = manager.merge_responses(responses)

        assert "Hello world" in merged
        assert "This is more content" in merged

    def test_merge_responses_with_overlap(self):
        """Test response merging with overlap detection"""
        manager = ContinuationManager()

        # Simulate overlap where model repeated end of previous output
        responses = [
            "First part of the response with some words at the end",
            "words at the end and then new content continues here"
        ]
        merged = manager.merge_responses(responses)

        # Should not have duplicate "words at the end"
        assert merged.count("words at the end") == 1

    def test_clean_continuation_response(self):
        """Test cleaning of continuation acknowledgments"""
        manager = ContinuationManager()

        # Test various continuation acknowledgments
        test_cases = [
            ("Continuing from where I left off: actual content", "actual content"),
            ("Here's the continuation: more stuff", "more stuff"),
            ("Picking up where I left off: data", "data"),
            ("Normal response without prefix", "Normal response without prefix"),
        ]

        for input_text, expected in test_cases:
            cleaned = manager._clean_continuation_response(input_text)
            assert cleaned == expected

    def test_create_state(self):
        """Test state creation"""
        manager = ContinuationManager()
        state = manager.create_state("Write a long story")

        assert state.original_request == "Write a long story"
        assert state.accumulated_response == ""
        assert state.continuation_count == 0
        assert state.is_complete is False

    def test_update_state(self):
        """Test state updates"""
        manager = ContinuationManager()
        manager.create_state("test request")

        # First response - truncated
        state = manager.update_state(
            response_text="First part of response",
            finish_reason="length",
            input_tokens=100,
            output_tokens=500
        )

        assert state.accumulated_response == "First part of response"
        assert state.continuation_count == 1
        assert state.total_input_tokens == 100
        assert state.total_output_tokens == 500
        assert state.is_complete is False
        assert state.finish_reason == FinishReason.LENGTH

        # Second response - complete
        state = manager.update_state(
            response_text="Second part completes.",
            finish_reason="stop",
            input_tokens=150,
            output_tokens=300
        )

        assert state.continuation_count == 2
        assert state.total_input_tokens == 250
        assert state.total_output_tokens == 800
        assert state.is_complete is True
        assert state.finish_reason == FinishReason.STOP


class TestContextWindowManager:
    """Test the ContextWindowManager class"""

    def test_initialization(self):
        """Test basic initialization"""
        manager = ContextWindowManager(
            max_context_tokens=128000,
            reserve_output_tokens=4096
        )

        assert manager.max_context_tokens == 128000
        assert manager.reserve_output_tokens == 4096
        assert manager.available_input_tokens == 128000 - 4096

    def test_calculate_token_budget(self):
        """Test token budget calculation"""
        manager = ContextWindowManager(
            max_context_tokens=10000,
            reserve_output_tokens=2000
        )

        budget = manager.calculate_token_budget(
            system_tokens=500,
            history_tokens=3000,
            new_message_tokens=200
        )

        assert budget["system"] == 500
        assert budget["history"] == 3000
        assert budget["new_message"] == 200
        assert budget["total_input"] == 3700
        assert budget["available"] == 8000  # 10000 - 2000
        assert budget["remaining"] == 4300  # 8000 - 3700
        assert budget["needs_truncation"] is False

    def test_calculate_token_budget_needs_truncation(self):
        """Test budget when truncation is needed"""
        manager = ContextWindowManager(
            max_context_tokens=5000,
            reserve_output_tokens=1000
        )

        budget = manager.calculate_token_budget(
            system_tokens=500,
            history_tokens=4000,  # Too much history
            new_message_tokens=200
        )

        assert budget["needs_truncation"] is True
        assert budget["remaining"] < 0

    def test_needs_summarization(self):
        """Test summarization threshold detection"""
        manager = ContextWindowManager(
            max_context_tokens=10000,
            reserve_output_tokens=2000,
            summarization_threshold=0.8
        )

        # available = 8000, threshold = 6400
        assert manager.needs_summarization(5000) is False
        assert manager.needs_summarization(6500) is True
        assert manager.needs_summarization(8000) is True

    def test_get_safe_max_tokens(self):
        """Test safe max_tokens calculation"""
        manager = ContextWindowManager(
            max_context_tokens=10000,
            reserve_output_tokens=4000
        )

        # With 5000 input tokens
        safe = manager.get_safe_max_tokens(5000)
        assert safe <= 10000 - 5000 - 100  # Must leave buffer
        assert safe >= 1000  # Minimum

        # With very high input tokens
        safe = manager.get_safe_max_tokens(9500)
        assert safe == 1000  # Should return minimum


class TestContinuationIntegration:
    """Integration tests for continuation system"""

    def test_full_continuation_flow(self):
        """Test full continuation flow"""
        manager = ContinuationManager(max_continuations=5)

        # Create initial state
        state = manager.create_state("Write a comprehensive guide")

        # Simulate multiple continuations
        responses = [
            ("Part 1: Introduction to the topic", "length"),
            ("Part 2: Main content continues here", "length"),
            ("Part 3: Conclusion. The end.", "stop"),
        ]

        for response_text, finish_reason in responses:
            state = manager.update_state(
                response_text=response_text,
                finish_reason=finish_reason,
                input_tokens=100,
                output_tokens=200
            )

            if finish_reason == "stop":
                break

        assert state.is_complete is True
        assert state.continuation_count == 3
        assert "Part 1" in state.accumulated_response
        assert "Part 3" in state.accumulated_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
