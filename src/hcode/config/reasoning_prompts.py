"""
Optimized Reasoning Prompts for GPT-OSS and other LLMs.

This module provides carefully crafted prompts designed to maximize
reasoning performance, accuracy, and structured output quality.

Key features:
- Multi-level reasoning depth prompts
- Structured output templates
- Self-critique triggers
- Confidence calibration guidelines
- Task-specific reasoning patterns
"""


def method_name():
    from typing import Dict, Any, Optional, List
    return Any, Dict, Optional


Any, Dict, Optional = method_name()
from dataclasses import dataclass, field
from enum import Enum


class ReasoningDepth(Enum):
    """Depth levels for reasoning prompts"""

    QUICK = "quick"  # Level 1: Fast decisions
    STANDARD = "standard"  # Level 2: Balanced analysis
    DEEP = "deep"  # Level 3: Comprehensive reasoning


@dataclass
class ReasoningPromptConfig:
    """Configuration for reasoning prompt generation"""

    depth: ReasoningDepth = ReasoningDepth.STANDARD
    require_confidence: bool = True
    require_fallback: bool = True
    require_evidence: bool = True
    require_counter_arguments: bool = True
    require_action_items: bool = True
    max_thinking_tokens: int = 4000
    temperature_thinking: float = 0.7
    temperature_decision: float = 0.2


# =============================================================================
# CORE REASONING SYSTEM PROMPT
# =============================================================================


from hcode.config.prompts import get_prompts_config
from hcode.config.core_prompts.core import CorePromptLoader

# =============================================================================
# PROMPT BUILDER CLASS
# =============================================================================


