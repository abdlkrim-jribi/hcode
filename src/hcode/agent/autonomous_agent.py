"""
Autonomous Coding Agent.

Extends HcodeCodingAgent with autonomous execution capabilities,
matching Claude Code's behavior for auto, plan, and interactive modes.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional, AsyncGenerator, Callable

from .autonomous import (
    AutonomousEngine,
    ActionProposal,
    ExecutionDecision,
    ExecutionResult,
)
from .coding_agent import HcodeCodingAgent, ExecutionContext
from .modes import AgentMode, SafetyConfig, get_mode_config


@dataclass
class HcodeAutonomousExecutionContext(ExecutionContext):
    """Extended context for autonomous execution"""

    mode: AgentMode = AgentMode.INTERACTIVE
    actions_executed: int = 0
    actions_confirmed: int = 0
    actions_skipped: int = 0
    plan_displayed: bool = False
    plan_approved: bool = False


class HcodeAutonomousCodingAgent(HcodeCodingAgent):
    """
    HcodeCodingAgent with autonomous execution capabilities.

    Features:
    - Multiple operation modes (interactive, auto, plan, review)
    - Smart decision-making about when to ask permission
    - Safety guards for dangerous operations
    - Plan creation and approval workflow
    - Error recovery with retries
    """

    AUTONOMOUS_SYSTEM_PROMPT = """You are an autonomous coding assistant with advanced execution capabilities.

OPERATION MODES:
- INTERACTIVE: Ask permission before each action (safest)
- AUTO: Execute automatically, only ask for dangerous operations
- PLAN: Create plan first, then execute automatically
- REVIEW: Show plan, get approval, then execute

CURRENT MODE: {mode}

AUTONOMOUS BEHAVIOR:
1. In AUTO mode:
   - Execute read operations immediately
   - Execute safe file edits without asking
   - Ask permission only for dangerous operations (rm, git push --force, etc.)
   - Track your progress with TodoWrite

2. In PLAN mode:
   - First, create a complete execution plan
   - Show the plan to user
   - Execute all planned actions automatically
   - Report progress and results

3. In REVIEW mode:
   - Create and show plan
   - Wait for user approval
   - Then execute automatically

SAFETY RULES (Always Apply):
- Never execute destructive commands without confirmation
- Protected files (.env, package.json, etc.) require confirmation
- git push --force, rm -rf, DROP TABLE always require confirmation
- If in doubt, ask for confirmation

EXECUTION PATTERN:
1. Analyze the task
2. Create plan using TodoWrite
3. Execute each step:
   - Mark todo as in_progress
   - Execute the action
   - Mark todo as completed
4. Report final results

{additional_context}

