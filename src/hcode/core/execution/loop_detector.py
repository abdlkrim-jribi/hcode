"""
Loop detection for Hcode agent execution.

This module detects when the agent is stuck repeating the same response,
which indicates it's in an infinite loop and needs to break out.
"""

from typing import List, Optional


class LoopDetector:
    """
    Detect when the agent is stuck in a loop repeating responses.
    
    Tracks recent responses and uses hash comparison to detect
    when the same response is being generated repeatedly.
    
    Attributes:
        max_recent: Maximum number of responses to track
        stuck_threshold: Number of repeated responses before declaring stuck
    """
    
    def __init__(self, max_recent: int = 5, stuck_threshold: int = 3):
        """
        Initialize the loop detector.
        
        Args:
            max_recent: Maximum number of responses to track
            stuck_threshold: Number of repeated responses before declaring stuck
        """
        self.max_recent = max_recent
        self.stuck_threshold = stuck_threshold
        self._recent_responses: List[str] = []
    
    
    
    
    def reset(self) -> None:
        """Reset the detection state."""
        self._recent_responses.clear()
    
    @property
    def recent_count(self) -> int:
        """Get the number of tracked responses."""
        return len(self._recent_responses)