class ReasoningPromptBuilder:
    """
    Builds optimized reasoning prompts based on task and configuration.
    """

    def __init__(self, config: Optional[ReasoningPromptConfig] = None):
        self.config = config or ReasoningPromptConfig()
        self.prompts_config = get_prompts_config()

    def build_system_prompt(
        self, task_type: Optional[str] = None, include_self_critique: bool = True
    ) -> str:
        """
        Build complete system prompt for reasoning.

        Args:
            task_type: Optional specific task type
            include_self_critique: Whether to include self-critique section

        Returns:
            Complete system prompt
        """
        # Fetch base system prompt from config
        parts = [self.prompts_config.get_reasoning_system_prompt()]

        # Add task-specific section if applicable
        if task_type:
            task_prompt = self.prompts_config.get_reasoning_task_specific(task_type)
            if task_prompt:
                parts.append("\n" + task_prompt)

        # Add self-critique if requested
        if include_self_critique:
            self_critique = self.prompts_config.get_reasoning_enhancement("self_critique")
            if self_critique:
                parts.append("\n" + self_critique)

        return "\n".join(parts)

    def build_thinking_prompt(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        depth: Optional[ReasoningDepth] = None,
    ) -> str:
        """
        Build prompt to trigger thinking for a specific task.

        Args:
            task: The task to reason about
            context: Additional context
            depth: Reasoning depth level

        Returns:
            Prompt to trigger structured thinking
        """
        depth = depth or self.config.depth

        if depth == ReasoningDepth.QUICK:
            template = self._quick_thinking_template()
        elif depth == ReasoningDepth.STANDARD:
            template = self._standard_thinking_template()
        else:
            template = self._deep_thinking_template()

        prompt_parts = [
            f"Task: {task}",
            "",
            "Please reason through this using the following structure:",
            "",
            template,
        ]

        if context:
            # Format context nicely
            context_str = []
            for k, v in context.items():
                if k == "git_status" and v:
                    context_str.append(f"Git Status:\n{v}")
                elif k == "active_files" and v:
                    context_str.append(f"Active Files: {', '.join(v)}")
                else:
                    context_str.append(f"{k}: {v}")
            
            if context_str:
                prompt_parts.insert(1, "\nContext:\n" + "\n".join(context_str) + "\n")

        return "\n".join(prompt_parts)

    def _quick_thinking_template(self) -> str:
        loader = CorePromptLoader()
        return loader.get_thinking_template("quick")

    def _standard_thinking_template(self) -> str:
        loader = CorePromptLoader()
        return loader.get_thinking_template("standard")

    def _deep_thinking_template(self) -> str:
        loader = CorePromptLoader()
        return loader.get_thinking_template("deep")

    def build_refinement_prompt(self, original_reasoning: str, feedback: str, outcome: str) -> str:
        """
        Build prompt for refining reasoning based on feedback.

        Args:
            original_reasoning: The original thinking
            feedback: Feedback received
            outcome: What actually happened

        Returns:
            Prompt for reasoning refinement
        """
        loader = CorePromptLoader()
        return loader.build_refinement_prompt(
            original_reasoning=original_reasoning,
            feedback=feedback,
            outcome=outcome,
        )

    def get_task_type_from_message(self, message: str) -> Optional[str]:
        """
        Detect task type from user message.

        Args:
            message: User's message

        Returns:
            Detected task type or None
        """
        message_lower = message.lower()

        # Task type indicators
        indicators = {
            "code_generation": [
                "write",
                "create",
                "implement",
                "add function",
                "new feature",
                "generate code",
                "build",
            ],
            "debugging": [
                "fix",
                "bug",
                "error",
                "exception",
                "failing",
                "not working",
                "broken",
                "debug",
                "issue",
            ],
            "refactoring": [
                "refactor",
                "clean up",
                "reorganize",
                "restructure",
                "improve code",
                "optimize",
                "simplify",
            ],
            "security_review": [
                "security",
                "vulnerability",
                "audit",
                "penetration",
                "secure",
                "authentication",
                "authorization",
            ],
            "architecture_design": [
                "architecture",
                "design",
                "system design",
                "structure",
                "how should",
                "best approach",
                "planning",
            ],
        }

        for task_type, keywords in indicators.items():
            if any(kw in message_lower for kw in keywords):
                return task_type

        return None

    def determine_depth(self, message: str, estimated_complexity: float = 0.5) -> ReasoningDepth:
        """
        Determine appropriate reasoning depth.

        Args:
            message: User's message
            estimated_complexity: Complexity score 0-1

        Returns:
            Appropriate reasoning depth
        """
        message_lower = message.lower()

        # Quick indicators
        quick_indicators = ["show", "list", "what is", "read", "check", "status", "help", "how to"]

        # Deep indicators
        deep_indicators = [
            "refactor",
            "architecture",
            "design",
            "migration",
            "security audit",
            "optimize",
            "complex",
            "multiple files",
            "entire",
            "comprehensive",
            "thoroughly",
        ]

        if any(ind in message_lower for ind in quick_indicators):
            return ReasoningDepth.QUICK

        if any(ind in message_lower for ind in deep_indicators):
            return ReasoningDepth.DEEP

        if estimated_complexity > 0.7:
            return ReasoningDepth.DEEP
        elif estimated_complexity < 0.3:
            return ReasoningDepth.QUICK

        return ReasoningDepth.STANDARD


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_reasoning_system_prompt(task_type: Optional[str] = None) -> str:
    """Get the complete reasoning system prompt"""
    builder = ReasoningPromptBuilder()
    return builder.build_system_prompt(task_type=task_type)


