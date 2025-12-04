"""
Hcode Agent with full tool integration.
Integrates all features: tools, sub-agents, web capabilities, interactive features.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console

# Import modern UI system
from ..ui import (
    get_console as get_themed_console,
    get_palette,
    Icons,
)
from ..ui.panels import (
    ToolPanel,
    ErrorPanel,
    SuccessPanel,
    AIMessagePanel,
)

from ..providers import (
    ProviderSelector,
    ProviderPreferences,
    TaskComplexity,
    TaskType,
    Message,
    AIProvider,
)
from ..tools import ToolManager, ToolExecutionContext
from ..agents import HcodeAgentOrchestrator, HcodeAgentType
from .context import ContextManager
from .safety import SafetyGuard

# Import optimization components
from .optimizations import (
    CachedTokenCounter,
    ToolResultCache,
    ParallelToolExecutor,
    ExecutionStateMachine,
    ExecutionState,
    get_token_counter,
)
from .analytics import (
    ExecutionAnalytics,
    get_analytics,
)

# Import memory system
try:
    from ..memory import MemoryManager, get_memory_manager

    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

# Import interaction logger
from .interaction_logger import get_logger, InteractionLogger

# Thinking block parser
import re
from dataclasses import dataclass
from typing import Tuple


@dataclass
class ThinkingBlock:
    """
    Thinking block with multi-dimensional reasoning capabilities.

    Supports advanced cognitive patterns:
    - Analytical decomposition
    - Hypothesis generation and testing
    - Meta-cognitive reflection
    - Adversarial self-critique
    - Confidence calibration
    """

    # === PHASE 1: PERCEPTION ===
    observe: str = ""  # What do I literally see/read?
    interpret: str = ""  # What does this mean?

    # === PHASE 2: COMPREHENSION ===
    understand: str = ""  # Core understanding of the request
    context: str = ""  # Relevant context and constraints
    assumptions: str = ""  # What am I assuming? (NEW)

    # === PHASE 3: ANALYSIS ===
    decompose: str = ""  # Break into sub-problems (NEW)
    dependencies: str = ""  # What depends on what? (NEW)
    options: str = ""  # Possible approaches

    # === PHASE 4: REASONING ===
    hypothesis: str = ""  # My best hypothesis (NEW)
    evidence: str = ""  # Evidence for/against (NEW)
    counterargument: str = ""  # Devil's advocate - why might I be wrong? (NEW)

    # === PHASE 5: DECISION ===
    decision: str = ""  # Final decision
    confidence: str = ""  # How confident am I? (NEW)
    fallback: str = ""  # What if this fails? (NEW)

    # === PHASE 6: VERIFICATION ===
    risk_check: str = ""  # Safety and risk assessment
    verify: str = ""  # How will I verify success? (NEW)

    # === META ===
    reflection: str = ""  # What did I learn? (NEW)
    raw_content: str = ""

    def is_valid(self) -> bool:
        """Check if thinking block has meaningful content"""
        # Valid if we have core understanding or decision
        return bool(self.understand or self.decision or self.observe)

    def get_confidence_level(self) -> str:
        """Extract confidence level from thinking"""
        if self.confidence:
            confidence_lower = self.confidence.lower()
            if any(
                word in confidence_lower
                for word in ["very high", "certain", "95%", "100%", "absolutely"]
            ):
                return "very_high"
            elif any(
                word in confidence_lower for word in ["high", "confident", "80%", "85%", "90%"]
            ):
                return "high"
            elif any(
                word in confidence_lower for word in ["medium", "moderate", "60%", "70%", "likely"]
            ):
                return "medium"
            elif any(
                word in confidence_lower for word in ["low", "uncertain", "unsure", "40%", "50%"]
            ):
                return "low"
            else:
                return "unknown"
        return "unknown"

    def has_fallback(self) -> bool:
        """Check if a fallback plan exists"""
        return bool(self.fallback and len(self.fallback.strip()) > 10)

    def is_self_critical(self) -> bool:
        """Check if thinking includes self-critique"""
        return bool(self.counterargument and len(self.counterargument.strip()) > 10)

    def summary(self) -> str:
        """Get a short summary of the decision"""
        if self.decision:
            # Extract the key decision
            lines = self.decision.strip().split("\n")
            for line in lines:
                if (
                    "best choice" in line.lower()
                    or "reason" in line.lower()
                    or "choose" in line.lower()
                ):
                    return line.strip()
            return lines[0] if lines else ""
        if self.hypothesis:
            return f"Hypothesis: {self.hypothesis.split(chr(10))[0][:60]}"
        return ""

    def quality_score(self) -> float:
        """Calculate thinking quality score (0-1)"""
        score = 0.0
        weights = {
            "understand": 0.15,
            "context": 0.10,
            "assumptions": 0.10,
            "decompose": 0.10,
            "options": 0.10,
            "hypothesis": 0.10,
            "counterargument": 0.10,
            "decision": 0.15,
            "confidence": 0.05,
            "risk_check": 0.05,
        }
        for field, weight in weights.items():
            value = getattr(self, field, "")
            if value and len(value.strip()) > 10:
                score += weight
        return min(score, 1.0)


def parse_thinking_block(text: str) -> Tuple[Optional[ThinkingBlock], str]:
    """
    Parse a thinking block from model output.

    Supports both simple (5-step) and advanced (multi-phase) thinking formats.

    Args:
        text: The model's response text

    Returns:
        Tuple of (ThinkingBlock or None, remaining text without thinking block)
    """
    # Pattern to match <thinking>...</thinking> blocks
    pattern = r"<thinking>(.*?)</thinking>"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

    if not match:
        return None, text

    thinking_content = match.group(1).strip()
    remaining_text = text[: match.start()] + text[match.end() :]
    remaining_text = remaining_text.strip()

    # Parse sections within thinking block
    block = ThinkingBlock(raw_content=thinking_content)

    # === MULTI-PHASE PARSING ===
    # Supports flexible section headers with various formats

    # Phase 1: Perception
    section_patterns = {
        # Perception phase
        "observe": [
            r"(?:OBSERVE|PERCEPTION|SEE|INPUT):?\s*(.*?)(?=(?:INTERPRET|UNDERSTAND|CONTEXT|ANALYZE|$))",
            r"\[OBSERVE\]:?\s*(.*?)(?=\[|$)",
        ],
        "interpret": [
            r"(?:INTERPRET|MEANING|IMPLIES):?\s*(.*?)(?=(?:UNDERSTAND|CONTEXT|ANALYZE|$))",
        ],
        # Comprehension phase
        "understand": [
            r"(?:\d+\.\s*)?UNDERSTAND(?:ING)?:?\s*(.*?)(?=(?:\d+\.\s*)?(?:CONTEXT|ASSUMPTIONS|ANALYZE|DECOMPOSE|OPTIONS|$))",
            r"\[UNDERSTAND\]:?\s*(.*?)(?=\[|$)",
            r"GOAL:?\s*(.*?)(?=(?:CONTEXT|$))",
        ],
        "context": [
            r"(?:\d+\.\s*)?CONTEXT:?\s*(.*?)(?=(?:\d+\.\s*)?(?:ASSUMPTIONS|ANALYZE|DECOMPOSE|OPTIONS|$))",
            r"\[CONTEXT\]:?\s*(.*?)(?=\[|$)",
            r"KNOWN:?\s*(.*?)(?=(?:ASSUMPTIONS|OPTIONS|$))",
        ],
        "assumptions": [
            r"(?:\d+\.\s*)?ASSUMPTIONS?:?\s*(.*?)(?=(?:\d+\.\s*)?(?:ANALYZE|DECOMPOSE|OPTIONS|HYPOTHESIS|$))",
            r"\[ASSUMPTIONS?\]:?\s*(.*?)(?=\[|$)",
            r"ASSUMING:?\s*(.*?)(?=(?:OPTIONS|$))",
        ],
        # Analysis phase
        "decompose": [
            r"(?:\d+\.\s*)?(?:DECOMPOSE|BREAKDOWN|SUB.?PROBLEMS?|STEPS?):?\s*(.*?)(?=(?:\d+\.\s*)?(?:DEPENDENCIES|OPTIONS|HYPOTHESIS|$))",
            r"\[DECOMPOSE\]:?\s*(.*?)(?=\[|$)",
        ],
        "dependencies": [
            r"(?:\d+\.\s*)?(?:DEPENDENCIES|DEPENDS|ORDER|SEQUENCE):?\s*(.*?)(?=(?:\d+\.\s*)?(?:OPTIONS|HYPOTHESIS|$))",
            r"\[DEPENDENCIES\]:?\s*(.*?)(?=\[|$)",
        ],
        "options": [
            r"(?:\d+\.\s*)?OPTIONS?:?\s*(.*?)(?=(?:\d+\.\s*)?(?:HYPOTHESIS|EVIDENCE|DECISION|CHOOSE|$))",
            r"\[OPTIONS?\]:?\s*(.*?)(?=\[|$)",
            r"ALTERNATIVES?:?\s*(.*?)(?=(?:DECISION|$))",
        ],
        # Reasoning phase
        "hypothesis": [
            r"(?:\d+\.\s*)?HYPOTHESIS:?\s*(.*?)(?=(?:\d+\.\s*)?(?:EVIDENCE|COUNTER|DECISION|$))",
            r"\[HYPOTHESIS\]:?\s*(.*?)(?=\[|$)",
            r"THEORY:?\s*(.*?)(?=(?:EVIDENCE|$))",
        ],
        "evidence": [
            r"(?:\d+\.\s*)?EVIDENCE:?\s*(.*?)(?=(?:\d+\.\s*)?(?:COUNTER|DECISION|$))",
            r"\[EVIDENCE\]:?\s*(.*?)(?=\[|$)",
            r"SUPPORT(?:ING)?:?\s*(.*?)(?=(?:COUNTER|$))",
        ],
        "counterargument": [
            r"(?:\d+\.\s*)?(?:COUNTER.?ARGUMENT|COUNTER|CHALLENGE|DEVIL.?S?.?ADVOCATE|WHY.?WRONG|CRITIQUE):?\s*(.*?)(?=(?:\d+\.\s*)?(?:DECISION|CONFIDENCE|$))",
            r"\[COUNTER\]:?\s*(.*?)(?=\[|$)",
            r"(?:BUT|HOWEVER|ALTERNATIVELY):?\s*(.*?)(?=(?:DECISION|$))",
        ],
        # Decision phase
        "decision": [
            r"(?:\d+\.\s*)?DECISION:?\s*(.*?)(?=(?:\d+\.\s*)?(?:CONFIDENCE|FALLBACK|RISK|VERIFY|$))",
            r"\[DECISION\]:?\s*(.*?)(?=\[|$)",
            r"(?:CHOOSE|SELECTED?|FINAL):?\s*(.*?)(?=(?:CONFIDENCE|RISK|$))",
            r"BEST\s*CHOICE:?\s*(.*?)(?=(?:REASON|CONFIDENCE|$))",
        ],
        "confidence": [
            r"(?:\d+\.\s*)?CONFIDENCE:?\s*(.*?)(?=(?:\d+\.\s*)?(?:FALLBACK|RISK|VERIFY|$))",
            r"\[CONFIDENCE\]:?\s*(.*?)(?=\[|$)",
            r"CERTAINTY:?\s*(.*?)(?=(?:FALLBACK|RISK|$))",
        ],
        "fallback": [
            r"(?:\d+\.\s*)?(?:FALLBACK|BACKUP|PLAN.?B|IF.?FAILS?|ALTERNATIVE):?\s*(.*?)(?=(?:\d+\.\s*)?(?:RISK|VERIFY|$))",
            r"\[FALLBACK\]:?\s*(.*?)(?=\[|$)",
        ],
        # Verification phase
        "risk_check": [
            r"(?:\d+\.\s*)?RISK(?:\s*CHECK)?:?\s*(.*?)(?=(?:\d+\.\s*)?(?:VERIFY|REFLECTION|$))",
            r"\[RISK\]:?\s*(.*?)(?=\[|$)",
            r"SAFETY:?\s*(.*?)(?=(?:VERIFY|$))",
        ],
        "verify": [
            r"(?:\d+\.\s*)?(?:VERIFY|VALIDATION?|CHECK|TEST|CONFIRM):?\s*(.*?)(?=(?:\d+\.\s*)?(?:REFLECTION|$))",
            r"\[VERIFY\]:?\s*(.*?)(?=\[|$)",
        ],
        # Meta phase
        "reflection": [
            r"(?:\d+\.\s*)?(?:REFLECTION?|LEARN(?:ED)?|INSIGHT|META):?\s*(.*?)$",
            r"\[REFLECT(?:ION)?\]:?\s*(.*?)(?=\[|$)",
        ],
    }

    # Try each pattern for each section
    for attr, patterns in section_patterns.items():
        for pattern in patterns:
            section_match = re.search(pattern, thinking_content, re.DOTALL | re.IGNORECASE)
            if section_match:
                value = section_match.group(1).strip()
                if value and len(value) > 2:  # Ignore empty or trivial matches
                    setattr(block, attr, value)
                    break  # Use first matching pattern

    return block, remaining_text


def format_thinking_display(
    block: ThinkingBlock, console: Console, debug_mode: bool = False
) -> None:
    """
    Display a thinking block with quality indicators.

    In normal mode (debug_mode=False): Shows only the key goal/understanding as simple text.
    In debug mode (debug_mode=True): Shows full panel with quality indicators.

    Args:
        block: The parsed thinking block
        console: Rich console for output
        debug_mode: If True, show full verbose panel. If False, show minimal output.
    """
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table

    # Get themed colors
    palette = get_palette()
    icons = Icons()

    # ═══════════════════════════════════════════════════════════════════════════
    # NORMAL MODE: Claude Code-style minimal output - just show the goal/intent
    # ═══════════════════════════════════════════════════════════════════════════
    if not debug_mode:
        # Show only the understanding/goal as simple text (like Claude Code does)
        if block.understand:
            goal_text = block.understand.strip()
            # Get first meaningful line
            first_line = goal_text.split("\n")[0].strip()
            if first_line.startswith("-"):
                first_line = first_line[1:].strip()
            # Don't show anything in normal mode - just like Claude Code
            # The goal is conveyed through the actual response
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # DEBUG MODE: Full verbose panel with quality indicators
    # ═══════════════════════════════════════════════════════════════════════════

    # Build the thinking display
    content = Text()

    # === QUALITY INDICATOR ===
    quality = block.quality_score()
    confidence = block.get_confidence_level()
    quality_bar = "[" + ("=" * int(quality * 10)) + ("-" * (10 - int(quality * 10))) + "]"
    quality_color = (
        palette.success if quality > 0.7 else palette.warning if quality > 0.4 else palette.error
    )

    content.append(f"Quality: {quality_bar} {quality:.0%}", style=f"dim {quality_color}")
    if confidence != "unknown":
        conf_colors = {
            "very_high": palette.success,
            "high": palette.info,
            "medium": palette.warning,
            "low": palette.error,
        }
        conf_color = conf_colors.get(confidence, palette.text_muted)
        content.append(f" | Confidence: {confidence}", style=f"dim {conf_color}")
    content.append("\n")

    # === KEY UNDERSTANDING === (full text in debug mode)
    if block.understand:
        content.append(f"{icons.BULLET} GOAL: ", style=f"bold {palette.info}")
        # Show full text in debug mode, not truncated
        goal_text = block.understand.strip()
        if goal_text.startswith("-"):
            goal_text = goal_text[1:].strip()
        content.append(goal_text + "\n", style=palette.text_primary)

    # === HYPOTHESIS (if advanced thinking) ===
    if block.hypothesis:
        content.append(f"{icons.BULLET} HYPOTHESIS: ", style=f"bold {palette.secondary}")
        # Full text in debug mode
        content.append(block.hypothesis.strip() + "\n", style=f"dim {palette.secondary}")

    # === SELF-CRITIQUE (shows depth of reasoning) ===
    if block.counterargument:
        content.append(f"{icons.WARNING} CHALLENGE: ", style=f"bold {palette.error}")
        counter_text = block.counterargument.strip()
        if counter_text.startswith("-"):
            counter_text = counter_text[1:].strip()
        # Full text in debug mode
        content.append(counter_text + "\n", style=f"dim {palette.error}")

    # === DECISION ===
    if block.decision:
        content.append(f"{icons.SUCCESS} DECISION: ", style=f"bold {palette.success}")
        # Full text in debug mode
        content.append(block.decision.strip() + "\n", style=palette.text_primary)

    # === FALLBACK (if exists) ===
    if block.fallback:
        content.append(f"{icons.ARROW_RIGHT} FALLBACK: ", style=f"bold {palette.warning}")
        # Full text in debug mode
        content.append(block.fallback.strip() + "\n", style=f"dim {palette.warning}")

    # === RISK CHECK ===
    if block.risk_check:
        content.append(f"{icons.WARNING} RISK: ", style=f"bold {palette.warning}")
        risk_text = block.risk_check.strip()
        if risk_text.startswith("-"):
            risk_text = risk_text[1:].strip()
        # Full text in debug mode
        content.append(risk_text, style=palette.text_muted)

    # Add indicators for thinking quality
    indicators = []
    if block.is_self_critical():
        indicators.append(f"[{palette.info}]◈ Self-Critical[/]")
    if block.has_fallback():
        indicators.append(f"[{palette.warning}]◈ Has Fallback[/]")
    if block.assumptions:
        indicators.append(f"[{palette.secondary}]◈ Explicit Assumptions[/]")

    # Build title with icon
    title = Text()
    title.append(f" {icons.THINKING} ", style=f"bold {palette.accent}")
    title.append("Deep Thinking", style=f"bold {palette.primary}")
    if indicators:
        title.append("  " + " ".join(indicators))

    console.print(Panel(content, title=title, border_style=palette.primary, padding=(0, 1)))


class HcodeAgent:
    """
    Hcode agent with comprehensive tool integration.

    Features:
    - Comprehensive tool system (Read, Write, Edit, Glob, Grep)
    - Web capabilities (WebFetch, WebSearch)
    - Interactive tools (AskUserQuestion, TodoWrite)
    - Jupyter notebook support
    - Sub-agents for specialized tasks (Explore, Plan, Implement)
    - Slash commands and skills
    - Hooks for custom workflows
    - Persistent memory system (AGENT.md, sessions, semantic memory)
    """

    def __init__(
        self,
        anthropic_key: Optional[str] = None,
        openai_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        anthropic_model: Optional[str] = None,
        openai_model: Optional[str] = None,
        root_dir: Optional[str] = None,
        preferences: Optional[ProviderPreferences] = None,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Hcode agent.

        Args:
            anthropic_key: Anthropic API key
            openai_key: OpenAI API key
            openai_base_url: Custom OpenAI base URL
            anthropic_model: Specific Anthropic model name
            openai_model: Specific OpenAI model name
            root_dir: Root directory for operations
            preferences: Provider preferences
            session_id: Session ID to resume
            config: Configuration dictionary
        """
        self.root_dir = Path(root_dir or Path.cwd())
        self.console = get_themed_console()  # Use themed console
        self._palette = get_palette()
        self._icons = Icons()
        self.config = config or {}
        self.session_id = session_id

        # Initialize provider selector
        self.provider_selector = ProviderSelector(
            anthropic_key=anthropic_key,
            openai_key=openai_key,
            openai_base_url=openai_base_url,
            anthropic_model=anthropic_model,
            openai_model=openai_model,
            preferences=preferences or ProviderPreferences(),
        )

        # Initialize tool manager
        self.tool_manager = ToolManager(root_dir=str(self.root_dir), config=self.config)

        # Initialize agent orchestrator
        self.agent_orchestrator = HcodeAgentOrchestrator(
            provider_selector=self.provider_selector, tool_registry=self.tool_manager.tool_registry
        )

        # Connect agent orchestrator to tool manager
        self.tool_manager.set_agent_orchestrator(self.agent_orchestrator)

        # Initialize context and safety
        self.context_manager = ContextManager(root_dir=str(self.root_dir), session_id=session_id)
        self.safety_guard = SafetyGuard(root_dir=str(self.root_dir))

        # Initialize continuation manager for long outputs
        from .continuation import ContinuationManager, ContextWindowManager

        self.continuation_manager = ContinuationManager(
            max_continuations=10, max_total_tokens=100000, console=self.console
        )
        self.context_window_manager = ContextWindowManager(
            max_context_tokens=128000, reserve_output_tokens=8192
        )

        self.current_provider: Optional[AIProvider] = None

        # Initialize memory system (if available)
        self.memory_manager: Optional["MemoryManager"] = None
        if MEMORY_AVAILABLE:
            try:
                self.memory_manager = get_memory_manager(
                    project_root=self.root_dir, session_id=session_id
                )
                self._debug_print("[dim]Memory system initialized[/dim]")
            except Exception as e:
                self.console.print(f"[dim yellow]Memory system unavailable: {e}[/dim yellow]")
                self.memory_manager = None

        # Initialize interaction logger
        self.logger: InteractionLogger = get_logger()
        self._debug_print(f"[dim]Logging to: {self.logger.log_dir}[/dim]")

        # Initialize optimization components
        self.token_counter = get_token_counter()
        self.tool_cache = ToolResultCache(ttl_seconds=300)  # 5 min cache
        self.analytics = get_analytics()
        self.execution_state = ExecutionStateMachine()

        # Initialize resilient provider if multiple providers available
        self._init_resilient_provider(anthropic_key, openai_key, openai_base_url)

    def _is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.config.get("debug", False) or self.config.get("ui", {}).get("debug_mode", False)

    def _debug_print(self, message: str):
        """Print message only if debug mode is enabled."""
        if self._is_debug_mode():
            self.console.print(message)

    def _init_resilient_provider(
        self,
        anthropic_key: Optional[str],
        openai_key: Optional[str],
        openai_base_url: Optional[str],
    ):
        """Initialize resilient provider with automatic failover"""
        self.resilient_provider = None

        # Only create resilient provider if we have multiple providers
        if anthropic_key and openai_key:
            try:
                from ..providers.resilient_provider import (
                    ResilientProvider,
                    create_resilient_provider,
                )

                self.resilient_provider = create_resilient_provider(
                    anthropic_key=anthropic_key,
                    openai_key=openai_key,
                    primary="anthropic",  # Default to Anthropic
                )

                # Set callbacks for failover events
                def on_failover(from_prov: str, to_prov: str, error: Exception):
                    self.console.print(
                        f"[yellow]Provider failover: {from_prov} -> {to_prov} "
                        f"(reason: {type(error).__name__})[/yellow]"
                    )
                    self.analytics.record_tool_execution(
                        tool_name="provider_failover",
                        duration=0,
                        success=True,
                        task_context=f"{from_prov}->{to_prov}",
                    )

                def on_recovery(provider: str):
                    self.console.print(f"[green]Provider {provider} recovered[/green]")

                self.resilient_provider.set_failover_callback(on_failover)
                self.resilient_provider.set_recovery_callback(on_recovery)

                self._debug_print(
                    "[dim]Resilient provider initialized with automatic failover[/dim]"
                )
            except Exception as e:
                self.console.print(f"[dim yellow]Resilient provider unavailable: {e}[/dim yellow]")

    async def execute_task(
        self,
        task: str,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        task_type: TaskType = TaskType.CODE_GENERATION,
        stream: bool = True,
        use_sub_agents: bool = False,
    ) -> str:
        """
        Execute a task using the agent capabilities.

        Args:
            task: Task description
            complexity: Task complexity
            task_type: Task type
            stream: Stream responses
            use_sub_agents: Use specialized sub-agents

        Returns:
            Task result
        """
        # Start safety transaction
        tx_id = self.safety_guard.start_transaction(description=task)

        # Track execution with analytics
        import time

        task_start_time = time.time()
        self.analytics.start_conversation(self.context_manager.session_id)
        self.execution_state.transition(ExecutionState.PLANNING)

        try:
            # Use sub-agents if requested
            if use_sub_agents:
                self.execution_state.transition(ExecutionState.EXECUTING)
                result = await self.agent_orchestrator.auto_execute(task)
                response = result.output

                self.execution_state.transition(ExecutionState.COMPLETED)
                self.analytics.end_conversation(
                    self.context_manager.session_id,
                    success=True,
                    total_cost=self.current_provider.total_cost if self.current_provider else 0,
                )
                self.safety_guard.commit_transaction()
                return response

            # Select provider
            self.current_provider = self.provider_selector.select_provider(
                complexity=complexity, task_type=task_type
            )

            self.console.print(f"[bold green]Using {self.current_provider}[/bold green]")

            # Start logging session
            provider_name = (
                self.current_provider.get_provider_name()
                if hasattr(self.current_provider, "get_provider_name")
                else str(self.current_provider)
            )
            model_name = (
                self.current_provider.model
                if hasattr(self.current_provider, "model")
                else "unknown"
            )
            self.logger.start_session(
                task=task,
                provider=provider_name,
                model=model_name,
                metadata={
                    "complexity": (
                        complexity.value if hasattr(complexity, "value") else str(complexity)
                    )
                },
            )

            # IMPORTANT: Clear context for new unrelated tasks to prevent context pollution
            # This ensures old test runs don't influence new exploration tasks
            self._maybe_clear_context_for_new_task(task)

            # Set system prompt with tool descriptions and memory context
            system_prompt = self._build_system_prompt(query=task)
            self.context_manager.set_system_prompt(system_prompt)

            # Add task to context with format guidance for OSS models
            formatted_task = self._format_user_task(task)
            self.context_manager.add_message(
                role="user", content=formatted_task, importance=1.0, provider=self.current_provider
            )

            # Add message to memory system
            if self.memory_manager:
                try:
                    self.memory_manager.add_message(
                        role="user", content=task, extract_memories=True
                    )
                except Exception:
                    pass  # Memory system is optional

            # Execute with tool calling
            self.execution_state.transition(ExecutionState.EXECUTING)
            response = await self._execute_with_tools(stream=stream)

            # Add response to context
            self.context_manager.add_message(
                role="assistant", content=response, importance=0.8, provider=self.current_provider
            )

            # Add response to memory system
            if self.memory_manager:
                try:
                    self.memory_manager.add_message(
                        role="assistant", content=response, extract_memories=True
                    )
                except Exception:
                    pass  # Memory system is optional

            # End logging session
            self.logger.end_session(final_result=response)

            # Track completion with analytics
            self.execution_state.transition(ExecutionState.COMPLETED)
            task_duration = time.time() - task_start_time
            self.analytics.end_conversation(
                self.context_manager.session_id,
                success=True,
                total_tokens=self.token_counter.count(response),
                total_cost=self.current_provider.total_cost if self.current_provider else 0,
            )

            self.safety_guard.commit_transaction()
            return response

        except Exception as e:
            # Log error before handling
            self.logger.log_error(str(e), context={"task": task})
            self.logger.end_session(final_result="", errors=[str(e)])

            # Track failure with analytics
            self.execution_state.transition(ExecutionState.IDLE)  # Reset state on error
            self.analytics.end_conversation(self.context_manager.session_id, success=False)
            self.analytics.record_tool_execution(
                tool_name="task_execution",
                duration=time.time() - task_start_time,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                task_context=task[:100],
            )

            self.safety_guard.rollback_transaction()

            # Import LLMConnectionError for checking
            from ..providers.openai_provider import LLMConnectionError

            error_str = str(e).lower()
            error_type = type(e).__name__

            # Handle LLMConnectionError specifically
            if isinstance(e, LLMConnectionError):
                self.console.print(f"[bold red][X] LLM Connection Error:[/bold red] {str(e)}")
                if hasattr(e, "base_url") and e.base_url:
                    self.console.print(f"[dim]API Endpoint: {e.base_url}[/dim]")
                self.console.print(
                    "[dim]Check your network connection and API endpoint configuration.[/dim]"
                )
                self.console.print(
                    "[dim]You can also check your OPENAI_BASE_URL environment variable.[/dim]"
                )
                raise

            # Handle built-in connection errors
            elif isinstance(e, ConnectionError) or "connection" in error_str:
                self.console.print(f"[bold red][X] Connection Error:[/bold red] {str(e)}")
                self.console.print(
                    "[dim]Check your network connection and API endpoint configuration.[/dim]"
                )
                raise

            elif isinstance(e, TimeoutError) or "timeout" in error_str:
                self.console.print(f"[bold red][X] Timeout Error:[/bold red] {str(e)}")
                self.console.print(
                    "[dim]The request took too long. Try again or increase timeout in config.[/dim]"
                )
                raise

            elif isinstance(e, RuntimeError):
                if "rate limit" in error_str:
                    self.console.print(f"[bold yellow][!] Rate Limited:[/bold yellow] {str(e)}")
                    self.console.print("[dim]Please wait a moment before trying again.[/dim]")
                else:
                    self.console.print(f"[bold red][X] Error:[/bold red] {str(e)}")
                raise

            elif isinstance(e, ValueError):
                self.console.print(f"[bold red][X] Configuration Error:[/bold red] {str(e)}")
                raise

            else:
                self.console.print(
                    f"[bold red][X] Unexpected Error ({error_type}):[/bold red] {str(e)}"
                )
                raise

    def _build_system_prompt(self, query: Optional[str] = None) -> str:
        """Build system prompt with tool documentation and memory context (Claude Code style)"""
        # Get base system prompt from external config
        base_prompt = self.current_provider.get_system_prompt_for_coding()

        # Get tool documentation from external config (Claude Code style)
        from ..config.tools import get_tools_config

        tools_config = get_tools_config()
        tool_docs = tools_config.get_tool_documentation()

        # Add tool documentation
        base_prompt += "\n\n" + tool_docs

        # Add memory context if available
        if self.memory_manager:
            try:
                memory_context = self.memory_manager.build_system_context(query=query)
                if memory_context:
                    base_prompt += "\n\n" + memory_context
            except Exception as e:
                self.console.print(
                    f"[dim yellow][!] Could not load memory context: {e}[/dim yellow]"
                )

        return base_prompt

    def _get_tool_call_format_instructions(self) -> str:
        """Get explicit instructions for tool call format when native function calling is not supported"""
        return """

## TOOL CALL FORMAT

To use tools, output JSON in a code fence. You can include explanations, but the JSON must be properly formatted.

### Tool Call Format:
```json
{"tool": "ToolName", "parameters": {"param1": "value1", "param2": "value2"}}
```

### Available Tools:

**WriteTool** - Write/create files (MOST IMPORTANT - use this to generate requested content):
```json
{"tool": "WriteTool", "parameters": {"file_path": "filename.ext", "content": "full file content here"}}
```

**ReadTool** - Read existing files:
```json
{"tool": "ReadTool", "parameters": {"file_path": "path/to/file"}}
```

**EditTool** - Modify existing files:
```json
{"tool": "EditTool", "parameters": {"file_path": "path/to/file", "old_string": "text to replace", "new_string": "new text"}}
```

**GlobTool** - Find files by pattern:
```json
{"tool": "GlobTool", "parameters": {"pattern": "**/*.py"}}
```

**GrepTool** - Search file contents:
```json
{"tool": "GrepTool", "parameters": {"pattern": "search_term"}}
```

**BashTool** - Run shell commands:
```json
{"tool": "BashTool", "parameters": {"command": "ls -la"}}
```

**LSTool** - List directory:
```json
{"tool": "LSTool", "parameters": {"path": "."}}
```

### CRITICAL: When asked to CREATE or GENERATE a file:
1. Generate the COMPLETE content directly
2. Use WriteTool immediately with the full content
3. Do NOT ask questions - just create the file
4. Do NOT explore the codebase first unless specifically asked

Example - User asks "Create a hello.html file":
```json
{"tool": "WriteTool", "parameters": {"file_path": "hello.html", "content": "<!DOCTYPE html>\\n<html>\\n<head><title>Hello</title></head>\\n<body><h1>Hello World</h1></body>\\n</html>"}}
```

### IMPORTANT for multi-line content:
Use \\n for newlines in JSON strings. The system will convert them to actual newlines.

### IMPORTANT: Handling Continuation Messages
When the user says things like "yes", "proceed", "continue", "do it", "ok", or similar confirmations:
1. This means they are confirming the previous task discussed in the conversation
2. You should continue with what you were planning to do
3. Do NOT ask for more details - just proceed with the task
4. Look at the conversation history to understand what task the user is confirming
5. Execute the task immediately using the appropriate tools"""

    async def _execute_with_tools(self, stream: bool = False) -> str:
        """
        Execute task with tool calling support, automatic tool execution loop,
        and automatic continuation for long outputs.

        Implements Claude Code-like seamless generation by:
        1. Detecting when output is truncated (finish_reason = "length")
        2. Automatically continuing generation
        3. Merging responses seamlessly
        4. Checking todo list for incomplete tasks and continuing
        5. STOPPING ONLY when the task is truly complete

        ROBUSTNESS FEATURES:
        - Graceful error recovery - never crashes, always returns something
        - Automatic retry on transient errors
        - Truncated content detection and continuation
        - Partial results saved on failure
        - NO HARD ITERATION LIMIT - continues until task completion

        The agent will continue until:
        - Task is explicitly completed (model says done/complete)
        - Too many consecutive errors occur (circuit breaker)
        - Model is stuck in a loop (same response repeated)
        """
        import json
        import traceback

        # Get tool schemas from external config (Claude Code style)
        from ..config.tools import get_tools_config

        tools_config = get_tools_config()
        provider_name = self.current_provider.get_provider_name().lower()

        if provider_name == "openai":
            tool_schemas = tools_config.get_openai_schemas()
        else:
            tool_schemas = tools_config.get_anthropic_schemas()

        all_response_parts = []
        iteration = 0
        consecutive_no_tool_calls = 0  # Track iterations without tool calls
        last_tool_call_iteration = 0
        consecutive_errors = 0  # Track consecutive errors for circuit breaker
        max_consecutive_errors = 3
        partial_file_content = {}  # Track partial file content for long writes
        accumulated_results = []  # Track all results even on failure
        last_successful_response = ""  # Keep track of last successful output

        # LLM-DRIVEN COMPLETION: Track todo continuation prompts
        todo_continuation_prompts = 0  # Track how many times we've prompted about incomplete todos
        max_todo_continuation_prompts = 3  # Safety limit to prevent infinite loops

        # SUBSTANTIVE ANSWER CHECK: Track prompts for actual user-facing response
        answer_prompts = 0  # Track how many times we've prompted for substantive answer
        max_answer_prompts = (
            2  # Safety limit - if model can't provide answer after 2 prompts, accept it
        )

        # RETRY LOOP PREVENTION: Track failed commands to prevent infinite retries
        failed_commands: Dict[str, int] = {}  # command -> failure count
        max_command_retries = 2  # Maximum times to retry the same failing command

        # LOOP DETECTION: Track recent responses to detect stuck loops
        recent_responses: List[str] = []
        max_recent_responses = 5
        stuck_threshold = 3  # If same response appears this many times, we're stuck

        # MAX ITERATION SAFETY: Prevent runaway loops
        max_iterations = 50  # Safety limit - should complete most tasks

        # TASK TRACKING: Track completed actions for summary
        completed_actions: List[Dict[str, Any]] = []

        # Continue until task completion or max iterations
        while iteration < max_iterations:
            try:  # ROBUSTNESS: Wrap each iteration in try-except
                iteration += 1

                # Progress feedback every 10 iterations
                if iteration > 1 and iteration % 10 == 0:
                    self._debug_print(f"[dim][...] Processing... (iteration {iteration})[/dim]")

                # LOOP DETECTION: Check if we're stuck repeating the same response
                if len(recent_responses) >= stuck_threshold:
                    # Check for repeated responses
                    last_response_hash = hash(recent_responses[-1][:500]) if recent_responses else 0
                    repeat_count = sum(
                        1 for r in recent_responses if hash(r[:500]) == last_response_hash
                    )
                    if repeat_count >= stuck_threshold:
                        self._debug_print(
                            f"[yellow][!] Detected stuck loop (same response {repeat_count} times). Breaking out.[/yellow]"
                        )
                        break

                # Get messages with context - ensure we leave room for output
                context_window = self.current_provider.get_context_window()
                max_output_tokens = self.current_provider.max_tokens

                # Calculate available tokens for context, with safety minimum
                available_for_context = context_window - max_output_tokens - 2000  # Extra buffer
                min_context_tokens = 4000  # Minimum context to be useful

                if available_for_context < min_context_tokens:
                    # Context overflow - need to truncate more aggressively
                    self._debug_print(
                        f"[yellow][!] Context near limit. Truncating older messages.[/yellow]"
                    )
                    available_for_context = min_context_tokens

                messages = self.context_manager.get_messages(max_tokens=available_for_context)

                # CLAUDE CODE STYLE: Show thinking indicator on first iteration
                if iteration == 1:
                    if self._is_debug_mode():
                        self.console.print(f"[dim][*] Thinking...[/dim]", end="\r")

                # Generate completion with tools
                finish_reason = "stop"
                response_text = ""
                raw_response = None

                try:
                    if stream and iteration == 1:
                        # Only stream the first iteration
                        response_parts = []
                        stream_result = await self.current_provider.generate_completion(
                            messages=messages,
                            stream=True,
                            functions=tool_schemas if provider_name == "openai" else None,
                            tools=tool_schemas if provider_name == "anthropic" else None,
                        )

                        # Clear thinking indicator
                        self.console.print(" " * 20, end="\r")

                        async for chunk in stream_result:
                            response_parts.append(chunk)
                            print(chunk, end="", flush=True)

                        print()  # New line
                        response_text = "".join(response_parts)
                        # For streaming, we need to check finish reason differently
                        # Assume "stop" unless the response looks truncated
                        if self.continuation_manager.should_continue("stop", response_text):
                            finish_reason = "length"
                    else:
                        response = await self.current_provider.generate_completion(
                            messages=messages,
                            stream=False,
                            functions=tool_schemas if provider_name == "openai" else None,
                            tools=tool_schemas if provider_name == "anthropic" else None,
                        )

                        # Clear thinking indicator
                        if iteration == 1:
                            self.console.print(" " * 20, end="\r")

                        response_text = response.content
                        raw_response = (
                            response.raw_response if hasattr(response, "raw_response") else None
                        )
                        finish_reason = (
                            response.finish_reason if hasattr(response, "finish_reason") else "stop"
                        )

                    # Success - reset error counter and save successful response
                    consecutive_errors = 0
                    if response_text.strip():
                        last_successful_response = response_text

                    # EMPTY RESPONSE HANDLING: If first response is empty, add explicit instruction
                    if iteration == 1 and not response_text.strip():
                        self.console.print(
                            f"[dim yellow][!] Empty first response. Adding guidance...[/dim yellow]"
                        )
                        # Add a direct instruction to the context
                        self.context_manager.add_message(
                            role="user",
                            content="Please respond to the task above. Start with a brief explanation of what you'll do, then call a tool.",
                            importance=1.0,
                            provider=self.current_provider,
                        )
                        continue  # Retry with the guidance

                except Exception as gen_error:
                    # Handle generation errors gracefully
                    consecutive_errors += 1
                    error_msg = str(gen_error)
                    self.console.print(
                        f"[bold red][!] Generation error (attempt {consecutive_errors}/{max_consecutive_errors}): {error_msg[:100]}[/bold red]"
                    )

                    if consecutive_errors >= max_consecutive_errors:
                        self.console.print(
                            f"[bold red][X] Too many consecutive errors. Returning accumulated results.[/bold red]"
                        )
                        # Return whatever we have so far
                        if all_response_parts:
                            return "\n".join(all_response_parts)
                        elif last_successful_response:
                            return last_successful_response
                        else:
                            return f"Task interrupted due to errors: {error_msg}"

                    # Wait before retry
                    await asyncio.sleep(2)
                    continue

                all_response_parts.append(response_text)
                accumulated_results.append({"iteration": iteration, "response": response_text})

                # LOOP DETECTION: Track recent responses
                recent_responses.append(response_text)
                if len(recent_responses) > max_recent_responses:
                    recent_responses.pop(0)  # Remove oldest

                # DEEP THINKING: Parse and display thinking blocks
                thinking_block, response_without_thinking = parse_thinking_block(response_text)

                if thinking_block and thinking_block.is_valid():
                    # Display the thinking block (only shows verbose panel in debug mode)
                    debug_mode = self.config.get("debug", False) or self.config.get("ui", {}).get(
                        "debug_mode", False
                    )
                    format_thinking_display(thinking_block, self.console, debug_mode=debug_mode)

                    # Log the thinking for debugging
                    self.logger.log_interaction(
                        iteration=iteration,
                        request_messages=[],
                        response_text=f"[THINKING] {thinking_block.summary()}",
                        finish_reason="thinking",
                        tool_calls_detected=0,
                        continuation_needed=False,
                        pending_work_detected=False,
                        metadata={"thinking": thinking_block.raw_content},
                    )

                    # AUTO-EXTRACT TODOS FROM THINKING BLOCK - DISABLED
                    # This was causing garbage todos from thinking text patterns
                    # Let the model explicitly call TodoWrite instead
                    # auto_todos = self._extract_todos_from_thinking(thinking_block.raw_content)
                    # if auto_todos and iteration <= 2:
                    #     ... (disabled - creates garbage todos from thinking patterns)

                # ═══════════════════════════════════════════════════════════════════════════════
                # DISPLAY RESPONSE TEXT: Show the actual response to the user (not just thinking)
                # For non-streaming iterations, we need to explicitly display the response
                # ═══════════════════════════════════════════════════════════════════════════════
                if iteration > 1 or not stream:
                    # Get the response without thinking and without tool call JSON
                    display_text = (
                        response_without_thinking if response_without_thinking else response_text
                    )

                    # Strip out tool call JSON patterns (these shouldn't be shown to user)
                    import re

                    # Remove JSON blocks inside code fences (```json ... ```)
                    display_text = re.sub(r"```json\s*\{[\s\S]*?\}\s*```", "", display_text)

                    # Remove multiline JSON tool calls with nested content
                    # This handles: {"tool": "X", "parameters": {...}}
                    display_text = re.sub(
                        r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[\s\S]*?\}\s*\}',
                        "",
                        display_text,
                        flags=re.DOTALL,
                    )

                    # Remove TodoWrite JSON specifically (handles arrays in todos)
                    display_text = re.sub(
                        r'\{\s*"tool"\s*:\s*"TodoWrite"\s*,\s*"parameters"\s*:\s*\{[\s\S]*?"todos"\s*:\s*\[[\s\S]*?\]\s*\}\s*\}',
                        "",
                        display_text,
                        flags=re.DOTALL,
                    )

                    # Remove simple tool JSON
                    display_text = re.sub(
                        r'\{\s*"tool"\s*:\s*"[^"]+"\s*\}', "", display_text, flags=re.DOTALL
                    )

                    # Remove any remaining JSON objects that look like tool calls
                    display_text = re.sub(
                        r'\{[^{}]*"tool"[^{}]*\}', "", display_text, flags=re.DOTALL
                    )

                    # Clean up excess whitespace
                    display_text = re.sub(r"\n\s*\n\s*\n+", "\n\n", display_text)
                    display_text = display_text.strip()

                    # Only display if there's substantive content (not just whitespace or tool metadata)
                    if display_text and len(display_text) > 20:
                        # Check it's not just thinking metadata patterns
                        if not re.match(
                            r"^\s*\[(?:UNDERSTAND|CONTEXT|OPTIONS|DECISION|RISK|ASSUMPTIONS|OK|!)\]",
                            display_text,
                        ):
                            self.console.print(f"\n{display_text}\n")

                # THINKING ENFORCEMENT: For OpenAI/OSS models, if no thinking block found
                # on first iteration with a tool call, request thinking first
                if provider_name == "openai" and iteration == 1:
                    tool_calls_preview = self._extract_tool_calls(
                        raw_response, response_text, provider_name
                    )
                    if tool_calls_preview and not thinking_block:
                        # Model skipped thinking - request it thinks first
                        self._debug_print(
                            f"[dim yellow][!] Requesting deeper thinking before tool use...[/dim yellow]"
                        )
                        self.context_manager.add_message(
                            role="user",
                            content="""STOP! Before using that tool, you MUST think first.

Output a <thinking> block that explains:
1. UNDERSTAND: What is the user asking?
2. CONTEXT: What do I know?
3. OPTIONS: What tools could I use?
4. DECISION: Why this specific tool?
5. RISK CHECK: Is this safe?

Then repeat your tool call.""",
                            importance=1.0,
                            provider=self.current_provider,
                        )
                        # Don't execute the tool yet, continue to get thinking
                        continue

                # Check for and execute tool calls
                tool_calls = self._extract_tool_calls(raw_response, response_text, provider_name)

                # Track if TodoWrite has been used
                has_used_todowrite = any(
                    tc.get("name", "").lower() == "todowrite" for tc in (tool_calls or [])
                ) or any(
                    action.get("tool", "").lower() == "todowrite" for action in completed_actions
                )

                # ENFORCE TODOWRITE: On iteration 2, if no TodoWrite used, prompt for it
                if iteration == 2 and not has_used_todowrite and tool_calls:
                    self._debug_print(
                        f"[dim yellow][!] Reminder: Use TodoWrite to track your tasks![/dim yellow]"
                    )
                    # Add reminder to context
                    self.context_manager.add_message(
                        role="user",
                        content="IMPORTANT: Please use TodoWrite to create a task list before continuing. Use TodoWrite with todos array to plan your steps.",
                        importance=1.0,
                        provider=self.current_provider,
                    )

                # Log this interaction (full response, not truncated)
                self.logger.log_interaction(
                    iteration=iteration,
                    request_messages=(
                        messages[-3:] if len(messages) > 3 else messages
                    ),  # Last 3 for brevity
                    response_text=response_text,  # FULL response
                    finish_reason=finish_reason,
                    tool_calls_detected=len(tool_calls) if tool_calls else 0,
                    continuation_needed=False,  # Will update if needed
                    pending_work_detected=False,  # Will update if needed
                )

                if tool_calls:
                    consecutive_no_tool_calls = 0
                    last_tool_call_iteration = iteration

                    # Execute tool calls and add results to context
                    try:
                        tool_results = await self._execute_tool_calls(tool_calls)
                        # Track completed actions for summary
                        for tool_name, result, arguments in tool_results:
                            action = {
                                "tool": tool_name,
                                "success": result.success,
                                "args": arguments,
                                "iteration": iteration,
                            }
                            completed_actions.append(action)

                            # AUTO-UPDATE TODOS: Mark matching todos as completed
                            self._auto_update_todos(action)
                    except Exception as tool_error:
                        self.console.print(
                            f"[bold red][!] Tool execution error: {tool_error}[/bold red]"
                        )
                        tool_results = []
                        # Continue anyway - don't crash

                    # Add assistant message with tool calls to context
                    self.context_manager.add_message(
                        role="assistant",
                        content=response_text,
                        importance=0.7,
                        provider=self.current_provider,
                    )

                    # Add tool results to context with continuation guidance
                    for tool_name, result, arguments in tool_results:
                        # Log tool call with FULL output (not truncated)
                        self.logger.log_tool_call(
                            tool_name=tool_name,
                            arguments=arguments,
                            success=result.success,
                            output=result.output,  # FULL output for debugging
                            error=result.error,
                            metadata=result.metadata if hasattr(result, "metadata") else {},
                        )

                        # RETRY LOOP PREVENTION: Track failed commands
                        if not result.success:
                            # Create a unique key for the command
                            cmd_key = self._get_command_key(tool_name, arguments)
                            failed_commands[cmd_key] = failed_commands.get(cmd_key, 0) + 1

                            if failed_commands[cmd_key] > max_command_retries:
                                self.console.print(
                                    f"[bold red][!] Command has failed {failed_commands[cmd_key]} times. Stopping retry loop.[/bold red]"
                                )
                                self.logger.log_error(
                                    f"Retry loop detected: {tool_name} failed {failed_commands[cmd_key]} times",
                                    context={"command_key": cmd_key, "arguments": arguments},
                                )

                        if result.success:
                            # Check if this was a truncated file write that needs continuation
                            is_truncated_write = (
                                result.metadata
                                and result.metadata.get("is_truncated", False)
                                and tool_name.lower() in ["writetool", "write"]
                            )

                            if is_truncated_write:
                                # Special handling for truncated file writes
                                file_path = arguments.get("file_path", "the file")
                                truncation_reason = result.metadata.get(
                                    "truncation_reason", "incomplete content"
                                )
                                result_content = f"""Tool '{tool_name}' wrote PARTIAL content to {file_path}.

[!]️ FILE CONTENT IS TRUNCATED: {truncation_reason}

The file was written but the content appears incomplete. You MUST continue writing the remaining content.

To continue the file, use WriteTool with mode='append':
{{"tool": "WriteTool", "parameters": {{"file_path": "{file_path}", "content": "<remaining content>", "mode": "append"}}}}

IMPORTANT: Continue from EXACTLY where the content was cut off. Do not restart the file.

Continue generating the remaining content now:"""
                            else:
                                # Limit output size to prevent context overflow
                                # Use SMART truncation: keep head + tail to preserve important info
                                MAX_OUTPUT_CHARS = 15000  # ~4k tokens
                                output_text = result.output
                                output_truncated = False

                                if len(output_text) > MAX_OUTPUT_CHARS:
                                    output_truncated = True
                                    # Smart truncation: keep first part AND last part
                                    # This ensures we see both the start and end of output
                                    # (e.g., for test results, we need the TOTAL line at the end)
                                    HEAD_CHARS = int(MAX_OUTPUT_CHARS * 0.6)  # 60% for head
                                    TAIL_CHARS = int(MAX_OUTPUT_CHARS * 0.35)  # 35% for tail
                                    head = output_text[:HEAD_CHARS]
                                    tail = output_text[-TAIL_CHARS:]
                                    truncated_count = len(output_text) - HEAD_CHARS - TAIL_CHARS
                                    output_text = f"{head}\n\n... [{truncated_count} characters omitted] ...\n\n{tail}"

                                result_content = f"""Tool '{tool_name}' executed successfully.

RESULT:
{output_text}

NEXT STEPS - You MUST do one of the following:
1. If the task requires more exploration, call another tool using the correct format:
   {{"tool": "ToolName", "parameters": {{"param": "value"}}}}

2. If you have enough information, provide a complete answer to the user in natural language.

DO NOT output partial JSON like {{"path": "..."}} - this is invalid.
DO NOT stop without completing the user's request.

What will you do next?"""
                        else:
                            # CRITICAL: For failed tools, include BOTH error and output
                            # Many test runners put actual errors in stdout, not stderr
                            full_error_info = result.error or "Unknown error"

                            # Include stdout too - it often contains critical error details
                            # But limit size to prevent context overflow
                            MAX_ERROR_OUTPUT_CHARS = 10000  # ~2.5k tokens
                            output_info = ""
                            if result.output and result.output.strip():
                                output_text = result.output
                                if len(output_text) > MAX_ERROR_OUTPUT_CHARS:
                                    output_text = output_text[:MAX_ERROR_OUTPUT_CHARS]
                                    output_text += (
                                        f"\n\n... [TRUNCATED - see full output in log file]"
                                    )
                                output_info = f"\n\nFULL OUTPUT (may contain additional error details):\n{output_text}"

                            # Check for retry loop
                            cmd_key = self._get_command_key(tool_name, arguments)
                            retry_count = failed_commands.get(cmd_key, 0)
                            retry_warning = ""
                            if retry_count >= max_command_retries:
                                retry_warning = f"""

[!] STOP! This exact command has FAILED {retry_count} TIMES already.
DO NOT run this command again. You MUST try a DIFFERENT approach:
- Read the error message carefully
- Use Read or Grep to investigate the root cause
- Fix the underlying issue before running tests again
- Or ask the user for help if you're stuck
"""

                            result_content = f"""Tool '{tool_name}' failed.

ERROR: {full_error_info}
{output_info}
{retry_warning}
IMPORTANT: Read the FULL error message above carefully. Do NOT retry the same command.
Instead, analyze the error and:
1. If it's a missing module error - check if the module exists or needs to be installed
2. If it's a file not found error - verify the path is correct
3. If it's a syntax error - read the specific error and fix it
4. If you need more information - use Read or Grep tools to investigate

What specific action will you take to address this error?"""

                        self.context_manager.add_message(
                            role="user",  # Tool results are added as user messages for the next turn
                            content=result_content,
                            importance=0.6,
                            provider=self.current_provider,
                        )

                        # Display tool execution with tool-specific formatting
                        self._display_tool_result(tool_name, result, arguments)

                    continue  # Continue loop for next iteration
                else:
                    consecutive_no_tool_calls += 1

                # ═══════════════════════════════════════════════════════════════════════════════
                # LLM-DRIVEN COMPLETION: Let the model decide when task is complete
                # Simple rules:
                #   1. If model made tool calls this iteration → continue (it's working)
                #   2. If model stopped (finish_reason="stop") with no tool calls → it's done
                #   3. Only override if response is truncated/incomplete
                # ═══════════════════════════════════════════════════════════════════════════════

                # Get todo state for reference only
                todos_state = self._get_todos_completion_state()
                all_todos_completed = (
                    todos_state["total"] == 0 or todos_state["completed"] == todos_state["total"]
                )

                # Check for truncated/incomplete response (model was cut off)
                response_stripped = response_text.strip()
                is_truncated = self._is_response_truncated(response_text, finish_reason)

                # LLM decides: If model stopped and didn't make tool calls, it's signaling completion
                model_signaled_done = finish_reason == "stop" and not is_truncated

                # Task is complete if:
                # - Model signaled done (no more tool calls, finish_reason=stop)
                # - AND response is not empty/truncated
                task_completed = model_signaled_done and len(response_stripped) > 10

                # Debug logging (only in debug mode)
                self._debug_print(
                    f"[dim][?] Iteration {iteration}: model_signaled_done={model_signaled_done}, all_todos_completed={all_todos_completed}, truncated={is_truncated}, finish={finish_reason}[/dim]"
                )

                # Check if there are incomplete todos that need attention
                has_incomplete_todos = (
                    todos_state["total"] > 0 and todos_state["completed"] < todos_state["total"]
                )
                incomplete_count = (
                    todos_state["total"] - todos_state["completed"] if has_incomplete_todos else 0
                )

                # ═══════════════════════════════════════════════════════════════════════════════
                # LLM-DRIVEN COMPLETION: Let the model make informed decisions
                # Instead of forcing continuation, we inject todo state as context
                # and let the LLM decide whether to continue or finalize
                # ═══════════════════════════════════════════════════════════════════════════════

                if task_completed:
                    # FIRST: Check if model provided a substantive answer to the user
                    has_substantive = self._has_substantive_answer(response_text)

                    if not has_substantive and answer_prompts < max_answer_prompts:
                        # Model stopped without providing actual answer - prompt for response
                        answer_prompts += 1
                        self._debug_print(
                            f"[dim yellow][!] No substantive answer detected, prompting for response (prompt {answer_prompts}/{max_answer_prompts})[/dim yellow]"
                        )

                        accumulated = "\n".join(all_response_parts)
                        self.context_manager.add_message(
                            role="assistant",
                            content=accumulated,
                            importance=0.7,
                            provider=self.current_provider,
                        )

                        self.context_manager.add_message(
                            role="user",
                            content="""IMPORTANT: You have not provided the actual answer yet!

You've done the research and tool calls. Now you MUST output the actual response.

DO NOT just think about what to do - actually DO IT now:
- If the user asked for code: Output the complete code with comments
- If the user asked for an explanation: Write out the full explanation
- If the user asked for a file: Show the file contents

Start your response with the actual content the user requested, not with more thinking or tool calls.""",
                            importance=1.0,
                            provider=self.current_provider,
                        )
                        continue

                    # SECOND: Check if we should inform about incomplete todos
                    if (
                        has_incomplete_todos
                        and todo_continuation_prompts < max_todo_continuation_prompts
                    ):
                        # Inject todo state and let LLM decide
                        todo_continuation_prompts += 1
                        pending_todos_list = self._format_pending_todos()
                        self._debug_print(
                            f"[dim yellow][!] Model stopped with {incomplete_count} todo(s) remaining (prompt {todo_continuation_prompts}/{max_todo_continuation_prompts})[/dim yellow]"
                        )

                        accumulated = "\n".join(all_response_parts)
                        self.context_manager.add_message(
                            role="assistant",
                            content=accumulated,
                            importance=0.7,
                            provider=self.current_provider,
                        )

                        # LLM-driven: Give context and let model decide
                        context_message = f"""[System Notice: Task Status Check]

You have {incomplete_count} incomplete todo item(s):
{pending_todos_list}

Please review the remaining items:
- If these tasks still need to be completed, continue working on them.
- If these tasks are no longer relevant or were already addressed, you may mark them complete or provide your final summary.
- If you believe the task is truly complete, provide a comprehensive summary of what was accomplished."""

                        self.context_manager.add_message(
                            role="user",
                            content=context_message,
                            importance=1.0,
                            provider=self.current_provider,
                        )
                        continue

                    # Either all checks passed, or we've reached max prompts - trust LLM decision
                    if not has_substantive and answer_prompts >= max_answer_prompts:
                        self._debug_print(
                            f"[dim yellow][!] Reached max answer prompts ({max_answer_prompts}), accepting response[/dim yellow]"
                        )
                    if (
                        has_incomplete_todos
                        and todo_continuation_prompts >= max_todo_continuation_prompts
                    ):
                        self._debug_print(
                            f"[dim yellow][!] Reached max continuation prompts ({max_todo_continuation_prompts}), accepting LLM decision[/dim yellow]"
                        )

                    # Only show task completed message in debug mode (Claude Code doesn't show this)
                    self._debug_print(
                        f"[bold {self._palette.success}]{self._icons.SUCCESS} Task completed![/bold {self._palette.success}]"
                    )
                    summary = self._generate_task_summary(completed_actions, response_text)
                    if summary and self._is_debug_mode():
                        self.console.print(summary)
                    break

                # Only continue if response was truncated (model was cut off mid-response)
                if is_truncated:
                    self.console.print(f"[dim]-> Response truncated, continuing...[/dim]")
                    accumulated = "\n".join(all_response_parts)
                    self.context_manager.add_message(
                        role="assistant",
                        content=accumulated,
                        importance=0.7,
                        provider=self.current_provider,
                    )
                    self.context_manager.add_message(
                        role="user",
                        content="Please continue.",
                        importance=0.9,
                        provider=self.current_provider,
                    )
                    continue

                # Empty response - prompt model to engage
                if len(response_stripped) < 10 and iteration < 3:
                    self.console.print(f"[dim yellow][!] Empty response, prompting...[/dim yellow]")
                    self.context_manager.add_message(
                        role="user",
                        content="Please respond to the user's request.",
                        importance=1.0,
                        provider=self.current_provider,
                    )
                    continue

                # Check for substantive answer before allowing completion
                has_substantive = self._has_substantive_answer(response_text)

                if not has_substantive and answer_prompts < max_answer_prompts:
                    # Model stopped without providing actual answer - prompt for response
                    answer_prompts += 1
                    self.console.print(
                        f"[dim yellow][!] No substantive answer detected, prompting for response (prompt {answer_prompts}/{max_answer_prompts})[/dim yellow]"
                    )

                    accumulated = "\n".join(all_response_parts)
                    self.context_manager.add_message(
                        role="assistant",
                        content=accumulated,
                        importance=0.7,
                        provider=self.current_provider,
                    )

                    self.context_manager.add_message(
                        role="user",
                        content="""IMPORTANT: You have not provided the actual answer yet!

You've done the research and tool calls. Now you MUST output the actual response.

DO NOT just think about what to do - actually DO IT now:
- If the user asked for code: Output the complete code with comments
- If the user asked for an explanation: Write out the full explanation
- If the user asked for a file: Show the file contents

Start your response with the actual content the user requested, not with more thinking or tool calls.""",
                        importance=1.0,
                        provider=self.current_provider,
                    )
                    continue

                # Model stopped without tool calls - inform about incomplete todos if any
                if (
                    has_incomplete_todos
                    and todo_continuation_prompts < max_todo_continuation_prompts
                ):
                    todo_continuation_prompts += 1
                    pending_todos_list = self._format_pending_todos()
                    self.console.print(
                        f"[dim yellow][!] {incomplete_count} todo(s) remaining, informing LLM (prompt {todo_continuation_prompts}/{max_todo_continuation_prompts})[/dim yellow]"
                    )

                    accumulated = "\n".join(all_response_parts)
                    self.context_manager.add_message(
                        role="assistant",
                        content=accumulated,
                        importance=0.7,
                        provider=self.current_provider,
                    )

                    context_message = f"""[System Notice: Task Status Check]

You have {incomplete_count} incomplete todo item(s):
{pending_todos_list}

Please review and decide:
- Continue working on remaining tasks, OR
- Provide your final summary if the task is complete."""

                    self.context_manager.add_message(
                        role="user",
                        content=context_message,
                        importance=1.0,
                        provider=self.current_provider,
                    )
                    continue

                # All done - model stopped, trust its decision
                self._debug_print(
                    f"[bold {self._palette.success}]{self._icons.SUCCESS} Task completed![/bold {self._palette.success}]"
                )
                summary = self._generate_task_summary(completed_actions, response_text)
                if summary and self._is_debug_mode():
                    self.console.print(summary)
                break

            except Exception as iteration_error:
                # ROBUSTNESS: Catch any unexpected errors in the iteration
                consecutive_errors += 1
                error_msg = str(iteration_error)
                self.console.print(
                    f"[bold red][!] Iteration error ({consecutive_errors}/{max_consecutive_errors}): {error_msg[:150]}[/bold red]"
                )

                if consecutive_errors >= max_consecutive_errors:
                    self.console.print(
                        f"[bold red][X] Too many errors. Returning partial results.[/bold red]"
                    )
                    break

                # Try to recover by continuing
                await asyncio.sleep(1)
                continue

        # Check if we hit max iterations (safety limit)
        if iteration >= max_iterations:
            self._debug_print(
                f"[bold yellow][!] Reached maximum iterations ({max_iterations}). Stopping.[/bold yellow]"
            )
            summary = self._generate_task_summary(completed_actions, response_text)
            if summary and self._is_debug_mode():
                self.console.print(summary)

        # Return accumulated results - clean up and never return empty
        result = "\n".join(all_response_parts)
        result = self._clean_final_response(result)
        if not result.strip():
            if last_successful_response:
                return self._clean_final_response(last_successful_response)
            return "Task completed but no output was generated. Please try again."
        return result

    def _has_pending_work(self, response_text: str) -> bool:
        """
        Check if there's pending work that the model should continue.

        This is particularly important for GPT-OSS models that may stop
        mid-task without properly indicating they need to continue.

        Args:
            response_text: The model's response

        Returns:
            True if there appears to be pending work
        """
        import re
        import json

        response_lower = response_text.lower()
        response_stripped = response_text.strip()

        # Check for pending todos - but only as a soft signal, not absolute
        # If model has provided substantive answer, pending todos shouldn't block completion
        todos_state = self._get_todos_completion_state()
        if todos_state["total"] > 0 and todos_state["completed"] < todos_state["total"]:
            pending_count = todos_state["total"] - todos_state["completed"]
            # Check if model has provided a substantive answer despite pending todos
            # If yes, allow completion - the model may have decided to answer without completing all todos
            if self._has_substantive_answer(response_text):
                self.console.print(
                    f"[dim cyan][!] {pending_count} pending todos but substantive answer provided - allowing completion[/dim cyan]"
                )
                # Don't return True - let other checks proceed
            else:
                # No substantive answer and pending todos - should continue
                self.console.print(
                    f"[dim yellow][!] {pending_count} pending todos remain - continuing...[/dim yellow]"
                )
                return True

        # CRITICAL: Check if response looks like an incomplete tool call or JSON fragment
        # GPT-OSS often outputs partial JSON when trying to continue
        json_fragment_patterns = [
            r"^\s*\{[^}]*$",  # Opening brace without closing
            r"^\s*\[[^\]]*$",  # Opening bracket without closing
            r'^\s*\{"[^"]+"\s*:\s*"[^"]*"\s*\}?\s*$',  # Simple JSON object like {"path": "..."}
            r'^\s*\{"(?:path|file_path|command|pattern|content)"',  # Looks like tool parameters
        ]

        for pattern in json_fragment_patterns:
            if re.match(pattern, response_stripped, re.DOTALL):
                self.console.print(
                    f"[dim yellow][!] Detected JSON fragment pattern - continuing...[/dim yellow]"
                )
                # Store the fragment so we can help the model fix it
                self._last_json_fragment = response_stripped
                return True

        # Also detect incomplete JSON that lacks the "tool" key
        if response_stripped.startswith("{") and response_stripped.endswith("}"):
            try:
                parsed = json.loads(response_stripped)
                if isinstance(parsed, dict) and "tool" not in parsed:
                    self.console.print(
                        f"[dim yellow][!] Detected incomplete JSON (no tool key) - continuing...[/dim yellow]"
                    )
                    self._last_json_fragment = response_stripped
                    return True
            except json.JSONDecodeError:
                pass

        # Check if response is ONLY JSON (model trying to make a tool call but malformed)
        if response_stripped.startswith("{") and response_stripped.endswith("}"):
            # Try to parse as JSON
            try:
                parsed = json.loads(response_stripped)
                # If it's valid JSON but NOT a proper tool call, the model is stuck
                if isinstance(parsed, dict):
                    # Check if it looks like a proper tool call
                    has_tool_key = "tool" in parsed or "name" in parsed or "function" in parsed
                    if not has_tool_key:
                        # It's just a JSON object without tool designation - model is stuck
                        self.console.print(
                            f"[dim yellow][!] Detected incomplete JSON (no tool key) - continuing...[/dim yellow]"
                        )
                        return True
            except json.JSONDecodeError:
                # Invalid JSON - might be trying to output something
                pass

            # Also check if it's just JSON without any natural language explanation
            non_json_text = re.sub(r"\{[^{}]*\}", "", response_stripped).strip()
            if len(non_json_text) < 20:  # Very little non-JSON text
                self.console.print(
                    f"[dim yellow][!] Response is mostly JSON without explanation - continuing...[/dim yellow]"
                )
                return True

        # Check for visual todo list formatting - model outputting display instead of executing
        # Patterns like "[ ] Task" or "[~] Task" indicate model is showing a todo but not executing
        visual_todo_patterns = [
            r"\[\s*\]\s+\w+",  # [ ] Task
            r"\[\s*~\s*\]\s+\w+",  # [~] Task
            r"\[\s*x\s*\]\s+\w+",  # [x] Task
            r"\[\s*✓\s*\]\s+\w+",  # [✓] Task
            r"○\s+Pending",  # ○ Pending
            r"⟳\s+In\s+Progress",  # ⟳ In Progress
            r"\|\s+\[\s*\]",  # Table with checkbox
            r"\|\s+○\s+",  # Table with pending symbol
        ]

        for pattern in visual_todo_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                # Model is outputting a visual todo list instead of executing
                self.console.print(
                    f"[dim yellow][!] Detected visual todo list - model needs to execute tools[/dim yellow]"
                )
                return True

        # FIRST: Check if all todos are completed - if so, be much more lenient about stopping
        todos_state = self._get_todos_completion_state()
        all_todos_completed = (
            todos_state["total"] > 0 and todos_state["completed"] == todos_state["total"]
        )

        # Check if the response appears to be a COMPLETE answer (should NOT continue)
        # This prevents the model from continuing when it has already answered the user
        # IMPORTANT: Check completion indicators BEFORE error investigation
        completion_indicators = [
            "here is the",
            "here's the",
            "the repository contains",
            "the project contains",
            "the codebase contains",
            "this is a",
            "this project is",
            "summary:",
            "in summary",
            "to summarize",
            "as you can see",
            "based on my analysis",
            "i found that",
            "the structure is",
            "the content includes",
            "task completed",
            "all done",
            "completed successfully",
            "what was done",
            "all requested work",
        ]

        # Strong completion signals that indicate the task is done
        strong_completion_signals = [
            "task completed",
            "all done",
            "all requested work is now complete",
            "all tasks completed",
            "successfully completed all",
            "what was done",
            "### what was done",
            "## summary",
        ]

        has_strong_completion = any(
            signal in response_lower for signal in strong_completion_signals
        )
        has_completion_indicator = any(
            indicator in response_lower for indicator in completion_indicators
        )

        # If all todos are completed AND we have a strong completion signal, definitely stop
        if all_todos_completed and has_strong_completion:
            self.console.print(
                f"[dim green][✓] All todos completed with strong completion signal - stopping[/dim green]"
            )
            return False

        # If all todos completed AND we have any completion indicator, also stop
        if all_todos_completed and has_completion_indicator:
            self.console.print(
                f"[dim green][✓] All todos completed with completion indicator - stopping[/dim green]"
            )
            return False

        # NOW check for ACTIVE error investigation (not past-tense completions)
        # These indicate the model is CURRENTLY working on a problem
        active_investigation_indicators = [
            "investigating",
            "looking into",
            "need to fix",
            "trying to",
            "attempting to",
            "working on",
            "debugging",
            "still need",
            "must resolve",
            "cannot import",
            "not found",
            "does not exist",
        ]

        # These are PAST-TENSE or completion words that should NOT trigger continuation
        completion_words_to_ignore = [
            "fixed",
            "resolved",
            "solved",
            "addressed",
            "corrected",
            "handled",
            "completed",
            "done",
            "finished",
        ]

        # Check for active investigation (but not if it's past-tense)
        is_actively_investigating = any(
            indicator in response_lower for indicator in active_investigation_indicators
        )
        has_completion_words = any(word in response_lower for word in completion_words_to_ignore)

        # Only continue for error investigation if:
        # 1. There's active investigation language
        # 2. No strong completion signals
        # 3. Todos are NOT all completed
        if is_actively_investigating and not has_strong_completion and not all_todos_completed:
            self.console.print(
                f"[dim yellow][!] Active error investigation in progress - continuing...[/dim yellow]"
            )
            return True

        # If we have completion indicators (even weak ones), don't continue
        if has_completion_indicator:
            # Model has provided a substantive answer - don't continue
            return False

        # Check for explicit indicators of pending work
        # IMPORTANT: These should be STRONG indicators that the model is mid-task
        pending_indicators = [
            "next, i will",
            "now i'll",
            "first, let me",
            "continuing with",
            "remaining tasks:",
            "then i will",
            "[waiting]",
            "awaiting",
            "waiting for",
            "pending",
            "will proceed",
            "will continue",
            "let me check",
            "let me run",
            "let me look",
            "let me read",
            "let me examine",
        ]

        # If any pending indicator is found, continue working
        if any(indicator in response_lower for indicator in pending_indicators):
            self.console.print(
                f"[dim yellow][!] Detected pending work indicator - continuing...[/dim yellow]"
            )
            return True

        # Check for unclosed code blocks
        if response_text.count("```") % 2 == 1:
            return True

        # Check for truncation patterns specific to GPT-OSS
        truncation_patterns = [
            response_text.rstrip().endswith(","),
            response_text.rstrip().endswith("{"),
            response_text.rstrip().endswith("["),
            response_text.rstrip().endswith(":"),
            "..." in response_text[-50:] if len(response_text) > 50 else False,
        ]

        if any(truncation_patterns):
            return True

        # Check for pending todos in the tool manager
        # IMPORTANT: Skip this check for read-only tasks to prevent unwanted continuations
        if hasattr(self, "_current_task_is_readonly") and self._current_task_is_readonly:
            # For read-only tasks, don't force continuation based on todos
            return False

        if self._has_pending_todos():
            return True

        return False

    def _clean_final_response(self, response: str) -> str:
        """
        Clean the final response before showing to user.

        Removes:
        - <thinking> blocks (internal reasoning)
        - Raw JSON tool calls that weren't executed
        - Duplicate content
        - Internal prompts and continuations

        Args:
            response: The raw accumulated response

        Returns:
            Cleaned response for user display
        """
        import re

        if not response:
            return response

        cleaned = response

        # 1. Remove all <thinking>...</thinking> blocks
        cleaned = re.sub(r"<thinking>.*?</thinking>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 2. Remove raw JSON tool calls (already executed, shown in tool display)
        # Pattern: {"tool": "...", "parameters": {...}}
        cleaned = re.sub(
            r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^}]*\}\s*\}',
            "",
            cleaned,
            flags=re.DOTALL,
        )

        # 3. Remove incomplete/fragment JSON that looks like tool calls
        cleaned = re.sub(
            r'\{\s*"(?:tool|path|file_path|command)"\s*:\s*"[^"]*"\s*(?:,\s*"[^"]+"\s*:\s*[^}]*)?\}?',
            "",
            cleaned,
            flags=re.DOTALL,
        )

        # 4. Remove internal continuation prompts
        internal_phrases = [
            r"\[UNDERSTAND\].*?(?=\n\n|\[|$)",
            r"\[CONTEXT\].*?(?=\n\n|\[|$)",
            r"\[ASSUMPTIONS?\].*?(?=\n\n|\[|$)",
            r"\[OPTIONS?\].*?(?=\n\n|\[|$)",
            r"\[DECISION\].*?(?=\n\n|\[|$)",
            r"\[RISK\].*?(?=\n\n|\[|$)",
            r"\[PLAN\].*?(?=\n\n|\[|$)",
            r"UNDERSTAND:.*?(?=\n\n|CONTEXT:|ASSUMPTIONS:|OPTIONS:|DECISION:|$)",
            r"CONTEXT:.*?(?=\n\n|ASSUMPTIONS:|OPTIONS:|DECISION:|RISK:|$)",
        ]

        for pattern in internal_phrases:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 5. Clean up multiple consecutive newlines
        cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)

        # 6. Clean up whitespace at start/end
        cleaned = cleaned.strip()

        # 7. If cleaning removed everything meaningful, try to extract just the answer
        if not cleaned or len(cleaned) < 10:
            # Try to find any useful content
            lines = response.split("\n")
            useful_lines = []
            for line in lines:
                line = line.strip()
                # Skip internal reasoning markers
                if line.startswith("[") and "]" in line[:50]:
                    continue
                if line.startswith("<thinking") or line.startswith("</thinking"):
                    continue
                if line.startswith('{"tool"'):
                    continue
                if line:
                    useful_lines.append(line)

            if useful_lines:
                cleaned = "\n".join(useful_lines[-5:])  # Take last 5 useful lines

        return cleaned

    def _is_task_completed(
        self, response_text: str, completed_actions: List[Dict[str, Any]] = None, iteration: int = 0
    ) -> bool:
        """
        Check if the task has been completed based on the model's response.

        This is the primary stopping condition for the agent loop.
        Uses multiple signals to determine task completion.
        IMPORTANT: Must verify BOTH completion signal AND substantive answer provided.

        Args:
            response_text: The model's response
            completed_actions: List of completed tool actions
            iteration: Current iteration number

        Returns:
            True if the task appears to be completed
        """
        response_lower = response_text.lower()
        response_stripped = response_text.strip()

        # Don't complete too early - need at least some work done
        # This prevents false positives when model is still investigating
        min_actions_for_completion = 3
        min_iterations_for_phrase_completion = 5
        action_count = len(completed_actions) if completed_actions else 0

        # CRITICAL: Check if there are pending todos - if so, don't complete early!
        todos_state = self._get_todos_completion_state()
        has_todos = todos_state["total"] > 0
        todos_completed_ratio = (
            todos_state["completed"] / todos_state["total"] if has_todos else 1.0
        )
        all_todos_completed = (
            todos_state["completed"] == todos_state["total"] if has_todos else True
        )
        has_pending_todos = has_todos and not all_todos_completed

        # STRICT: If there are ANY pending todos, require substantive content to complete
        # This prevents the agent from saying "task completed" without actually answering
        if has_pending_todos:
            # Get the pending todos to check if any are "summary" type
            pending_is_summary = False
            try:
                todo_tool = self.tool_manager.get_tool("TodoWrite")
                if todo_tool and hasattr(todo_tool, "todos") and todo_tool.todos:
                    for todo in todo_tool.todos:
                        content = (
                            todo.content.lower()
                            if hasattr(todo, "content")
                            else todo.get("content", "").lower()
                        )
                        status = (
                            todo.status
                            if hasattr(todo, "status")
                            else todo.get("status", "pending")
                        )
                        if status != "completed":
                            # Check if this pending todo is a summary/compile type
                            summary_keywords = [
                                "summarize",
                                "summarise",
                                "summary",
                                "compile",
                                "overview",
                                "describe",
                                "provide",
                                "write",
                                "generate",
                                "create",
                            ]
                            if any(kw in content for kw in summary_keywords):
                                pending_is_summary = True
                                break
            except Exception:
                pass

            # Check if response contains substantive content (actual answer to user)
            has_substantive_content = self._has_substantive_answer(response_text)

            if not has_substantive_content:
                if pending_is_summary:
                    self.console.print(
                        f"[dim yellow][?] Pending summary task ({todos_state['completed']}/{todos_state['total']}) - MUST provide actual summary/answer to complete[/dim yellow]"
                    )
                else:
                    self.console.print(
                        f"[dim yellow][?] Pending todos ({todos_state['completed']}/{todos_state['total']}) - need substantive answer to complete[/dim yellow]"
                    )
                return False

            # Even with substantive content, if it's a summary task, verify it's REALLY an answer
            if pending_is_summary:
                # For summary tasks, be extra strict - need markdown headers or explicit summary structure
                import re

                clean_text = response_text
                # Strip thinking blocks
                clean_text = re.sub(
                    r"<thinking>[\s\S]*?</thinking>", "", clean_text, flags=re.IGNORECASE
                )
                clean_text = re.sub(r'\{["\']tool["\'][\s\S]*?\}', "", clean_text)
                clean_text = clean_text.strip()

                has_summary_structure = (
                    "## " in clean_text
                    or "### " in clean_text
                    or "summary" in clean_text.lower()
                    or "overview" in clean_text.lower()
                    or (clean_text.count("\n") > 10 and len(clean_text) > 500)
                )
                if not has_summary_structure:
                    self.console.print(
                        f"[dim yellow][?] Summary task pending - need actual summary output, not just thinking[/dim yellow]"
                    )
                    return False
        else:
            # Check if response contains substantive content (not just "task completed")
            has_substantive_content = self._has_substantive_answer(response_text)

        # Strong completion indicators - these signal the task is done
        # But only if we've done enough work AND provided an answer
        completion_phrases = [
            "task completed",
            "task is complete",
            "task has been completed",
            "all done",
            "i have completed",
            "i've completed",
            "successfully completed",
            "finished the task",
            "that completes",
            "this completes",
            "all tasks are complete",
            "all tasks completed",
            "nothing more to do",
            "no further action",
        ]

        # Weaker phrases that might appear mid-task - require more conditions
        weak_completion_phrases = [
            "let me know if you need",
            "feel free to ask",
            "is there anything else",
            "hope this helps",
            "here's the summary",
            "here is the summary",
            "in conclusion",
            "to summarize",
            "summary:",
            "changes have been made",
            "changes are complete",
            "implementation is complete",
            "done!",
            "that's it",
            "everything is",
        ]

        # Strong phrases: require minimum work done AND substantive content
        if action_count >= min_actions_for_completion:
            if any(phrase in response_lower for phrase in completion_phrases):
                # IMPORTANT: Must have substantive content, not just "task completed"
                if has_substantive_content or all_todos_completed:
                    return True
                else:
                    # Don't return True - need actual answer
                    self.console.print(
                        f"[dim yellow][?] Completion phrase found but no substantive answer provided yet[/dim yellow]"
                    )

        # Weak phrases: require more iterations AND no tool calls in response
        if (
            iteration >= min_iterations_for_phrase_completion
            and action_count >= min_actions_for_completion
        ):
            if any(phrase in response_lower for phrase in weak_completion_phrases):
                if not self._looks_like_tool_call(response_text) and has_substantive_content:
                    return True

        # Check if all todos are marked as completed
        if all_todos_completed and has_todos:
            return True

        # For read-only tasks, check if a substantive answer was provided
        if hasattr(self, "_current_task_is_readonly") and self._current_task_is_readonly:
            # Read-only tasks are complete if we have a summary-like response
            if len(response_text) > 200 and any(
                word in response_lower
                for word in [
                    "contains",
                    "includes",
                    "structure",
                    "files",
                    "directories",
                    "repository",
                    "project",
                    "codebase",
                    "found",
                    "here is",
                    "here are",
                ]
            ):
                return True

        # HEURISTIC: If we've done MANY actions and response looks like a definitive conclusion
        # Require MORE actions to avoid premature termination
        if completed_actions and len(completed_actions) >= 5:
            # Check if response looks like it's explicitly wrapping up
            conclusion_indicators = [
                "completed" in response_lower
                and ("all" in response_lower or "task" in response_lower),
                "finished" in response_lower and "all" in response_lower,
                "done" in response_lower and "all" in response_lower,
                "successful" in response_lower
                and ("completed" in response_lower or "all" in response_lower),
            ]
            # Require stronger signals of completion AND substantive content
            if (
                len(response_stripped) > 100
                and sum(conclusion_indicators) >= 1
                and has_substantive_content
            ):
                return True

        # HEURISTIC: If model gives a VERY long response without tool calls, it might be done
        # Increased threshold to avoid premature termination
        if len(response_stripped) > 500 and not self._looks_like_tool_call(response_text):
            # Check for explicit completion language before marking as done
            explicit_completion = any(
                phrase in response_lower
                for phrase in [
                    "have completed",
                    "has been completed",
                    "is now complete",
                    "all tasks done",
                    "all done",
                    "finished all",
                ]
            )
            if explicit_completion and has_substantive_content:
                return True

        # SAFETY: After MANY iterations with tool calls, if model stops calling tools, it might be done
        # Require more iterations and actions before auto-completing
        if iteration > 8 and completed_actions and len(completed_actions) > 5:
            # If the last response doesn't look like it needs more work
            continuing_indicators = [
                "next" in response_lower,
                "now i" in response_lower,
                "let me" in response_lower,
                "i will" in response_lower,
                "need to" in response_lower,
                "should" in response_lower,
                "investigate" in response_lower,
                "check" in response_lower,
                "fix" in response_lower,
                "error" in response_lower,
                "issue" in response_lower,
            ]
            if not any(continuing_indicators) and has_substantive_content:
                return True

        return False

    def _get_todos_completion_state(self) -> Dict[str, int]:
        """Get the current state of todos (completed count, total count)."""
        try:
            todo_tool = self.tool_manager.get_tool("TodoWrite")
            if todo_tool and hasattr(todo_tool, "todos") and todo_tool.todos:
                todos = todo_tool.todos
                total = len(todos)
                completed = sum(
                    1
                    for t in todos
                    if (hasattr(t, "status") and t.status == "completed")
                    or (isinstance(t, dict) and t.get("status") == "completed")
                )
                return {"total": total, "completed": completed}
        except Exception:
            pass
        return {"total": 0, "completed": 0}

    def _format_pending_todos(self) -> str:
        """Format the list of pending (incomplete) todos for LLM context injection."""
        try:
            todo_tool = self.tool_manager.get_tool("TodoWrite")
            if not todo_tool or not hasattr(todo_tool, "todos") or not todo_tool.todos:
                return "No todos found."

            pending_items = []
            for i, todo in enumerate(todo_tool.todos, 1):
                # Handle both object and dict formats
                if hasattr(todo, "status"):
                    status = todo.status
                    content = getattr(todo, "content", str(todo))
                elif isinstance(todo, dict):
                    status = todo.get("status", "unknown")
                    content = todo.get("content", str(todo))
                else:
                    continue

                if status != "completed":
                    status_icon = "⏳" if status == "in_progress" else "○"
                    pending_items.append(f"  {status_icon} [{status}] {content}")

            if not pending_items:
                return "All todos are completed."

            return "\n".join(pending_items)
        except Exception as e:
            return f"Error retrieving todos: {e}"

    def _has_substantive_answer(self, response_text: str) -> bool:
        """
        Check if the response contains a substantive answer to the user's question.

        This prevents marking tasks as complete when the model just says "done"
        without actually providing the requested information.

        IMPORTANT: Very strict - only returns True if there's clear user-facing prose
        that actually answers a question (not just tool calls or thinking).
        """
        import re

        # CRITICAL: Strip ALL non-user-facing content
        clean_text = response_text

        # 1. Strip thinking blocks (all formats)
        thinking_patterns = [
            r"<thinking>[\s\S]*?</thinking>",
            r"<think>[\s\S]*?</think>",
            r"\[UNDERSTAND\][\s\S]*?(?=\[(?:CONTEXT|OPTIONS|DECISION|RISK|ASSUMPTIONS)\]|$)",
            r"\[CONTEXT\][\s\S]*?(?=\[(?:UNDERSTAND|OPTIONS|DECISION|RISK|ASSUMPTIONS)\]|$)",
            r"\[OPTIONS\][\s\S]*?(?=\[(?:UNDERSTAND|CONTEXT|DECISION|RISK|ASSUMPTIONS)\]|$)",
            r"\[DECISION\][\s\S]*?(?=\[(?:UNDERSTAND|CONTEXT|OPTIONS|RISK|ASSUMPTIONS)\]|$)",
            r"\[RISK\][\s\S]*?(?=\[(?:UNDERSTAND|CONTEXT|OPTIONS|DECISION|ASSUMPTIONS)\]|$)",
            r"\[ASSUMPTIONS\][\s\S]*?(?=\[(?:UNDERSTAND|CONTEXT|OPTIONS|DECISION|RISK)\]|$)",
        ]
        for pattern in thinking_patterns:
            clean_text = re.sub(pattern, "", clean_text, flags=re.IGNORECASE | re.DOTALL)

        # 2. Strip ALL JSON-like content (tool calls, parameters, etc.)
        # This is aggressive but necessary - tool calls are NOT answers
        json_patterns = [
            r'\{[^{}]*"tool"[^{}]*\}',  # Simple tool call
            r'\{[^{}]*"parameters"[^{}]*\}',  # Parameters block
            r'\{"[^"]+"\s*:\s*"[^"]*"\}',  # Simple key-value JSON
            r"\{[\s\S]*?\}",  # Any remaining JSON blocks
        ]
        for pattern in json_patterns:
            clean_text = re.sub(pattern, "", clean_text, flags=re.DOTALL)

        # 3. Strip status lines and metadata
        clean_text = re.sub(r"\*\s*GOAL:.*", "", clean_text)
        clean_text = re.sub(r"\[OK\].*", "", clean_text)
        clean_text = re.sub(r"\[!\].*", "", clean_text)
        clean_text = re.sub(r"\[CHALLENGE\].*", "", clean_text)

        # 4. Clean up whitespace
        clean_text = re.sub(r"\n\s*\n\s*\n+", "\n\n", clean_text)
        response_stripped = clean_text.strip()
        response_lower = response_stripped.lower()

        # STRICT CHECK 1: Must have substantial remaining text (at least 100 chars)
        # After stripping all tool calls and thinking, there should be real content
        if len(response_stripped) < 100:
            return False

        # CODE BLOCK CHECK: If response contains code blocks, that's a substantive answer
        # Code blocks are a valid way to answer programming questions
        if "```" in response_stripped and response_stripped.count("```") >= 2:
            # Has at least one complete code block - this is likely an answer
            return True

        # STRICT CHECK 2: Must have explicit answer indicators
        # These indicate the model is DIRECTLY addressing the user with information
        answer_indicators = [
            # Direct summaries
            "here is a summary",
            "here is an overview",
            "here is the",
            "the repository contains",
            "this repository is",
            "this project is",
            "the codebase includes",
            "the main components are",
            # Explicit answers
            "in summary,",
            "to summarize,",
            "overall,",
            "in conclusion,",
            # Structure descriptions
            "the structure is",
            "it contains the following",
            "the following",
            "consists of",
            "is organized as",
            "includes:",
        ]

        has_answer_indicator = any(ind in response_lower for ind in answer_indicators)
        if not has_answer_indicator:
            return False

        # STRICT CHECK 3: Must have prose structure (sentences, not just keywords)
        # Real answers have sentences with periods and proper structure
        sentence_count = len(re.findall(r"[.!?]\s+[A-Z]", response_stripped))
        if sentence_count < 2:
            return False

        return True

    def _looks_like_tool_call(self, text: str) -> bool:
        """Check if text looks like it contains a tool call"""
        import re

        # Check for JSON-like tool call patterns
        patterns = [
            r'\{"tool"',
            r'\{"name"',
            r'"parameters"\s*:',
            r'"function"\s*:',
        ]
        return any(re.search(p, text) for p in patterns)

    def _auto_update_todos(self, completed_action: Dict[str, Any]) -> bool:
        """
        Automatically update todo list when a tool action completes successfully.

        Matches completed tool calls to pending todos and marks them as completed.
        This ensures the todo list stays in sync with actual progress.

        Strategy:
        1. Try to match action to a specific todo based on content
        2. If no specific match, mark the current in_progress todo as completed
        3. Auto-advance to next pending todo

        Args:
            completed_action: Dict with 'tool', 'success', 'args', 'iteration'

        Returns:
            True if a todo was updated, False otherwise
        """
        if not completed_action.get("success", False):
            return False

        tool_name = completed_action.get("tool", "").lower()
        args = completed_action.get("args", {})

        # Skip TodoWrite itself - don't create a loop
        if tool_name in ["todowrite", "todo_write", "todo"]:
            return False

        try:
            # Get the TodoWrite tool
            todo_tool = self.tool_manager.get_tool("TodoWrite")
            if not todo_tool or not hasattr(todo_tool, "todos") or not todo_tool.todos:
                return False

            todos = todo_tool.todos
            updated = False

            # Create a description of what we just did
            action_desc = tool_name
            file_name = ""
            if "file_path" in args:
                file_name = Path(args["file_path"]).name
                action_desc = f"{tool_name} {file_name}"
            elif "path" in args:
                file_name = Path(args["path"]).name if args["path"] else ""
                action_desc = f"{tool_name} {file_name}"
            elif "pattern" in args:
                action_desc = f"{tool_name} {args['pattern'][:30]}"
            elif "command" in args:
                cmd = (
                    args["command"][:40]
                    if isinstance(args["command"], str)
                    else str(args["command"])[:40]
                )
                action_desc = f"{tool_name} {cmd}"

            action_desc_lower = action_desc.lower()

            # Helper to get todo info
            def get_todo_info(t):
                if hasattr(t, "content"):
                    return t.content.lower(), t.status
                elif isinstance(t, dict):
                    return t.get("content", "").lower(), t.get("status", "pending")
                return "", "pending"

            # Helper to set todo status
            def set_todo_status(t, idx, new_status):
                if hasattr(t, "status"):
                    t.status = new_status
                elif isinstance(t, dict):
                    todos[idx]["status"] = new_status

            # Find the current in_progress todo index
            current_in_progress_idx = None
            for i, todo in enumerate(todos):
                _, status = get_todo_info(todo)
                if status == "in_progress":
                    current_in_progress_idx = i
                    break

            # Find the first pending todo index (for fallback)
            first_pending_idx = None
            for i, todo in enumerate(todos):
                _, status = get_todo_info(todo)
                if status == "pending":
                    first_pending_idx = i
                    break

            # Try to find a matching todo based on content
            best_match_idx = None
            best_match_score = 0

            for i, todo in enumerate(todos):
                content, status = get_todo_info(todo)

                # Only update in_progress or pending todos
                if status == "completed":
                    continue

                # Match based on tool type and content
                match_score = 0

                # Check for tool-type match (expanded keywords)
                tool_keywords = {
                    "read": [
                        "read",
                        "view",
                        "check",
                        "look",
                        "examine",
                        "inspect",
                        "review",
                        "understand",
                        "analyze",
                        "explore",
                    ],
                    "grep": ["search", "find", "look for", "grep", "scan", "locate", "identify"],
                    "glob": [
                        "find files",
                        "list",
                        "search files",
                        "locate",
                        "identify",
                        "discover",
                    ],
                    "bash": ["run", "execute", "test", "build", "install", "compile", "check"],
                    "write": ["write", "create", "add", "implement", "generate"],
                    "edit": ["edit", "modify", "change", "update", "fix", "refactor", "improve"],
                }

                for key, keywords in tool_keywords.items():
                    if key in tool_name:
                        for keyword in keywords:
                            if keyword in content:
                                match_score += 2
                                break

                # Check for file/path match
                file_path_arg = args.get("file_path") or args.get("path", "")
                if file_path_arg:
                    fn = Path(file_path_arg).name.lower() if file_path_arg else ""
                    if fn and fn in content:
                        match_score += 4  # Strong match
                    elif file_path_arg and any(
                        part in content
                        for part in file_path_arg.lower().split("/")
                        if len(part) > 2
                    ):
                        match_score += 2

                # Bonus for in_progress status
                if status == "in_progress":
                    match_score += 1

                # Track best match
                if match_score > best_match_score:
                    best_match_score = match_score
                    best_match_idx = i

            # Determine which todo to mark as completed
            target_idx = None

            # If we found a good match (score >= 2), use it
            if best_match_idx is not None and best_match_score >= 2:
                target_idx = best_match_idx
            # Otherwise, if there's a current in_progress todo, mark it completed
            # This is a fallback for tasks like "Read README" when we do read a file
            elif current_in_progress_idx is not None:
                # Only auto-complete if the tool type somewhat matches the task
                current_content, _ = get_todo_info(todos[current_in_progress_idx])
                # Check if tool type is broadly compatible with task
                read_tools = ["read", "grep", "glob", "ls"]
                modify_tools = ["write", "edit", "bash"]

                tool_is_read = any(t in tool_name for t in read_tools)
                tool_is_modify = any(t in tool_name for t in modify_tools)

                task_is_read = any(
                    w in current_content
                    for w in [
                        "read",
                        "check",
                        "look",
                        "examine",
                        "view",
                        "find",
                        "search",
                        "explore",
                        "understand",
                        "identify",
                    ]
                )
                task_is_modify = any(
                    w in current_content
                    for w in [
                        "write",
                        "create",
                        "edit",
                        "modify",
                        "fix",
                        "update",
                        "implement",
                        "add",
                    ]
                )

                # If tool type matches task type, mark as completed
                if (tool_is_read and task_is_read) or (tool_is_modify and task_is_modify):
                    target_idx = current_in_progress_idx

            # Mark the target todo as completed and advance
            if target_idx is not None:
                set_todo_status(todos[target_idx], target_idx, "completed")

                # Find next pending todo and mark as in_progress
                for j in range(target_idx + 1, len(todos)):
                    _, next_status = get_todo_info(todos[j])
                    if next_status == "pending":
                        set_todo_status(todos[j], j, "in_progress")
                        break

                updated = True

                # Display update
                completed_count = sum(1 for t in todos if get_todo_info(t)[1] == "completed")
                total_count = len(todos)
                self.console.print(
                    f"[dim cyan][{self._icons.SUCCESS}] Todo {target_idx + 1}/{total_count}: completed ({completed_count}/{total_count} total)[/dim cyan]"
                )

            return updated

        except Exception as e:
            # Don't crash if todo update fails
            self.console.print(f"[dim red]Todo auto-update error: {e}[/dim red]")
            return False

    def _generate_task_summary(
        self, completed_actions: List[Dict[str, Any]], final_response: str
    ) -> str:
        """
        Generate a clean summary of the completed task.

        Args:
            completed_actions: List of tool actions that were executed
            final_response: The final response from the model

        Returns:
            Formatted summary string
        """
        from rich.panel import Panel
        from rich.text import Text
        from io import StringIO

        if not completed_actions:
            return ""

        # Build summary
        summary_parts = []

        # Count actions by type
        action_counts = {}
        successful = 0
        failed = 0
        for action in completed_actions:
            tool = action.get("tool", "Unknown")
            action_counts[tool] = action_counts.get(tool, 0) + 1
            if action.get("success", False):
                successful += 1
            else:
                failed += 1

        # Header
        summary_parts.append(f"[bold cyan]=== Task Summary ===[/bold cyan]")

        # Stats
        total = len(completed_actions)
        stats = f"[dim]Actions: {total} total ({successful} successful"
        if failed > 0:
            stats += f", {failed} failed"
        stats += ")[/dim]"
        summary_parts.append(stats)

        # Action breakdown (only if more than 1 type)
        if len(action_counts) > 1:
            breakdown = []
            for tool, count in sorted(action_counts.items(), key=lambda x: -x[1]):
                breakdown.append(f"{tool}: {count}")
            summary_parts.append(f"[dim]Tools used: {', '.join(breakdown)}[/dim]")

        # Files modified (if any write/edit actions)
        modified_files = set()
        for action in completed_actions:
            tool = action.get("tool", "").lower()
            args = action.get("args", {})
            if tool in ["write", "writetool", "edit", "edittool"] and action.get("success"):
                file_path = args.get("file_path", args.get("path", ""))
                if file_path:
                    # Show just filename, not full path
                    modified_files.add(file_path.split("/")[-1].split("\\")[-1])

        if modified_files and len(modified_files) <= 5:
            summary_parts.append(f"[dim]Files modified: {', '.join(modified_files)}[/dim]")
        elif modified_files:
            summary_parts.append(f"[dim]Files modified: {len(modified_files)} files[/dim]")

        summary_parts.append(f"[bold cyan]====================[/bold cyan]")

        return "\n".join(summary_parts)

    def _extract_todos_from_thinking(self, thinking_content: str) -> list:
        """
        Extract todo items from a thinking block content.

        Looks for patterns like:
        - [DECISION] Option A: Do X, then Y
        - Steps: 1. First thing 2. Second thing
        - Numbered lists
        - Bullet points with action items

        Args:
            thinking_content: Raw thinking block content

        Returns:
            List of normalized todo items or empty list
        """
        if not thinking_content:
            return []

        todos = []

        def generate_active_form(content: str) -> str:
            """Generate present continuous form from imperative form."""
            if not content:
                return "Working..."
            words = content.strip().split()
            if not words:
                return "Working..."
            verb = words[0].lower()
            rest = " ".join(words[1:]) if len(words) > 1 else ""

            verb_map = {
                "add": "Adding",
                "create": "Creating",
                "fix": "Fixing",
                "update": "Updating",
                "remove": "Removing",
                "delete": "Deleting",
                "implement": "Implementing",
                "write": "Writing",
                "read": "Reading",
                "test": "Testing",
                "run": "Running",
                "check": "Checking",
                "analyze": "Analyzing",
                "review": "Reviewing",
                "refactor": "Refactoring",
                "debug": "Debugging",
                "investigate": "Investigating",
                "explore": "Exploring",
                "search": "Searching",
                "find": "Finding",
                "look": "Looking",
                "build": "Building",
                "compile": "Compiling",
                "install": "Installing",
                "configure": "Configuring",
                "setup": "Setting up",
                "set": "Setting",
                "get": "Getting",
                "fetch": "Fetching",
                "load": "Loading",
                "use": "Using",
                "execute": "Executing",
                "call": "Calling",
                "verify": "Verifying",
                "validate": "Validating",
                "ensure": "Ensuring",
            }

            if verb in verb_map:
                return f"{verb_map[verb]} {rest}".strip()
            elif verb.endswith("e"):
                return f"{verb[:-1].capitalize()}ing {rest}".strip()
            else:
                return f"{verb.capitalize()}ing {rest}".strip()

        # Pattern 1: Look for explicit step/task lists
        # Matches: "1. Do something" or "- Do something" or "* Do something"
        step_patterns = [
            r"(?:step|task|action)s?\s*(?:to take|:)?\s*\n((?:\s*[-*•]\s*.+\n?)+)",
            r"(?:plan|approach|strategy)\s*:\s*\n((?:\s*\d+[\.\)]\s*.+\n?)+)",
            r"(?:i will|let me|need to)\s*:\s*\n((?:\s*[-*•]\s*.+\n?)+)",
            # Match OPTIONS section with Option A/B format
            r"\[OPTIONS\][^\[]*?((?:Option\s+[A-Z]:\s*[^\n]+\n?)+)",
            r"options?\s*:?\s*\n((?:\s*[-*•]\s*Option\s+[A-Z]:\s*[^\n]+\n?)+)",
        ]

        for pattern in step_patterns:
            match = re.search(pattern, thinking_content, re.IGNORECASE)
            if match:
                steps_text = match.group(1)
                for line in steps_text.split("\n"):
                    line = re.sub(r"^[\s\d\.\)\-\*•]+", "", line).strip()
                    if line and len(line) > 5 and len(line) < 200:
                        todos.append(line)

        # Pattern 2: Look for actions in DECISION section
        decision_match = re.search(
            r"\[DECISION\](.*?)(?:\[|$)", thinking_content, re.IGNORECASE | re.DOTALL
        )
        if decision_match and not todos:
            decision_text = decision_match.group(1)

            # Look for "then" separated actions
            if " then " in decision_text.lower():
                parts = re.split(r",?\s+then\s+", decision_text, flags=re.IGNORECASE)
                for part in parts:
                    part = part.strip()
                    if part and len(part) > 5 and len(part) < 200:
                        part = re.sub(r"^[\s\d\.\)\-\*•:]+", "", part).strip()
                        part = re.sub(r"^\w+:\s*", "", part).strip()
                        if part:
                            todos.append(part)

            # If no "then" structure, extract the selected action
            if not todos:
                # Match "Selected: X" or "Choose Option X: Y"
                selected_match = re.search(
                    r"(?:selected|chose|choose|picking|using)[:\s]+(.{10,150}?)(?:\.|$|\n)",
                    decision_text,
                    re.IGNORECASE,
                )
                if selected_match:
                    action = selected_match.group(1).strip()
                    action = re.sub(r"^Option\s+[A-Z]:\s*", "", action, flags=re.IGNORECASE)
                    if action and len(action) > 5:
                        todos.append(action)

        # Pattern 3: Extract from UNDERSTAND/GOAL section
        goal_match = re.search(
            r"\[(?:UNDERSTAND|GOAL)\](.*?)(?:\[|$)", thinking_content, re.IGNORECASE | re.DOTALL
        )
        if goal_match and not todos:
            goal_text = goal_match.group(1).strip()
            # Extract core goal if mentioned
            core_match = re.search(
                r"(?:core goal|main goal|objective)[:\s]+(.{10,100}?)(?:\.|$|\n)",
                goal_text,
                re.IGNORECASE,
            )
            if core_match:
                todos.append(core_match.group(1).strip())

        # Pattern 3: Look for explicit numbered items anywhere
        if not todos:
            numbered_items = re.findall(
                r"(?:^|\n)\s*(\d+)[\.\)]\s*(.{10,150}?)(?=\n\s*\d+[\.\)]|\n\n|$)",
                thinking_content,
                re.DOTALL,
            )
            for num, item in numbered_items:
                item = item.strip()
                # Skip if it's a section header or too short
                if item and not item.startswith("[") and not item.endswith(":") and len(item) > 10:
                    todos.append(item)

        # Limit to 5 items and format properly
        todos = todos[:5]
        if not todos:
            return []

        # Convert to proper todo format
        formatted_todos = []
        for i, content in enumerate(todos):
            # Clean up the content
            content = content.strip()
            content = re.sub(r"\s+", " ", content)  # Normalize whitespace
            if content:
                formatted_todos.append(
                    {
                        "content": content,
                        "status": "in_progress" if i == 0 else "pending",
                        "activeForm": generate_active_form(content),
                    }
                )

        return formatted_todos

    def _has_pending_todos(self) -> bool:
        """
        Check if there are pending or in-progress todos that haven't been completed.

        Returns:
            True if there are incomplete todos
        """
        try:
            # Try to get the TodoWriteTool from the tool manager
            todo_tool = self.tool_manager.get_tool("todowrite")
            if todo_tool and hasattr(todo_tool, "todos") and todo_tool.todos:
                for todo in todo_tool.todos:
                    if hasattr(todo, "status"):
                        if todo.status in ["pending", "in_progress"]:
                            return True
                    elif isinstance(todo, dict) and todo.get("status") in [
                        "pending",
                        "in_progress",
                    ]:
                        return True
        except Exception:
            pass
        return False

    def _format_user_task(self, task: str) -> str:
        """
        Format the user task with explicit output format instructions.

        This helps OSS models understand the expected response format.

        Args:
            task: The user's task

        Returns:
            Formatted task with instructions
        """
        # Check if this is an OpenAI/OSS provider that needs extra guidance
        provider_name = ""
        if self.current_provider:
            provider_name = (
                self.current_provider.get_provider_name()
                if hasattr(self.current_provider, "get_provider_name")
                else ""
            )

        # For OpenAI/OSS models, add explicit format instructions
        if "openai" in provider_name.lower() or "gpt" in str(self.current_provider).lower():
            # Detect if this is a read-only task
            task_lower = task.lower()
            is_read_only = any(
                word in task_lower
                for word in [
                    "what is",
                    "what are",
                    "show",
                    "list",
                    "display",
                    "content",
                    "explain",
                    "describe",
                    "find",
                    "search",
                    "where",
                    "how many",
                    "tell me",
                    "check",
                    "view",
                    "see",
                    "repo",
                    "structure",
                    "folder",
                ]
            )

            # Also check for negative indicators that suggest NOT read-only
            is_action_task = any(
                word in task_lower
                for word in [
                    "run",
                    "test",
                    "pytest",
                    "execute",
                    "fix",
                    "modify",
                    "change",
                    "update",
                    "create",
                    "write",
                    "delete",
                    "install",
                    "build",
                    "generate",
                    "make",
                    "add",
                    "implement",
                    "save",
                    "put",
                    "output",
                    "refactor",
                    "rename",
                    "move",
                    "copy",
                    "edit",
                    "append",
                    "insert",
                ]
            )

            # Store this flag so continuation logic can use it
            self._current_task_is_readonly = is_read_only and not is_action_task

            if self._current_task_is_readonly:
                return f"""USER TASK: {task}

CRITICAL CONSTRAINTS:
- This is a READ-ONLY task
- Do NOT run tests (pytest, unittest, etc.)
- Do NOT execute any code
- Do NOT modify any files
- ONLY use: LS, Glob, Grep, Read

MANDATORY RESPONSE FORMAT:
1. First, output a <thinking> block with your reasoning
2. Then call a READ-ONLY tool (LS, Glob, Grep, or Read)
3. After exploring, provide a SUMMARY to the user

WHEN TO STOP:
- Once you have gathered enough information, provide a summary
- Do NOT continue indefinitely - summarize your findings

Example:
<thinking>
1. UNDERSTAND: User wants to see [what]
2. CONTEXT: I need to explore [what]
3. OPTIONS: LS to list, Glob to find files, Read to see content
4. DECISION: Best choice is [tool] because [reason]
5. RISK CHECK: This is read-only, safe to proceed
</thinking>

{{"tool": "LS", "parameters": {{"path": "."}}}}

START NOW - think first, then explore:"""
            else:
                return f"""USER TASK: {task}

MANDATORY RESPONSE FORMAT:
1. First, output a <thinking> block with your reasoning
2. Then call the appropriate tool

Example:
<thinking>
1. UNDERSTAND: User wants [what]
2. CONTEXT: I know [context]
3. OPTIONS: [list possible tools]
4. DECISION: Best choice is [tool] because [reason]
5. RISK CHECK: [is this safe?]
</thinking>

{{"tool": "ToolName", "parameters": {{"key": "value"}}}}

Available: Bash, Read, Write, Edit, Glob, Grep, LS

START NOW - think first, then act:"""

        # For Claude/Anthropic, just return the task as-is
        return task

    def _maybe_clear_context_for_new_task(self, task: str) -> None:
        """
        Determine if the context should be cleared for a new task.

        This prevents context pollution where old test runs or other
        unrelated commands influence new tasks (e.g., exploration queries
        being confused by old pytest executions).

        Args:
            task: The new task being executed
        """
        # Get current context size
        current_context = self.context_manager.context
        if not current_context:
            return  # No context to clear

        task_lower = task.lower()

        # Detect read-only/exploration tasks
        is_exploration_task = any(
            word in task_lower
            for word in [
                "what is",
                "what are",
                "show",
                "list",
                "display",
                "content",
                "explain",
                "describe",
                "structure",
                "repo",
                "folder",
                "files",
                "tell me",
                "check",
                "view",
                "see",
                "explore",
            ]
        )

        # Check if previous context contains action commands that might pollute
        context_has_action_commands = False
        for entry in current_context:
            content_lower = entry.content.lower()
            if any(
                cmd in content_lower
                for cmd in [
                    "pytest",
                    "python -m pytest",
                    "npm test",
                    "npm run",
                    "make test",
                    "cargo test",
                    "go test",
                    "jest",
                    "git commit",
                    "git push",
                    "pip install",
                ]
            ):
                context_has_action_commands = True
                break

        # Clear context if we're switching from action commands to exploration
        if is_exploration_task and context_has_action_commands:
            self.console.print(
                f"[dim yellow][!] Clearing old context to prevent pollution (switching to exploration task)[/dim yellow]"
            )
            self.context_manager.clear_context(keep_system=True)

            # Reset the readonly flag
            self._current_task_is_readonly = True

    def _get_empty_response_prompt(self) -> str:
        """
        Get a prompt for when the model returns an empty or minimal response.

        This happens when GPT-OSS models fail to engage with the task.

        Returns:
            Prompt string to force engagement
        """
        # Check if this is a read-only task
        if hasattr(self, "_current_task_is_readonly") and self._current_task_is_readonly:
            return """ERROR: You returned an empty response.

You MUST respond with BOTH:
1. A brief explanation of what you're doing (1-2 sentences)
2. A READ-ONLY tool call in JSON format

Example correct response:
"I'll explore the repository structure first.

{"tool": "LS", "parameters": {"path": "."}}"

NOW respond with text explanation + tool call:"""

        return """ERROR: You returned an empty response.

You MUST respond with BOTH:
1. A brief explanation of what you're doing (1-2 sentences)
2. A tool call in JSON format

Example correct response:
"I'll explore the codebase to understand the structure.

{"tool": "LS", "parameters": {"path": "."}}"

NOW respond with text explanation + tool call:"""

    def _get_pending_work_prompt(self) -> str:
        """
        Get a prompt that encourages the model to continue with pending work.

        This is especially important for GPT-OSS models that tend to output
        partial JSON or stop mid-task.

        Returns:
            Prompt string for continuing pending work
        """
        # Check if we have a recent JSON fragment that needs fixing
        fragment = getattr(self, "_last_json_fragment", None)
        if fragment:
            # Clear it so we don't repeat
            self._last_json_fragment = None
            return f"""ERROR: Your output "{fragment}" is NOT a valid tool call.

CORRECT FORMAT: {{"tool": "ToolName", "parameters": {{"key": "value"}}}}

The "tool" key is REQUIRED. Examples:
- {{"tool": "Bash", "parameters": {{"command": "python -m pytest"}}}}
- {{"tool": "Read", "parameters": {{"file_path": "tests/test_file.py"}}}}
- {{"tool": "LS", "parameters": {{"path": "."}}}}

Fix your response and output a VALID tool call now:"""

        # Check for pending todos - most important signal
        todos_state = self._get_todos_completion_state()
        if todos_state["total"] > 0 and todos_state["completed"] < todos_state["total"]:
            pending_count = todos_state["total"] - todos_state["completed"]
            # Get the first pending todo content
            pending_todos = []
            try:
                todo_tool = self.tool_manager.get_tool("TodoWrite")
                if todo_tool and hasattr(todo_tool, "todos") and todo_tool.todos:
                    for todo in todo_tool.todos:
                        if hasattr(todo, "status") and todo.status != "completed":
                            pending_todos.append(todo.content)
                        elif isinstance(todo, dict) and todo.get("status") != "completed":
                            pending_todos.append(todo.get("content", ""))
            except Exception:
                pass

            pending_list = "\n".join(f"- {t}" for t in pending_todos[:3]) if pending_todos else ""

            return f"""IMPORTANT: You have {pending_count} pending todos that must be completed!

Pending tasks:
{pending_list}

You MUST complete the remaining tasks. If this is the final task (e.g., "compile summary" or "provide overview"), generate a detailed response answering the user's original question.

Continue working or provide your final answer:"""

        # Check if this appears to be a read-only/exploration task
        if hasattr(self, "_current_task_is_readonly") and self._current_task_is_readonly:
            return """You have pending work. Continue with READ-ONLY tools to complete the exploration.

Example: {"tool": "Read", "parameters": {"file_path": "README.md"}}

What will you read or explore next?"""

        return """You have pending work. Continue with the appropriate tool.

Example: {"tool": "LS", "parameters": {"path": "."}}

What tool will you call?"""

    def _should_continue_generation(self, finish_reason: str, response_text: str) -> bool:
        """
        Determine if we should continue generating.

        Args:
            finish_reason: The finish reason from API
            response_text: The generated text

        Returns:
            True if we should continue
        """
        # Check finish reason first
        if finish_reason == "length":
            return True

        # Use continuation manager's detection
        return self.continuation_manager.should_continue(finish_reason, response_text)

    def _is_response_truncated(self, response_text: str, finish_reason: str) -> bool:
        """
        Check if the response was truncated (model cut off mid-response).

        This is a simple check - only returns True if:
        - finish_reason is "length" (hit token limit)
        - OR response ends with clear truncation indicators

        Args:
            response_text: The model's response
            finish_reason: The API finish reason

        Returns:
            True if response appears truncated
        """
        # Clear truncation: hit token limit
        if finish_reason == "length":
            return True

        # Check for unclosed code blocks
        if response_text.count("```") % 2 == 1:
            return True

        # Check for ending mid-sentence (ends with comma, colon, or opening bracket)
        stripped = response_text.rstrip()
        truncation_endings = [",", ":", "{", "[", "("]
        if stripped and stripped[-1] in truncation_endings:
            return True

        return False

    def _get_continuation_prompt(self, iteration: int) -> str:
        """
        Get the continuation prompt for requesting more output from external config.

        Args:
            iteration: Current iteration number

        Returns:
            Continuation prompt string
        """
        from ..config.prompts import get_prompts_config

        return get_prompts_config().get_continuation_prompt(iteration)

    def _extract_tool_calls(self, raw_response, response_text: str, provider_name: str) -> list:
        """Extract tool calls from response - handles native API tool calls and text-based JSON"""
        import json
        import re

        tool_calls = []

        # Check OpenAI style tool calls from raw response
        if raw_response and hasattr(raw_response, "choices"):
            choice = raw_response.choices[0]
            if (
                hasattr(choice, "message")
                and hasattr(choice.message, "tool_calls")
                and choice.message.tool_calls
            ):
                for tc in choice.message.tool_calls:
                    tool_calls.append(
                        {"name": tc.function.name, "arguments": json.loads(tc.function.arguments)}
                    )
                return tool_calls

        # Check Anthropic style tool calls from raw response
        if raw_response and hasattr(raw_response, "content"):
            for block in raw_response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    tool_calls.append({"name": block.name, "arguments": block.input})
            if tool_calls:
                return tool_calls

        # Fallback: Parse tool calls from text (for models that output JSON in text)
        # This handles models like gpt-oss-120b that output tool calls as JSON text
        tool_calls = self._parse_json_tool_calls_from_text(response_text)

        return tool_calls

    def _parse_json_tool_calls_from_text(self, text: str) -> list:
        """Parse JSON tool calls from model text output - with validation"""
        import json
        import re

        tool_calls = []

        # Check debug mode - only show verbose messages in debug mode
        debug_mode = self.config.get("debug", False) or self.config.get("ui", {}).get(
            "debug_mode", False
        )

        def debug_print(message: str):
            """Print message only if debug mode is enabled."""
            if debug_mode:
                self.console.print(message)

        # Valid tool names that we should accept (lowercase for comparison)
        VALID_TOOLS = {
            "ls",
            "lstool",
            "read",
            "readtool",
            "write",
            "writetool",
            "edit",
            "edittool",
            "bash",
            "bashtool",
            "glob",
            "globtool",
            "grep",
            "greptool",
            "todowrite",
            "askuserquestion",
            "askuser",
            "notebookedit",
            "webfetch",
            "websearch",
            "task",
        }

        def is_valid_tool_name(name: str) -> bool:
            """Check if tool name is valid"""
            if not name:
                return False
            return name.lower() in VALID_TOOLS

        def is_valid_tool_call(tool_name: str, args: dict) -> bool:
            """Validate that the tool call has reasonable arguments"""
            if not is_valid_tool_name(tool_name):
                return False

            tool_lower = tool_name.lower().replace("tool", "")

            # Validate based on tool type
            if tool_lower in ["ls", "list"]:
                # LS needs path, and "/" on Windows is suspicious - fix it
                path = args.get("path", "")
                if path == "/" or path == "\\":
                    self.console.print(
                        f"[dim yellow][!] Fixing LS root path '{path}' to '.' (current directory)[/dim yellow]"
                    )
                    args["path"] = "."  # This modifies in place
                elif not path:
                    args["path"] = "."  # Default to current directory
                return True

            if tool_lower in ["read"]:
                return "file_path" in args

            if tool_lower in ["write"]:
                return "file_path" in args and "content" in args

            if tool_lower in ["edit"]:
                return "file_path" in args and ("old_string" in args or "new_string" in args)

            if tool_lower in ["bash"]:
                return "command" in args

            if tool_lower in ["glob"]:
                return "pattern" in args

            if tool_lower in ["grep"]:
                return "pattern" in args

            # Default: accept if it has at least one argument
            return bool(args)

        def unescape_content(content: str) -> str:
            """
            Carefully unescape content that may have double-escaped sequences.

            The model sometimes outputs \\n instead of \n in JSON, which after
            JSON parsing becomes the literal string '\n' (backslash-n) instead
            of an actual newline character.

            IMPORTANT: We must be careful not to break valid Python/code escape
            sequences. Only unescape when the content appears to be entirely
            single-line with escaped newlines (indicating double-escaping).
            """
            if not isinstance(content, str):
                return content

            # If content already has actual newlines, don't unescape -
            # it's already properly formatted code
            if "\n" in content:
                return content

            # If content has no backslashes at all, nothing to unescape
            if "\\" not in content:
                return content

            # Only unescape if content appears to be a single-line string
            # with escaped newlines (indicating the model double-escaped it)
            # This is heuristic: if we see \\n but no actual newlines,
            # it's likely the model intended actual newlines
            result = content

            # Replace literal \n with actual newline (only if no real newlines exist)
            result = result.replace("\\n", "\n")
            # Replace literal \t with actual tab
            result = result.replace("\\t", "\t")
            # Replace literal \r with actual carriage return
            result = result.replace("\\r", "\r")

            # DON'T unescape quotes or backslashes - these are often
            # intentional in code strings and unescaping them causes
            # syntax errors in Python/JavaScript/etc.
            # result = result.replace('\\"', '"')  # DISABLED - breaks code
            # result = result.replace("\\'", "'")  # DISABLED - breaks code
            # result = result.replace('\\\\', '\\')  # DISABLED - breaks code

            return result

        def process_arguments(args: dict) -> dict:
            """Process arguments - only unescape content for WriteTool when needed"""
            if not isinstance(args, dict):
                return args

            processed = {}
            for key, value in args.items():
                if key == "content" and isinstance(value, str):
                    # Only unescape content field for file writes, not for edit old_string/new_string
                    # Check if this looks like double-escaped content (no real newlines)
                    if "\n" not in value and "\\n" in value:
                        processed[key] = unescape_content(value)
                    else:
                        processed[key] = value
                elif key in ("old_string", "new_string") and isinstance(value, str):
                    # For edit operations, DON'T unescape - preserve exact strings
                    # The model should output these with proper escaping already
                    processed[key] = value
                elif isinstance(value, dict):
                    processed[key] = process_arguments(value)
                else:
                    processed[key] = value
            return processed

        def extract_tool_args(data: dict) -> dict:
            """
            Extract tool arguments from data, handling different formats:
            1. {"tool": "X", "parameters": {...}} - Standard format
            2. {"tool": "X", "params": {...}} - Alternate key
            3. {"tool": "X", "path": "...", "pattern": "..."} - Flat format (params at root level)
            """
            # Check for nested parameters first
            if "parameters" in data:
                return data["parameters"]
            if "params" in data:
                return data["params"]
            if "arguments" in data:
                return data["arguments"]

            # Flat format - parameters at root level alongside "tool"
            # Extract all keys except "tool" as parameters
            args = {}
            for key, value in data.items():
                if key != "tool":
                    args[key] = value
            return args

        # STRATEGY 0: Detect malformed TodoWrite attempts
        # Model sometimes outputs: **Task List** ```json {"todos": [...]}```
        # Need to convert this to proper TodoWrite tool call
        def normalize_todo_item(item, index=0, first_in_progress=True):
            """Normalize a todo item to proper format with content, status, activeForm."""
            if isinstance(item, str):
                # String item - convert to proper format
                content = item.strip()
                status = "in_progress" if (index == 0 and first_in_progress) else "pending"
                # Generate activeForm from content (imperative -> present continuous)
                active_form = generate_active_form(content)
                return {"content": content, "status": status, "activeForm": active_form}
            elif isinstance(item, dict):
                # Dict item - normalize field names
                content = (
                    item.get("content")
                    or item.get("title")
                    or item.get("task")
                    or item.get("text")
                    or item.get("description")
                    or item.get("name")
                    or ""
                )
                if not content:
                    return None
                status = item.get("status", "pending")
                if status not in ["pending", "in_progress", "completed", "blocked", "skipped"]:
                    status = "pending"
                active_form = (
                    item.get("activeForm")
                    or item.get("active_form")
                    or item.get("activeform")
                    or generate_active_form(content)
                )
                return {"content": content, "status": status, "activeForm": active_form}
            return None

        def generate_active_form(content: str) -> str:
            """Generate present continuous form from imperative form."""
            if not content:
                return "Working..."
            # Common verb transformations
            words = content.strip().split()
            if not words:
                return "Working..."
            verb = words[0].lower()
            rest = " ".join(words[1:]) if len(words) > 1 else ""

            # Handle common verbs
            verb_map = {
                "add": "Adding",
                "create": "Creating",
                "fix": "Fixing",
                "update": "Updating",
                "remove": "Removing",
                "delete": "Deleting",
                "implement": "Implementing",
                "write": "Writing",
                "read": "Reading",
                "test": "Testing",
                "run": "Running",
                "check": "Checking",
                "analyze": "Analyzing",
                "review": "Reviewing",
                "refactor": "Refactoring",
                "debug": "Debugging",
                "investigate": "Investigating",
                "explore": "Exploring",
                "search": "Searching",
                "find": "Finding",
                "look": "Looking",
                "build": "Building",
                "compile": "Compiling",
                "install": "Installing",
                "configure": "Configuring",
                "setup": "Setting up",
                "set": "Setting",
                "get": "Getting",
                "fetch": "Fetching",
                "load": "Loading",
                "save": "Saving",
                "export": "Exporting",
                "import": "Importing",
                "parse": "Parsing",
                "extract": "Extracting",
                "convert": "Converting",
                "validate": "Validating",
                "verify": "Verifying",
                "ensure": "Ensuring",
            }

            if verb in verb_map:
                return f"{verb_map[verb]} {rest}".strip()
            elif verb.endswith("e"):
                return f"{verb[:-1].capitalize()}ing {rest}".strip()
            else:
                return f"{verb.capitalize()}ing {rest}".strip()

        def normalize_todos_list(todos_raw):
            """Normalize a list of todos to proper format."""
            if not isinstance(todos_raw, list) or not todos_raw:
                return None

            normalized = []
            has_in_progress = False

            for i, item in enumerate(todos_raw):
                todo = normalize_todo_item(item, i, not has_in_progress)
                if todo:
                    if todo["status"] == "in_progress":
                        has_in_progress = True
                    normalized.append(todo)

            # REMOVED: Don't force in_progress status
            # The model may explicitly mark all todos as "completed" to signal task completion
            # Forcing one to in_progress caused infinite loops where model couldn't finish
            # if normalized and not has_in_progress:
            #     normalized[0]['status'] = 'in_progress'

            return normalized if normalized else None

        # Try to find TodoWrite JSON anywhere in the text
        todowrite_patterns = [
            # Full TodoWrite tool call with various nested formats
            r'\{\s*["\']tool["\']\s*:\s*["\']TodoWrite["\']\s*,\s*["\'](?:parameters|params|arguments)["\']\s*:\s*\{\s*["\']todos["\']\s*:\s*(\[[\s\S]*?\])\s*\}\s*\}',
            # Just {"todos": [...]} format
            r'\{\s*["\']todos["\']\s*:\s*(\[[\s\S]*?\])\s*\}',
            # Task list markdown followed by JSON
            r'(?:task\s*list|todowrite|tasks?)[\s\S]{0,50}\{\s*["\']todos["\']\s*:\s*(\[[\s\S]*?\])',
        ]

        for pattern in todowrite_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                try:
                    todos_str = match.group(1)
                    # Clean up the JSON string
                    todos_str = todos_str.strip()
                    todos_raw = json.loads(todos_str)
                    normalized = normalize_todos_list(todos_raw)
                    if normalized:
                        debug_print(
                            f"[bold blue][+] Detected TodoWrite - normalizing {len(normalized)} items[/bold blue]"
                        )
                        tool_calls.append({"name": "TodoWrite", "arguments": {"todos": normalized}})
                        return tool_calls
                except (json.JSONDecodeError, IndexError) as e:
                    continue

        # STRATEGY 1: Look for JSON in code fences (most reliable)
        json_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)

        for block in json_blocks:
            try:
                data = json.loads(block)
                if "tool" in data:
                    args = extract_tool_args(data)
                    if is_valid_tool_call(data["tool"], args):
                        tool_calls.append(
                            {"name": data["tool"], "arguments": process_arguments(args)}
                        )
                        debug_print(
                            f"[bold blue][+] Detected {data['tool']} from JSON block[/bold blue]"
                        )
                elif "todos" in data:
                    # This is a TodoWrite without the tool wrapper - normalize it
                    normalized = normalize_todos_list(data["todos"])
                    if normalized:
                        debug_print(
                            f"[bold blue][+] Detected TodoWrite from JSON block - normalizing {len(normalized)} items[/bold blue]"
                        )
                        tool_calls.append({"name": "TodoWrite", "arguments": {"todos": normalized}})
                elif "file_path" in data and "content" in data:
                    # Looks like WriteTool parameters - requires both file_path and content
                    tool_calls.append({"name": "WriteTool", "arguments": process_arguments(data)})
                    debug_print(f"[bold blue][+] Detected WriteTool from JSON block[/bold blue]")
            except json.JSONDecodeError:
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 2: Find JSON objects with "tool" field anywhere in text
        # More permissive regex that handles multiline and nested objects
        # Supports: parameters, params, arguments
        tool_json_pattern = r'\{\s*["\']tool["\']\s*:\s*["\'](\w+)["\']\s*,\s*["\'](?:parameters|params|arguments)["\']\s*:\s*(\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\})'

        for match in re.finditer(tool_json_pattern, text, re.DOTALL):
            tool_name = match.group(1)
            params_str = match.group(2)
            try:
                params = json.loads(params_str)
                if is_valid_tool_call(tool_name, params):
                    tool_calls.append({"name": tool_name, "arguments": process_arguments(params)})
                    debug_print(f"[bold blue][+] Detected {tool_name} from inline JSON[/bold blue]")
            except json.JSONDecodeError:
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 3: Look for any JSON object that could be a tool call
        # Try to find standalone JSON objects
        json_objects = re.findall(
            r'(\{[^{}]*(?:"tool"|"file_path"|"content")[^{}]*\})', text, re.DOTALL
        )

        for obj_str in json_objects:
            try:
                data = json.loads(obj_str)
                if "tool" in data:
                    args = extract_tool_args(data)
                    if is_valid_tool_call(data["tool"], args):
                        tool_calls.append(
                            {"name": data["tool"], "arguments": process_arguments(args)}
                        )
                        debug_print(
                            f"[bold blue][+] Detected {data['tool']} from standalone JSON[/bold blue]"
                        )
                elif "file_path" in data and "content" in data:
                    tool_calls.append({"name": "WriteTool", "arguments": process_arguments(data)})
                    debug_print(
                        f"[bold blue][+] Detected WriteTool from standalone JSON[/bold blue]"
                    )
            except json.JSONDecodeError:
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 4: Look for the full JSON structure including nested parameters
        # This handles cases where the JSON spans multiple lines
        # Try to find ALL tool JSON objects, not just the first one
        for match in re.finditer(r'\{\s*["\']tool["\']', text):
            try:
                # Try to extract a balanced JSON from this point
                json_str = self._extract_balanced_json(text[match.start() :])
                if json_str:
                    data = json.loads(json_str)
                    if "tool" in data:
                        args = extract_tool_args(data)
                        if is_valid_tool_call(data["tool"], args):
                            tool_calls.append(
                                {"name": data["tool"], "arguments": process_arguments(args)}
                            )
                            debug_print(
                                f"[bold blue][+] Detected {data['tool']} from balanced extraction[/bold blue]"
                            )
            except (json.JSONDecodeError, Exception):
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 5: Handle gpt-oss-120b specific patterns
        # Pattern: {"function": "ToolName", "args": {...}}
        func_pattern = (
            r'\{\s*["\']function["\']\s*:\s*["\'](\w+)["\']\s*,\s*["\']args["\']\s*:\s*(\{[^}]+\})'
        )
        for match in re.finditer(func_pattern, text, re.DOTALL):
            try:
                tool_name = match.group(1)
                args = json.loads(match.group(2))
                if is_valid_tool_call(tool_name, args):
                    tool_calls.append({"name": tool_name, "arguments": process_arguments(args)})
                    debug_print(
                        f"[bold blue][+] Detected {tool_name} from function/args pattern[/bold blue]"
                    )
            except:
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 6: Handle labeled tool code blocks
        # Pattern: ```tool:WriteTool\n{...}\n```
        labeled_blocks = re.findall(r"```tool:(\w+)\s*\n(\{[\s\S]*?\})\s*```", text)
        for tool_name, json_str in labeled_blocks:
            try:
                args = json.loads(json_str)
                if is_valid_tool_call(tool_name, args):
                    tool_calls.append({"name": tool_name, "arguments": process_arguments(args)})
                    debug_print(
                        f"[bold blue][+] Detected {tool_name} from labeled code block[/bold blue]"
                    )
            except:
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 7: Handle action/input format (some OSS models use this)
        # Pattern: {"action": "ToolName", "input": {...}}
        action_pattern = r'\{\s*["\']action["\']\s*:\s*["\'](\w+)["\']\s*,\s*["\'](?:action_)?input["\']\s*:\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
        for match in re.finditer(action_pattern, text, re.DOTALL):
            try:
                tool_name = match.group(1)
                args = json.loads(match.group(2))
                if is_valid_tool_call(tool_name, args):
                    tool_calls.append({"name": tool_name, "arguments": process_arguments(args)})
                    debug_print(
                        f"[bold blue][+] Detected {tool_name} from action/input pattern[/bold blue]"
                    )
            except:
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 8: Last resort - look for file_path and content anywhere
        # This handles cases where the model outputs WriteTool parameters without the wrapper
        # Require BOTH file_path and content, and content must be substantial
        file_path_match = re.search(r'["\']file_path["\']\s*:\s*["\']([^"\']+)["\']', text)
        content_match = re.search(
            r'["\']content["\']\s*:\s*["\'](.+?)["\'](?:\s*[,}])', text, re.DOTALL
        )

        if file_path_match and content_match:
            file_path = file_path_match.group(1)
            content = content_match.group(1)

            # Validate: file_path should look like a real path, content should be substantial
            if file_path and len(content) > 10:  # Minimum content length
                # Unescape the content using the helper function
                content = unescape_content(content)
                tool_calls.append(
                    {"name": "WriteTool", "arguments": {"file_path": file_path, "content": content}}
                )
                debug_print(
                    f"[bold blue][+] Detected WriteTool from scattered JSON fields: {file_path}[/bold blue]"
                )

        # STRATEGY 9: Handle command-style tool calls
        # Pattern: "I'll use the Read tool to read file.py" followed by potential JSON
        command_patterns = [
            (
                r"(?:use|call|invoke|run)\s+(?:the\s+)?(\w+)(?:\s+tool)?(?:\s+to\s+|\s+on\s+)(?:[^{]*?)\{([^}]+)\}",
                "command",
            ),
            (r"Tool:\s*(\w+)\s*(?:\n|:)\s*\{([^}]+)\}", "labeled"),
        ]

        for pattern, pattern_name in command_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                try:
                    tool_name = match.group(1)
                    json_str = "{" + match.group(2) + "}"
                    args = json.loads(json_str)
                    if is_valid_tool_call(tool_name, args):
                        tool_calls.append({"name": tool_name, "arguments": process_arguments(args)})
                        debug_print(
                            f"[bold blue][+] Detected {tool_name} from {pattern_name} pattern[/bold blue]"
                        )
                except:
                    continue

        return tool_calls

    def _extract_balanced_json(self, text: str, max_length: int = 10000) -> Optional[str]:
        """Extract a balanced JSON object from text"""
        if not text or text[0] != "{":
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[:max_length]):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[: i + 1]

        return None

    def _normalize_tool_arguments(self, tool_name: str, arguments: dict) -> dict:
        """
        Normalize tool arguments to handle different parameter names from different models.

        Maps common alternate parameter names to expected names for each tool.
        """
        # Parameter name mappings for different tools
        # Maps common alternate parameter names to the expected parameter names
        PARAM_MAPPINGS = {
            "glob": {
                # If 'path' looks like a glob pattern, it's probably meant to be 'pattern'
                # e.g. {"tool": "Glob", "path": "**/*.html"} -> {"pattern": "**/*.html"}
                "include": "pattern",  # Some models use 'include' for glob patterns
                "file_pattern": "pattern",
                "files": "pattern",
            },
            "grep": {
                "query": "pattern",
                "search": "pattern",
                "text": "pattern",
                "regex": "pattern",
                "include": "glob",  # File filter pattern
                "file_pattern": "glob",
                "filter": "glob",
                "-i": "case_insensitive",
                "ignore_case": "case_insensitive",
                "-A": "context_after",
                "-B": "context_before",
                "-C": "context",  # Will need special handling
                "directory": "path",
                "dir": "path",
                "folder": "path",
            },
            "read": {
                "path": "file_path",
                "filename": "file_path",
                "file": "file_path",
                "filepath": "file_path",
            },
            "write": {
                "path": "file_path",
                "filename": "file_path",
                "file": "file_path",
                "filepath": "file_path",
                "text": "content",
                "data": "content",
                "body": "content",
            },
            "edit": {
                "path": "file_path",
                "filename": "file_path",
                "file": "file_path",
                "filepath": "file_path",
                "old": "old_string",
                "new": "new_string",
                "search": "old_string",
                "replace": "new_string",
                "find": "old_string",
                "replacement": "new_string",
            },
            "bash": {
                "cmd": "command",
                "shell": "command",
                "run": "command",
                "script": "command",
                "exec": "command",
            },
            "ls": {
                "dir": "path",
                "directory": "path",
                "folder": "path",
                "file_path": "path",
            },
            "task": {
                "type": "subagent_type",
                "agent_type": "subagent_type",
                "agent": "subagent_type",
            },
            "todowrite": {
                "items": "todos",
                "tasks": "todos",
                "list": "todos",
            },
            "webfetch": {
                "query": "prompt",
                "question": "prompt",
            },
            "websearch": {
                "search": "query",
                "q": "query",
                "term": "query",
            },
            "askuserquestion": {
                "question": "questions",  # Single question -> questions array
                "prompt": "questions",
                "message": "questions",
                "ask": "questions",
                "action": "questions",  # GPT-OSS sometimes uses 'action'
            },
            "askuser": {
                "question": "questions",
                "prompt": "questions",
                "message": "questions",
                "ask": "questions",
                "action": "questions",
            },
        }

        # Get tool's base name (without 'tool' suffix)
        base_name = tool_name.lower()
        if base_name.endswith("tool"):
            base_name = base_name[:-4]

        # Get mappings for this tool
        mappings = PARAM_MAPPINGS.get(base_name, {})

        # Apply mappings
        normalized = {}
        for key, value in arguments.items():
            # Check if this key should be mapped to another name
            if key in mappings:
                normalized[mappings[key]] = value
            else:
                normalized[key] = value

        # Special handling for GlobTool: if 'path' contains glob characters, it's probably 'pattern'
        if base_name == "glob":
            if "path" in normalized and "pattern" not in normalized:
                path_val = normalized.get("path", "")
                if isinstance(path_val, str) and ("*" in path_val or "?" in path_val):
                    # This looks like a pattern, not a directory path
                    normalized["pattern"] = path_val
                    # Set path to current directory
                    normalized["path"] = "."

        # Special handling for Task tool: ensure subagent_type is set
        if base_name == "task":
            if "subagent_type" not in normalized:
                # Default to 'Explore' for investigation tasks, 'general-purpose' otherwise
                prompt = normalized.get("prompt", "").lower()
                if any(
                    word in prompt
                    for word in ["find", "search", "look", "explore", "where", "what files"]
                ):
                    normalized["subagent_type"] = "Explore"
                else:
                    normalized["subagent_type"] = "general-purpose"
                self.console.print(
                    f"[dim]ℹ Task tool: defaulting subagent_type to '{normalized['subagent_type']}'[/dim]"
                )

            # Ensure description is set
            if "description" not in normalized:
                prompt = normalized.get("prompt", "")
                normalized["description"] = prompt[:50] + "..." if len(prompt) > 50 else prompt

        # Special handling for AskUserQuestion: convert simple formats to expected format
        if base_name in ["askuserquestion", "askuser", "ask"]:
            questions = normalized.get("questions")

            # If questions is a string (simple question), convert to proper format
            if isinstance(questions, str):
                normalized["questions"] = [
                    {
                        "question": questions,
                        "header": "Question",
                        "type": "open",  # Open-ended question (no options)
                    }
                ]
            # If questions is missing but there's other text-like content, use it
            elif questions is None:
                # Look for any string value that could be the question
                for key in ["text", "query", "input", "content"]:
                    if key in normalized and isinstance(normalized[key], str):
                        normalized["questions"] = [
                            {"question": normalized[key], "header": "Question", "type": "open"}
                        ]
                        break
                else:
                    # Last resort: if there's any string argument, use it
                    for key, value in list(arguments.items()):
                        if isinstance(value, str) and key != "tool":
                            normalized["questions"] = [
                                {"question": value, "header": "Question", "type": "open"}
                            ]
                            break

        return normalized

    async def _execute_tool_calls(
        self, tool_calls: list, require_confirmation: bool = True, max_retries: int = 2
    ) -> list:
        """
        Execute a list of tool calls and return results with optional confirmation for file operations.

        Args:
            tool_calls: List of tool call dictionaries with 'name' and 'arguments'
            require_confirmation: Whether to ask user confirmation for write operations
            max_retries: Maximum number of retries for transient failures (default 2)

        Returns:
            List of (tool_name, result, arguments) tuples
        """
        import asyncio
        from ..tools.tool_manager import ToolExecutionContext
        from ..tools.base_tool import ToolResult

        # Transient error patterns that warrant a retry
        TRANSIENT_ERRORS = ["timeout", "temporary", "retry", "busy", "unavailable", "connection"]

        def is_transient_error(error_msg: str) -> bool:
            """Check if error is likely transient and worth retrying"""
            if not error_msg:
                return False
            error_lower = error_msg.lower()
            return any(pattern in error_lower for pattern in TRANSIENT_ERRORS)

        async def execute_with_retry(tool_name: str, arguments: dict) -> ToolResult:
            """Execute a tool with retry logic for transient failures"""
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    result = await self.tool_manager.execute_tool(tool_name, **arguments)

                    # Check for transient errors that might succeed on retry
                    if not result.success and attempt < max_retries:
                        if is_transient_error(result.error):
                            self.console.print(
                                f"[dim][R] Retrying {tool_name} (attempt {attempt + 2}/{max_retries + 1})...[/dim]"
                            )
                            await asyncio.sleep(1)  # Brief delay before retry
                            continue

                    return result

                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        self.console.print(f"[dim][R] Tool error, retrying {tool_name}: {e}[/dim]")
                        await asyncio.sleep(1)
                        continue

                    # All retries exhausted
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed after {max_retries + 1} attempts: {str(last_error)}",
                    )

            # Should not reach here, but return error just in case
            return ToolResult(
                success=False, output="", error=f"Unexpected error after {max_retries + 1} attempts"
            )

        results = []
        write_operations = []
        other_operations = []

        # Separate write operations (need confirmation) from others
        for tc in tool_calls:
            tool_name = tc["name"].lower()
            if tool_name in [
                "writetool",
                "edittool",
                "multiedittool",
                "write",
                "edit",
                "multiedit",
            ]:
                write_operations.append(tc)
            else:
                other_operations.append(tc)

        # Execute non-write operations immediately with retry support
        for tc in other_operations:
            tool_name = tc["name"].lower()
            arguments = self._normalize_tool_arguments(tool_name, tc["arguments"])

            # Only show tool call message in debug mode
            self._debug_print(f"[bold yellow][>] Calling tool: {tool_name}[/bold yellow]")

            result = await execute_with_retry(tool_name, arguments)
            results.append((tool_name, result, arguments))

        # Handle write operations with confirmation
        if write_operations:
            if require_confirmation:
                # Display pending write operations
                self._display_pending_writes(write_operations)

                # Ask for confirmation (default is Yes - press Enter to accept)
                self.console.print(
                    "[bold yellow]Execute these file operations?[/bold yellow] [[green]Ok[/green]/n]: ",
                    end="",
                )
                try:
                    response = input().strip().lower()
                except (EOFError, KeyboardInterrupt):
                    response = "n"

                # Default to "yes" if user just presses Enter
                if response == "":
                    response = "y"

                if response not in ["y", "yes", "ok"]:
                    self.console.print("[bold red][X] File operations cancelled by user[/bold red]")
                    for tc in write_operations:
                        arguments = self._normalize_tool_arguments(
                            tc["name"].lower(), tc["arguments"]
                        )
                        results.append(
                            (
                                tc["name"],
                                ToolResult(
                                    success=False, output="", error="Operation cancelled by user"
                                ),
                                arguments,
                            )
                        )
                    return results

            # Execute write operations with retry support
            for tc in write_operations:
                tool_name = tc["name"].lower()
                arguments = self._normalize_tool_arguments(tool_name, tc["arguments"])

                # Only show writing message in debug mode
                self._debug_print(f"[bold green][W]  Writing: {tool_name}[/bold green]")

                result = await execute_with_retry(tool_name, arguments)
                results.append((tool_name, result, arguments))

        return results

    def _get_command_key(self, tool_name: str, arguments: dict) -> str:
        """
        Create a unique key for a command to track retries.

        This normalizes similar commands so we can detect retry loops.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            A string key representing the command
        """
        import hashlib
        import json

        tool_lower = tool_name.lower().replace("tool", "")

        # For bash commands, use the command itself
        if tool_lower == "bash":
            cmd = arguments.get("command", "")
            # Normalize whitespace and extract core command
            normalized = " ".join(cmd.split())
            return f"bash:{normalized}"

        # For other tools, create a hash of the key arguments
        key_parts = [tool_lower]
        for key in sorted(arguments.keys()):
            value = arguments[key]
            if isinstance(value, str):
                key_parts.append(f"{key}={value}")
            else:
                key_parts.append(f"{key}={json.dumps(value)}")

        return ":".join(key_parts)

    def _display_pending_writes(self, write_operations: list):
        """
        Display pending write operations for user review - Claude Code style.

        Shows actual file diffs with syntax highlighting:
        - For new files: shows full content with + prefix (green)
        - For edits: shows removed lines (-) and added lines (+)
        """
        from rich.panel import Panel
        from rich.text import Text
        from rich.syntax import Syntax
        from rich.table import Table
        from rich import box
        from pathlib import Path

        palette = self._palette
        icons = self._icons

        for tc in write_operations:
            tool_name = tc["name"].lower()
            args = tc["arguments"]

            if tool_name in ["writetool", "write"]:
                file_path = args.get("file_path", "unknown")
                content = args.get("content", "")

                # Check if file exists (edit vs create)
                file_exists = Path(file_path).exists()

                # Build diff display
                diff_lines = []
                if file_exists:
                    # Read existing content for diff
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                            old_content = f.read()
                        # Show as replacement
                        for line in old_content.split("\n")[:20]:
                            diff_lines.append(("remove", line))
                        if old_content.count("\n") > 20:
                            diff_lines.append(
                                (
                                    "info",
                                    f"... ({old_content.count(chr(10)) - 20} more lines removed)",
                                )
                            )
                    except:
                        pass

                # Add new content
                new_lines = content.split("\n")
                for line in new_lines[:30]:
                    diff_lines.append(("add", line))
                if len(new_lines) > 30:
                    diff_lines.append(("info", f"... ({len(new_lines) - 30} more lines)"))

                # Display header
                action = "Edit" if file_exists else "Write"
                self.console.print(
                    f"\n[bold {palette.warning}]{icons.FILE} {action}: {file_path}[/bold {palette.warning}]"
                )

                # Display diff
                for line_type, line in diff_lines:
                    if line_type == "remove":
                        self.console.print(f"[red]- {line}[/red]")
                    elif line_type == "add":
                        self.console.print(f"[green]+ {line}[/green]")
                    else:
                        self.console.print(f"[dim]{line}[/dim]")

            elif tool_name in ["edittool", "edit"]:
                file_path = args.get("file_path", "unknown")
                old_str = args.get("old_string", "")
                new_str = args.get("new_string", "")

                # Display header
                self.console.print(
                    f"\n[bold {palette.warning}]{icons.EDIT} Edit: {file_path}[/bold {palette.warning}]"
                )

                # Show removed lines
                old_lines = old_str.split("\n")
                for line in old_lines[:15]:
                    self.console.print(f"[red]- {line}[/red]")
                if len(old_lines) > 15:
                    self.console.print(f"[dim]... ({len(old_lines) - 15} more lines removed)[/dim]")

                # Show added lines
                new_lines = new_str.split("\n")
                for line in new_lines[:15]:
                    self.console.print(f"[green]+ {line}[/green]")
                if len(new_lines) > 15:
                    self.console.print(f"[dim]... ({len(new_lines) - 15} more lines added)[/dim]")

            elif tool_name in ["multiedittool", "multiedit"]:
                file_path = args.get("file_path", "unknown")
                edits = args.get("edits", [])

                self.console.print(
                    f"\n[bold {palette.warning}]{icons.EDIT} MultiEdit: {file_path}[/bold {palette.warning}]"
                )
                self.console.print(f"[dim]{len(edits)} edit(s) to apply[/dim]")

                for i, edit in enumerate(edits[:3], 1):
                    old_str = edit.get("old_string", "")[:50]
                    new_str = edit.get("new_string", "")[:50]
                    self.console.print(
                        f"[dim]  {i}. [red]-[/red] {old_str}{'...' if len(edit.get('old_string', '')) > 50 else ''}[/dim]"
                    )
                    self.console.print(
                        f"[dim]     [green]+[/green] {new_str}{'...' if len(edit.get('new_string', '')) > 50 else ''}[/dim]"
                    )

                if len(edits) > 3:
                    self.console.print(f"[dim]  ... and {len(edits) - 3} more edits[/dim]")

        self.console.print("")  # Empty line before prompt

    def _display_tool_result(self, tool_name: str, result, arguments: dict):
        """
        Display tool execution result in Claude Code style.

        Uses the HcodeToolDisplay class for consistent formatting:
        - WriteTool: Only show file path and byte count (no content)
        - EditTool: Show file path with diff (old -> new)
        - BashTool: Show command and full output in box
        - ReadTool: Show file path and line count
        - TodoWrite: Show task panel with progress
        - Other tools: Show appropriate preview
        """
        from ..cli.tool_display import HcodeToolDisplay
        from rich.panel import Panel
        from rich import box

        # Special handling for TodoWrite - skip display here
        # The main_cli.py handles todo display with its own todo bar
        # This prevents duplicate todo displays
        if tool_name.lower() == "todowrite":
            # Only show in debug mode
            if self._is_debug_mode():
                todos = arguments.get("todos", [])
                if todos:
                    total = len(todos)
                    completed = sum(1 for t in todos if t.get("status") == "completed")
                    status_text = f"[{self._palette.info}]{self._icons.GEAR} Tasks updated: {completed}/{total} completed[/]"
                    self.console.print(status_text)
            return

        # Use Hcode-style tool display for other tools
        display = HcodeToolDisplay(self.console)
        display.display_tool_call(tool_name, arguments, result)

    async def explore_codebase(self, query: str, thoroughness: str = "medium") -> str:
        """
        Explore codebase using specialized Explore agent.

        Args:
            query: What to explore
            thoroughness: quick, medium, or very thorough

        Returns:
            Exploration results
        """
        result = await self.agent_orchestrator.execute_with_agents(
            task=query, agent_types=[HcodeAgentType.EXPLORE], parallel=False
        )

        return result[0].output if result else "No results"

    async def plan_implementation(self, task: str, explore_first: bool = True) -> str:
        """
        Create implementation plan using Plan agent.

        Args:
            task: Task to plan
            explore_first: Explore codebase first

        Returns:
            Implementation plan
        """
        agent_types = [HcodeAgentType.PLAN]
        if explore_first:
            agent_types.insert(0, HcodeAgentType.EXPLORE)

        results = await self.agent_orchestrator.execute_with_agents(
            task=task, agent_types=agent_types, parallel=False
        )

        return results[-1].output if results else "No plan created"

    async def implement_with_plan(self, task: str) -> str:
        """
        Full implementation flow: Explore → Plan → Implement.

        Args:
            task: Task to implement

        Returns:
            Implementation result
        """
        results = await self.agent_orchestrator.execute_with_agents(
            task=task,
            agent_types=[HcodeAgentType.EXPLORE, HcodeAgentType.PLAN, HcodeAgentType.IMPLEMENT],
            parallel=False,
        )

        return results[-1].output if results else "Implementation failed"

    async def ask_user(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ask user questions interactively.

        Args:
            questions: List of questions

        Returns:
            User answers
        """
        result = await self.tool_manager.ask_user(questions)
        return result.output if result.success else {}

    async def update_todos(self, todos: List[Dict[str, str]]):
        """Update todo list"""
        await self.tool_manager.update_todos(todos)

    async def web_search(self, query: str, **kwargs) -> str:
        """
        Search the web.

        Args:
            query: Search query
            **kwargs: Additional arguments

        Returns:
            Search results
        """
        result = await self.tool_manager.web_search(query, **kwargs)
        return result.output if result.success else ""

    async def web_fetch(self, url: str, prompt: str) -> str:
        """
        Fetch web content.

        Args:
            url: URL to fetch
            prompt: Processing prompt

        Returns:
            Processed content
        """
        result = await self.tool_manager.web_fetch(url, prompt)
        return result.output if result.success else ""

    def get_tool_usage_stats(self) -> Dict[str, int]:
        """Get statistics on tool usage"""
        return self.tool_manager.get_usage_stats()

    def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        return {
            "context": self.context_manager.get_context_stats(),
            "provider": str(self.current_provider) if self.current_provider else "None",
            "total_cost": self.current_provider.total_cost if self.current_provider else 0,
            "tool_usage": self.get_tool_usage_stats(),
            "available_providers": self.provider_selector.get_available_providers(),
        }

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get analytics summary including performance metrics"""
        return self.analytics.get_summary()

    def get_health_report(self) -> Dict[str, Any]:
        """Get system health report with issues and recommendations"""
        return self.analytics.get_health_report()

    def get_performance_insights(self) -> List[Dict[str, Any]]:
        """Get actionable performance improvement insights"""
        return self.analytics.get_performance_insights()

    def get_provider_health(self) -> Dict[str, Any]:
        """Get health status of all providers (if resilient provider is active)"""
        if self.resilient_provider:
            return self.resilient_provider.get_summary()
        return {"resilient_provider": False}

    def export_analytics(self, format: str = "json") -> str:
        """Export analytics report in specified format (json or markdown)"""
        return self.analytics.export_report(format)

    def export_session(self, output_path: str):
        """Export session"""
        self.context_manager.export_session(output_path)
        self.console.print(f"[green]Session exported to {output_path}[/green]")

    # Memory system methods

    def remember(self, content: str, memory_type: str = "context", importance: float = 0.5) -> bool:
        """
        Explicitly add something to long-term memory.

        Args:
            content: What to remember
            memory_type: Type of memory (fact, preference, code_pattern, decision, context, error, todo, learning)
            importance: How important (0-1)

        Returns:
            True if memory was added successfully
        """
        if not self.memory_manager:
            self.console.print("[yellow]Memory system not available[/yellow]")
            return False

        try:
            from ..memory import MemoryType

            mem_type = MemoryType(memory_type) if isinstance(memory_type, str) else memory_type
            self.memory_manager.remember(
                content=content, memory_type=mem_type, importance=importance, source="agent"
            )
            return True
        except Exception as e:
            self.console.print(f"[red]Failed to save memory: {e}[/red]")
            return False

    def recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search long-term memory for relevant information.

        Args:
            query: What to search for
            top_k: Number of results

        Returns:
            List of memory dictionaries with content and scores
        """
        if not self.memory_manager:
            return []

        try:
            results = self.memory_manager.recall(query=query, top_k=top_k)
            return [
                {
                    "content": memory.content,
                    "type": memory.memory_type.value,
                    "importance": memory.importance,
                    "score": score,
                }
                for memory, score in results
            ]
        except Exception as e:
            self.console.print(f"[red]Failed to recall memory: {e}[/red]")
            return []

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system."""
        if not self.memory_manager:
            return {"available": False}

        try:
            stats = self.memory_manager.get_stats()
            stats["available"] = True
            return stats
        except Exception as e:
            return {"available": False, "error": str(e)}

    def update_agent_memory(
        self, content: str, scope: str = "project", section: Optional[str] = None
    ) -> bool:
        """
        Update an AGENT.md memory file.

        Args:
            content: Content to write
            scope: "global", "project", or "local"
            section: Optional section to update

        Returns:
            True if update was successful
        """
        if not self.memory_manager:
            self.console.print("[yellow]Memory system not available[/yellow]")
            return False

        try:
            path = self.memory_manager.update_file_memory(
                content=content, scope=scope, section=section
            )
            self.console.print(f"[green]Updated {scope} memory: {path}[/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]Failed to update memory: {e}[/red]")
            return False

    def new_memory_session(self) -> Optional[str]:
        """
        Start a new memory session (preserves history).

        Returns:
            New session ID or None if failed
        """
        if not self.memory_manager:
            return None

        try:
            session = self.memory_manager.new_session()
            return session.session_id
        except Exception:
            return None

    def cleanup_memory(self) -> Dict[str, int]:
        """
        Run cleanup on memory system (prune old memories, compact sessions).

        Returns:
            Cleanup statistics
        """
        if not self.memory_manager:
            return {}

        try:
            return self.memory_manager.cleanup(
                prune_semantic=True, compact_session=True, apply_decay=True
            )
        except Exception as e:
            self.console.print(f"[red]Cleanup failed: {e}[/red]")
            return {}
