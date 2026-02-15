"""
Response processing package for Hcode agent.

This package handles parsing and processing of LLM responses:
- Thinking block extraction and display
- Tool call parsing from JSON
- Task completion detection
- Response cleaning for display
"""

from .thinking_processor import ThinkingBlockProcessor
from .parser import ResponseParser
from .completion_detector import TaskCompletionDetector
from .cleaner import ResponseCleaner
# from .output_handler import ... (Removed)
from .continuation import ContinuationManager

__all__ = [
    "ThinkingBlockProcessor",
    "ResponseParser",
    "TaskCompletionDetector",
    "ResponseCleaner",
    "ContinuationManager",
]
