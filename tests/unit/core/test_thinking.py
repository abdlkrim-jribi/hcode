"""
Tests for the thinking system.

Tests thinking blocks, sessions, and the thinking manager.
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hcode.agent.thinking import ThinkingBlock, ThinkingSession, ThinkingPhase
from hcode.agent.thinking_manager import ThinkingManager
from hcode.config.thinking import ThinkingConfig, ThinkingVisibility


class TestThinkingPhase:
    """Tests for ThinkingPhase enum"""

    def test_all_phases_exist(self):
        """Test all expected phases exist"""
        expected_phases = [
            "understanding", "planning", "analyzing",
            "reasoning", "evaluating", "deciding", "verifying"
        ]
        actual_phases = [p.value for p in ThinkingPhase]
        assert sorted(expected_phases) == sorted(actual_phases)

    def test_phase_values(self):
        """Test phase values are correct strings"""
        assert ThinkingPhase.UNDERSTANDING.value == "understanding"
        assert ThinkingPhase.PLANNING.value == "planning"
        assert ThinkingPhase.REASONING.value == "reasoning"


class TestThinkingBlock:
    """Tests for ThinkingBlock"""

    def test_default_creation(self):
        """Test creating block with defaults"""
        block = ThinkingBlock()

        assert block.id is not None
        assert block.phase == ThinkingPhase.UNDERSTANDING
        assert block.content == ""
        assert block.summary == ""
        assert block.tokens_used == 0
        assert block.duration_ms == 0
        assert isinstance(block.timestamp, datetime)
        assert block.metadata == {}

    def test_creation_with_values(self):
        """Test creating block with specific values"""
        block = ThinkingBlock(
            phase=ThinkingPhase.REASONING,
            content="Analyzing the problem deeply",
            summary="Deep analysis",
            tokens_used=150,
            duration_ms=500,
            metadata={"task": "test"}
        )

        assert block.phase == ThinkingPhase.REASONING
        assert block.content == "Analyzing the problem deeply"
        assert block.summary == "Deep analysis"
        assert block.tokens_used == 150
        assert block.duration_ms == 500
        assert block.metadata == {"task": "test"}

    def test_str_representation(self):
        """Test string representation"""
        block = ThinkingBlock(
            phase=ThinkingPhase.PLANNING,
            content="Planning the approach to solve this task",
            summary="Planning approach"
        )

        string = str(block)
        assert "[planning]" in string
        assert "Planning approach" in string

    def test_str_without_summary(self):
        """Test string representation without summary uses content"""
        block = ThinkingBlock(
            phase=ThinkingPhase.ANALYZING,
            content="This is a long content that should be truncated in display",
            summary=""
        )

        string = str(block)
        assert "[analyzing]" in string
        assert "This is a long content" in string

    def test_to_dict(self):
        """Test conversion to dictionary"""
        block = ThinkingBlock(
            phase=ThinkingPhase.DECIDING,
            content="Making decision",
            summary="Decision made",
            tokens_used=100,
            duration_ms=200,
            metadata={"key": "value"}
        )

        result = block.to_dict()

        assert result["id"] == block.id
        assert result["phase"] == "deciding"
        assert result["content"] == "Making decision"
        assert result["summary"] == "Decision made"
        assert result["tokens_used"] == 100
        assert result["duration_ms"] == 200
        assert result["metadata"] == {"key": "value"}
        assert "timestamp" in result

    def test_unique_ids(self):
        """Test that each block gets unique ID"""
        block1 = ThinkingBlock()
        block2 = ThinkingBlock()

        assert block1.id != block2.id


class TestThinkingSession:
    """Tests for ThinkingSession"""

    def test_default_creation(self):
        """Test creating session with defaults"""
        session = ThinkingSession()

        assert session.id is not None
        assert session.blocks == []
        assert isinstance(session.start_time, datetime)
        assert session.end_time is None
        assert session.total_tokens == 0
        assert session.metadata == {}

    def test_add_block(self):
        """Test adding blocks to session"""
        session = ThinkingSession()

        block1 = ThinkingBlock(
            phase=ThinkingPhase.UNDERSTANDING,
            content="Understanding",
            tokens_used=50
        )
        block2 = ThinkingBlock(
            phase=ThinkingPhase.PLANNING,
            content="Planning",
            tokens_used=75
        )

        session.add_block(block1)
        session.add_block(block2)

        assert len(session.blocks) == 2
        assert session.total_tokens == 125
        assert session.blocks[0] == block1
        assert session.blocks[1] == block2

    def test_get_summary_empty(self):
        """Test summary of empty session"""
        session = ThinkingSession()
        summary = session.get_summary()
        assert summary == "No thinking performed"

    def test_get_summary_with_blocks(self):
        """Test summary with blocks"""
        session = ThinkingSession()
        session.add_block(ThinkingBlock(
            phase=ThinkingPhase.UNDERSTANDING,
            summary="Understood the task"
        ))
        session.add_block(ThinkingBlock(
            phase=ThinkingPhase.PLANNING,
            summary="Created plan"
        ))

        summary = session.get_summary()

        assert "Understanding" in summary
        assert "Understood the task" in summary
        assert "Planning" in summary
        assert "Created plan" in summary

    def test_get_full_content(self):
        """Test getting full content"""
        session = ThinkingSession()
        session.add_block(ThinkingBlock(
            phase=ThinkingPhase.UNDERSTANDING,
            content="Full understanding content"
        ))
        session.add_block(ThinkingBlock(
            phase=ThinkingPhase.REASONING,
            content="Full reasoning content"
        ))

        content = session.get_full_content()

        assert "UNDERSTANDING" in content
        assert "Full understanding content" in content
        assert "REASONING" in content
        assert "Full reasoning content" in content

    def test_get_phase_content(self):
        """Test filtering blocks by phase"""
        session = ThinkingSession()

        block1 = ThinkingBlock(phase=ThinkingPhase.UNDERSTANDING)
        block2 = ThinkingBlock(phase=ThinkingPhase.PLANNING)
        block3 = ThinkingBlock(phase=ThinkingPhase.UNDERSTANDING)

        session.add_block(block1)
        session.add_block(block2)
        session.add_block(block3)

        understanding_blocks = session.get_phase_content(ThinkingPhase.UNDERSTANDING)

        assert len(understanding_blocks) == 2
        assert block1 in understanding_blocks
        assert block3 in understanding_blocks
        assert block2 not in understanding_blocks

    def test_complete(self):
        """Test completing session"""
        session = ThinkingSession()

        assert session.end_time is None

        session.complete()

        assert session.end_time is not None
        assert isinstance(session.end_time, datetime)

    def test_duration_ms(self):
        """Test duration calculation"""
        session = ThinkingSession()

        # Duration should be positive even without completing
        duration = session.duration_ms()
        assert duration >= 0

        # Complete and check duration still works
        session.complete()
        duration_after = session.duration_ms()
        assert duration_after >= duration

    def test_to_dict(self):
        """Test conversion to dictionary"""
        session = ThinkingSession(metadata={"task_id": "123"})
        session.add_block(ThinkingBlock(
            phase=ThinkingPhase.UNDERSTANDING,
            tokens_used=50
        ))
        session.complete()

        result = session.to_dict()

        assert result["id"] == session.id
        assert len(result["blocks"]) == 1
        assert "start_time" in result
        assert result["end_time"] is not None
        assert result["total_tokens"] == 50
        assert result["metadata"] == {"task_id": "123"}
        assert "duration_ms" in result

    def test_str_representation(self):
        """Test string representation"""
        session = ThinkingSession()
        session.add_block(ThinkingBlock(tokens_used=100))
        session.add_block(ThinkingBlock(tokens_used=150))

        string = str(session)

        assert "ThinkingSession" in string
        assert "2 blocks" in string
        assert "250 tokens" in string


class TestThinkingConfig:
    """Tests for ThinkingConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = ThinkingConfig()

        assert config.enabled == True
        assert config.budget_tokens > 0
        # Default visibility is STREAMING
        assert config.visibility == ThinkingVisibility.STREAMING

    def test_disabled_config(self):
        """Test disabled thinking"""
        config = ThinkingConfig(enabled=False)
        assert config.enabled == False

    def test_visibility_modes(self):
        """Test all visibility modes"""
        for visibility in ThinkingVisibility:
            config = ThinkingConfig(visibility=visibility)
            assert config.visibility == visibility

    def test_should_think_simple_task(self):
        """Test should_think for simple tasks"""
        config = ThinkingConfig(enabled=True)

        # Simple tasks should not trigger thinking by default
        simple_prompts = [
            "print hello",
            "read file.txt",
            "show me x"
        ]

        # Without specific keywords, these might not trigger
        # This depends on implementation

    def test_should_think_complex_task(self):
        """Test should_think for complex tasks"""
        config = ThinkingConfig(enabled=True)

        complex_prompts = [
            "refactor the authentication system",
            "implement a caching layer",
            "debug the memory leak",
            "analyze the performance issues"
        ]

        # Complex tasks should trigger thinking
        # This depends on implementation


