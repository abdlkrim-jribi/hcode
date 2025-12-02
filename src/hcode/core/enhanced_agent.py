"""
Enhanced Hcode Agent with full tool integration.
Integrates all advanced features: tools, sub-agents, web capabilities, interactive features.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console

from ..providers import (
    ProviderSelector,
    ProviderPreferences,
    TaskComplexity,
    TaskType,
    Message,
    AIProvider
)
from ..tools import ToolManager, ToolExecutionContext
from ..agents import HcodeAgentOrchestrator, HcodeAgentType
from .context import ContextManager
from .safety import SafetyGuard

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
    Enhanced thinking block with multi-dimensional reasoning capabilities.

    Supports advanced cognitive patterns:
    - Analytical decomposition
    - Hypothesis generation and testing
    - Meta-cognitive reflection
    - Adversarial self-critique
    - Confidence calibration
    """
    # === PHASE 1: PERCEPTION ===
    observe: str = ""           # What do I literally see/read?
    interpret: str = ""         # What does this mean?

    # === PHASE 2: COMPREHENSION ===
    understand: str = ""        # Core understanding of the request
    context: str = ""           # Relevant context and constraints
    assumptions: str = ""       # What am I assuming? (NEW)

    # === PHASE 3: ANALYSIS ===
    decompose: str = ""         # Break into sub-problems (NEW)
    dependencies: str = ""      # What depends on what? (NEW)
    options: str = ""           # Possible approaches

    # === PHASE 4: REASONING ===
    hypothesis: str = ""        # My best hypothesis (NEW)
    evidence: str = ""          # Evidence for/against (NEW)
    counterargument: str = ""   # Devil's advocate - why might I be wrong? (NEW)

    # === PHASE 5: DECISION ===
    decision: str = ""          # Final decision
    confidence: str = ""        # How confident am I? (NEW)
    fallback: str = ""          # What if this fails? (NEW)

    # === PHASE 6: VERIFICATION ===
    risk_check: str = ""        # Safety and risk assessment
    verify: str = ""            # How will I verify success? (NEW)

    # === META ===
    reflection: str = ""        # What did I learn? (NEW)
    raw_content: str = ""

    def is_valid(self) -> bool:
        """Check if thinking block has meaningful content"""
        # Valid if we have core understanding or decision
        return bool(self.understand or self.decision or self.observe)

    def get_confidence_level(self) -> str:
        """Extract confidence level from thinking"""
        if self.confidence:
            confidence_lower = self.confidence.lower()
            if any(word in confidence_lower for word in ['very high', 'certain', '95%', '100%', 'absolutely']):
                return "very_high"
            elif any(word in confidence_lower for word in ['high', 'confident', '80%', '85%', '90%']):
                return "high"
            elif any(word in confidence_lower for word in ['medium', 'moderate', '60%', '70%', 'likely']):
                return "medium"
            elif any(word in confidence_lower for word in ['low', 'uncertain', 'unsure', '40%', '50%']):
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
            lines = self.decision.strip().split('\n')
            for line in lines:
                if 'best choice' in line.lower() or 'reason' in line.lower() or 'choose' in line.lower():
                    return line.strip()
            return lines[0] if lines else ""
        if self.hypothesis:
            return f"Hypothesis: {self.hypothesis.split(chr(10))[0][:60]}"
        return ""

    def quality_score(self) -> float:
        """Calculate thinking quality score (0-1)"""
        score = 0.0
        weights = {
            'understand': 0.15,
            'context': 0.10,
            'assumptions': 0.10,
            'decompose': 0.10,
            'options': 0.10,
            'hypothesis': 0.10,
            'counterargument': 0.10,
            'decision': 0.15,
            'confidence': 0.05,
            'risk_check': 0.05,
        }
        for field, weight in weights.items():
            value = getattr(self, field, "")
            if value and len(value.strip()) > 10:
                score += weight
        return min(score, 1.0)


