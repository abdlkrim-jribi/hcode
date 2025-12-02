"""
Core components for Hcode.
"""

from .agent import HcodeAgent
from .enhanced_agent import EnhancedHcodeAgent
from .filesystem import FileSystemManager, FileWatcher
from .safety import SafetyGuard, DryRunContext
from .context import ContextManager, ContextEntry
from .interaction_logger import (
    InteractionLogger,
    get_logger,
    start_logging,
    log_interaction,
    log_tool_call,
    log_error,
    end_logging
)
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

__all__ = [
    "HcodeAgent",
    "EnhancedHcodeAgent",
    "FileSystemManager",
    "FileWatcher",
    "SafetyGuard",
    "DryRunContext",
    "ContextManager",
    "ContextEntry",
    # Logging
    "InteractionLogger",
    "get_logger",
    "start_logging",
    "log_interaction",
    "log_tool_call",
    "log_error",
    "end_logging",
    # Output handling
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
]
