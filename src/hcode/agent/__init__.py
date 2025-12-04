"""
Agent components for Hcode.

Includes thinking, todo management, ReAct loop, autonomous operation,
and enhanced reasoning capabilities for maximum AI performance.
"""

from hcode.agent.autonomous import (
    ExecutionDecision,
    ExecutionContext as AutonomousContext,
    ActionProposal,
    ExecutionResult,
    AutonomousEngine,
    create_read_action,
    create_edit_action,
    create_write_action,
    create_bash_action,
    create_search_action,
)
from hcode.agent.autonomous_agent import HcodeAutonomousCodingAgent, HcodeAutonomousExecutionContext
from hcode.agent.autonomous_prompt import (
    get_autonomous_prompt,
    get_mode_transition_prompt,
    get_confirmation_prompt,
    get_error_recovery_prompt,
)
from hcode.agent.coding_agent import HcodeCodingAgent, ExecutionContext
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
# Autonomous operation components
from hcode.agent.modes import (
    AgentMode,
    ConfirmationLevel,
    RiskLevel,
    ModeConfig,
    SafetyConfig,
    get_mode_config,
    get_mode_description,
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
# Reasoning-driven executor
from hcode.agent.reasoning_executor import (
    ReasoningDrivenExecutor,
    ReasoningToExecutionBridge,
    ReasoningExecutionValidator,
    ExecutionStrategy,
    ExecutionPhase,
    ExecutionStep,
    ExecutionPlan,
    ExecutionResult as ReasoningExecutionResult,
)
# Smart todo extraction
from hcode.agent.smart_todo_extractor import (
    SmartTodoExtractor,
    ReasoningTodoBridge,
    ExtractedTodo,
    TodoPriority,
    extract_todos_from_text,
    extract_todos_from_reasoning,
)
from hcode.agent.thinking import ThinkingBlock, ThinkingSession, ThinkingPhase
from hcode.agent.thinking_manager import ThinkingManager
from hcode.agent.todo import TodoItem, TodoManager, TodoStatus

__all__ = [
    # Thinking
    "ThinkingBlock",
    "ThinkingSession",
    "ThinkingPhase",
    "ThinkingManager",
    # Todo
    "TodoItem",
    "TodoManager",
    "TodoStatus",
    # Base agent
    "HcodeCodingAgent",
    "ExecutionContext",
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
    # Modes
    "AgentMode",
    "ConfirmationLevel",
    "RiskLevel",
    "ModeConfig",
    "SafetyConfig",
    "get_mode_config",
    "get_mode_description",
    # Autonomous engine
    "ExecutionDecision",
    "AutonomousContext",
    "ActionProposal",
    "ExecutionResult",
    "AutonomousEngine",
    "create_read_action",
    "create_edit_action",
    "create_write_action",
    "create_bash_action",
    "create_search_action",
    # Autonomous agent
    "HcodeAutonomousCodingAgent",
    "HcodeAutonomousExecutionContext",
    # Prompts
    "get_autonomous_prompt",
    "get_mode_transition_prompt",
    "get_confirmation_prompt",
    "get_error_recovery_prompt",
    # Smart Todo Extraction
    "SmartTodoExtractor",
    "ReasoningTodoBridge",
    "ExtractedTodo",
    "TodoPriority",
    "extract_todos_from_text",
    "extract_todos_from_reasoning",
    # Reasoning-driven Executor
    "ReasoningDrivenExecutor",
    "ReasoningToExecutionBridge",
    "ReasoningExecutionValidator",
    "ExecutionStrategy",
    "ExecutionPhase",
    "ExecutionStep",
    "ExecutionPlan",
    "ReasoningExecutionResult",
]
