"""
Agent-related tools for Hcode.
Includes Task (agent launcher), ExitPlanMode, and TodoRead tools.
"""

from typing import List

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class TaskTool(BaseTool):
    """
    Launches a new agent to handle complex, multi-step tasks autonomously.

    The Task tool launches specialized agents (subprocesses) that autonomously handle complex tasks.
    Each agent type has specific capabilities and tools available to it.

    Available agent types:
    - general-purpose: General-purpose agent for researching complex questions
    - Explore: Fast agent specialized for exploring codebases
    - Plan: Agent specialized for creating implementation plans
    - Implement: Agent for code implementation tasks
    """

    def __init__(self, agent_orchestrator=None):
        super().__init__()
        self.name = "Task"
        self.category = ToolCategory.AGENT
        self.agent_orchestrator = agent_orchestrator

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="subagent_type",
                type="string",
                description="The type of specialized agent to use for this task (general-purpose, Explore, Plan, Implement)",
                required=True,
            ),
            ToolParameter(
                name="prompt",
                type="string",
                description="The task for the agent to perform autonomously. Should include detailed instructions.",
                required=True,
            ),
            ToolParameter(
                name="description",
                type="string",
                description="A short (3-5 word) description of the task",
                required=True,
            ),
            ToolParameter(
                name="model",
                type="string",
                description="Optional model to use for this agent (sonnet, opus, haiku). If not specified, inherits from parent.",
                required=False,
            ),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        """Launch a specialized agent"""
        subagent_type = kwargs.get("subagent_type")
        prompt = kwargs.get("prompt")
        description = kwargs.get("description")
        model = kwargs.get("model")

        if not subagent_type or not prompt or not description:
            return ToolResult(
                success=False,
                output="",
                error="subagent_type, prompt, and description are required",
            )

        # Validate agent type
        valid_types = ["general-purpose", "Explore", "Plan", "Implement"]
        if subagent_type not in valid_types:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid subagent_type. Must be one of: {', '.join(valid_types)}",
            )

        try:
            if not self.agent_orchestrator:
                return ToolResult(
                    success=False, output="", error="Agent orchestrator not initialized"
                )

            # Launch agent
            from ..agents import AgentType

            # Map subagent_type to AgentType
            type_mapping = {
                "general-purpose": AgentType.GENERAL,
                "Explore": AgentType.EXPLORE,
                "Plan": AgentType.PLAN,
                "Implement": AgentType.IMPLEMENT,
            }

            agent_type = type_mapping.get(subagent_type, AgentType.GENERAL)

            # Execute agent task
            result = await self.agent_orchestrator.execute_agent_task(
                agent_type=agent_type,
                task=prompt,
                context={"description": description, "model": model},
            )

            return ToolResult(
                success=result.get("success", True),
                output=result.get("output", "Agent task completed"),
                metadata={
                    "agent_type": subagent_type,
                    "description": description,
                    "model": model,
                    "result": result,
                },
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to launch agent: {str(e)}")


class ExitPlanModeTool(BaseTool):
    """
    Use this tool when you are in plan mode and have finished presenting your plan
    and are ready to code.

    IMPORTANT: Only use this tool when the task requires planning the implementation
    steps of a task that requires writing code. For research tasks where you're gathering
    information, searching files, reading files or in general trying to understand the
    codebase - do NOT use this tool.
    """

    def __init__(self):
        super().__init__()
        self.name = "ExitPlanMode"
        self.category = ToolCategory.PLANNING

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan",
                type="string",
                description="The plan you came up with, that you want to run by the user for approval. Supports markdown. The plan should be pretty concise.",
                required=True,
            ),
        ]

    async def execute(self, plan: str) -> ToolResult:
        """Exit plan mode with the finalized plan"""
        if not plan:
            return ToolResult(success=False, output="", error="plan is required")

        # Format the plan for display
        output = f"""
# Implementation Plan

{plan}

---

**Ready to proceed with implementation.**

Would you like me to:
1. Start implementing this plan
2. Modify the plan
3. Cancel and reconsider

Please confirm to proceed.
"""

        return ToolResult(
            success=True,
            output=output,
            metadata={"plan": plan, "mode": "exit_plan", "awaiting_confirmation": True},
        )
