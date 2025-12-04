"""
Thinking blocks and session management for extended reasoning.

Matches Claude Code's thinking block structure and display.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import uuid


class ThinkingPhase(Enum):
    """Phases of thinking matching Claude Code"""

    UNDERSTANDING = "understanding"  # Understanding the problem
    PLANNING = "planning"  # Planning the approach
    ANALYZING = "analyzing"  # Analyzing options
    REASONING = "reasoning"  # Deep reasoning
    EVALUATING = "evaluating"  # Evaluating solutions
    DECIDING = "deciding"  # Making decisions
    VERIFYING = "verifying"  # Verifying approach


@dataclass
class ThinkingBlock:
    """
    A single thinking block.

    Matches Claude Code's thinking block structure.
    """

    # Unique identifier
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Phase of thinking
    phase: ThinkingPhase = ThinkingPhase.UNDERSTANDING

    # Thinking content
    content: str = ""

    # Brief summary for display
    summary: str = ""

    # Token usage
    tokens_used: int = 0

    # Duration in milliseconds
    duration_ms: int = 0

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation"""
        return f"[{self.phase.value}] {self.summary or self.content[:50]}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "phase": self.phase.value,
            "content": self.content,
            "summary": self.summary,
            "tokens_used": self.tokens_used,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ThinkingSession:
    """
    A session of thinking with multiple blocks.

    Manages a complete thinking session from start to finish.
    """

    # Session identifier
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Thinking blocks
    blocks: List[ThinkingBlock] = field(default_factory=list)

    # Session start time
    start_time: datetime = field(default_factory=datetime.now)

    # Session end time
    end_time: Optional[datetime] = None

    # Total tokens used
    total_tokens: int = 0

    # Session metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_block(self, block: ThinkingBlock) -> None:
        """
        Add a thinking block to the session.

        Args:
            block: Thinking block to add
        """
        self.blocks.append(block)
        self.total_tokens += block.tokens_used

    def get_summary(self) -> str:
        """
        Get a summary of the thinking session.

        Returns:
            Summary string
        """
        if not self.blocks:
            return "No thinking performed"

        summaries = []
        for block in self.blocks:
            phase_name = block.phase.value.title()
            summary = block.summary or block.content[:100]
            summaries.append(f"• {phase_name}: {summary}")

        return "\n".join(summaries)

    def get_full_content(self) -> str:
        """
        Get full content of all thinking blocks.

        Returns:
            Full thinking content
        """
        if not self.blocks:
            return ""

        parts = []
        for block in self.blocks:
            phase_name = block.phase.value.upper()
            parts.append(f"=== {phase_name} ===\n{block.content}")

        return "\n\n".join(parts)

    def get_phase_content(self, phase: ThinkingPhase) -> List[ThinkingBlock]:
        """
        Get all blocks for a specific phase.

        Args:
            phase: Phase to filter by

        Returns:
            List of blocks for that phase
        """
        return [block for block in self.blocks if block.phase == phase]

    def complete(self) -> None:
        """Mark session as complete"""
        self.end_time = datetime.now()

    def duration_ms(self) -> int:
        """
        Get total session duration in milliseconds.

        Returns:
            Duration in milliseconds
        """
        if self.end_time is None:
            end = datetime.now()
        else:
            end = self.end_time

        delta = end - self.start_time
        return int(delta.total_seconds() * 1000)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "blocks": [block.to_dict() for block in self.blocks],
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_tokens": self.total_tokens,
            "duration_ms": self.duration_ms(),
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation"""
        duration = self.duration_ms() / 1000
        return f"ThinkingSession({len(self.blocks)} blocks, {self.total_tokens} tokens, {duration:.1f}s)"
