"""
Hcode Agent with full tool integration.
Integrates all features: tools, sub-agents, web capabilities, interactive features.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List

from rich.markup import escape

from .adapters import AgentAdapter  # New SOLID PEV adapter
from .context import ContextManager
from .observability import (
    get_analytics,
)
# Import optimization components
from .optimization import (
    ToolResultCache,
    get_token_counter,
)
from .safety import SafetyGuard
from ..agents import HcodeAgentOrchestrator  # Legacy orchestrator for sub-agents
from ..providers import (
    ProviderSelector,
    ProviderPreferences,
    TaskComplexity,
    TaskType,
    AIProvider,
)
from ..tools import ToolManager
# Import modern UI system
from ..ui import (
    get_console as get_themed_console,
    get_palette,
    Icons,
)

# Import memory system
try:
    from hcode.memory import get_memory_manager

    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

# Import interaction logger
from hcode.core.observability import get_logger, InteractionLogger

# Thinking block parser
from typing import Tuple, Optional

# Import refactored components
from .response import (
    ThinkingBlockProcessor,
    ResponseParser,
    TaskCompletionDetector,
    ResponseCleaner,
)
from .response.thinking_processor import (
    parse_thinking_block,
    is_valid_thinking,
    get_thinking_summary,
    format_thinking_display,
)
from .execution import (
    LoopDetector,
    CircuitBreaker,
)
from .prompt import (
    ContextInjector,
    UserTaskFormatter,
)
from hcode.core.todo import TodoManager, TodoAutoUpdater
from hcode.core.tools import ToolCallParser
from hcode.core.execution import ToolExecutor
from hcode.core.loop import AgentLoopController, StopReason, Phase


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
            autonomous_mode: bool = False,
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
        # Detect project root by looking for marker files
        self.root_dir = self._find_project_root(Path(root_dir)) if root_dir else self._find_project_root(Path.cwd())
        self.console = get_themed_console()  # Use themed console
        self._palette = get_palette()
        self._icons = Icons()
        self.config = config or {}
        self.session_id = session_id
        self.autonomous_mode = autonomous_mode or self.config.get("autonomous_mode", False)

        # Initialize provider selector
        import os
        
        self.provider_selector = ProviderSelector(
            anthropic_key=anthropic_key or os.getenv("ANTHROPIC_API_KEY"),
            openai_key=openai_key or os.getenv("OPENAI_API_KEY"),
            openai_base_url=openai_base_url or os.getenv("OPENAI_BASE_URL"),
            anthropic_model=anthropic_model,
            openai_model=openai_model or os.getenv("OPENAI_MODEL"),
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
        from .response.continuation import ContinuationManager, ContextWindowManager

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
        # self.execution_state = ... (Removed, using _loop_controller)

        # Initialize refactored components
        debug_mode = self._is_debug_mode() if hasattr(self, '_is_debug_mode') else False

        # Todo management
        self._todo_manager = TodoManager(self.tool_manager)

        # Response processing
        self._response_parser = ResponseParser(
            tool_registry=self.tool_manager.tool_registry,
            console=self.console,
            debug_mode=debug_mode,
        )
        self._response_cleaner = ResponseCleaner()
        self._completion_detector = TaskCompletionDetector(
            todo_manager=self._todo_manager,
            console=self.console,
            debug_mode=debug_mode,
        )
        self._thinking_processor = ThinkingBlockProcessor(
            console=self.console,
            debug_mode=debug_mode,
        )

        # Execution control
        self._loop_detector = LoopDetector(max_recent=5, stuck_threshold=3)
        self._circuit_breaker = CircuitBreaker(max_failures=3, reset_timeout=30.0)

        # Prompt building
        self._context_injector = ContextInjector(
            root_dir=self.root_dir,
            memory_manager=self.memory_manager,
            autonomous_mode=self.autonomous_mode,
        )
        self._task_formatter = UserTaskFormatter()

        # NEW: Refactored module initialization (PEV architecture)
        # Tool call parsing (Perception)
        self._tool_call_parser = ToolCallParser(
            console=self.console,
            debug_mode=debug_mode,
        )

        # Tool execution (Execution Pipeline)
        self._tool_executor = ToolExecutor(
            tool_manager=self.tool_manager,
            console=self.console,
            icons=self._icons,
        )

        # Todo auto-updater (Perception)
        self._todo_auto_updater = TodoAutoUpdater(
            tool_manager=self.tool_manager,
            console=self.console,
            icons=self._icons,
        )

        # Loop controller (Orchestration)
        self._loop_controller = AgentLoopController(
            console=self.console,
            debug_mode=debug_mode,
        )

        # Response cleaner (Presentation)
        self._response_cleaner = ResponseCleaner()

        # Initialize resilient provider if multiple providers available
        self._init_resilient_provider(anthropic_key, openai_key, openai_base_url)

        # Initialize PEV adapter (new SOLID architecture)
        # This bridges the new phase handlers with the existing agent
        self._pev_adapter: Optional[AgentAdapter] = None

        # PEV workflow is ALWAYS ENABLED by default (SOLID architecture)
        # This ensures consistent Planning → Execution → Verification flow
        # for ALL tasks regardless of complexity or type
        agent_config = self.config.get("agent", {})
        self._pev_enabled = agent_config.get("pev_workflow") if isinstance(agent_config, dict) else None
        if self._pev_enabled is None:
            # DEFAULT TO TRUE: PEV is mandatory for all tasks
            self._pev_enabled = self.config.get("pev_workflow", True)

    def _is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self.config.get("debug", False) or self.config.get("ui", {}).get("debug_mode", False)

    def _debug_print(self, message: str):
        """Print message only if debug mode is enabled."""
        if self._is_debug_mode():
            self.console.print(message)

    async def connect_mcp_servers(self):
        """Connect MCP servers and make their tools available."""
        await self.tool_manager.connect_mcp_servers()

    def _get_pev_adapter(self) -> Optional[AgentAdapter]:
        """
        Get or create the PEV adapter for SOLID workflow.

        Lazy initialization to avoid circular dependencies and ensure
        all components are ready before creating the adapter.
        """
        if self._pev_adapter is None and self.current_provider:
            try:
                self._pev_adapter = AgentAdapter(
                    provider=self.current_provider,
                    tool_executor=self._tool_executor,
                    context_manager=self.context_manager,
                    working_dir=str(self.root_dir),
                    console=self.console,
                )
                self._debug_print("[dim]PEV adapter initialized[/dim]")
            except Exception as e:
                self.console.print(f"[dim yellow]PEV adapter initialization failed: {e}[/dim yellow]")
        return self._pev_adapter

    def _should_use_pev_workflow(self, task: str, use_sub_agents: bool) -> bool:
        """
        Determine if task should use the PEV workflow (Execution + Verification).

        Args:
            task: User's task description
            use_sub_agents: Whether sub-agents are being used

        Returns:
            True if PEV workflow should be used
        """
        # Don't use PEV with sub-agents (they have their own orchestration)
        if use_sub_agents:
            return False

        # Check environment variable to DISABLE PEV (for testing/debugging only)
        import os
        disable_pev = os.environ.get("HCODE_DISABLE_PEV", "").lower() == "true"
        if disable_pev:
            self._debug_print("[dim yellow][!] PEV disabled via HCODE_DISABLE_PEV env var[/dim yellow]")
            return False

        # Check config setting to explicitly disable (not recommended)
        if self._pev_enabled is False:
            return False

        return True

    def _needs_planning_phase(self, task: str) -> bool:
        """
        Determine if the task requires the planning phase.

        Planning is activated when:
        - The user explicitly uses /plan  → always plan, OR
        - The task is classified as complex AND user did not use /fast

        /fast explicitly opts out of planning regardless of complexity.

        Args:
            task: User's task description (may include /plan or /fast prefix)

        Returns:
            True if planning phase should run before execution
        """
        stripped = task.strip().lower()

        # /fast always skips planning
        if stripped.startswith("/fast"):
            return False

        # /plan always activates planning
        if stripped.startswith("/plan"):
            return True

        # Complex tasks benefit from upfront planning
        from .classification import TaskClassifier
        classifier = TaskClassifier()
        return classifier.requires_pev_workflow(task)

    def _strip_mode_command(self, task: str) -> str:
        """Strip /plan or /fast prefix from task if present."""
        stripped = task.strip()
        for prefix in ("/plan ", "/fast "):
            if stripped.lower().startswith(prefix):
                return stripped[len(prefix):].strip()
        # bare /plan or /fast with no body — keep as-is
        return stripped

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

    def _find_project_root(self, start_path: Path) -> Path:
        """
        Find the project root by looking for marker files.
        
        Traverses parent directories looking for .git, pyproject.toml, setup.py,
        or package.json to identify the project root.
        
        Args:
            start_path: Directory to start searching from
            
        Returns:
            Project root path, or start_path if no markers found
        """
        markers = [".git", "pyproject.toml", "setup.py", "package.json", ".hcode"]
        current = start_path.resolve()

        # Traverse up to 10 levels (safety limit)
        for _ in range(10):
            for marker in markers:
                if (current / marker).exists():
                    return current
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            current = parent

        # Fallback to original path if no markers found
        return start_path.resolve()

    async def execute_task(
            self,
            task: str,
            complexity: TaskComplexity = TaskComplexity.MODERATE,
            task_type: TaskType = TaskType.CODE_GENERATION,
            stream: bool = True,
            use_sub_agents: bool = False,
            force_planning: Optional[bool] = None,
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
        self.safety_guard.start_transaction(description=task)

        # Track execution with analytics
        import time

        task_start_time = time.time()
        self.analytics.start_conversation(self.context_manager.session_id)
        self._loop_controller.transition(Phase.PLANNING)

        # Determine if planning phase is needed:
        # - force_planning from CLI mode toggle takes precedence
        # - otherwise detect from /plan//fast prefix or task complexity
        task = self._strip_mode_command(task)
        if force_planning is not None:
            use_planning = force_planning
        else:
            use_planning = self._needs_planning_phase(task)

        # Initialize Hcode Display for task header
        from hcode.ui.hcode_display import get_hcode_display, TaskMode
        hcode_display = get_hcode_display(self.console)
        # Show PLANNING mode only when planning phase will actually run
        initial_mode = TaskMode.EXECUTION if (use_sub_agents or not use_planning) else TaskMode.PLANNING
        hcode_display.start_task(task, initial_mode)

        try:
            # Use sub-agents if requested
            if use_sub_agents:
                self._loop_controller.transition(Phase.EXECUTION)
                result = await self.agent_orchestrator.auto_execute(task)
                response = result.output

                self._loop_controller.stop(StopReason.TASK_COMPLETE)
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

            # Check if we should use the new PEV workflow
            if self._should_use_pev_workflow(task, use_sub_agents):
                workflow_label = "PEV (planning+execution+verification)" if use_planning else "EV (execution+verification)"
                self._debug_print(f"[dim]Using {workflow_label} workflow[/dim]")
                pev_adapter = self._get_pev_adapter()
                if pev_adapter:
                    # Execute via PEV workflow (Planning -> Execution -> Verification)
                    pev_result = await pev_adapter.execute_task(
                        task=task,
                        session_id=self.context_manager.session_id,
                        use_planning=use_planning,
                    )

                    self._loop_controller.stop(StopReason.TASK_COMPLETE if pev_result.get("success") else StopReason.ERROR)
                    self.analytics.end_conversation(
                        self.context_manager.session_id,
                        success=pev_result.get("success", False),
                        total_cost=self.current_provider.total_cost if self.current_provider else 0,
                    )

                    if pev_result.get("success"):
                        self.safety_guard.commit_transaction()
                    else:
                        self.safety_guard.rollback_transaction()

                    return pev_result.get("output", "Task completed")

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
            # self._loop_controller.transition(Phase.EXECUTION) # Transitions automatically based on activity
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
            self._loop_controller.stop(StopReason.TASK_COMPLETE)
            time.time() - task_start_time
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
            self._loop_controller.reset()  # Reset state on error
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
                self.console.print(f"[bold red][X] LLM Connection Error:[/bold red] {escape(str(e))}")
                if hasattr(e, "base_url") and e.base_url:
                    self.console.print(f"[dim]API Endpoint: {escape(e.base_url)}[/dim]")
                self.console.print(
                    "[dim]Check your network connection and API endpoint configuration.[/dim]"
                )
                self.console.print(
                    "[dim]You can also check your OPENAI_BASE_URL environment variable.[/dim]"
                )
                raise

            # Handle built-in connection errors
            elif isinstance(e, ConnectionError) or "connection" in error_str:
                self.console.print(f"[bold red][X] Connection Error:[/bold red] {escape(str(e))}")
                self.console.print(
                    "[dim]Check your network connection and API endpoint configuration.[/dim]"
                )
                raise

            elif isinstance(e, TimeoutError) or "timeout" in error_str:
                self.console.print(f"[bold red][X] Timeout Error:[/bold red] {escape(str(e))}")
                self.console.print(
                    "[dim]The request took too long. Try again or increase timeout in config.[/dim]"
                )
                raise

            elif isinstance(e, RuntimeError):
                if "rate limit" in error_str:
                    self.console.print(f"[bold yellow][!] Rate Limited:[/bold yellow] {escape(str(e))}")
                    self.console.print("[dim]Please wait a moment before trying again.[/dim]")
                else:
                    self.console.print(f"[bold red][X] Error:[/bold red] {escape(str(e))}")
                raise

            elif isinstance(e, ValueError):
                self.console.print(f"[bold red][X] Configuration Error:[/bold red] {escape(str(e))}")
                raise

            else:
                self.console.print(
                    f"[bold red][X] Unexpected Error ({error_type}):[/bold red] {escape(str(e))}"
                )
                raise

        finally:
            if 'hcode_display' in locals():
                hcode_display.end_task()

    def _build_system_prompt(self, query: Optional[str] = None) -> str:
        """Build system prompt with tool documentation and memory context """
        # Get base system prompt from external config
        base_prompt = self.current_provider.get_system_prompt_for_coding()

        # Get tool documentation from external config
        from ..config.tools import get_tools_config

        tools_config = get_tools_config()
        tool_docs = tools_config.get_tool_documentation()

        # Add tool documentation
        base_prompt += "\n\n" + tool_docs

        # INJECT PROJECT ROOT CONTEXT so model knows correct paths
        base_prompt += f"""
