"""
Response processing package for Hcode agent.

This package handles parsing and processing of LLM responses:
- Thinking block extraction and display
- Tool call parsing from JSON
- Task completion detection
- Response cleaning for display
"""

from .cleaner import ResponseCleaner
from .completion_detector import TaskCompletionDetector
# from .output_handler import ... (Removed)
from .continuation import ContinuationManager
from .parser import ResponseParser
from .thinking_processor import ThinkingBlockProcessor

__all__ = [
    "ThinkingBlockProcessor",
    "ResponseParser",
    "TaskCompletionDetector",
    "ResponseCleaner",
    "ContinuationManager",
]