def get_thinking_prompt(
    task: str,
    depth: ReasoningDepth = ReasoningDepth.STANDARD,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Get a thinking trigger prompt for a task"""
    builder = ReasoningPromptBuilder()
    return builder.build_thinking_prompt(task=task, context=context, depth=depth)


def detect_task_type(message: str) -> Optional[str]:
    """Detect task type from a message"""
    builder = ReasoningPromptBuilder()
    return builder.get_task_type_from_message(message)


def determine_reasoning_depth(message: str, complexity: float = 0.5) -> ReasoningDepth:
    """Determine appropriate reasoning depth for a message"""
    builder = ReasoningPromptBuilder()
    return builder.determine_depth(message, complexity)


# =============================================================================
# CLAUDE-STYLE 3-PHASE WORKFLOW PROMPTS
# =============================================================================

def get_claude_workflow_prompt(phase: str) -> str:
    """
    Get Claude-style workflow prompt for a specific phase.

    Args:
        phase: One of 'planning', 'execution', 'verification'

    Returns:
        Workflow prompt for the specified phase
    """
    loader = CorePromptLoader()
    try:
        return loader.get_phase_prompt(phase, "workflow")
    except KeyError:
        return ""


# Legacy constant for backwards compatibility
# Dynamically loads from YAML when accessed
class _WorkflowPromptsProxy:
    """Proxy class to load prompts on demand for backwards compatibility."""

    def get(self, phase: str, default: str = "") -> str:
        return get_claude_workflow_prompt(phase) or default

    def __getitem__(self, phase: str) -> str:
        return get_claude_workflow_prompt(phase)


CLAUDE_WORKFLOW_PROMPTS = _WorkflowPromptsProxy()


# =============================================================================
# CLAUDE-STYLE REASONING PHASE PROMPTS (from YAML)
# =============================================================================


def get_claude_reasoning_phase(phase_name: str) -> str:
    """
    Get a specific Claude-style reasoning phase template.

    This loads from the YAML configuration if available, otherwise returns
    a default template.

    Args:
        phase_name: One of 'perception', 'comprehension', 'analysis',
                   'reasoning', 'change_impact', 'decision',
                   'pre_execution', 'verification'

    Returns:
        Reasoning phase template
    """
    try:
        from .prompts import get_prompts_config

        config = get_prompts_config()
        phases = config._prompts_data.get("claude_reasoning_phases", {})
        return phases.get(phase_name, f"[PHASE: {phase_name.upper()}]\n")
    except Exception:
        # Fallback to basic template if config not available
        return f"[PHASE: {phase_name.upper()}]\n"


def get_claude_example(example_name: str) -> str:
    """
    Get a Claude-style interaction example.

    Args:
        example_name: Example identifier (e.g., 'simple_fix', 'complex_feature')

    Returns:
        Example interaction text
    """
    try:
        from .prompts import get_prompts_config

        config = get_prompts_config()
        examples = config._prompts_data.get("claude_examples", {})
        return examples.get(example_name, "")
    except Exception:
        return ""


# =============================================================================
# CLAUDE INTEGRATION HELPERS
# =============================================================================


class ClaudeReasoningBuilder:
    """Helper class for building Claude-style reasoning prompts."""

    @staticmethod
    def build_phase_prompt(
        phase_name: str, task_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build a complete prompt for a specific reasoning phase.

        Args:
            phase_name: Name of the reasoning phase
            task_context: Optional context dictionary

        Returns:
            Complete phase prompt with context
        """
        phase_template = get_claude_reasoning_phase(phase_name)

        if task_context:
            context_str = "\n".join(
                f"{k}: {v}" for k, v in task_context.items() if v
            )
            return f"{phase_template}\n\nContext:\n{context_str}"

        return phase_template

    @staticmethod
    def build_workflow_transition(
        from_phase: str, to_phase: str, reason: str = ""
    ) -> str:
        """
        Build a prompt for transitioning between workflow phases.

        Args:
            from_phase: Current phase
            to_phase: Target phase
            reason: Optional reason for transition

        Returns:
            Transition prompt
        """
        transition = f"\n--- Transitioning from {from_phase.upper()} to {to_phase.upper()} ---\n"
        if reason:
            transition += f"\nReason: {reason}\n"
        transition += f"\n{get_claude_workflow_prompt(to_phase)}"
        return transition

    @staticmethod
    def validate_reasoning_output(output: str) -> Dict[str, bool]:
        """
        Validate that reasoning output contains expected phase markers.

        Args:
            output: Agent's reasoning output

        Returns:
            Dictionary mapping phase names to presence (True/False)
        """
        phases = [
            "PERCEPTION",
            "COMPREHENSION",
            "ANALYSIS",
            "REASONING",
            "CHANGE IMPACT",
            "DECISION",
            "PRE-EXECUTION",
            "VERIFICATION",
        ]

        validation = {}
        for phase in phases:
            validation[phase] = f"[PHASE" in output and phase in output.upper()

        return validation