<user_information>
The USER's OS version is Windows.
The user has 1 active workspaces, each defined by a URI and a CorpusName. Multiple URIs potentially map to the same CorpusName. The mapping is shown as follows in the format [URI] -> [CorpusName]:
{self.root_dir} -> main

Code relating to the user's requests should be written in the locations listed above. Avoid writing project code files to tmp, in the .gemini dir, or directly to the Desktop and similar folders unless explicitly asked.
</user_information>"""

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

        # INJECT CURRENT TASK AND PLAN
        try:
            hcode_dir = self.root_dir / ".hcode"
            task_file = hcode_dir / "task.md"
            plan_file = hcode_dir / "implementation_plan.md"

            context_injection = "\n\n## CURRENT TASK CONTEXT\n"
            has_context = False

            if task_file.exists():
                task_content = task_file.read_text(encoding="utf-8")
                context_injection += f"\n### Current Task List ({task_file.name})\n{task_content}\n"
                has_context = True

            if plan_file.exists():
                plan_content = plan_file.read_text(encoding="utf-8")
                context_injection += f"\n### Implementation Plan ({plan_file.name})\n{plan_content}\n"
                has_context = True

            if has_context:
                base_prompt += context_injection

        except Exception as e:
            self.console.print(f"[dim yellow][!] Could not inject task context: {e}[/dim yellow]")

        # AUTONOMOUS MODE INSTRUCTION
        if self.autonomous_mode:
            base_prompt += """