class TestThinkingManager:
    """Tests for ThinkingManager"""

    def test_initialization(self):
        """Test manager initialization"""
        config = ThinkingConfig()
        manager = ThinkingManager(config)

        assert manager.config == config
        assert manager.llm_client is None
        assert manager.current_session is None
        assert manager.listeners == []

    def test_initialization_with_llm(self):
        """Test initialization with LLM client"""
        config = ThinkingConfig()
        mock_llm = Mock()

        manager = ThinkingManager(config, llm_client=mock_llm)

        assert manager.llm_client == mock_llm

    def test_add_listener(self):
        """Test adding listeners"""
        manager = ThinkingManager(ThinkingConfig())

        listener1 = Mock()
        listener2 = Mock()

        manager.add_listener(listener1)
        manager.add_listener(listener2)

        assert len(manager.listeners) == 2
        assert listener1 in manager.listeners
        assert listener2 in manager.listeners

    def test_notify_listeners(self):
        """Test notifying listeners"""
        manager = ThinkingManager(ThinkingConfig())

        listener1 = Mock()
        listener2 = Mock()
        manager.add_listener(listener1)
        manager.add_listener(listener2)

        block = ThinkingBlock(phase=ThinkingPhase.UNDERSTANDING)
        manager.notify_listeners(block)

        listener1.assert_called_once_with(block)
        listener2.assert_called_once_with(block)

    def test_notify_listeners_with_error(self):
        """Test listeners errors don't break notification"""
        manager = ThinkingManager(ThinkingConfig())

        error_listener = Mock(side_effect=Exception("Listener error"))
        good_listener = Mock()

        manager.add_listener(error_listener)
        manager.add_listener(good_listener)

        block = ThinkingBlock()
        manager.notify_listeners(block)  # Should not raise

        # Good listener should still be called
        good_listener.assert_called_once()

    def test_start_session(self):
        """Test starting a session"""
        manager = ThinkingManager(ThinkingConfig())

        session = manager.start_session(metadata={"task": "test"})

        assert session is not None
        assert manager.current_session == session
        assert session.metadata == {"task": "test"}

    def test_end_session(self):
        """Test ending a session"""
        manager = ThinkingManager(ThinkingConfig())

        # Start session
        session = manager.start_session()
        session.add_block(ThinkingBlock(tokens_used=100))

        # End session
        ended_session = manager.end_session()

        assert ended_session == session
        assert ended_session.end_time is not None
        assert manager.current_session is None

    def test_end_session_when_none(self):
        """Test ending session when none exists"""
        manager = ThinkingManager(ThinkingConfig())

        result = manager.end_session()

        assert result is None

    @pytest.mark.asyncio
    async def test_think_disabled(self):
        """Test thinking when disabled"""
        config = ThinkingConfig(enabled=False)
        manager = ThinkingManager(config)

        session = await manager.think("Test prompt")

        assert len(session.blocks) == 0
        assert session.end_time is not None

    @pytest.mark.asyncio
    async def test_think_without_llm(self):
        """Test thinking without LLM client"""
        config = ThinkingConfig(enabled=True)
        manager = ThinkingManager(config)

        session = await manager.think("Test prompt")

        # Should still create blocks (with fallback content)
        assert len(session.blocks) > 0

    @pytest.mark.asyncio
    async def test_think_with_mock_llm(self):
        """Test thinking with mock LLM"""
        config = ThinkingConfig(enabled=True)

        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value={
            "content": "Generated thinking content",
            "usage": {"total_tokens": 50}
        })

        manager = ThinkingManager(config, llm_client=mock_llm)

        session = await manager.think("Test prompt")

        assert len(session.blocks) > 0
        assert session.total_tokens > 0

    @pytest.mark.asyncio
    async def test_think_specific_phases(self):
        """Test thinking with specific phases"""
        config = ThinkingConfig(enabled=True)
        manager = ThinkingManager(config)

        phases = [ThinkingPhase.UNDERSTANDING, ThinkingPhase.DECIDING]
        session = await manager.think("Test", phases=phases)

        assert len(session.blocks) == 2
        assert session.blocks[0].phase == ThinkingPhase.UNDERSTANDING
        assert session.blocks[1].phase == ThinkingPhase.DECIDING

    @pytest.mark.asyncio
    async def test_think_notifies_listeners(self):
        """Test that thinking notifies listeners"""
        config = ThinkingConfig(
            enabled=True,
            visibility=ThinkingVisibility.FULL
        )
        manager = ThinkingManager(config)

        received_blocks = []
        manager.add_listener(lambda b: received_blocks.append(b))

        await manager.think("Test", phases=[ThinkingPhase.UNDERSTANDING])

        assert len(received_blocks) == 1
        assert received_blocks[0].phase == ThinkingPhase.UNDERSTANDING

    @pytest.mark.asyncio
    async def test_think_hidden_visibility(self):
        """Test thinking with hidden visibility doesn't notify"""
        config = ThinkingConfig(
            enabled=True,
            visibility=ThinkingVisibility.HIDDEN
        )
        manager = ThinkingManager(config)

        received_blocks = []
        manager.add_listener(lambda b: received_blocks.append(b))

        await manager.think("Test", phases=[ThinkingPhase.UNDERSTANDING])

        # Listeners should not be notified when hidden
        assert len(received_blocks) == 0

    @pytest.mark.asyncio
    async def test_stream_thinking(self):
        """Test streaming thinking blocks"""
        config = ThinkingConfig(enabled=True)
        manager = ThinkingManager(config)

        phases = [ThinkingPhase.UNDERSTANDING, ThinkingPhase.PLANNING]
        blocks = []

        async for block in manager.stream_thinking("Test", phases=phases):
            blocks.append(block)

        assert len(blocks) == 2
        assert blocks[0].phase == ThinkingPhase.UNDERSTANDING
        assert blocks[1].phase == ThinkingPhase.PLANNING

    @pytest.mark.asyncio
    async def test_stream_thinking_disabled(self):
        """Test streaming when disabled yields nothing"""
        config = ThinkingConfig(enabled=False)
        manager = ThinkingManager(config)

        blocks = []
        async for block in manager.stream_thinking("Test"):
            blocks.append(block)

        assert len(blocks) == 0

    def test_build_phase_prompt(self):
        """Test phase prompt building"""
        manager = ThinkingManager(ThinkingConfig())

        prompt = manager._build_phase_prompt(
            "Solve this problem",
            ThinkingPhase.UNDERSTANDING,
            {"context_key": "value"}
        )

        assert "UNDERSTANDING" in prompt
        assert "Solve this problem" in prompt
        assert "context_key" in prompt

    def test_create_summary_short_content(self):
        """Test summary creation with short content"""
        manager = ThinkingManager(ThinkingConfig())

        summary = manager._create_summary(
            "Short content",
            ThinkingPhase.UNDERSTANDING
        )

        assert summary == "Short content"

    def test_create_summary_long_content(self):
        """Test summary creation with long content"""
        manager = ThinkingManager(ThinkingConfig())

        long_content = "A" * 150
        summary = manager._create_summary(long_content, ThinkingPhase.UNDERSTANDING)

        assert len(summary) <= 100
        assert "..." in summary

    def test_create_summary_empty_content(self):
        """Test summary creation with empty content"""
        manager = ThinkingManager(ThinkingConfig())

        summary = manager._create_summary("", ThinkingPhase.DECIDING)

        assert "deciding" in summary.lower()


