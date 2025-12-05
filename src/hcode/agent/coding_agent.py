"""
Coding agent with integrated ReAct loop and reasoning.

Combines thinking, planning, action, and observation in a continuous loop.
"""

from typing import Any, Dict, List, Optional, AsyncGenerator, TYPE_CHECKING

from hcode.agent.thinking import ThinkingPhase, ThinkingSession
from hcode.agent.thinking_manager import ThinkingManager
from hcode.agent.todo import TodoManager, TodoItem, TodoStatus
from hcode.config.thinking import ThinkingConfig
from hcode.config.prompts import get_system_prompt
from hcode.tools.tool_manager import ToolManager

# Avoid circular import - TodoWriteTool is imported lazily when needed
if TYPE_CHECKING:
    from ..tools.todo_write import TodoWriteTool


class ExecutionContext:
    """
    Context for agent execution.

    Tracks state throughout the ReAct loop.
    """

    def __init__(self):
        """Initialize execution context"""
        self.user_message: str = ""
        self.thinking_session: Optional[ThinkingSession] = None
        self.todos: List[TodoItem] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.observations: List[str] = []
        self.final_response: str = ""
        self.metadata: Dict[str, Any] = {}


class HcodeCodingAgent:
    """
    Coding agent with ReAct loop.

    Implements: THINK → PLAN → ACT → OBSERVE → UPDATE → REPEAT
    """

    # System prompt for the agent - loaded from config
    SYSTEM_PROMPT = get_system_prompt("react_coding_agent")

    def __init__(
        self,
        llm_client: Any,
        tool_manager: Optional[ToolManager] = None,
        thinking_config: Optional[ThinkingConfig] = None,
        thinking_manager: Optional[ThinkingManager] = None,
        todo_manager: Optional[TodoManager] = None,
    ):
        """
        Initialize coding agent.

        Args:
            llm_client: LLM client for generation
            tool_manager: Tool manager instance
            thinking_config: Thinking configuration
            thinking_manager: Thinking manager instance
            todo_manager: Todo manager instance
        """
        self.llm_client = llm_client
        self.tool_manager = tool_manager or ToolManager()
        self.thinking_config = thinking_config or ThinkingConfig()
        self.thinking_manager = thinking_manager or ThinkingManager(
            self.thinking_config, llm_client
        )
        self.todo_manager = todo_manager or TodoManager()

        # Register TodoWrite tool (lazy import to avoid circular dependency)
        from ..tools.todo_write import TodoWriteTool

        todo_tool = TodoWriteTool(self.todo_manager)
        self.tool_manager.register_tool(todo_tool)

    async def execute(
        self, user_message: str, context: Optional[ExecutionContext] = None
    ) -> ExecutionContext:
        """
        Execute agent with ReAct loop.

        Args:
            user_message: User's request
            context: Optional execution context

        Returns:
            Execution context with results
        """
        # Initialize context
        ctx = context or ExecutionContext()
        ctx.user_message = user_message

        # PHASE 1: THINK
        if self.thinking_config.should_think(user_message):
            ctx.thinking_session = await self.thinking_manager.think(
                user_message, context=ctx.metadata
            )

        # PHASE 2: PLAN
        # Agent should use TodoWrite to create plan
        # This happens through LLM interaction

        # PHASE 3-6: ACT → OBSERVE → UPDATE → REPEAT
        # NO HARD LIMIT - continue until task completion
        iteration = 0

        while True:
            iteration += 1

            # Check if we're done
            if self._is_complete(ctx):
                break

            # Get next action from LLM
            action = await self._get_next_action(ctx)

            if action["type"] == "tool_call":
                # Execute tool
                result = await self._execute_tool(action)
                ctx.tool_calls.append({"action": action, "result": result})

                # Observe results
                observation = self._create_observation(result)
                ctx.observations.append(observation)

            elif action["type"] == "response":
                # Final response
                ctx.final_response = action["content"]
                break

            elif action["type"] == "think":
                # Additional thinking
                block = await self.thinking_manager._think_phase(
                    action["prompt"], ThinkingPhase.REASONING, ctx.metadata
                )
                if ctx.thinking_session:
                    ctx.thinking_session.add_block(block)

        return ctx

    async def stream_execute(self, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream execution with real-time updates.

        Args:
            user_message: User's request

        Yields:
            Execution events (thinking, todos, tool_calls, response)
        """
        ctx = ExecutionContext()
        ctx.user_message = user_message

        # Stream thinking if enabled
        if self.thinking_config.should_think(user_message):
            async for block in self.thinking_manager.stream_thinking(
                user_message, context=ctx.metadata
            ):
                yield {"type": "thinking", "block": block.to_dict()}

        # Execute with streaming
        # NO HARD LIMIT - continue until task completion
        iteration = 0

        while True:
            iteration += 1

            if self._is_complete(ctx):
                break

            action = await self._get_next_action(ctx)

            # Yield action
            yield {"type": "action", "action": action}

            if action["type"] == "tool_call":
                result = await self._execute_tool(action)
                ctx.tool_calls.append({"action": action, "result": result})

                # Yield result
                yield {"type": "tool_result", "result": result}

                observation = self._create_observation(result)
                ctx.observations.append(observation)

            elif action["type"] == "response":
                ctx.final_response = action["content"]
                yield {"type": "response", "content": action["content"]}
                break

        # Yield final context
        yield {
            "type": "complete",
            "context": {
                "tool_calls": len(ctx.tool_calls),
                "observations": len(ctx.observations),
                "todos": self.todo_manager.get_progress(),
            },
        }

    async def _get_next_action(self, ctx: ExecutionContext) -> Dict[str, Any]:
        """
        Get next action from LLM.

        Args:
            ctx: Execution context

        Returns:
            Action dictionary
        """
        # Build prompt with context
        prompt = self._build_action_prompt(ctx)

        # Get LLM response
        from hcode.config.defaults import get_agent_temperature
        
        response = await self.llm_client.generate(
            prompt=prompt,
            system=self.SYSTEM_PROMPT,
            tools=self.tool_manager.get_tool_schemas(),
            temperature=get_agent_temperature("coding"),
        )

        # Parse response into action
        return self._parse_action(response)

    def _build_action_prompt(self, ctx: ExecutionContext) -> str:
        """
        Build prompt for next action.

        Args:
            ctx: Execution context

        Returns:
            Prompt string
        """
        parts = ["User request:", ctx.user_message, ""]

        # Add thinking summary if available
        if ctx.thinking_session:
            parts.extend(["Thinking summary:", ctx.thinking_session.get_summary(), ""])

        # Add current todos
        if self.todo_manager.todos:
            parts.append("Current todos:")
            for todo in self.todo_manager.todos:
                parts.append(str(todo))
            parts.append("")

        # Add recent observations
        if ctx.observations:
            parts.append("Recent observations:")
            for obs in ctx.observations[-3:]:
                parts.append(f"- {obs}")
            parts.append("")

        parts.append("What is the next action?")

        return "\n".join(parts)

    def _parse_action(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse LLM response into action.

        Args:
            response: LLM response

        Returns:
            Action dictionary
        """
        # Check for tool calls
        if "tool_calls" in response and response["tool_calls"]:
            tool_call = response["tool_calls"][0]
            return {
                "type": "tool_call",
                "tool": tool_call["name"],
                "parameters": tool_call["parameters"],
            }

        # Check for thinking request
        content = response.get("content", "")
        if "<think>" in content:
            # Extract thinking prompt
            start = content.index("<think>") + 7
            end = content.index("</think>") if "</think>" in content else len(content)
            think_prompt = content[start:end].strip()

            return {"type": "think", "prompt": think_prompt}

        # Default: response
        return {"type": "response", "content": content}

    async def _execute_tool(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool call.

        Args:
            action: Tool action

        Returns:
            Tool result
        """
        tool_name = action["tool"]
        parameters = action["parameters"]

        try:
            result = await self.tool_manager.execute_tool(tool_name, **parameters)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_observation(self, result: Dict[str, Any]) -> str:
        """
        Create observation from tool result.

        Args:
            result: Tool result

        Returns:
            Observation string
        """
        if result.get("success"):
            return f"Tool succeeded: {str(result.get('result', ''))[:100]}"
        else:
            return f"Tool failed: {result.get('error', 'Unknown error')}"

    def _is_complete(self, ctx: ExecutionContext) -> bool:
        """
        Check if execution is complete.

        Args:
            ctx: Execution context

        Returns:
            True if complete
        """
        # Check if all todos are completed
        if self.todo_manager.todos:
            all_done = all(
                todo.status in [TodoStatus.COMPLETED, TodoStatus.SKIPPED]
                for todo in self.todo_manager.todos
            )
            return all_done

        # Check if we have a final response
        return bool(ctx.final_response)