## AUTONOMOUS EXECUTION MODE
Active Mode: **AUTONOMOUS**

You are operating in AUTONOMOUS MODE.
1. You do NOT need to ask for user approval for implementation plans.
2. You should create the plan and relevant artifacts, but then PROCEED DIRECTLY to Execution.
3. DO NOT STOP to ask the user to review the plan.
4. Execute the plan immediately after creating it.
"""

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

{self.tool_manager.get_tool_documentation()}

### CRITICAL RULES:
1. **Tool Names**: Use the exact names shown above.
2. **Parameters**: Use the exact parameter names.
3. **Paths**: ALWAYS use absolute paths for file parameters.
4. **Editing**: You MUST read the file (`view_file`) before using `replace_file_content` to ensure you have the exact `TargetContent`.

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

        Implements hCode seamless generation by:
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

        # Get tool schemas from external config
        from ..config.tools import get_tools_config

        tools_config = get_tools_config()
        provider_name = self.current_provider.get_provider_name().lower()

        if provider_name == "openai":
            tool_schemas = tools_config.get_openai_schemas()
        else:
            tool_schemas = tools_config.get_anthropic_schemas()

        # Initialize orchestration
        self._loop_controller.reset()

        # Heuristics state (TODO: Move to specialized detector)
        heuristics = {
            "consecutive_no_tool_calls": 0,
            "todo_continuation_prompts": 0,
            "answer_prompts": 0,
            "thinking_only_prompts": 0,
            "last_tool_call_iteration": 0,
        }

        # Helper variables
        all_response_parts = []
        accumulated_results = []
        last_successful_response = ""

        # Main execution loop
        while self._loop_controller.tick():
            iteration = self._loop_controller.state.iteration
            try:  # ROBUSTNESS: Wrap each iteration in try-except
                # Progress feedback every 10 iterations
                if iteration > 1 and iteration % 10 == 0:
                    self._debug_print(f"[dim][...] Processing... (iteration {iteration})[/dim]")

                # DYNAMIC CONTEXT REFRESH: Reload system prompt to include latest task.md/plan.md
                # This ensures the model "sees" the updated task status immediately
                if iteration > 1:
                    try:
                        # Re-build system prompt (query=None to avoid expensive memory re-fetch)
                        refreshed_prompt = self._build_system_prompt(query=None)
                        self.context_manager.set_system_prompt(refreshed_prompt)
                    except Exception as refresh_err:
                        self._debug_print(f"[dim yellow]⚠ Failed to refresh context: {refresh_err}[/dim yellow]")

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

                if iteration == 1:
                    if self._is_debug_mode():
                        self.console.print(f"[dim][*] Thinking...[/dim]", end="\r")

                # Generate completion with tools
                finish_reason = "stop"
                response_text = ""
                raw_response = None
                response = None  # Initialize to prevent UnboundLocalError if exception occurs early
                displayed_thinking = False

                try:
                    response_text, finish_reason, raw_response, displayed_thinking = await self._generate_response(
                        iteration, messages, stream, tool_schemas, provider_name
                    )

                    # Success - reset error counter and save successful response
                    self._loop_controller.state.errors = 0
                    if response_text.strip():
                        last_successful_response = response_text

                    # EMPTY RESPONSE HANDLING: If first response is empty AND no tool calls, add explicit instruction
                    has_tool_calls = hasattr(response, "tool_calls") and response.tool_calls
                    if iteration == 1 and not response_text.strip() and not has_tool_calls:
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
                    should_continue = self._loop_controller.record_error()
                    consecutive_errors = self._loop_controller.state.errors
                    error_msg = str(gen_error)
                    self.console.print(
                        f"[bold red][!] Generation error (attempt {consecutive_errors}/{self._loop_controller.state.max_errors}): {escape(error_msg[:100])}[/bold red]"
                    )

                    if not should_continue:
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
                self._loop_controller.record_response(response_text)

                # DEEP THINKING: Parse and display thinking blocks
                thinking_block, response_without_thinking = parse_thinking_block(response_text)

                if thinking_block and is_valid_thinking(thinking_block) and not displayed_thinking:
                    # Display the thinking block (only shows verbose panel in debug mode)
                    debug_mode = self.config.get("debug", False) or self.config.get("ui", {}).get(
                        "debug_mode", False
                    )
                    format_thinking_display(thinking_block, self.console, debug_mode=debug_mode)

                    # Log the thinking for debugging
                    self.logger.log_interaction(
                        iteration=iteration,
                        request_messages=[],
                        response_text=get_thinking_summary(thinking_block),
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
                    content = response_without_thinking if response_without_thinking else response_text

                    # Use ResponseCleaner to strip tool calls
                    display_text = self._response_cleaner.strip_tool_calls_for_display(content)

                    # Only display if there's substantive content
                    if display_text and len(display_text) > 20:
                        if not self._response_cleaner.is_thinking_metadata_only(display_text):
                            self.console.print(f"\n{escape(display_text)}\n")

                # THINKING ENFORCEMENT: For OpenAI/OSS models, if no thinking block found
                # on first iteration with a tool call, request thinking first
                if provider_name == "openai" and iteration == 1:
                    tool_calls_preview = self._tool_call_parser.extract_tool_calls(
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

Output a <thinking> block that explains your reasoning naturally. Consider what the user is asking, what you know, what tools you could use, why you're choosing this specific tool, and whether it's safe to proceed.

Then repeat your tool call.""",
                            importance=1.0,
                            provider=self.current_provider,
                        )
                        # Don't execute the tool yet, continue to get thinking
                        continue

                # ═══════════════════════════════════════════════════════════════════════════════
                # ACTION EXECUTION LAYER
                # 1. Prioritize tool execution (Strict State Machine: PLAN -> ACT -> OBSERVE)
                # 2. Handle both native and text-extracted tool calls
                # 3. Add results with correct role="tool"
                # ═══════════════════════════════════════════════════════════════════════════════

                # Extract tool calls (Native + Text Fallback)
                tool_calls = self._tool_call_parser.extract_tool_calls(
                    raw_response, response_text, provider_name
                )

                # EXECUTE TOOLS IF PRESENT
                if tool_calls:
                    heuristics["consecutive_no_tool_calls"] = 0
                    heuristics["last_tool_call_iteration"] = iteration

                    # Process tool calls
                    await self._process_tool_calls(tool_calls, response_text, iteration)

                    # FORCE CONTINUE after tool execution
                    continue

                # ═══════════════════════════════════════════════════════════════════════════════
                # NO TOOLS DETECTED - COMPLETION CHECK
                # ═══════════════════════════════════════════════════════════════════════════════

                # Add response to context first (since we didn't do it in tool_calls block)
                if not tool_calls:
                    self.context_manager.add_message(
                        role="assistant",
                        content=response_text,
                        importance=0.5,
                        provider=self.current_provider
                    )

                # Check completion using detector
                completion_state = self._completion_detector.is_complete(
                    response_text,
                    self._loop_controller.state.actions,
                    self._loop_controller.state.iteration
                )

                if completion_state.is_complete:
                    self._debug_print(
                        f"[bold {self._palette.success}]{self._icons.SUCCESS} Task completed: {completion_state.reason}[/bold {self._palette.success}]"
                    )
                    summary = self._generate_task_summary(self._loop_controller.state.actions)
                    if summary and self._is_debug_mode():
                        self.console.print(summary)
                    break

                # Handle Truncation
                if self._completion_detector.is_response_truncated(response_text, finish_reason):
                    self.console.print(f"[dim]-> Response truncated, continuing...[/dim]")
                    self.context_manager.add_message(
                        role="user",
                        content="Please continue.",
                        provider=self.current_provider
                    )
                    continue

                # If we are here, we are NOT complete, and had NO tools.
                # Must Prompt to continue.
                reason = completion_state.reason or "No tool calls detected."
                self.console.print(f"[dim yellow][!] {reason} Prompting to continue...[/dim yellow]")

                # Hallucination Check (Simplified)
                warning = ""
                if "```" in response_text and len(response_text) > 200 and "walkthrough" not in response_text.lower():
                    warning = "\n\nWARNING: You showed code blocks but did not call Write/Edit tool. You MUST use tools to apply changes."

                self.context_manager.add_message(
                    role="user",
                    content=f"Please continue. {reason}{warning}",
                    provider=self.current_provider
                )
                continue


            except Exception as iteration_error:
                # ROBUSTNESS: Catch any unexpected errors in the iteration
                should_continue = self._loop_controller.record_error()
                error_msg = str(iteration_error)
                import traceback
                self.console.print(f"[dim red]{traceback.format_exc()}[/dim red]")
                self.console.print(
                    f"[bold red][!] Iteration error ({self._loop_controller.state.errors}/{self._loop_controller.state.max_errors}): {error_msg[:150]}[/bold red]"
                )

                if not should_continue:
                    self.console.print(
                        f"[bold red][X] Too many errors. Returning partial results.[/bold red]"
                    )
                    break

                # Try to recover by continuing
                await asyncio.sleep(1)
                continue

        # Check if we hit max iterations (safety limit)
        # Check if we hit max iterations (safety limit)
        if self._loop_controller.state.stop_reason == StopReason.MAX_ITERATIONS:
            self._debug_print(
                f"[bold yellow][!] Reached maximum iterations ({self._loop_controller.state.max_iterations}). Stopping.[/bold yellow]"
            )
            # Use state.actions instead of missing local variable
            summary = self._generate_task_summary(self._loop_controller.state.actions)
            if summary and self._is_debug_mode():
                self.console.print(summary)

        # Return accumulated results - clean up and never return empty
        result = self._loop_controller.get_final_response()
        if not result.strip():
            return "Task completed but no output was generated. Please try again."
        return result

    def _generate_task_summary(
            self, completed_actions: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a clean summary of the completed task.

        Args:
            completed_actions: List of tool actions that were executed
            final_response: The final response from the model

        Returns:
            Formatted summary string
        """

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

        # For OpenAI-compatible models, add explicit format instructions to improve tool usage
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
- ONLY use: LS, Glob, Grep, Read, codebase_search

MANDATORY RESPONSE FORMAT:
1. First, output a <thinking> block with your reasoning
2. Then call a READ-ONLY tool (LS, Glob, Grep, or Read)
3. After exploring, provide a SUMMARY to the user

WHEN TO STOP:
- Once you have gathered enough information, provide a summary
- Do NOT continue indefinitely - summarize your findings

Example:
<thinking>
The user wants to see [what]. I need to explore [what] to understand it better. I could use LS to list directories, Glob to find specific files, or Read to see file content. The best choice is [tool] because [reason]. This is read-only, so it's safe to proceed.
</thinking>

{{"tool": "LS", "parameters": {{"DirectoryPath": "."}}}}

START NOW - think first, then explore:"""
            else:
                return f"""USER TASK: {task}

MANDATORY RESPONSE FORMAT:
1. First, output a <thinking> block with your reasoning
2. Then call the appropriate tool

EFFICIENCY RULES:
- **Multiple Edits**: Use `MultiReplaceFileContent` for multiple non-contiguous edits to the same file.
- **Targeted Testing**: Run tests for the specific file/component first (e.g., `pytest path/to/file.py`). Do NOT run the full suite unless requested.
- **Batching**: Group independent operations where possible.

Example:
<thinking>
The user wants [what]. I know [context] about the current state. I could use [list possible tools], and for multiple edits to the same file, MultiReplaceFileContent would be the most efficient. The best choice is [tool] because [reason]. This is safe because [safety check]. I will batch the edits using MultiReplace for efficiency.
</thinking>

{{"tool": "ToolName", "parameters": {{"key": "value"}}}}

Available: Bash, Read, Write, Edit, MultiReplaceFileContent, Glob, Grep, LS

START NOW - think first, then act:"""

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

    async def _generate_response(
            self,
            iteration: int,
            messages: List[Dict[str, Any]],
            stream: bool,
            tool_schemas: Optional[List[Dict[str, Any]]],
            provider_name: str,
    ) -> Tuple[str, str, Any, bool]:
        """Generate response with optional streaming and thinking display."""
        should_stream = stream and (iteration == 1) and (provider_name != "openai")

        response_text = ""
        finish_reason = "stop"
        raw_response = None
        displayed_thinking = False

        if should_stream:
            response_parts = []
            stream_result = await self.current_provider.generate_completion(
                messages=messages,
                stream=True,
                functions=tool_schemas if provider_name == "openai" else None,
                tools=tool_schemas if provider_name == "anthropic" else None,
            )

            from hcode.ui.hcode_display import get_hcode_display
            from hcode.ui.live_todo_bar import get_stdout_lock, get_live_todo_bar
            hcode_display = get_hcode_display(self.console)
            stdout_lock = get_stdout_lock()
            live_bar = get_live_todo_bar(self.console)
            live_bar.pause()
            live_bar._clear_status_area()

            try:
                buffer = ""
                in_thinking = False
                thinking_content = []
                first_chunk = True
                displayed_thinking = False

                async for chunk in stream_result:
                    response_parts.append(chunk)
                    buffer += chunk

                    if "<thinking>" in buffer and not in_thinking:
                        pre, post = buffer.split("<thinking>", 1)
                        if pre:
                            hcode_display.end_thinking()
                            with stdout_lock:
                                print(pre, end="", flush=True)
                        in_thinking = True
                        buffer = post
                        if not hcode_display.thinking_start_time:
                            hcode_display.start_thinking()
                        with stdout_lock:
                            print()

                    if in_thinking:
                        if "</thinking>" in buffer:
                            content, remaining = buffer.split("</thinking>", 1)
                            thinking_content.append(content)
                            full_thinking = "".join(thinking_content)
                            hcode_display.end_thinking()
                            if full_thinking.strip():
                                hcode_display.display_thinking_block(full_thinking)
                            displayed_thinking = True
                            in_thinking = False
                            buffer = remaining
                            thinking_content = []
                        else:
                            thinking_content.append(buffer)
                            buffer = ""
                    else:
                        if "<" in buffer and len(buffer) < 20:
                            pass
                        else:
                            if first_chunk and buffer.strip():
                                hcode_display.end_thinking()
                                first_chunk = False
                            with stdout_lock:
                                print(buffer, end="", flush=True)
                            buffer = ""

                if buffer:
                    if in_thinking:
                        thinking_content.append(buffer)
                        full_thinking = "".join(thinking_content)
                        hcode_display.end_thinking()
                        if full_thinking.strip():
                            hcode_display.display_thinking_block(full_thinking)
                        displayed_thinking = True
                    else:
                        if first_chunk:
                            hcode_display.end_thinking()
                        with stdout_lock:
                            print(buffer, end="", flush=True)

                with stdout_lock:
                    print()
            finally:
                live_bar.resume()

            response_text = "".join(response_parts)
            if self.continuation_manager.should_continue("stop", response_text):
                finish_reason = "length"
        else:
            response = await self.current_provider.generate_completion(
                messages=messages,
                stream=False,
                functions=tool_schemas if provider_name == "openai" else None,
                tools=tool_schemas if provider_name == "anthropic" else None,
            )
            if iteration == 1:
                self.console.print(" " * 20, end="\r")
            response_text = response.content
            raw_response = getattr(response, "raw_response", None)
            finish_reason = getattr(response, "finish_reason", "stop")

        return response_text, finish_reason, raw_response, displayed_thinking

    async def _process_tool_calls(
            self,
            tool_calls: List[Dict[str, Any]],
            response_text: str,
            iteration: int,
    ) -> None:
        """Process and execute tool calls."""
        # 1. Add assistant message with tool calls to context
        self.context_manager.add_message(
            role="assistant",
            content=response_text,
            importance=0.7,
            provider=self.current_provider,
            tool_calls=tool_calls
        )

        try:
            # 2. Execute tools via ToolExecutor
            tool_results = await self._tool_executor.execute_tool_calls(
                tool_calls,
                normalize_fn=self._tool_call_parser.normalize_arguments
            )

            # 3. Process results
            for i, (tool_name, result, arguments) in enumerate(tool_results):
                # Track action
                self._loop_controller.record_action(tool_name, arguments, result.success)

                # Display result
                self._tool_executor.display_tool_result(tool_name, result, arguments)

                # Log tool result
                self.logger.log_tool_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    success=result.success,
                    output=result.output,
                    error=result.error
                )

                if result.success:
                    self._todo_auto_updater.auto_update({
                        "tool": tool_name,
                        "success": True,
                        "args": arguments,
                        "iteration": self._loop_controller.state.iteration,
                    })

                    # PEV FLOW: Auto-transition phases based on activity
                    t_lower = tool_name.lower()
                    fpath = str(arguments.get("file_path", "")).lower()

                    if "task.md" in fpath or "implementation_plan.md" in fpath:
                        if self._loop_controller.state.phase != Phase.PLANNING:
                            self._loop_controller.transition(Phase.PLANNING)
                    elif "walkthrough.md" in fpath:
                        if self._loop_controller.state.phase != Phase.VERIFICATION:
                            self._loop_controller.transition(Phase.VERIFICATION)
                    elif t_lower == "bash":
                        cmd = str(arguments.get("command", "")).lower()
                        if "pytest" in cmd or "test" in cmd:
                            if self._loop_controller.state.phase != Phase.VERIFICATION:
                                self._loop_controller.transition(Phase.VERIFICATION)
                    elif t_lower in ["write", "edit", "replace_file_content", "multi_replace_file_content"]:
                        # If we were in PLANNING and start writing code, move to EXECUTION
                        if self._loop_controller.state.phase == Phase.PLANNING:
                            self._loop_controller.transition(Phase.EXECUTION)

                # HCODE UI: Track file operations (Legacy UI support)
                try:
                    from hcode.ui.hcode_display import get_hcode_display, FileAction
                    hcode_display = get_hcode_display(self.console)
                    t_lower = tool_name.lower()
                    if result.success:
                        if "write" in t_lower or "edit" in t_lower:
                            fpath = arguments.get("file_path")
                            if fpath:
                                hcode_display.track_file(fpath, FileAction.EDITED)
                        elif "read" in t_lower or "view" in t_lower:
                            fpath = arguments.get("file_path")
                            if fpath:
                                hcode_display.track_file(fpath, FileAction.VIEWED)
                except Exception:
                    pass

                # Add to context
                tool_call_id = tool_calls[i].get("id") if i < len(tool_calls) else None

                result_content = result.output
                if not result.success and result.error:
                    result_content = f"Error: {result.error}\nOutput: {result.output}"

                self.context_manager.add_message(
                    role="tool",
                    content=result_content,
                    importance=0.8,
                    provider=self.current_provider,
                    tool_call_id=tool_call_id
                )

        except Exception as tool_error:
            self.console.print(f"[bold red][!] Tool execution error: {escape(str(tool_error))}[/bold red]")
            self.context_manager.add_message(
                role="tool",
                content=f"Tool Execution Failed System Error: {str(tool_error)}",
                importance=1.0,
                provider=self.current_provider
            )
