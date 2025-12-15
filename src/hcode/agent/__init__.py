"""
Agent components for Hcode.

Includes thinking, todo management, ReAct loop, autonomous operation,
and enhanced reasoning capabilities for maximum AI performance.
"""

# Enhanced thinking manager
from hcode.agent.enhanced_thinking_manager import (
    EnhancedThinkingManager,
    EnhancedThinkingMode,
    ThinkingResult,
    create_enhanced_thinking_manager,
)
# Feedback loop components
from hcode.agent.feedback_loop import (
    ThinkingExecutionFeedbackLoop,
    ExecutionResult as FeedbackExecutionResult,
    ExecutionStatus,
    FeedbackEntry,
    FeedbackType,
    ReasoningRevision,
    HypothesisValidator,
    FeedbackProcessor,
    ReasoningReviser,
)
# Enhanced reasoning components
from hcode.agent.reasoning import (
    StructuredReasoning,
    ReasoningParser,
    ReasoningLevel,
    ReasoningPhase,
    ConfidenceCalibrator,
    ReasoningToTodoIntegrator,
    SelfCritiqueEngine,
    ReasoningQualityMetrics,
    PerceptionOutput,
    ComprehensionOutput,
    AnalysisOutput,
    ReasoningOutput,
    DecisionOutput,
    VerificationOutput,
)
from hcode.agent.thinking import ThinkingBlock, ThinkingSession, ThinkingPhase
from hcode.agent.todo import TodoItem, TodoManager, TodoStatus

__all__ = [
    # Thinking
    "ThinkingBlock",
    "ThinkingSession",
    "ThinkingPhase",
    # Todo
    "TodoItem",
    "TodoManager",
    "TodoStatus",
    # Enhanced Reasoning System
    "StructuredReasoning",
    "ReasoningParser",
    "ReasoningLevel",
    "ReasoningPhase",
    "ConfidenceCalibrator",
    "ReasoningToTodoIntegrator",
    "SelfCritiqueEngine",
    "ReasoningQualityMetrics",
    "PerceptionOutput",
    "ComprehensionOutput",
    "AnalysisOutput",
    "ReasoningOutput",
    "DecisionOutput",
    "VerificationOutput",
    # Feedback Loop
    "ThinkingExecutionFeedbackLoop",
    "FeedbackExecutionResult",
    "ExecutionStatus",
    "FeedbackEntry",
    "FeedbackType",
    "ReasoningRevision",
    "HypothesisValidator",
    "FeedbackProcessor",
    "ReasoningReviser",
    # Enhanced Thinking Manager
    "EnhancedThinkingManager",
    "EnhancedThinkingMode",
    "ThinkingResult",
    "create_enhanced_thinking_manager",
]
