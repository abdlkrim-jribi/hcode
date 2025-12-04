"""
Core components for Hcode.
"""

from .agent import HcodeAgent
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
    end_logging,
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
from .optimizations import (
    CachedTokenCounter,
    BatchContextWriter,
    ParallelToolExecutor,
    ToolResultCache,
    ExecutionStateMachine,
    SmartContextOptimizer,
    ExecutionState,
    get_token_counter,
    get_context_writer,
)
from .analytics import (
    ExecutionAnalytics,
    ToolAnalytics,
    ReasoningAnalytics,
    CostAnalytics,
    ToolExecutionEvent,
    ReasoningEvent,
    get_analytics,
)

__all__ = [
    "HcodeAgent",
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
    # Optimizations
    "CachedTokenCounter",
    "BatchContextWriter",
    "ParallelToolExecutor",
    "ToolResultCache",
    "ExecutionStateMachine",
    "SmartContextOptimizer",
    "ExecutionState",
    "get_token_counter",
    "get_context_writer",
    # Analytics
    "ExecutionAnalytics",
    "ToolAnalytics",
    "ReasoningAnalytics",
    "CostAnalytics",
    "ToolExecutionEvent",
    "ReasoningEvent",
    "get_analytics",
]
