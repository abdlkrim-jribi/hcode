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
from ..agents import AgentOrchestrator, AgentType
from .context import ContextManager
from .safety import SafetyGuard


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
        self.agent_orchestrator = AgentOrchestrator(
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

        self.current_provider: Optional[AIProvider] = None

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

            # Set system prompt with tool descriptions
            system_prompt = self._build_system_prompt()
            self.context_manager.set_system_prompt(system_prompt)

            # Add task to context
            self.context_manager.add_message(
                role="user",
                content=task,
                importance=1.0,
                provider=self.current_provider
            )

            # Execute with tool calling
            response = await self._execute_with_tools(stream=stream)

            # Add response to context
            self.context_manager.add_message(
                role="assistant",
                content=response,
                importance=0.8,
                provider=self.current_provider
            )

            self.safety_guard.commit_transaction()
            return response

        except Exception as e:
            self.safety_guard.rollback_transaction()
            raise e

    def _build_system_prompt(self) -> str:
        """Build system prompt with tool documentation"""
        base_prompt = self.current_provider.get_system_prompt_for_coding()

        # Add tool documentation
        base_prompt += "\n\n" + self.tool_manager.get_tool_documentation()

        return base_prompt

    async def _execute_with_tools(self, stream: bool = False) -> str:
        """Execute task with tool calling support"""
        # Get messages with context
        messages = self.context_manager.get_messages(
            max_tokens=self.current_provider.get_context_window() - self.current_provider.max_tokens
        )

        # Get tool schemas for provider
        provider_name = self.current_provider.get_provider_name().lower()
        tool_schemas = self.tool_manager.get_tool_schemas_for_provider(provider_name)

        # Generate completion
        if stream:
            response_parts = []
            stream_result = await self.current_provider.generate_completion(
                messages=messages,
                stream=True
            )

            async for chunk in stream_result:
                response_parts.append(chunk)
                print(chunk, end="", flush=True)

            print()  # New line
            return "".join(response_parts)
        else:
            response = await self.current_provider.generate_completion(
                messages=messages,
                stream=False
            )
            return response.content

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
            agent_types=[AgentType.EXPLORE],
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
        agent_types = [AgentType.PLAN]
        if explore_first:
            agent_types.insert(0, AgentType.EXPLORE)

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
            agent_types=[AgentType.EXPLORE, AgentType.PLAN, AgentType.IMPLEMENT],
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
