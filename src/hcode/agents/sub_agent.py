"""
Sub-agent system for Hcode.
Specialized agents for different types of tasks (Explore, Plan, etc.).
"""

import asyncio
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

from ..providers import AIProvider, Message, ProviderSelector
from ..tools.base_tool import ToolRegistry, ToolResult


class HcodeAgentType(Enum):
    """Types of specialized Hcode agents"""

    GENERAL = "general-purpose"
    EXPLORE = "Explore"
    PLAN = "Plan"
    IMPLEMENT = "Implement"
    TEST = "Test"
    DEBUG = "Debug"
    REFACTOR = "Refactor"


@dataclass
class HcodeAgentResult:
    """Result from Hcode sub-agent execution"""

    agent_type: HcodeAgentType
    success: bool
    output: str
    metadata: Dict[str, Any]
    error: Optional[str] = None


class HcodeSubAgent:
    """Base class for specialized Hcode sub-agents"""

    def __init__(
        self, agent_type: HcodeAgentType, provider: AIProvider, tool_registry: ToolRegistry
    ):
        """
        Initialize sub-agent.

        Args:
            agent_type: Type of specialized agent
            provider: AI provider to use
            tool_registry: Available tools
        """
        self.agent_type = agent_type
        self.provider = provider
        self.tool_registry = tool_registry
        self.conversation_history: List[Message] = []

    async def execute(self, task: str, context: Optional[Dict] = None) -> HcodeAgentResult:
        """
        Execute the agent's specialized task.

        Args:
            task: Task description
            context: Additional context

        Returns:
            HcodeAgentResult with execution results
        """
        raise NotImplementedError

    def _get_system_prompt(self) -> str:
        """Get agent-specific system prompt from external config"""
        from ..config.prompts import get_system_prompt

        # Get base prompt from config
        base_prompt = get_system_prompt("sub_agent")

        # Add available tools list
        base_prompt += "\n\nAvailable tools:\n"
        for tool in self.tool_registry.list_tools():
            base_prompt += f"\n- {tool.name}: {tool.get_description()}"

        base_prompt += "\n\nUse these tools to accomplish your task effectively."

        return base_prompt


class HcodeExploreAgent(HcodeSubAgent):
    """
    Agent specialized for exploring codebases.
    Fast searches, pattern matching, and codebase understanding.
    """

    def __init__(self, provider: AIProvider, tool_registry: ToolRegistry):
        super().__init__(HcodeAgentType.EXPLORE, provider, tool_registry)

    def _get_system_prompt(self) -> str:
        """Get explore agent prompt from external config"""
        from ..config.prompts import get_system_prompt

        return get_system_prompt("explore_agent") + super()._get_system_prompt()

    async def execute(self, task: str, context: Optional[Dict] = None) -> HcodeAgentResult:
        """Execute exploration task"""
        try:
            thoroughness = context.get("thoroughness", "medium") if context else "medium"

            # Build exploration prompt
            prompt = f"""Explore the codebase to answer: {task}

Thoroughness level: {thoroughness}

Use Glob and Grep tools to search systematically. Report findings clearly."""

            # Add to conversation
            self.conversation_history.append(Message(role="user", content=prompt))

            # Get system prompt
            system_prompt = self._get_system_prompt()
            messages = [Message(role="system", content=system_prompt)] + self.conversation_history

            # Execute with AI
            response = await self.provider.generate_completion(messages=messages, stream=False)

            # Parse tool calls and execute them (simplified)
            # In production, this would parse AI's tool requests and execute them

            return HcodeAgentResult(
                agent_type=self.agent_type,
                success=True,
                output=response.content,
                metadata={"thoroughness": thoroughness, "tokens_used": response.usage.total_tokens},
            )

        except Exception as e:
            return HcodeAgentResult(
                agent_type=self.agent_type, success=False, output="", metadata={}, error=str(e)
            )


class HcodePlanAgent(HcodeSubAgent):
    """
    Agent specialized for planning implementations.
    Creates detailed, step-by-step plans for complex tasks.
    """

    def __init__(self, provider: AIProvider, tool_registry: ToolRegistry):
        super().__init__(HcodeAgentType.PLAN, provider, tool_registry)

    def _get_system_prompt(self) -> str:
        """Get plan agent prompt from external config"""
        from ..config.prompts import get_system_prompt

        return get_system_prompt("plan_agent") + super()._get_system_prompt()

    async def execute(self, task: str, context: Optional[Dict] = None) -> HcodeAgentResult:
        """Create implementation plan"""
        try:
            # Explore codebase first if needed
            if context and context.get("explore_first", True):
                explore_agent = HcodeExploreAgent(self.provider, self.tool_registry)
                explore_result = await explore_agent.execute(
                    f"Understand the codebase structure for: {task}", {"thoroughness": "quick"}
                )
                codebase_context = explore_result.output
            else:
                codebase_context = "No prior exploration"

            # Build planning prompt
            prompt = f"""Create a detailed implementation plan for: {task}

Codebase context:
{codebase_context}

Provide:
1. High-level approach
2. Step-by-step breakdown
3. Files to create/modify
4. Dependencies and risks
5. Testing strategy
"""

            self.conversation_history.append(Message(role="user", content=prompt))

            # Get system prompt
            system_prompt = self._get_system_prompt()
            messages = [Message(role="system", content=system_prompt)] + self.conversation_history

            # Execute with AI
            response = await self.provider.generate_completion(messages=messages, stream=False)

            return HcodeAgentResult(
                agent_type=self.agent_type,
                success=True,
                output=response.content,
                metadata={
                    "tokens_used": response.usage.total_tokens,
                    "explored_first": context.get("explore_first", True) if context else True,
                },
            )

        except Exception as e:
            return HcodeAgentResult(
                agent_type=self.agent_type, success=False, output="", metadata={}, error=str(e)
            )


