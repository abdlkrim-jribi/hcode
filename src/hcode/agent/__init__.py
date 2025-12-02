"""
Agent components for Hcode.

Includes thinking, todo management, ReAct loop, and autonomous operation.
"""

from .thinking import ThinkingBlock, ThinkingSession, ThinkingPhase
from .thinking_manager import ThinkingManager
from .todo import TodoItem, TodoManager, TodoStatus
from .coding_agent import HcodeCodingAgent, ExecutionContext

# Autonomous operation components
from .modes import (
    AgentMode,
    ConfirmationLevel,
    RiskLevel,
    ModeConfig,
    SafetyConfig,
    get_mode_config,
    get_mode_description
)
from .autonomous import (
    ExecutionDecision,
    ExecutionContext as AutonomousContext,
    ActionProposal,
    ExecutionResult,
    AutonomousEngine,
    create_read_action,
    create_edit_action,
    create_write_action,
    create_bash_action,
    create_search_action
)
from .autonomous_agent import HcodeAutonomousCodingAgent, HcodeAutonomousExecutionContext
from .autonomous_prompt import (
    get_autonomous_prompt,
    get_mode_transition_prompt,
    get_confirmation_prompt,
    get_error_recovery_prompt
)

__all__ = [
    # Thinking
    'ThinkingBlock',
    'ThinkingSession',
    'ThinkingPhase',
    'ThinkingManager',
    # Todo
    'TodoItem',
    'TodoManager',
    'TodoStatus',
    # Base agent
    'HcodeCodingAgent',
    'ExecutionContext',
    # Modes
    'AgentMode',
    'ConfirmationLevel',
    'RiskLevel',
    'ModeConfig',
    'SafetyConfig',
    'get_mode_config',
    'get_mode_description',
    # Autonomous engine
    'ExecutionDecision',
    'AutonomousContext',
    'ActionProposal',
    'ExecutionResult',
    'AutonomousEngine',
    'create_read_action',
    'create_edit_action',
    'create_write_action',
    'create_bash_action',
    'create_search_action',
    # Autonomous agent
    'HcodeAutonomousCodingAgent',
    'HcodeAutonomousExecutionContext',
    # Prompts
    'get_autonomous_prompt',
    'get_mode_transition_prompt',
    'get_confirmation_prompt',
    'get_error_recovery_prompt',
]
