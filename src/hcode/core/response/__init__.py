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
from .output_handler import (
    OutputHandler,
    TruncatedOutput,
    ExtractedError,
    SearchMatch,
    ErrorSeverity,
    OutputType,
    truncate_output,
    extract_errors,
    search_in_output,
    get_latest_lines,
)
from .continuation import ContinuationManager

__all__ = [
    "ThinkingBlockProcessor",
    "ResponseParser",
    "TaskCompletionDetector",
    "ResponseCleaner",
    "OutputHandler",
    "TruncatedOutput",
    "ExtractedError",
    "SearchMatch",
    "ErrorSeverity",
    "OutputType",
    "truncate_output",
    "extract_errors",
    "search_in_output",
    "get_latest_lines",
    "ContinuationManager",
]