class HcodeImplementAgent(HcodeSubAgent):
    """
    Agent specialized for code implementation.
    Writes production-quality code based on plans.
    """

    def __init__(self, provider: AIProvider, tool_registry: ToolRegistry):
        super().__init__(HcodeAgentType.IMPLEMENT, provider, tool_registry)

    def _get_system_prompt(self) -> str:
        """Get code agent prompt from external config"""
        from ..config.prompts import get_system_prompt

        return get_system_prompt("code_agent") + super()._get_system_prompt()

    async def execute(self, task: str, context: Optional[Dict] = None) -> HcodeAgentResult:
        """Implement code based on plan"""
        try:
            plan = context.get("plan", "") if context else ""

            prompt = f"""Implement the following task: {task}

"""
            if plan:
                prompt += f"""Plan to follow:
{plan}

"""

            prompt += """Write production-quality code using the Write and Edit tools.
Include proper error handling, documentation, and tests."""

            self.conversation_history.append(Message(role="user", content=prompt))

            system_prompt = self._get_system_prompt()
            messages = [Message(role="system", content=system_prompt)] + self.conversation_history

            response = await self.provider.generate_completion(messages=messages, stream=False)

            return HcodeAgentResult(
                agent_type=self.agent_type,
                success=True,
                output=response.content,
                metadata={"tokens_used": response.usage.total_tokens, "had_plan": bool(plan)},
            )

        except Exception as e:
            return HcodeAgentResult(
                agent_type=self.agent_type, success=False, output="", metadata={}, error=str(e)
            )


class HcodeAgentOrchestrator:
    """
    Orchestrates multiple sub-agents working together.
    Coordinates parallel and sequential agent execution.
    """

    def __init__(self, provider_selector: ProviderSelector, tool_registry: ToolRegistry):
        """
        Initialize agent orchestrator.

        Args:
            provider_selector: Provider selector for choosing AI providers
            tool_registry: Available tools
        """
        self.provider_selector = provider_selector
        self.tool_registry = tool_registry

    async def execute_with_agents(
        self, task: str, agent_types: List[HcodeAgentType], parallel: bool = False
    ) -> List[HcodeAgentResult]:
        """
        Execute task using multiple agents.

        Args:
            task: Task description
            agent_types: Types of agents to use
            parallel: Execute agents in parallel

        Returns:
            List of agent results
        """
        # Select provider
        provider = self.provider_selector.select_provider()

        # Create agents
        agents = []
        for agent_type in agent_types:
            if agent_type == HcodeAgentType.EXPLORE:
                agents.append(HcodeExploreAgent(provider, self.tool_registry))
            elif agent_type == HcodeAgentType.PLAN:
                agents.append(HcodePlanAgent(provider, self.tool_registry))
            elif agent_type == HcodeAgentType.IMPLEMENT:
                agents.append(HcodeImplementAgent(provider, self.tool_registry))

        # Execute agents
        if parallel:
            # Parallel execution
            tasks = [agent.execute(task) for agent in agents]
            results = await asyncio.gather(*tasks)
        else:
            # Sequential execution with context passing
            results = []
            context = {}

            for agent in agents:
                result = await agent.execute(task, context)
                results.append(result)

                # Pass output to next agent
                if result.success:
                    if agent.agent_type == HcodeAgentType.EXPLORE:
                        context["exploration"] = result.output
                    elif agent.agent_type == HcodeAgentType.PLAN:
                        context["plan"] = result.output

        return results

    async def auto_execute(self, task: str) -> HcodeAgentResult:
        """
        Automatically determine and execute with appropriate agents.

        Args:
            task: Task description

        Returns:
            Final agent result
        """
        # Analyze task to determine agents needed
        if "explore" in task.lower() or "find" in task.lower() or "search" in task.lower():
            agent_types = [HcodeAgentType.EXPLORE]
        elif "plan" in task.lower():
            agent_types = [HcodeAgentType.EXPLORE, HcodeAgentType.PLAN]
        elif "implement" in task.lower() or "create" in task.lower() or "build" in task.lower():
            agent_types = [HcodeAgentType.EXPLORE, HcodeAgentType.PLAN, HcodeAgentType.IMPLEMENT]
        else:
            # Default: explore and plan
            agent_types = [HcodeAgentType.EXPLORE, HcodeAgentType.PLAN]

        # Execute agents sequentially
        results = await self.execute_with_agents(task, agent_types, parallel=False)

        # Return the last result (most complete)
        return (
            results[-1]
            if results
            else HcodeAgentResult(
                agent_type=HcodeAgentType.GENERAL,
                success=False,
                output="",
                metadata={},
                error="No agents executed",
            )
        )