def parse_thinking_block(text: str) -> Tuple[Optional[ThinkingBlock], str]:
    """
    Parse an enhanced thinking block from model output.

    Supports both simple (5-step) and advanced (multi-phase) thinking formats.

    Args:
        text: The model's response text

    Returns:
        Tuple of (ThinkingBlock or None, remaining text without thinking block)
    """
    # Pattern to match <thinking>...</thinking> blocks
    pattern = r'<thinking>(.*?)</thinking>'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

    if not match:
        return None, text

    thinking_content = match.group(1).strip()
    remaining_text = text[:match.start()] + text[match.end():]
    remaining_text = remaining_text.strip()

    # Parse sections within thinking block
    block = ThinkingBlock(raw_content=thinking_content)

    # === ENHANCED MULTI-PHASE PARSING ===
    # Supports flexible section headers with various formats

    # Phase 1: Perception
    section_patterns = {
        # Perception phase
        'observe': [
            r'(?:OBSERVE|PERCEPTION|SEE|INPUT):?\s*(.*?)(?=(?:INTERPRET|UNDERSTAND|CONTEXT|ANALYZE|$))',
            r'\[OBSERVE\]:?\s*(.*?)(?=\[|$)',
        ],
        'interpret': [
            r'(?:INTERPRET|MEANING|IMPLIES):?\s*(.*?)(?=(?:UNDERSTAND|CONTEXT|ANALYZE|$))',
        ],
        # Comprehension phase
        'understand': [
            r'(?:\d+\.\s*)?UNDERSTAND(?:ING)?:?\s*(.*?)(?=(?:\d+\.\s*)?(?:CONTEXT|ASSUMPTIONS|ANALYZE|DECOMPOSE|OPTIONS|$))',
            r'\[UNDERSTAND\]:?\s*(.*?)(?=\[|$)',
            r'GOAL:?\s*(.*?)(?=(?:CONTEXT|$))',
        ],
        'context': [
            r'(?:\d+\.\s*)?CONTEXT:?\s*(.*?)(?=(?:\d+\.\s*)?(?:ASSUMPTIONS|ANALYZE|DECOMPOSE|OPTIONS|$))',
            r'\[CONTEXT\]:?\s*(.*?)(?=\[|$)',
            r'KNOWN:?\s*(.*?)(?=(?:ASSUMPTIONS|OPTIONS|$))',
        ],
        'assumptions': [
            r'(?:\d+\.\s*)?ASSUMPTIONS?:?\s*(.*?)(?=(?:\d+\.\s*)?(?:ANALYZE|DECOMPOSE|OPTIONS|HYPOTHESIS|$))',
            r'\[ASSUMPTIONS?\]:?\s*(.*?)(?=\[|$)',
            r'ASSUMING:?\s*(.*?)(?=(?:OPTIONS|$))',
        ],
        # Analysis phase
        'decompose': [
            r'(?:\d+\.\s*)?(?:DECOMPOSE|BREAKDOWN|SUB.?PROBLEMS?|STEPS?):?\s*(.*?)(?=(?:\d+\.\s*)?(?:DEPENDENCIES|OPTIONS|HYPOTHESIS|$))',
            r'\[DECOMPOSE\]:?\s*(.*?)(?=\[|$)',
        ],
        'dependencies': [
            r'(?:\d+\.\s*)?(?:DEPENDENCIES|DEPENDS|ORDER|SEQUENCE):?\s*(.*?)(?=(?:\d+\.\s*)?(?:OPTIONS|HYPOTHESIS|$))',
            r'\[DEPENDENCIES\]:?\s*(.*?)(?=\[|$)',
        ],
        'options': [
            r'(?:\d+\.\s*)?OPTIONS?:?\s*(.*?)(?=(?:\d+\.\s*)?(?:HYPOTHESIS|EVIDENCE|DECISION|CHOOSE|$))',
            r'\[OPTIONS?\]:?\s*(.*?)(?=\[|$)',
            r'ALTERNATIVES?:?\s*(.*?)(?=(?:DECISION|$))',
        ],
        # Reasoning phase
        'hypothesis': [
            r'(?:\d+\.\s*)?HYPOTHESIS:?\s*(.*?)(?=(?:\d+\.\s*)?(?:EVIDENCE|COUNTER|DECISION|$))',
            r'\[HYPOTHESIS\]:?\s*(.*?)(?=\[|$)',
            r'THEORY:?\s*(.*?)(?=(?:EVIDENCE|$))',
        ],
        'evidence': [
            r'(?:\d+\.\s*)?EVIDENCE:?\s*(.*?)(?=(?:\d+\.\s*)?(?:COUNTER|DECISION|$))',
            r'\[EVIDENCE\]:?\s*(.*?)(?=\[|$)',
            r'SUPPORT(?:ING)?:?\s*(.*?)(?=(?:COUNTER|$))',
        ],
        'counterargument': [
            r'(?:\d+\.\s*)?(?:COUNTER.?ARGUMENT|COUNTER|CHALLENGE|DEVIL.?S?.?ADVOCATE|WHY.?WRONG|CRITIQUE):?\s*(.*?)(?=(?:\d+\.\s*)?(?:DECISION|CONFIDENCE|$))',
            r'\[COUNTER\]:?\s*(.*?)(?=\[|$)',
            r'(?:BUT|HOWEVER|ALTERNATIVELY):?\s*(.*?)(?=(?:DECISION|$))',
        ],
        # Decision phase
        'decision': [
            r'(?:\d+\.\s*)?DECISION:?\s*(.*?)(?=(?:\d+\.\s*)?(?:CONFIDENCE|FALLBACK|RISK|VERIFY|$))',
            r'\[DECISION\]:?\s*(.*?)(?=\[|$)',
            r'(?:CHOOSE|SELECTED?|FINAL):?\s*(.*?)(?=(?:CONFIDENCE|RISK|$))',
            r'BEST\s*CHOICE:?\s*(.*?)(?=(?:REASON|CONFIDENCE|$))',
        ],
        'confidence': [
            r'(?:\d+\.\s*)?CONFIDENCE:?\s*(.*?)(?=(?:\d+\.\s*)?(?:FALLBACK|RISK|VERIFY|$))',
            r'\[CONFIDENCE\]:?\s*(.*?)(?=\[|$)',
            r'CERTAINTY:?\s*(.*?)(?=(?:FALLBACK|RISK|$))',
        ],
        'fallback': [
            r'(?:\d+\.\s*)?(?:FALLBACK|BACKUP|PLAN.?B|IF.?FAILS?|ALTERNATIVE):?\s*(.*?)(?=(?:\d+\.\s*)?(?:RISK|VERIFY|$))',
            r'\[FALLBACK\]:?\s*(.*?)(?=\[|$)',
        ],
        # Verification phase
        'risk_check': [
            r'(?:\d+\.\s*)?RISK(?:\s*CHECK)?:?\s*(.*?)(?=(?:\d+\.\s*)?(?:VERIFY|REFLECTION|$))',
            r'\[RISK\]:?\s*(.*?)(?=\[|$)',
            r'SAFETY:?\s*(.*?)(?=(?:VERIFY|$))',
        ],
        'verify': [
            r'(?:\d+\.\s*)?(?:VERIFY|VALIDATION?|CHECK|TEST|CONFIRM):?\s*(.*?)(?=(?:\d+\.\s*)?(?:REFLECTION|$))',
            r'\[VERIFY\]:?\s*(.*?)(?=\[|$)',
        ],
        # Meta phase
        'reflection': [
            r'(?:\d+\.\s*)?(?:REFLECTION?|LEARN(?:ED)?|INSIGHT|META):?\s*(.*?)$',
            r'\[REFLECT(?:ION)?\]:?\s*(.*?)(?=\[|$)',
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


def format_thinking_display(block: ThinkingBlock, console: Console) -> None:
    """
    Display an enhanced thinking block with quality indicators.

    Shows key reasoning phases with visual indicators for:
    - Thinking quality score
    - Confidence level
    - Self-critique presence
    - Fallback availability

    Args:
        block: The parsed thinking block
        console: Rich console for output
    """
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table

    # Build the thinking display
    content = Text()

    # === QUALITY INDICATOR ===
    quality = block.quality_score()
    confidence = block.get_confidence_level()
    quality_bar = "[" + ("=" * int(quality * 10)) + ("-" * (10 - int(quality * 10))) + "]"
    quality_color = "green" if quality > 0.7 else "yellow" if quality > 0.4 else "red"

    content.append(f"Quality: {quality_bar} {quality:.0%}", style=f"dim {quality_color}")
    if confidence != "unknown":
        conf_color = {"very_high": "green", "high": "cyan", "medium": "yellow", "low": "red"}.get(confidence, "dim")
        content.append(f" | Confidence: {confidence}", style=f"dim {conf_color}")
    content.append("\n")

    # === KEY UNDERSTANDING ===
    if block.understand:
        content.append("GOAL: ", style="bold cyan")
        first_line = block.understand.split('\n')[0].strip()
        if first_line.startswith('-'):
            first_line = first_line[1:].strip()
        content.append(first_line[:80] + "\n", style="white")

    # === HYPOTHESIS (if advanced thinking) ===
    if block.hypothesis:
        content.append("HYPOTHESIS: ", style="bold magenta")
        hyp_line = block.hypothesis.split('\n')[0].strip()
        content.append(hyp_line[:70] + "\n", style="dim magenta")

    # === SELF-CRITIQUE (shows depth of reasoning) ===
    if block.counterargument:
        content.append("CHALLENGE: ", style="bold red")
        counter_line = block.counterargument.split('\n')[0].strip()
        if counter_line.startswith('-'):
            counter_line = counter_line[1:].strip()
        content.append(counter_line[:60] + "\n", style="dim red")

    # === DECISION ===
    if block.decision:
        content.append("DECISION: ", style="bold green")
        decision_lines = block.decision.strip().split('\n')
        for line in decision_lines:
            if any(word in line.lower() for word in ['best choice', 'choose', 'selected', 'will use']):
                content.append(line.strip() + "\n", style="white")
                break
        else:
            content.append(decision_lines[0][:60] + "\n", style="white")

    # === FALLBACK (if exists) ===
    if block.fallback:
        content.append("FALLBACK: ", style="bold yellow")
        fallback_line = block.fallback.split('\n')[0].strip()
        content.append(fallback_line[:50] + "\n", style="dim yellow")

    # === RISK CHECK ===
    if block.risk_check:
        content.append("RISK: ", style="bold yellow")
        risk_line = block.risk_check.split('\n')[0].strip()
        if risk_line.startswith('-'):
            risk_line = risk_line[1:].strip()
        content.append(risk_line[:60], style="dim")

    # Add indicators for thinking quality
    indicators = []
    if block.is_self_critical():
        indicators.append("[cyan]Self-Critical[/cyan]")
    if block.has_fallback():
        indicators.append("[yellow]Has Fallback[/yellow]")
    if block.assumptions:
        indicators.append("[magenta]Explicit Assumptions[/magenta]")

    title = "[bold blue]Deep Thinking[/bold blue]"
    if indicators:
        title += " " + " ".join(indicators)

    console.print(Panel(
        content,
        title=title,
        border_style="blue",
        padding=(0, 1)
    ))


class EnhancedHcodeAgent:
    """
    Enhanced Hcode agent with comprehensive tool integration.

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
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize enhanced Hcode agent.

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
        self.console = Console()
        self.config = config or {}
        self.session_id = session_id

        # Initialize provider selector
        self.provider_selector = ProviderSelector(
            anthropic_key=anthropic_key,
            openai_key=openai_key,
            openai_base_url=openai_base_url,
            anthropic_model=anthropic_model,
            openai_model=openai_model,
            preferences=preferences or ProviderPreferences()
        )

        # Initialize tool manager
        self.tool_manager = ToolManager(
            root_dir=str(self.root_dir),
            config=self.config
        )

        # Initialize agent orchestrator
        self.agent_orchestrator = HcodeAgentOrchestrator(
            provider_selector=self.provider_selector,
            tool_registry=self.tool_manager.tool_registry
        )

        # Connect agent orchestrator to tool manager
        self.tool_manager.set_agent_orchestrator(self.agent_orchestrator)

        # Initialize context and safety
        self.context_manager = ContextManager(
            root_dir=str(self.root_dir),
            session_id=session_id
        )
        self.safety_guard = SafetyGuard(root_dir=str(self.root_dir))

        # Initialize continuation manager for long outputs
        from .continuation import ContinuationManager, ContextWindowManager
        self.continuation_manager = ContinuationManager(
            max_continuations=10,
            max_total_tokens=100000,
            console=self.console
        )
        self.context_window_manager = ContextWindowManager(
            max_context_tokens=128000,
            reserve_output_tokens=8192
        )

        self.current_provider: Optional[AIProvider] = None

        # Initialize memory system (if available)
        self.memory_manager: Optional['MemoryManager'] = None
        if MEMORY_AVAILABLE:
            try:
                self.memory_manager = get_memory_manager(
                    project_root=self.root_dir,
                    session_id=session_id
                )
                self.console.print("[dim]Memory system initialized[/dim]")
            except Exception as e:
                self.console.print(f"[dim yellow]Memory system unavailable: {e}[/dim yellow]")
                self.memory_manager = None

        # Initialize interaction logger
        self.logger: InteractionLogger = get_logger()
        self.console.print(f"[dim]Logging to: {self.logger.log_dir}[/dim]")

    async def execute_task(
        self,
        task: str,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        task_type: TaskType = TaskType.CODE_GENERATION,
        stream: bool = True,
        use_sub_agents: bool = False
    ) -> str:
        """
        Execute a task using the enhanced agent capabilities.

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

        try:
            # Use sub-agents if requested
            if use_sub_agents:
                result = await self.agent_orchestrator.auto_execute(task)
                response = result.output

                self.safety_guard.commit_transaction()
                return response

            # Select provider
            self.current_provider = self.provider_selector.select_provider(
                complexity=complexity,
                task_type=task_type
            )

            self.console.print(f"[bold green]Using {self.current_provider}[/bold green]")

            # Start logging session
            provider_name = self.current_provider.get_provider_name() if hasattr(self.current_provider, 'get_provider_name') else str(self.current_provider)
            model_name = self.current_provider.model if hasattr(self.current_provider, 'model') else "unknown"
            self.logger.start_session(
                task=task,
                provider=provider_name,
                model=model_name,
                metadata={"complexity": complexity.value if hasattr(complexity, 'value') else str(complexity)}
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
                role="user",
                content=formatted_task,
                importance=1.0,
                provider=self.current_provider
            )

            # Add message to memory system
            if self.memory_manager:
                try:
                    self.memory_manager.add_message(
                        role="user",
                        content=task,
                        extract_memories=True
                    )
                except Exception:
                    pass  # Memory system is optional

            # Execute with tool calling
            response = await self._execute_with_tools(stream=stream)

            # Add response to context
            self.context_manager.add_message(
                role="assistant",
                content=response,
                importance=0.8,
                provider=self.current_provider
            )

            # Add response to memory system
            if self.memory_manager:
                try:
                    self.memory_manager.add_message(
                        role="assistant",
                        content=response,
                        extract_memories=True
                    )
                except Exception:
                    pass  # Memory system is optional

            # End logging session
            self.logger.end_session(final_result=response)

            self.safety_guard.commit_transaction()
            return response

        except Exception as e:
            # Log error before handling
            self.logger.log_error(str(e), context={"task": task})
            self.logger.end_session(final_result="", errors=[str(e)])

            self.safety_guard.rollback_transaction()

            # Import LLMConnectionError for checking
            from ..providers.openai_provider import LLMConnectionError

            error_str = str(e).lower()
            error_type = type(e).__name__

            # Handle LLMConnectionError specifically
            if isinstance(e, LLMConnectionError):
                self.console.print(f"[bold red][X] LLM Connection Error:[/bold red] {str(e)}")
                if hasattr(e, 'base_url') and e.base_url:
                    self.console.print(f"[dim]API Endpoint: {e.base_url}[/dim]")
                self.console.print("[dim]Check your network connection and API endpoint configuration.[/dim]")
                self.console.print("[dim]You can also check your OPENAI_BASE_URL environment variable.[/dim]")
                raise

            # Handle built-in connection errors
            elif isinstance(e, ConnectionError) or 'connection' in error_str:
                self.console.print(f"[bold red][X] Connection Error:[/bold red] {str(e)}")
                self.console.print("[dim]Check your network connection and API endpoint configuration.[/dim]")
                raise

            elif isinstance(e, TimeoutError) or 'timeout' in error_str:
                self.console.print(f"[bold red][X] Timeout Error:[/bold red] {str(e)}")
                self.console.print("[dim]The request took too long. Try again or increase timeout in config.[/dim]")
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
                self.console.print(f"[bold red][X] Unexpected Error ({error_type}):[/bold red] {str(e)}")
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
                self.console.print(f"[dim yellow][!] Could not load memory context: {e}[/dim yellow]")

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
                    self.console.print(f"[dim][...] Processing... (iteration {iteration})[/dim]")

                # LOOP DETECTION: Check if we're stuck repeating the same response
                if len(recent_responses) >= stuck_threshold:
                    # Check for repeated responses
                    last_response_hash = hash(recent_responses[-1][:500]) if recent_responses else 0
                    repeat_count = sum(1 for r in recent_responses if hash(r[:500]) == last_response_hash)
                    if repeat_count >= stuck_threshold:
                        self.console.print(f"[yellow][!] Detected stuck loop (same response {repeat_count} times). Breaking out.[/yellow]")
                        break

                # Get messages with context - ensure we leave room for output
                context_window = self.current_provider.get_context_window()
                max_output_tokens = self.current_provider.max_tokens

                # Calculate available tokens for context, with safety minimum
                available_for_context = context_window - max_output_tokens - 2000  # Extra buffer
                min_context_tokens = 4000  # Minimum context to be useful

                if available_for_context < min_context_tokens:
                    # Context overflow - need to truncate more aggressively
                    self.console.print(f"[yellow][!] Context near limit. Truncating older messages.[/yellow]")
                    available_for_context = min_context_tokens

                messages = self.context_manager.get_messages(
                    max_tokens=available_for_context
                )

                # CLAUDE CODE STYLE: Show thinking indicator on first iteration
                if iteration == 1:
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
                            tools=tool_schemas if provider_name == "anthropic" else None
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
                            tools=tool_schemas if provider_name == "anthropic" else None
                        )

                        # Clear thinking indicator
                        if iteration == 1:
                            self.console.print(" " * 20, end="\r")

                        response_text = response.content
                        raw_response = response.raw_response if hasattr(response, 'raw_response') else None
                        finish_reason = response.finish_reason if hasattr(response, 'finish_reason') else "stop"

                    # Success - reset error counter and save successful response
                    consecutive_errors = 0
                    if response_text.strip():
                        last_successful_response = response_text

                    # EMPTY RESPONSE HANDLING: If first response is empty, add explicit instruction
                    if iteration == 1 and not response_text.strip():
                        self.console.print(f"[dim yellow][!] Empty first response. Adding guidance...[/dim yellow]")
                        # Add a direct instruction to the context
                        self.context_manager.add_message(
                            role="user",
                            content="Please respond to the task above. Start with a brief explanation of what you'll do, then call a tool.",
                            importance=1.0,
                            provider=self.current_provider
                        )
                        continue  # Retry with the guidance

                except Exception as gen_error:
                    # Handle generation errors gracefully
                    consecutive_errors += 1
                    error_msg = str(gen_error)
                    self.console.print(f"[bold red][!] Generation error (attempt {consecutive_errors}/{max_consecutive_errors}): {error_msg[:100]}[/bold red]")

                    if consecutive_errors >= max_consecutive_errors:
                        self.console.print(f"[bold red][X] Too many consecutive errors. Returning accumulated results.[/bold red]")
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
                    # Display the thinking block nicely
                    format_thinking_display(thinking_block, self.console)

                    # Log the thinking for debugging
                    self.logger.log_interaction(
                        iteration=iteration,
                        request_messages=[],
                        response_text=f"[THINKING] {thinking_block.summary()}",
                        finish_reason="thinking",
                        tool_calls_detected=0,
                        continuation_needed=False,
                        pending_work_detected=False,
                        metadata={"thinking": thinking_block.raw_content}
                    )

                # THINKING ENFORCEMENT: For OpenAI/OSS models, if no thinking block found
                # on first iteration with a tool call, request thinking first
                if provider_name == "openai" and iteration == 1:
                    tool_calls_preview = self._extract_tool_calls(raw_response, response_text, provider_name)
                    if tool_calls_preview and not thinking_block:
                        # Model skipped thinking - request it thinks first
                        self.console.print(f"[dim yellow][!] Requesting deeper thinking before tool use...[/dim yellow]")
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
                            provider=self.current_provider
                        )
                        # Don't execute the tool yet, continue to get thinking
                        continue

                # Check for and execute tool calls
                tool_calls = self._extract_tool_calls(raw_response, response_text, provider_name)

                # Log this interaction (full response, not truncated)
                self.logger.log_interaction(
                    iteration=iteration,
                    request_messages=messages[-3:] if len(messages) > 3 else messages,  # Last 3 for brevity
                    response_text=response_text,  # FULL response
                    finish_reason=finish_reason,
                    tool_calls_detected=len(tool_calls) if tool_calls else 0,
                    continuation_needed=False,  # Will update if needed
                    pending_work_detected=False  # Will update if needed
                )

                if tool_calls:
                    consecutive_no_tool_calls = 0
                    last_tool_call_iteration = iteration

                    # Execute tool calls and add results to context
                    try:
                        tool_results = await self._execute_tool_calls(tool_calls)
                        # Track completed actions for summary
                        for tool_name, result, arguments in tool_results:
                            completed_actions.append({
                                'tool': tool_name,
                                'success': result.success,
                                'args': arguments,
                                'iteration': iteration
                            })
                    except Exception as tool_error:
                        self.console.print(f"[bold red][!] Tool execution error: {tool_error}[/bold red]")
                        tool_results = []
                        # Continue anyway - don't crash

                    # Add assistant message with tool calls to context
                    self.context_manager.add_message(
                        role="assistant",
                        content=response_text,
                        importance=0.7,
                        provider=self.current_provider
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
                            metadata=result.metadata if hasattr(result, 'metadata') else {}
                        )

                        # RETRY LOOP PREVENTION: Track failed commands
                        if not result.success:
                            # Create a unique key for the command
                            cmd_key = self._get_command_key(tool_name, arguments)
                            failed_commands[cmd_key] = failed_commands.get(cmd_key, 0) + 1

                            if failed_commands[cmd_key] > max_command_retries:
                                self.console.print(f"[bold red][!] Command has failed {failed_commands[cmd_key]} times. Stopping retry loop.[/bold red]")
                                self.logger.log_error(
                                    f"Retry loop detected: {tool_name} failed {failed_commands[cmd_key]} times",
                                    context={"command_key": cmd_key, "arguments": arguments}
                                )

                        if result.success:
                            # Check if this was a truncated file write that needs continuation
                            is_truncated_write = (
                                result.metadata and
                                result.metadata.get('is_truncated', False) and
                                tool_name.lower() in ['writetool', 'write']
                            )

                            if is_truncated_write:
                                # Special handling for truncated file writes
                                file_path = arguments.get('file_path', 'the file')
                                truncation_reason = result.metadata.get('truncation_reason', 'incomplete content')
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
                                    output_text += f"\n\n... [TRUNCATED - see full output in log file]"
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
                            provider=self.current_provider
                        )

                        # Display tool execution with tool-specific formatting
                        self._display_tool_result(tool_name, result, arguments)

                    continue  # Continue loop for next iteration
                else:
                    consecutive_no_tool_calls += 1

                # Check if we should continue based on various signals
                should_continue = self._should_continue_generation(finish_reason, response_text)

                # GPT-OSS specific: Check if there are pending todos that weren't completed
                # This helps when the model stops mid-task
                has_pending_work = self._has_pending_work(response_text)

                # TASK COMPLETION CHECK: Detect when the task is truly done
                task_completed = self._is_task_completed(response_text, completed_actions, iteration)
                if task_completed:
                    self.console.print(f"[bold green][*] Task completed![/bold green]")
                    # Generate and display summary
                    summary = self._generate_task_summary(completed_actions, response_text)
                    if summary:
                        self.console.print(summary)
                    break

                # CRITICAL: Check for empty or minimal responses - model failed to engage
                response_stripped = response_text.strip()
                is_empty_response = len(response_stripped) < 10

                if is_empty_response and iteration < 3:
                    # Model returned empty/minimal response - force it to engage
                    self.console.print(f"[bold yellow][!] Empty response detected (len={len(response_stripped)}). Prompting model to engage...[/bold yellow]")
                    has_pending_work = True  # Force continuation

                # Debug logging
                self.console.print(f"[dim][?] Iteration {iteration}: tool_calls={len(tool_calls) if tool_calls else 0}, should_continue={should_continue}, has_pending_work={has_pending_work}, finish={finish_reason}, response_len={len(response_stripped)}, completed={task_completed}[/dim]")
                if response_stripped:
                    self.console.print(f"[dim][N] Response preview: {response_stripped[:100].replace(chr(10), ' ')}...[/dim]")
                else:
                    self.console.print(f"[dim][N] Response: (empty)[/dim]")

                if should_continue or has_pending_work:
                    # Add accumulated response to context and request continuation
                    accumulated = "\n".join(all_response_parts)

                    self.context_manager.add_message(
                        role="assistant",
                        content=accumulated,
                        importance=0.7,
                        provider=self.current_provider
                    )

                    # Get appropriate continuation prompt
                    if is_empty_response:
                        # Model returned empty - give it a direct instruction
                        continuation_prompt = self._get_empty_response_prompt()
                    elif has_pending_work and not should_continue:
                        # Model stopped but there's pending work - use a stronger prompt
                        continuation_prompt = self._get_pending_work_prompt()
                    else:
                        continuation_prompt = self._get_continuation_prompt(iteration)

                    self.context_manager.add_message(
                        role="user",
                        content=continuation_prompt,
                        importance=0.9,
                        provider=self.current_provider
                    )

                    self.console.print(f"[dim]-> Continuing generation (part {iteration})...[/dim]")

                    # Safety check: if we've had too many iterations without tool calls
                    # after a tool call, the model might be stuck
                    if consecutive_no_tool_calls > 3 and last_tool_call_iteration > 0:
                        self.console.print(f"[dim yellow][!] Model may be stuck. Prompting for action...[/dim yellow]")
                        self.context_manager.add_message(
                            role="user",
                            content="Please use the available tools to complete the remaining tasks. Check the todo list and continue working on any pending items.",
                            importance=1.0,
                            provider=self.current_provider
                        )

                    continue  # Continue to generate more

                # Natural completion - we're done
                self.console.print(f"[bold green][*] Task completed![/bold green]")
                summary = self._generate_task_summary(completed_actions, response_text)
                if summary:
                    self.console.print(summary)
                break

            except Exception as iteration_error:
                # ROBUSTNESS: Catch any unexpected errors in the iteration
                consecutive_errors += 1
                error_msg = str(iteration_error)
                self.console.print(f"[bold red][!] Iteration error ({consecutive_errors}/{max_consecutive_errors}): {error_msg[:150]}[/bold red]")

                if consecutive_errors >= max_consecutive_errors:
                    self.console.print(f"[bold red][X] Too many errors. Returning partial results.[/bold red]")
                    break

                # Try to recover by continuing
                await asyncio.sleep(1)
                continue

        # Check if we hit max iterations (safety limit)
        if iteration >= max_iterations:
            self.console.print(f"[bold yellow][!] Reached maximum iterations ({max_iterations}). Stopping.[/bold yellow]")
            summary = self._generate_task_summary(completed_actions, response_text)
            if summary:
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

        # CRITICAL: Check if response looks like an incomplete tool call or JSON fragment
        # GPT-OSS often outputs partial JSON when trying to continue
        json_fragment_patterns = [
            r'^\s*\{[^}]*$',  # Opening brace without closing
            r'^\s*\[[^\]]*$',  # Opening bracket without closing
            r'^\s*\{"[^"]+"\s*:\s*"[^"]*"\s*\}?\s*$',  # Simple JSON object like {"path": "..."}
            r'^\s*\{"(?:path|file_path|command|pattern|content)"',  # Looks like tool parameters
        ]

        for pattern in json_fragment_patterns:
            if re.match(pattern, response_stripped, re.DOTALL):
                self.console.print(f"[dim yellow][!] Detected JSON fragment pattern - continuing...[/dim yellow]")
                # Store the fragment so we can help the model fix it
                self._last_json_fragment = response_stripped
                return True

        # Also detect incomplete JSON that lacks the "tool" key
        if response_stripped.startswith('{') and response_stripped.endswith('}'):
            try:
                parsed = json.loads(response_stripped)
                if isinstance(parsed, dict) and 'tool' not in parsed:
                    self.console.print(f"[dim yellow][!] Detected incomplete JSON (no tool key) - continuing...[/dim yellow]")
                    self._last_json_fragment = response_stripped
                    return True
            except json.JSONDecodeError:
                pass

        # Check if response is ONLY JSON (model trying to make a tool call but malformed)
        if response_stripped.startswith('{') and response_stripped.endswith('}'):
            # Try to parse as JSON
            try:
                parsed = json.loads(response_stripped)
                # If it's valid JSON but NOT a proper tool call, the model is stuck
                if isinstance(parsed, dict):
                    # Check if it looks like a proper tool call
                    has_tool_key = 'tool' in parsed or 'name' in parsed or 'function' in parsed
                    if not has_tool_key:
                        # It's just a JSON object without tool designation - model is stuck
                        self.console.print(f"[dim yellow][!] Detected incomplete JSON (no tool key) - continuing...[/dim yellow]")
                        return True
            except json.JSONDecodeError:
                # Invalid JSON - might be trying to output something
                pass

            # Also check if it's just JSON without any natural language explanation
            non_json_text = re.sub(r'\{[^{}]*\}', '', response_stripped).strip()
            if len(non_json_text) < 20:  # Very little non-JSON text
                self.console.print(f"[dim yellow][!] Response is mostly JSON without explanation - continuing...[/dim yellow]")
                return True

        # Check for visual todo list formatting - model outputting display instead of executing
        # Patterns like "[ ] Task" or "[~] Task" indicate model is showing a todo but not executing
        visual_todo_patterns = [
            r'\[\s*\]\s+\w+',  # [ ] Task
            r'\[\s*~\s*\]\s+\w+',  # [~] Task
            r'\[\s*x\s*\]\s+\w+',  # [x] Task
            r'\[\s*✓\s*\]\s+\w+',  # [✓] Task
            r'○\s+Pending',  # ○ Pending
            r'⟳\s+In\s+Progress',  # ⟳ In Progress
            r'\|\s+\[\s*\]',  # Table with checkbox
            r'\|\s+○\s+',  # Table with pending symbol
        ]

        for pattern in visual_todo_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                # Model is outputting a visual todo list instead of executing
                self.console.print(f"[dim yellow][!] Detected visual todo list - model needs to execute tools[/dim yellow]")
                return True

        # Check if the response appears to be a COMPLETE answer (should NOT continue)
        # This prevents the model from continuing when it has already answered the user
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
        ]

        if any(indicator in response_lower for indicator in completion_indicators):
            # Model has provided a substantive answer - don't continue
            return False

        # Check for explicit indicators of pending work
        # IMPORTANT: These should be STRONG indicators that the model is mid-task
        # Avoid phrases that appear in TODO list output or general descriptions
        pending_indicators = [
            "next, i will",
            "now i'll",
            "first, let me",
            "continuing with",
            "remaining tasks:",
            "then i will",
        ]

        if any(indicator in response_lower for indicator in pending_indicators):
            # Check if response ends abruptly (no conclusion)
            endings = [".", "!", "?", "```", "done", "complete", "finished", "success", "found", "contains"]
            stripped = response_text.rstrip()
            if not any(stripped.lower().endswith(end) for end in endings):
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
        if hasattr(self, '_current_task_is_readonly') and self._current_task_is_readonly:
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
        cleaned = re.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 2. Remove raw JSON tool calls (already executed, shown in tool display)
        # Pattern: {"tool": "...", "parameters": {...}}
        cleaned = re.sub(r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^}]*\}\s*\}', '', cleaned, flags=re.DOTALL)

        # 3. Remove incomplete/fragment JSON that looks like tool calls
        cleaned = re.sub(r'\{\s*"(?:tool|path|file_path|command)"\s*:\s*"[^"]*"\s*(?:,\s*"[^"]+"\s*:\s*[^}]*)?\}?', '', cleaned, flags=re.DOTALL)

        # 4. Remove internal continuation prompts
        internal_phrases = [
            r'\[UNDERSTAND\].*?(?=\n\n|\[|$)',
            r'\[CONTEXT\].*?(?=\n\n|\[|$)',
            r'\[ASSUMPTIONS?\].*?(?=\n\n|\[|$)',
            r'\[OPTIONS?\].*?(?=\n\n|\[|$)',
            r'\[DECISION\].*?(?=\n\n|\[|$)',
            r'\[RISK\].*?(?=\n\n|\[|$)',
            r'\[PLAN\].*?(?=\n\n|\[|$)',
            r'UNDERSTAND:.*?(?=\n\n|CONTEXT:|ASSUMPTIONS:|OPTIONS:|DECISION:|$)',
            r'CONTEXT:.*?(?=\n\n|ASSUMPTIONS:|OPTIONS:|DECISION:|RISK:|$)',
        ]

        for pattern in internal_phrases:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 5. Clean up multiple consecutive newlines
        cleaned = re.sub(r'\n{4,}', '\n\n\n', cleaned)

        # 6. Clean up whitespace at start/end
        cleaned = cleaned.strip()

        # 7. If cleaning removed everything meaningful, try to extract just the answer
        if not cleaned or len(cleaned) < 10:
            # Try to find any useful content
            lines = response.split('\n')
            useful_lines = []
            for line in lines:
                line = line.strip()
                # Skip internal reasoning markers
                if line.startswith('[') and ']' in line[:50]:
                    continue
                if line.startswith('<thinking') or line.startswith('</thinking'):
                    continue
                if line.startswith('{"tool"'):
                    continue
                if line:
                    useful_lines.append(line)

            if useful_lines:
                cleaned = '\n'.join(useful_lines[-5:])  # Take last 5 useful lines

        return cleaned

    def _is_task_completed(self, response_text: str, completed_actions: List[Dict[str, Any]] = None, iteration: int = 0) -> bool:
        """
        Check if the task has been completed based on the model's response.

        This is the primary stopping condition for the agent loop.
        Uses multiple signals to determine task completion.

        Args:
            response_text: The model's response
            completed_actions: List of completed tool actions
            iteration: Current iteration number

        Returns:
            True if the task appears to be completed
        """
        response_lower = response_text.lower()
        response_stripped = response_text.strip()

        # Strong completion indicators - these signal the task is done
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

        if any(phrase in response_lower for phrase in completion_phrases):
            return True

        # Check if all todos are marked as completed
        try:
            todo_tool = self.tool_manager.get_tool('todowrite')
            if todo_tool and hasattr(todo_tool, 'todos') and todo_tool.todos:
                all_completed = all(
                    (hasattr(t, 'status') and t.status == 'completed') or
                    (isinstance(t, dict) and t.get('status') == 'completed')
                    for t in todo_tool.todos
                )
                if all_completed and len(todo_tool.todos) > 0:
                    return True
        except Exception:
            pass

        # For read-only tasks, check if a substantive answer was provided
        if hasattr(self, '_current_task_is_readonly') and self._current_task_is_readonly:
            # Read-only tasks are complete if we have a summary-like response
            if len(response_text) > 200 and any(word in response_lower for word in [
                'contains', 'includes', 'structure', 'files', 'directories',
                'repository', 'project', 'codebase', 'found', 'here is', 'here are'
            ]):
                return True

        # HEURISTIC: If we've done some actions and response looks like a conclusion
        if completed_actions and len(completed_actions) >= 1:
            # Check if response looks like it's wrapping up
            conclusion_indicators = [
                response_stripped.endswith('.'),
                response_stripped.endswith('!'),
                'completed' in response_lower,
                'finished' in response_lower,
                'done' in response_lower,
                'successful' in response_lower,
            ]
            # If response has substantive content and looks conclusive
            if len(response_stripped) > 50 and sum(conclusion_indicators) >= 2:
                return True

        # HEURISTIC: If model gives a long response without tool calls, it's probably done
        if len(response_stripped) > 300 and not self._looks_like_tool_call(response_text):
            # Long natural language response without tool calls = likely complete
            return True

        # SAFETY: After many iterations with tool calls, if model stops calling tools, it's done
        if iteration > 5 and completed_actions and len(completed_actions) > 3:
            # If the last response doesn't look like it needs more work
            continuing_indicators = [
                'next' in response_lower,
                'now i' in response_lower,
                'let me' in response_lower,
                'will' in response_lower and 'i will' in response_lower,
            ]
            if not any(continuing_indicators):
                return True

        return False

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

    def _generate_task_summary(self, completed_actions: List[Dict[str, Any]], final_response: str) -> str:
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
            tool = action.get('tool', 'Unknown')
            action_counts[tool] = action_counts.get(tool, 0) + 1
            if action.get('success', False):
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
            tool = action.get('tool', '').lower()
            args = action.get('args', {})
            if tool in ['write', 'writetool', 'edit', 'edittool'] and action.get('success'):
                file_path = args.get('file_path', args.get('path', ''))
                if file_path:
                    # Show just filename, not full path
                    modified_files.add(file_path.split('/')[-1].split('\\')[-1])

        if modified_files and len(modified_files) <= 5:
            summary_parts.append(f"[dim]Files modified: {', '.join(modified_files)}[/dim]")
        elif modified_files:
            summary_parts.append(f"[dim]Files modified: {len(modified_files)} files[/dim]")

        summary_parts.append(f"[bold cyan]====================[/bold cyan]")

        return "\n".join(summary_parts)

    def _has_pending_todos(self) -> bool:
        """
        Check if there are pending or in-progress todos that haven't been completed.

        Returns:
            True if there are incomplete todos
        """
        try:
            # Try to get the TodoWriteTool from the tool manager
            todo_tool = self.tool_manager.get_tool('todowrite')
            if todo_tool and hasattr(todo_tool, 'todos') and todo_tool.todos:
                for todo in todo_tool.todos:
                    if hasattr(todo, 'status'):
                        if todo.status in ['pending', 'in_progress']:
                            return True
                    elif isinstance(todo, dict) and todo.get('status') in ['pending', 'in_progress']:
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
            provider_name = self.current_provider.get_provider_name() if hasattr(self.current_provider, 'get_provider_name') else ""

        # For OpenAI/OSS models, add explicit format instructions
        if "openai" in provider_name.lower() or "gpt" in str(self.current_provider).lower():
            # Detect if this is a read-only task
            task_lower = task.lower()
            is_read_only = any(word in task_lower for word in [
                'what is', 'what are', 'show', 'list', 'display', 'content',
                'explain', 'describe', 'find', 'search', 'where', 'how many',
                'tell me', 'check', 'view', 'see', 'repo', 'structure', 'folder'
            ])

            # Also check for negative indicators that suggest NOT read-only
            is_action_task = any(word in task_lower for word in [
                'run', 'test', 'pytest', 'execute', 'fix', 'modify', 'change',
                'update', 'create', 'write', 'delete', 'install', 'build'
            ])

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
        is_exploration_task = any(word in task_lower for word in [
            'what is', 'what are', 'show', 'list', 'display', 'content',
            'explain', 'describe', 'structure', 'repo', 'folder', 'files',
            'tell me', 'check', 'view', 'see', 'explore'
        ])

        # Check if previous context contains action commands that might pollute
        context_has_action_commands = False
        for entry in current_context:
            content_lower = entry.content.lower()
            if any(cmd in content_lower for cmd in [
                'pytest', 'python -m pytest', 'npm test', 'npm run',
                'make test', 'cargo test', 'go test', 'jest',
                'git commit', 'git push', 'pip install'
            ]):
                context_has_action_commands = True
                break

        # Clear context if we're switching from action commands to exploration
        if is_exploration_task and context_has_action_commands:
            self.console.print(f"[dim yellow][!] Clearing old context to prevent pollution (switching to exploration task)[/dim yellow]")
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
        if hasattr(self, '_current_task_is_readonly') and self._current_task_is_readonly:
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
        fragment = getattr(self, '_last_json_fragment', None)
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

        # Check if this appears to be a read-only/exploration task
        if hasattr(self, '_current_task_is_readonly') and self._current_task_is_readonly:
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
        if raw_response and hasattr(raw_response, 'choices'):
            choice = raw_response.choices[0]
            if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    tool_calls.append({
                        'name': tc.function.name,
                        'arguments': json.loads(tc.function.arguments)
                    })
                return tool_calls

        # Check Anthropic style tool calls from raw response
        if raw_response and hasattr(raw_response, 'content'):
            for block in raw_response.content:
                if hasattr(block, 'type') and block.type == 'tool_use':
                    tool_calls.append({
                        'name': block.name,
                        'arguments': block.input
                    })
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

        # Valid tool names that we should accept (lowercase for comparison)
        VALID_TOOLS = {
            'ls', 'lstool', 'read', 'readtool', 'write', 'writetool',
            'edit', 'edittool', 'bash', 'bashtool', 'glob', 'globtool',
            'grep', 'greptool', 'todowrite', 'askuserquestion', 'askuser',
            'notebookedit', 'webfetch', 'websearch', 'task'
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

            tool_lower = tool_name.lower().replace('tool', '')

            # Validate based on tool type
            if tool_lower in ['ls', 'list']:
                # LS needs path, and "/" on Windows is suspicious
                path = args.get('path', '')
                if path == '/':
                    self.console.print(f"[dim yellow][!] Ignoring LS with root path '/' - likely malformed[/dim yellow]")
                    return False
                return True

            if tool_lower in ['read']:
                return 'file_path' in args

            if tool_lower in ['write']:
                return 'file_path' in args and 'content' in args

            if tool_lower in ['edit']:
                return 'file_path' in args and ('old_string' in args or 'new_string' in args)

            if tool_lower in ['bash']:
                return 'command' in args

            if tool_lower in ['glob']:
                return 'pattern' in args

            if tool_lower in ['grep']:
                return 'pattern' in args

            # Default: accept if it has at least one argument
            return bool(args)

        def unescape_content(content: str) -> str:
            """
            Properly unescape content that may have double-escaped sequences.

            The model sometimes outputs \\n instead of \n in JSON, which after
            JSON parsing becomes the literal string '\n' (backslash-n) instead
            of an actual newline character.
            """
            if not isinstance(content, str):
                return content

            # Handle double-escaped sequences (model outputs \\n which becomes \n literal after JSON parse)
            # We need to convert these to actual control characters
            result = content

            # Replace literal \n with actual newline
            result = result.replace('\\n', '\n')
            # Replace literal \t with actual tab
            result = result.replace('\\t', '\t')
            # Replace literal \r with actual carriage return
            result = result.replace('\\r', '\r')
            # Replace escaped quotes
            result = result.replace('\\"', '"')
            result = result.replace("\\'", "'")
            # Replace escaped backslashes (should be done last)
            result = result.replace('\\\\', '\\')

            return result

        def process_arguments(args: dict) -> dict:
            """Process arguments and unescape content fields"""
            if not isinstance(args, dict):
                return args

            processed = {}
            for key, value in args.items():
                if key == 'content' and isinstance(value, str):
                    # Unescape content field
                    processed[key] = unescape_content(value)
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
            if 'parameters' in data:
                return data['parameters']
            if 'params' in data:
                return data['params']
            if 'arguments' in data:
                return data['arguments']

            # Flat format - parameters at root level alongside "tool"
            # Extract all keys except "tool" as parameters
            args = {}
            for key, value in data.items():
                if key != 'tool':
                    args[key] = value
            return args

        # STRATEGY 1: Look for JSON in code fences (most reliable)
        json_blocks = re.findall(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text, re.DOTALL)

        for block in json_blocks:
            try:
                data = json.loads(block)
                if 'tool' in data:
                    args = extract_tool_args(data)
                    if is_valid_tool_call(data['tool'], args):
                        tool_calls.append({
                            'name': data['tool'],
                            'arguments': process_arguments(args)
                        })
                        self.console.print(f"[bold blue][+] Detected {data['tool']} from JSON block[/bold blue]")
                elif 'file_path' in data and 'content' in data:
                    # Looks like WriteTool parameters - requires both file_path and content
                    tool_calls.append({
                        'name': 'WriteTool',
                        'arguments': process_arguments(data)
                    })
                    self.console.print(f"[bold blue][+] Detected WriteTool from JSON block[/bold blue]")
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
                    tool_calls.append({
                        'name': tool_name,
                        'arguments': process_arguments(params)
                    })
                    self.console.print(f"[bold blue][+] Detected {tool_name} from inline JSON[/bold blue]")
            except json.JSONDecodeError:
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 3: Look for any JSON object that could be a tool call
        # Try to find standalone JSON objects
        json_objects = re.findall(r'(\{[^{}]*(?:"tool"|"file_path"|"content")[^{}]*\})', text, re.DOTALL)

        for obj_str in json_objects:
            try:
                data = json.loads(obj_str)
                if 'tool' in data:
                    args = extract_tool_args(data)
                    if is_valid_tool_call(data['tool'], args):
                        tool_calls.append({
                            'name': data['tool'],
                            'arguments': process_arguments(args)
                        })
                        self.console.print(f"[bold blue][+] Detected {data['tool']} from standalone JSON[/bold blue]")
                elif 'file_path' in data and 'content' in data:
                    tool_calls.append({
                        'name': 'WriteTool',
                        'arguments': process_arguments(data)
                    })
                    self.console.print(f"[bold blue][+] Detected WriteTool from standalone JSON[/bold blue]")
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
                json_str = self._extract_balanced_json(text[match.start():])
                if json_str:
                    data = json.loads(json_str)
                    if 'tool' in data:
                        args = extract_tool_args(data)
                        if is_valid_tool_call(data['tool'], args):
                            tool_calls.append({
                                'name': data['tool'],
                                'arguments': process_arguments(args)
                            })
                            self.console.print(f"[bold blue][+] Detected {data['tool']} from balanced extraction[/bold blue]")
            except (json.JSONDecodeError, Exception):
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 5: Handle gpt-oss-120b specific patterns
        # Pattern: {"function": "ToolName", "args": {...}}
        func_pattern = r'\{\s*["\']function["\']\s*:\s*["\'](\w+)["\']\s*,\s*["\']args["\']\s*:\s*(\{[^}]+\})'
        for match in re.finditer(func_pattern, text, re.DOTALL):
            try:
                tool_name = match.group(1)
                args = json.loads(match.group(2))
                if is_valid_tool_call(tool_name, args):
                    tool_calls.append({
                        'name': tool_name,
                        'arguments': process_arguments(args)
                    })
                    self.console.print(f"[bold blue][+] Detected {tool_name} from function/args pattern[/bold blue]")
            except:
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 6: Handle labeled tool code blocks
        # Pattern: ```tool:WriteTool\n{...}\n```
        labeled_blocks = re.findall(r'```tool:(\w+)\s*\n(\{[\s\S]*?\})\s*```', text)
        for tool_name, json_str in labeled_blocks:
            try:
                args = json.loads(json_str)
                if is_valid_tool_call(tool_name, args):
                    tool_calls.append({
                        'name': tool_name,
                        'arguments': process_arguments(args)
                    })
                    self.console.print(f"[bold blue][+] Detected {tool_name} from labeled code block[/bold blue]")
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
                    tool_calls.append({
                        'name': tool_name,
                        'arguments': process_arguments(args)
                    })
                    self.console.print(f"[bold blue][+] Detected {tool_name} from action/input pattern[/bold blue]")
            except:
                continue

        if tool_calls:
            return tool_calls

        # STRATEGY 8: Last resort - look for file_path and content anywhere
        # This handles cases where the model outputs WriteTool parameters without the wrapper
        # Require BOTH file_path and content, and content must be substantial
        file_path_match = re.search(r'["\']file_path["\']\s*:\s*["\']([^"\']+)["\']', text)
        content_match = re.search(r'["\']content["\']\s*:\s*["\'](.+?)["\'](?:\s*[,}])', text, re.DOTALL)

        if file_path_match and content_match:
            file_path = file_path_match.group(1)
            content = content_match.group(1)

            # Validate: file_path should look like a real path, content should be substantial
            if file_path and len(content) > 10:  # Minimum content length
                # Unescape the content using the helper function
                content = unescape_content(content)
                tool_calls.append({
                    'name': 'WriteTool',
                    'arguments': {
                        'file_path': file_path,
                        'content': content
                    }
                })
                self.console.print(f"[bold blue][+] Detected WriteTool from scattered JSON fields: {file_path}[/bold blue]")

        # STRATEGY 9: Handle command-style tool calls
        # Pattern: "I'll use the Read tool to read file.py" followed by potential JSON
        command_patterns = [
            (r"(?:use|call|invoke|run)\s+(?:the\s+)?(\w+)(?:\s+tool)?(?:\s+to\s+|\s+on\s+)(?:[^{]*?)\{([^}]+)\}", "command"),
            (r"Tool:\s*(\w+)\s*(?:\n|:)\s*\{([^}]+)\}", "labeled"),
        ]

        for pattern, pattern_name in command_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                try:
                    tool_name = match.group(1)
                    json_str = "{" + match.group(2) + "}"
                    args = json.loads(json_str)
                    if is_valid_tool_call(tool_name, args):
                        tool_calls.append({
                            'name': tool_name,
                            'arguments': process_arguments(args)
                        })
                        self.console.print(f"[bold blue][+] Detected {tool_name} from {pattern_name} pattern[/bold blue]")
                except:
                    continue

        return tool_calls

    def _extract_balanced_json(self, text: str, max_length: int = 10000) -> Optional[str]:
        """Extract a balanced JSON object from text"""
        if not text or text[0] != '{':
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[:max_length]):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[:i + 1]

        return None

    def _normalize_tool_arguments(self, tool_name: str, arguments: dict) -> dict:
        """
        Normalize tool arguments to handle different parameter names from different models.

        Maps common alternate parameter names to expected names for each tool.
        """
        # Parameter name mappings for different tools
        # Maps common alternate parameter names to the expected parameter names
        PARAM_MAPPINGS = {
            'glob': {
                # If 'path' looks like a glob pattern, it's probably meant to be 'pattern'
                # e.g. {"tool": "Glob", "path": "**/*.html"} -> {"pattern": "**/*.html"}
                'include': 'pattern',  # Some models use 'include' for glob patterns
                'file_pattern': 'pattern',
                'files': 'pattern',
            },
            'grep': {
                'query': 'pattern',
                'search': 'pattern',
                'text': 'pattern',
                'regex': 'pattern',
                'include': 'glob',  # File filter pattern
                'file_pattern': 'glob',
                'filter': 'glob',
                '-i': 'case_insensitive',
                'ignore_case': 'case_insensitive',
                '-A': 'context_after',
                '-B': 'context_before',
                '-C': 'context',  # Will need special handling
                'directory': 'path',
                'dir': 'path',
                'folder': 'path',
            },
            'read': {
                'path': 'file_path',
                'filename': 'file_path',
                'file': 'file_path',
                'filepath': 'file_path',
            },
            'write': {
                'path': 'file_path',
                'filename': 'file_path',
                'file': 'file_path',
                'filepath': 'file_path',
                'text': 'content',
                'data': 'content',
                'body': 'content',
            },
            'edit': {
                'path': 'file_path',
                'filename': 'file_path',
                'file': 'file_path',
                'filepath': 'file_path',
                'old': 'old_string',
                'new': 'new_string',
                'search': 'old_string',
                'replace': 'new_string',
                'find': 'old_string',
                'replacement': 'new_string',
            },
            'bash': {
                'cmd': 'command',
                'shell': 'command',
                'run': 'command',
                'script': 'command',
                'exec': 'command',
            },
            'ls': {
                'dir': 'path',
                'directory': 'path',
                'folder': 'path',
                'file_path': 'path',
            },
            'task': {
                'type': 'subagent_type',
                'agent_type': 'subagent_type',
                'agent': 'subagent_type',
            },
            'todowrite': {
                'items': 'todos',
                'tasks': 'todos',
                'list': 'todos',
            },
            'webfetch': {
                'query': 'prompt',
                'question': 'prompt',
            },
            'websearch': {
                'search': 'query',
                'q': 'query',
                'term': 'query',
            },
            'askuserquestion': {
                'question': 'questions',  # Single question -> questions array
                'prompt': 'questions',
                'message': 'questions',
                'ask': 'questions',
                'action': 'questions',  # GPT-OSS sometimes uses 'action'
            },
            'askuser': {
                'question': 'questions',
                'prompt': 'questions',
                'message': 'questions',
                'ask': 'questions',
                'action': 'questions',
            },
        }

        # Get tool's base name (without 'tool' suffix)
        base_name = tool_name.lower()
        if base_name.endswith('tool'):
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
        if base_name == 'glob':
            if 'path' in normalized and 'pattern' not in normalized:
                path_val = normalized.get('path', '')
                if isinstance(path_val, str) and ('*' in path_val or '?' in path_val):
                    # This looks like a pattern, not a directory path
                    normalized['pattern'] = path_val
                    # Set path to current directory
                    normalized['path'] = '.'

        # Special handling for Task tool: ensure subagent_type is set
        if base_name == 'task':
            if 'subagent_type' not in normalized:
                # Default to 'Explore' for investigation tasks, 'general-purpose' otherwise
                prompt = normalized.get('prompt', '').lower()
                if any(word in prompt for word in ['find', 'search', 'look', 'explore', 'where', 'what files']):
                    normalized['subagent_type'] = 'Explore'
                else:
                    normalized['subagent_type'] = 'general-purpose'
                self.console.print(f"[dim]ℹ Task tool: defaulting subagent_type to '{normalized['subagent_type']}'[/dim]")

            # Ensure description is set
            if 'description' not in normalized:
                prompt = normalized.get('prompt', '')
                normalized['description'] = prompt[:50] + '...' if len(prompt) > 50 else prompt

        # Special handling for AskUserQuestion: convert simple formats to expected format
        if base_name in ['askuserquestion', 'askuser', 'ask']:
            questions = normalized.get('questions')

            # If questions is a string (simple question), convert to proper format
            if isinstance(questions, str):
                normalized['questions'] = [{
                    'question': questions,
                    'header': 'Question',
                    'type': 'open'  # Open-ended question (no options)
                }]
            # If questions is missing but there's other text-like content, use it
            elif questions is None:
                # Look for any string value that could be the question
                for key in ['text', 'query', 'input', 'content']:
                    if key in normalized and isinstance(normalized[key], str):
                        normalized['questions'] = [{
                            'question': normalized[key],
                            'header': 'Question',
                            'type': 'open'
                        }]
                        break
                else:
                    # Last resort: if there's any string argument, use it
                    for key, value in list(arguments.items()):
                        if isinstance(value, str) and key != 'tool':
                            normalized['questions'] = [{
                                'question': value,
                                'header': 'Question',
                                'type': 'open'
                            }]
                            break

        return normalized

    async def _execute_tool_calls(self, tool_calls: list, require_confirmation: bool = True, max_retries: int = 2) -> list:
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
        TRANSIENT_ERRORS = ['timeout', 'temporary', 'retry', 'busy', 'unavailable', 'connection']

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
                            self.console.print(f"[dim][R] Retrying {tool_name} (attempt {attempt + 2}/{max_retries + 1})...[/dim]")
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
                        error=f"Failed after {max_retries + 1} attempts: {str(last_error)}"
                    )

            # Should not reach here, but return error just in case
            return ToolResult(
                success=False,
                output="",
                error=f"Unexpected error after {max_retries + 1} attempts"
            )

        results = []
        write_operations = []
        other_operations = []

        # Separate write operations (need confirmation) from others
        for tc in tool_calls:
            tool_name = tc['name'].lower()
            if tool_name in ['writetool', 'edittool', 'multiedittool', 'write', 'edit', 'multiedit']:
                write_operations.append(tc)
            else:
                other_operations.append(tc)

        # Execute non-write operations immediately with retry support
        for tc in other_operations:
            tool_name = tc['name'].lower()
            arguments = self._normalize_tool_arguments(tool_name, tc['arguments'])

            self.console.print(f"[bold yellow][>] Calling tool: {tool_name}[/bold yellow]")

            result = await execute_with_retry(tool_name, arguments)
            results.append((tool_name, result, arguments))

        # Handle write operations with confirmation
        if write_operations:
            if require_confirmation:
                # Display pending write operations
                self._display_pending_writes(write_operations)

                # Ask for confirmation (default is Yes - press Enter to accept)
                self.console.print("[bold yellow]Execute these file operations?[/bold yellow] [[green]Ok[/green]/n]: ", end="")
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
                        arguments = self._normalize_tool_arguments(tc['name'].lower(), tc['arguments'])
                        results.append((tc['name'], ToolResult(
                            success=False,
                            output="",
                            error="Operation cancelled by user"
                        ), arguments))
                    return results

            # Execute write operations with retry support
            for tc in write_operations:
                tool_name = tc['name'].lower()
                arguments = self._normalize_tool_arguments(tool_name, tc['arguments'])

                self.console.print(f"[bold green][W]  Writing: {tool_name}[/bold green]")

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

        tool_lower = tool_name.lower().replace('tool', '')

        # For bash commands, use the command itself
        if tool_lower == 'bash':
            cmd = arguments.get('command', '')
            # Normalize whitespace and extract core command
            normalized = ' '.join(cmd.split())
            return f"bash:{normalized}"

        # For other tools, create a hash of the key arguments
        key_parts = [tool_lower]
        for key in sorted(arguments.keys()):
            value = arguments[key]
            if isinstance(value, str):
                key_parts.append(f"{key}={value}")
            else:
                key_parts.append(f"{key}={json.dumps(value)}")

        return ':'.join(key_parts)

    def _display_pending_writes(self, write_operations: list):
        """Display pending write operations for user review"""
        from rich.panel import Panel
        from rich.text import Text
        from rich.syntax import Syntax

        ops_text = Text()
        ops_text.append("[+] Pending File Operations:\n\n", style="bold yellow")

        for i, tc in enumerate(write_operations, 1):
            tool_name = tc['name']
            args = tc['arguments']

            ops_text.append(f"  {i}. ", style="bold")
            ops_text.append(f"{tool_name}\n", style="bold cyan")

            if tool_name.lower() == "writetool":
                file_path = args.get("file_path", "unknown")
                content = args.get("content", "")
                content_preview = content[:300] + "..." if len(content) > 300 else content
                ops_text.append(f"     [F] File: {file_path}\n", style="dim")
                ops_text.append(f"     [N] Content ({len(content)} chars):\n", style="dim")

            elif tool_name.lower() == "edittool":
                file_path = args.get("file_path", "unknown")
                old_str = args.get("old_string", "")
                new_str = args.get("new_string", "")
                old_preview = old_str[:100] + "..." if len(old_str) > 100 else old_str
                new_preview = new_str[:100] + "..." if len(new_str) > 100 else new_str
                ops_text.append(f"     [F] File: {file_path}\n", style="dim")
                ops_text.append(f"     [X] Remove: {old_preview}\n", style="red dim")
                ops_text.append(f"     [+] Add: {new_preview}\n", style="green dim")

            elif tool_name.lower() == "multiedittool":
                file_path = args.get("file_path", "unknown")
                edits = args.get("edits", [])
                ops_text.append(f"     [F] File: {file_path}\n", style="dim")
                ops_text.append(f"     [N] {len(edits)} edit(s)\n", style="dim")

            ops_text.append("\n")

        self.console.print(Panel(
            ops_text,
            title="[bold]Review File Changes[/bold]",
            border_style="yellow"
        ))

    def _display_tool_result(self, tool_name: str, result, arguments: dict):
        """
        Display tool execution result in Claude Code style.

        Uses the HcodeToolDisplay class for consistent formatting:
        - WriteTool: Only show file path and byte count (no content)
        - EditTool: Show file path with diff (old -> new)
        - BashTool: Show command and full output in box
        - ReadTool: Show file path and line count
        - Other tools: Show appropriate preview
        """
        from ..cli.tool_display import HcodeToolDisplay

        # Use Hcode-style tool display
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
            task=query,
            agent_types=[HcodeAgentType.EXPLORE],
            parallel=False
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
            task=task,
            agent_types=agent_types,
            parallel=False
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
            parallel=False
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
                content=content,
                memory_type=mem_type,
                importance=importance,
                source="agent"
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
                    "score": score
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

    def update_agent_memory(self, content: str, scope: str = "project", section: Optional[str] = None) -> bool:
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
                content=content,
                scope=scope,
                section=section
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
                prune_semantic=True,
                compact_session=True,
                apply_decay=True
            )
        except Exception as e:
            self.console.print(f"[red]Cleanup failed: {e}[/red]")
            return {}
