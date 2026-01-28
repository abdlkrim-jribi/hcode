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
        self._last_response_hash: Optional[int] = None
    
    def add_response(self, response: str) -> None:
        """
        Track a response for loop detection.
        
        Args:
            response: The response text to track
        """
        self._recent_responses.append(response)
        
        # Keep only the most recent responses
        if len(self._recent_responses) > self.max_recent:
            self._recent_responses.pop(0)
        
        # Update last response hash
        if response:
            self._last_response_hash = hash(response[:500])
    
    def is_stuck(self) -> bool:
        """
        Check if the model is stuck in a loop.
        
        Compares recent response hashes to detect when the same
        response is being generated repeatedly.
        
        Returns:
            True if the same response has been repeated >= stuck_threshold times
        """
        if len(self._recent_responses) < self.stuck_threshold:
            return False
        
        if not self._recent_responses:
            return False
        
        # Check for repeated responses using hash comparison
        last_response_hash = hash(self._recent_responses[-1][:500]) if self._recent_responses[-1] else 0
        repeat_count = sum(
            1 for r in self._recent_responses 
            if hash(r[:500]) == last_response_hash
        )
        
        return repeat_count >= self.stuck_threshold
    
    def get_repeat_count(self) -> int:
        """
        Get the number of times the last response was repeated.
        
        Returns:
            Count of repeated responses
        """
        if not self._recent_responses:
            return 0
        
        last_response_hash = hash(self._recent_responses[-1][:500]) if self._recent_responses[-1] else 0
        return sum(
            1 for r in self._recent_responses 
            if hash(r[:500]) == last_response_hash
        )
    
    def reset(self) -> None:
        """Reset the detection state."""
        self._recent_responses.clear()
        self._last_response_hash = None
    
    @property
    def recent_count(self) -> int:
        """Get the number of tracked responses."""
        return len(self._recent_responses)
