"""
Core components for Hcode.
"""

from hcode.core.agent import HcodeAgent
from hcode.core.analytics import (
    ExecutionAnalytics,
    ToolAnalytics,
    ReasoningAnalytics,
    CostAnalytics,
    ToolExecutionEvent,
    ReasoningEvent,
    get_analytics,
)
from hcode.core.context import ContextManager, ContextEntry
from hcode.core.filesystem import FileSystemManager, FileWatcher
from hcode.core.interaction_logger import (
    InteractionLogger,
    get_logger,
    start_logging,
    log_interaction,
    log_tool_call,
    log_error,
    end_logging,
)
from hcode.core.optimizations import (
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
from hcode.core.output_handler import (
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
from hcode.core.safety import SafetyGuard, DryRunContext

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