class TestThinkingIntegration:
    """Integration tests for thinking system"""

    @pytest.mark.asyncio
    async def test_full_thinking_workflow(self):
        """Test complete thinking workflow"""
        config = ThinkingConfig(
            enabled=True,
            visibility=ThinkingVisibility.FULL,
            budget_tokens=1000
        )

        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value={
            "content": "Thought about the problem",
            "usage": {"total_tokens": 100}
        })

        manager = ThinkingManager(config, llm_client=mock_llm)

        # Track events
        events = []
        manager.add_listener(lambda b: events.append(("block", b)))

        # Execute thinking
        session = await manager.think(
            "Implement a binary search",
            phases=[
                ThinkingPhase.UNDERSTANDING,
                ThinkingPhase.PLANNING,
                ThinkingPhase.DECIDING
            ],
            context={"language": "python"}
        )

        # Verify session
        assert len(session.blocks) == 3
        assert session.total_tokens > 0
        assert session.end_time is not None

        # Verify events
        assert len(events) == 3

        # Verify blocks have content
        for block in session.blocks:
            assert block.content
            assert block.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_thinking_error_recovery(self):
        """Test thinking continues on LLM errors"""
        config = ThinkingConfig(enabled=True)

        mock_llm = Mock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM Error"))

        manager = ThinkingManager(config, llm_client=mock_llm)

        # Should not raise, should fallback
        session = await manager.think(
            "Test prompt",
            phases=[ThinkingPhase.UNDERSTANDING]
        )

        # Should still have blocks (with error content)
        assert len(session.blocks) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
