"""
Core components for Hcode.
"""

from hcode.core.agent import HcodeAgent
from hcode.core.observability import (
    ExecutionAnalytics,
    ToolAnalytics,
    ReasoningAnalytics,
    CostAnalytics,
    ToolExecutionEvent,
    ReasoningEvent,
    get_analytics,
    InteractionLogger,
    get_logger,
    start_logging,
    log_interaction,
    log_tool_call,
    log_error,
    end_logging,
)
from hcode.core.context import ContextManager, ContextEntry
from hcode.core.filesystem import FileSystemManager, FileWatcher
from hcode.core.optimization import (
    CachedTokenCounter,
    BatchContextWriter,
    ParallelToolExecutor,
    ToolResultCache,
    SmartContextOptimizer,
    get_token_counter,
    get_context_writer,
)
from hcode.core.execution import (
    ExecutionStateMachine,
    ExecutionState,
)
from hcode.core.response import (
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
    # Logging & Analytics
    "InteractionLogger",
    "get_logger",
    "start_logging",
    "log_interaction",
    "log_tool_call",
    "log_error",
    "end_logging",
    "ExecutionAnalytics",
    "ToolAnalytics",
    "ReasoningAnalytics",
    "CostAnalytics",
    "ToolExecutionEvent",
    "ReasoningEvent",
    "get_analytics",
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
    "SmartContextOptimizer",
    "get_token_counter",
    "get_context_writer",
    # Execution
    "ExecutionStateMachine",
    "ExecutionState",
]