Remember: Be efficient in auto mode, but never sacrifice safety."""

    def __init__(
        self,
        *args,
        mode: AgentMode = AgentMode.INTERACTIVE,
        safety_config: Optional[SafetyConfig] = None,
            **kwargs,
    ):
        """
        Initialize autonomous coding agent.

        Args:
            *args: Arguments for HcodeCodingAgent
            mode: Initial operation mode
            safety_config: Safety configuration
            **kwargs: Keyword arguments for HcodeCodingAgent
        """
        super().__init__(*args, **kwargs)

        self.mode = mode
        self.safety_config = safety_config or SafetyConfig()

        # Create autonomous engine
        self.autonomous_engine = AutonomousEngine(mode=mode, safety_config=self.safety_config)

        # Callbacks
        self._confirmation_callback: Optional[Callable[[str], bool]] = None
        self._progress_callback: Optional[Callable[[str, float], None]] = None
        self._display_callback: Optional[Callable[[str], None]] = None
        self._mode_change_callback: Optional[Callable[[AgentMode], None]] = None

    # ============================================================
    # MODE MANAGEMENT
    # ============================================================

    def set_mode(self, mode: AgentMode):
        """Change operation mode"""
        old_mode = self.mode
        self.mode = mode
        self.autonomous_engine.set_mode(mode)

        if self._mode_change_callback:
            self._mode_change_callback(mode)

        if self._display_callback:
            mode_config = get_mode_config(mode)
            self._display_callback(
                f"Mode changed: {old_mode.value} → {mode.value}\n" f"  {mode_config.description}"
            )

    def get_mode(self) -> AgentMode:
        """Get current mode"""
        return self.mode

    def is_auto_mode(self) -> bool:
        """Check if in auto or plan mode"""
        return self.mode in [AgentMode.AUTO, AgentMode.PLAN]

    def toggle_mode(self):
        """Toggle between interactive and auto modes"""
        if self.mode == AgentMode.INTERACTIVE:
            self.set_mode(AgentMode.AUTO)
        else:
            self.set_mode(AgentMode.INTERACTIVE)

    # ============================================================
    # CALLBACKS
    # ============================================================

    def set_confirmation_callback(self, callback: Callable[[str], bool]):
        """Set callback for user confirmations"""
        self._confirmation_callback = callback
        self.autonomous_engine.set_confirmation_callback(callback)

    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """Set callback for progress updates"""
        self._progress_callback = callback
        self.autonomous_engine.set_progress_callback(callback)

    def set_display_callback(self, callback: Callable[[str], None]):
        """Set callback for displaying messages"""
        self._display_callback = callback
        self.autonomous_engine.set_display_callback(callback)

    def set_mode_change_callback(self, callback: Callable[[AgentMode], None]):
        """Set callback for mode changes"""
        self._mode_change_callback = callback

    # ============================================================
    # AUTONOMOUS EXECUTION
    # ============================================================

    async def execute_autonomous(
            self, user_message: str, context: Optional[HcodeAutonomousExecutionContext] = None
    ) -> HcodeAutonomousExecutionContext:
        """
        Execute with autonomous capabilities.

        Args:
            user_message: User's request
            context: Optional execution context

        Returns:
            Execution context with results
        """
        # Initialize context
        ctx = context or HcodeAutonomousExecutionContext(mode=self.mode)
        ctx.user_message = user_message

        # Reset engine for new task
        self.autonomous_engine.reset_context()

        # PHASE 1: THINKING (if enabled)
        if self.thinking_config.should_think(user_message):
            ctx.thinking_session = await self.thinking_manager.think(
                user_message, context=ctx.metadata
            )

        # PHASE 2: PLANNING (in plan/review modes)
        if self.autonomous_engine.should_show_plan():
            await self._create_and_show_plan(ctx)

            # Wait for approval in review mode
            if self.autonomous_engine.needs_plan_approval():
                approved = await self.autonomous_engine.confirm_plan()
                ctx.plan_approved = approved

                if not approved:
                    ctx.final_response = "Plan rejected by user."
                    return ctx

        # PHASE 3-6: EXECUTE with autonomous decision-making
        # NO HARD LIMIT - continue until task completion
        iteration = 0

        while True:
            iteration += 1

            # Check completion
            if self._is_complete(ctx):
                break

            # Get next action from LLM
            action = await self._get_next_action(ctx)

            if action["type"] == "tool_call":
                # Create action proposal
                proposal = self._create_proposal(action)

                # Decide whether to execute
                decision = self.autonomous_engine.decide_execution(proposal)

                if decision == ExecutionDecision.EXECUTE:
                    # Execute immediately
                    result = await self._execute_tool_autonomous(action, proposal)
                    ctx.tool_calls.append({"action": action, "result": result, "confirmed": False})
                    ctx.actions_executed += 1

                elif decision == ExecutionDecision.CONFIRM:
                    # Ask for confirmation
                    confirmed = await self.autonomous_engine.confirm_action(proposal)

                    if confirmed:
                        result = await self._execute_tool_autonomous(action, proposal)
                        ctx.tool_calls.append(
                            {"action": action, "result": result, "confirmed": True}
                        )
                        ctx.actions_executed += 1
                        ctx.actions_confirmed += 1
                    else:
                        ctx.actions_skipped += 1
                        ctx.observations.append(
                            f"Skipped: {proposal.tool_name} - {proposal.reason}"
                        )

                elif decision == ExecutionDecision.SKIP:
                    ctx.actions_skipped += 1

                elif decision == ExecutionDecision.ABORT:
                    ctx.final_response = "Execution aborted for safety."
                    break

                # Update progress
                self._update_progress(ctx)

            elif action["type"] == "response":
                ctx.final_response = action["content"]
                break

            elif action["type"] == "think":
                # Additional thinking
                from .thinking import ThinkingPhase

                block = await self.thinking_manager._think_phase(
                    action["prompt"], ThinkingPhase.REASONING, ctx.metadata
                )
                if ctx.thinking_session:
                    ctx.thinking_session.add_block(block)

        return ctx

    async def stream_execute_autonomous(
            self, user_message: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream autonomous execution with real-time updates.

        Args:
            user_message: User's request

        Yields:
            Execution events
        """
        ctx = HcodeAutonomousExecutionContext(mode=self.mode)
        ctx.user_message = user_message

        # Yield mode info
        yield {
            "type": "mode",
            "mode": self.mode.value,
            "description": get_mode_config(self.mode).description,
        }

        # Reset engine
        self.autonomous_engine.reset_context()

        # Stream thinking if enabled
        if self.thinking_config.should_think(user_message):
            async for block in self.thinking_manager.stream_thinking(
                    user_message, context=ctx.metadata
            ):
                yield {"type": "thinking", "block": block.to_dict()}

        # Plan phase
        if self.autonomous_engine.should_show_plan():
            yield {"type": "planning", "status": "creating"}

            await self._create_and_show_plan(ctx)

            yield {"type": "plan", "content": self.autonomous_engine.format_plan_display()}

            if self.autonomous_engine.needs_plan_approval():
                yield {"type": "awaiting_approval"}

                approved = await self.autonomous_engine.confirm_plan()
                ctx.plan_approved = approved

                yield {"type": "plan_approval", "approved": approved}

                if not approved:
                    yield {"type": "response", "content": "Plan rejected."}
                    return

        # Execute with streaming
        # NO HARD LIMIT - continue until task completion
        iteration = 0

        while True:
            iteration += 1

            if self._is_complete(ctx):
                break

            action = await self._get_next_action(ctx)

            if action["type"] == "tool_call":
                proposal = self._create_proposal(action)
                decision = self.autonomous_engine.decide_execution(proposal)

                yield {
                    "type": "decision",
                    "tool": proposal.tool_name,
                    "risk": proposal.risk_level,
                    "decision": decision.value,
                }

                if decision == ExecutionDecision.EXECUTE:
                    yield {
                        "type": "executing",
                        "tool": proposal.tool_name,
                        "reason": proposal.reason,
                    }

                    result = await self._execute_tool_autonomous(action, proposal)
                    ctx.tool_calls.append({"action": action, "result": result, "confirmed": False})
                    ctx.actions_executed += 1

                    yield {
                        "type": "tool_result",
                        "success": result.success,
                        "output": result.output[:500] if result.success else result.error,
                    }

                elif decision == ExecutionDecision.CONFIRM:
                    yield {
                        "type": "confirm_required",
                        "tool": proposal.tool_name,
                        "reason": proposal.reason,
                        "risk": proposal.risk_level,
                    }

                    confirmed = await self.autonomous_engine.confirm_action(proposal)

                    yield {"type": "confirmed", "approved": confirmed}

                    if confirmed:
                        result = await self._execute_tool_autonomous(action, proposal)
                        ctx.tool_calls.append(
                            {"action": action, "result": result, "confirmed": True}
                        )
                        ctx.actions_executed += 1
                        ctx.actions_confirmed += 1

                        yield {
                            "type": "tool_result",
                            "success": result.success,
                            "output": result.output[:500] if result.success else result.error,
                        }
                    else:
                        ctx.actions_skipped += 1

                elif decision == ExecutionDecision.SKIP:
                    ctx.actions_skipped += 1
                    yield {"type": "skipped", "tool": proposal.tool_name}

                elif decision == ExecutionDecision.ABORT:
                    yield {"type": "aborted", "reason": "Safety abort"}
                    break

            elif action["type"] == "response":
                ctx.final_response = action["content"]
                yield {"type": "response", "content": action["content"]}
                break

        # Final statistics
        yield {
            "type": "complete",
            "stats": {
                "mode": self.mode.value,
                "executed": ctx.actions_executed,
                "confirmed": ctx.actions_confirmed,
                "skipped": ctx.actions_skipped,
                "todos": self.todo_manager.get_progress(),
            },
        }

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _create_proposal(self, action: Dict[str, Any]) -> ActionProposal:
        """Create action proposal from LLM action"""
        tool_name = action.get("tool", "")
        parameters = action.get("parameters", {})

        # Determine reason from context
        reason = parameters.get("description", f"Execute {tool_name}")

        return ActionProposal(tool_name=tool_name, arguments=parameters, reason=reason)

    async def _execute_tool_autonomous(
            self, action: Dict[str, Any], proposal: ActionProposal
    ) -> ExecutionResult:
        """Execute tool with error handling and retries"""
        tool_name = action["tool"]
        parameters = action["parameters"]

        # Safety check
        is_safe, reason = self.autonomous_engine.check_safety(tool_name, parameters)
        if not is_safe:
            return ExecutionResult(success=False, output="", error=f"Safety check failed: {reason}")

        # Execute with retries
        max_retries = 3
        retry_delays = [1, 2, 5]

        for attempt in range(max_retries):
            try:
                import time

                start_time = time.time()

                result = await self.tool_manager.execute_tool(tool_name, **parameters)

                duration = time.time() - start_time

                # Track success
                self.autonomous_engine.track_action(proposal, True)

                return ExecutionResult(
                    success=True, output=str(result), duration=duration, retries=attempt
                )

            except Exception as e:
                if attempt < max_retries - 1:
                    # Wait before retry
                    await asyncio.sleep(retry_delays[attempt])
                else:
                    # Final failure
                    self.autonomous_engine.track_action(proposal, False)

                    return ExecutionResult(
                        success=False, output="", error=str(e), retries=attempt + 1
                    )

        # Should not reach here
        return ExecutionResult(success=False, output="", error="Unknown error")

    async def _create_and_show_plan(self, ctx: HcodeAutonomousExecutionContext):
        """Create execution plan"""
        # Use LLM to generate plan
        plan_prompt = f"""Create an execution plan for this task:

{ctx.user_message}

Generate a step-by-step plan with:
1. What actions to take
2. Files to modify
3. Commands to run

Use TodoWrite to create the plan."""

        # Get plan from LLM
        response = await self.llm_client.generate(
            prompt=plan_prompt,
            system=self._get_system_prompt(),
            tools=self.tool_manager.get_tool_schemas(),
            temperature=0.5,
        )

        # Process any tool calls (like TodoWrite)
        if "tool_calls" in response and response["tool_calls"]:
            for tool_call in response["tool_calls"]:
                await self.tool_manager.execute_tool(tool_call["name"], **tool_call["parameters"])

        ctx.plan_displayed = True

    def _update_progress(self, ctx: HcodeAutonomousExecutionContext):
        """Update progress callback"""
        if self._progress_callback:
            total = ctx.actions_executed + ctx.actions_skipped
            if total > 0:
                # Use todo progress if available
                progress = self.todo_manager.get_progress()
                pct = progress.get("completion_percentage", 0)
                message = f"Actions: {ctx.actions_executed} executed, {ctx.actions_skipped} skipped"
                self._progress_callback(message, pct / 100)

    def _get_system_prompt(self) -> str:
        """Get system prompt with mode context"""
        additional = ""

        if self.mode == AgentMode.AUTO:
            additional = """
CURRENT CONTEXT: AUTO MODE
- Execute most actions without asking
- Only confirm dangerous operations
- Be efficient and proactive"""

        elif self.mode == AgentMode.PLAN:
            additional = """
CURRENT CONTEXT: PLAN MODE
- First create a complete plan
- Show the plan before executing
- Then execute automatically"""

        elif self.mode == AgentMode.REVIEW:
            additional = """
CURRENT CONTEXT: REVIEW MODE
- Create a complete plan
- Wait for user approval
- Then execute automatically"""

        return self.AUTONOMOUS_SYSTEM_PROMPT.format(
            mode=self.mode.value.upper(), additional_context=additional
        )

    def _build_action_prompt(self, ctx: ExecutionContext) -> str:
        """Build prompt with mode awareness"""
        parts = [f"[MODE: {self.mode.value.upper()}]", ""]
        parts.append(super()._build_action_prompt(ctx))

        if self.is_auto_mode():
            parts.append("")
            parts.append("Remember: Execute safe operations automatically.")

        return "\n".join(parts)

    # ============================================================
    # STATISTICS
    # ============================================================

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        engine_stats = self.autonomous_engine.get_statistics()

        return {
            **engine_stats,
            "thinking_enabled": self.thinking_config.enabled,
            "todo_progress": self.todo_manager.get_progress(),
        }
