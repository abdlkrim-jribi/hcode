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
# from hcode.core.filesystem import FileSystemManager, FileWatcher (Removed)
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
# from hcode.core.response import (Removed OutputHandler usage)
from hcode.core.safety import SafetyGuard

__all__ = [
    "HcodeAgent",
    "SafetyGuard",
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
    # Output handling (Removed)
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
