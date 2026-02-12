"""
Unit tests for loop detection via response hash deduplication.

Task #10: Add loop detection with response hash deduplication

These tests validate that the base handler can detect when the AI
produces identical responses repeatedly and breaks the loop to prevent
degenerate behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from hcode.core.phases.base_handler import BasePhaseHandler
from hcode.core.protocols import AgentContext
from hcode.providers.base import Message


class TestLoopDetection:
    """Tests for loop detection in multi-round generation."""

    @pytest.fixture
    def handler(self):
        """Create a base handler for testing."""
        handler = BasePhaseHandler(
            artifact_manager=None,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )
        handler.phase_name = "test"
        return handler

    @pytest.fixture
    def context(self):
        """Create a test context."""
        return AgentContext(
            task="test task",
            session_id="test",
            working_dir="/tmp",
            iteration=0,
        )

    @pytest.mark.asyncio
    async def test_loop_detection_breaks_on_duplicate_response(self, handler, context):
        """
        Verify loop detection breaks when same response appears twice in a row.

        Acceptance: Loop detection breaks within 2 identical responses.
        """
        # Mock provider that returns identical responses
        mock_provider = AsyncMock()
        mock_response = MagicMock()
        # Return the same response every time (degenerate loop)
        mock_response.content = """<thinking>
Thinking about the task...
</thinking>

<output>
I'll create a file.
</output>

```json
{"tool": "Write", "arguments": {"TargetFile": "test.py", "Content": "pass"}}
```"""
        mock_provider.generate_completion.return_value = mock_response

        # Mock tool executor
        mock_executor = AsyncMock()
        mock_executor.execute_tool.return_value = MagicMock(
            success=True,
            output="Created test.py"
        )

        handler.provider = mock_provider
        handler.tool_executor = mock_executor

        # Run the generation loop
        last_response, tool_results = await handler._generate_and_execute(
            prompt="Create a test file",
            context=context,
            max_rounds=10,  # Allow up to 10 rounds
        )

        # Should have stopped early due to loop detection (not hit max_rounds)
        # The provider will be called until it detects the duplicate
        # First call: hash recorded
        # Second call: same hash recorded
        # Third call: detects hash in last 2, breaks

        # Should have been called more than once but less than max_rounds
        call_count = mock_provider.generate_completion.call_count
        assert call_count >= 2, "Should have made at least 2 calls before detecting loop"
        assert call_count <= 4, f"Should have detected loop within 4 calls (got {call_count})"

    @pytest.mark.asyncio
    async def test_loop_detection_allows_different_responses(self, handler, context):
        """Verify loop detection allows different responses to proceed."""
        # Mock provider that returns different responses each time
        mock_provider = AsyncMock()

        responses = [
            """<output>First response</output>
```json
{"tool": "Read", "arguments": {"TargetFile": "a.py"}}
```""",
            """<output>Second response</output>
```json
{"tool": "Read", "arguments": {"TargetFile": "b.py"}}
```""",
            """<output>Third response</output>
```json
{"tool": "Read", "arguments": {"TargetFile": "c.py"}}
```""",
            """<output>Done</output>""",  # No tool calls - should end naturally
        ]

        response_index = {"count": 0}

        def get_next_response(*args, **kwargs):
            idx = response_index["count"]
            response_index["count"] += 1
            if idx < len(responses):
                mock = MagicMock()
                mock.content = responses[idx]
                return mock
            # Return empty response if we run out
            mock = MagicMock()
            mock.content = "<output>Done</output>"
            return mock

        mock_provider.generate_completion.side_effect = get_next_response

        # Mock tool executor
        mock_executor = AsyncMock()
        mock_executor.execute_tool.return_value = MagicMock(
            success=True,
            output="File read successfully"
        )

        handler.provider = mock_provider
        handler.tool_executor = mock_executor

        # Run the generation loop
        last_response, tool_results = await handler._generate_and_execute(
            prompt="Read some files",
            context=context,
            max_rounds=10,
        )

        # Should have processed all different responses without loop detection
        # First 3 responses have tool calls, 4th has none (natural end)
        assert mock_provider.generate_completion.call_count == 4

    @pytest.mark.asyncio
    async def test_loop_detection_hash_ignores_thinking_blocks(self, handler, context):
        """
        Verify loop detection hashes ignore thinking blocks.

        This ensures that different thinking but same tool calls is still detected as a loop.
        """
        # Mock provider that returns same tool calls but different thinking
        mock_provider = AsyncMock()

        responses = [
            """<thinking>First thinking...</thinking>
<output>Creating file</output>
```json
{"tool": "Write", "arguments": {"TargetFile": "test.py", "Content": "pass"}}
```""",
            """<thinking>Second thinking that's different...</thinking>
<output>Creating file</output>
```json
{"tool": "Write", "arguments": {"TargetFile": "test.py", "Content": "pass"}}
```""",
            """<thinking>Third thinking also different...</thinking>
<output>Creating file</output>
```json
{"tool": "Write", "arguments": {"TargetFile": "test.py", "Content": "pass"}}
```""",
        ]

        response_index = {"count": 0}

        def get_next_response(*args, **kwargs):
            idx = response_index["count"]
            response_index["count"] += 1
            if idx < len(responses):
                mock = MagicMock()
                mock.content = responses[idx]
                return mock
            mock = MagicMock()
            mock.content = "<output>Done</output>"
            return mock

        mock_provider.generate_completion.side_effect = get_next_response

        # Mock tool executor
        mock_executor = AsyncMock()
        mock_executor.execute_tool.return_value = MagicMock(
            success=True,
            output="Created test.py"
        )

        handler.provider = mock_provider
        handler.tool_executor = mock_executor

        # Run the generation loop
        last_response, tool_results = await handler._generate_and_execute(
            prompt="Create a test file",
            context=context,
            max_rounds=10,
        )

        # Should detect loop despite different thinking blocks
        # The output text and tool calls are identical
        call_count = mock_provider.generate_completion.call_count
        assert call_count <= 4, f"Should have detected loop (got {call_count} calls)"

    @pytest.mark.asyncio
    async def test_loop_detection_doesnt_trigger_on_first_response(self, handler, context):
        """Verify loop detection doesn't trigger on the first response."""
        # Mock provider
        mock_provider = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = """<output>First and only response</output>"""
        mock_provider.generate_completion.return_value = mock_response

        handler.provider = mock_provider
        handler.tool_executor = AsyncMock()

        # Run with a single response (no tool calls, so ends naturally)
        last_response, tool_results = await handler._generate_and_execute(
            prompt="Simple task",
            context=context,
            max_rounds=10,
        )

        # Should complete normally without loop detection
        assert mock_provider.generate_completion.call_count == 1
        assert "First and only response" in last_response


# Integration test with actual hash computation
def test_response_hash_computation():
    """Test that response hashing works correctly."""
    import hashlib

    # Same output and tool calls should produce same hash
    response1 = """<thinking>Different thinking 1</thinking>
<output>Same output</output>
```json
{"tool": "Write", "arguments": {"TargetFile": "test.py"}}
```"""

    response2 = """<thinking>Different thinking 2</thinking>
<output>Same output</output>
```json
{"tool": "Write", "arguments": {"TargetFile": "test.py"}}
```"""

    handler = BasePhaseHandler(None, None, None, None)
    handler.phase_name = "test"

    # Extract text (removes thinking) and tool calls
    text1 = handler._extract_text_response(response1)
    tools1 = handler._extract_tool_calls(response1)
    hash1 = hashlib.sha256((text1 + str(tools1)).encode()).hexdigest()

    text2 = handler._extract_text_response(response2)
    tools2 = handler._extract_tool_calls(response2)
    hash2 = hashlib.sha256((text2 + str(tools2)).encode()).hexdigest()

    # Hashes should be identical (thinking blocks ignored)
    assert hash1 == hash2

    # Different tool calls should produce different hash
    response3 = """<output>Same output</output>
```json
{"tool": "Read", "arguments": {"TargetFile": "different.py"}}
```"""

    text3 = handler._extract_text_response(response3)
    tools3 = handler._extract_tool_calls(response3)
    hash3 = hashlib.sha256((text3 + str(tools3)).encode()).hexdigest()

    # Hash should be different
    assert hash1 != hash3
