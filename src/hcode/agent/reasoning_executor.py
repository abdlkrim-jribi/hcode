"""
Reasoning-Driven Executor for HCode.

Integrates reasoning output with execution strategy:
- Uses reasoning phases to guide tool selection
- Validates execution against reasoning expectations
- Provides adaptive execution based on confidence
- Tracks reasoning-execution alignment
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .reasoning import (
    ReasoningOutput,
    AnalysisOutput,
    DecisionOutput,
    VerificationOutput,
)


class ExecutionStrategy(Enum):
    """Strategies for execution based on reasoning"""

    CONFIDENT = "confident"  # High confidence, execute directly
    CAUTIOUS = "cautious"  # Medium confidence, validate each step
    EXPLORATORY = "exploratory"  # Low confidence, gather more info first
    INTERACTIVE = "interactive"  # Requires user input


class ExecutionPhase(Enum):
    """Phases of reasoning-driven execution"""

    PLANNING = "planning"
    VALIDATION = "validation"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    ROLLBACK = "rollback"
    COMPLETE = "complete"


@dataclass
class ExecutionStep:
    """A single execution step derived from reasoning"""

    id: str
    description: str
    tool_name: str
    tool_params: Dict[str, Any]
    expected_outcome: str
    dependencies: List[str] = field(default_factory=list)
    confidence: float = 0.8
    is_reversible: bool = True
    rollback_action: Optional[Dict[str, Any]] = None
    executed: bool = False
    success: Optional[bool] = None
    result: Any = None
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """Plan derived from reasoning output"""

    steps: List[ExecutionStep]
    strategy: ExecutionStrategy
    estimated_duration: float  # seconds
    risk_level: str  # low, medium, high
    requires_user_approval: bool = False
    parallel_groups: List[List[str]] = field(default_factory=list)  # Steps that can run in parallel


@dataclass
class ExecutionResult:
    """Result of reasoning-driven execution"""

    plan: ExecutionPlan
    completed_steps: List[str]
    failed_steps: List[str]
    skipped_steps: List[str]
    total_duration: float
    success: bool
    error: Optional[str] = None
    rollback_performed: bool = False


class ReasoningToExecutionBridge:
    """
    Translates reasoning output to executable steps.
    """

    # Mapping from reasoning actions to tools
    ACTION_TO_TOOL = {
        "read": "readtool",
        "write": "writetool",
        "edit": "edittool",
        "search": "greptool",
        "find": "globtool",
        "execute": "bashtool",
        "run": "bashtool",
        "test": "bashtool",
        "ask": "askuserquestiontool",
        "fetch": "webfetchtool",
        "search_web": "websearchtool",
        "create": "writetool",
        "modify": "edittool",
        "delete": "bashtool",
        "list": "lstool",
    }

    def __init__(self):
        self._step_counter = 0

    def _generate_step_id(self) -> str:
        """Generate unique step ID"""
        self._step_counter += 1
        return f"step_{self._step_counter:04d}"

    def translate_reasoning(self, reasoning: ReasoningOutput) -> ExecutionPlan:
        """
        Translate reasoning output to execution plan.

        Args:
            reasoning: Complete reasoning output

        Returns:
            ExecutionPlan ready for execution
        """
        steps = []
        parallel_groups = []

        # Extract steps from different reasoning phases
        if reasoning.analysis:
            analysis_steps = self._extract_from_analysis(reasoning.analysis)
            steps.extend(analysis_steps)

        if reasoning.decision:
            decision_steps = self._extract_from_decision(reasoning.decision)
            steps.extend(decision_steps)

        if reasoning.verification:
            verification_steps = self._extract_from_verification(reasoning.verification)
            steps.extend(verification_steps)

        # Determine execution strategy
        strategy = self._determine_strategy(reasoning)

        # Identify parallel opportunities
        parallel_groups = self._identify_parallel_groups(steps)

        # Calculate risk level
        risk_level = self._assess_risk(steps, reasoning)

        # Check if user approval needed
        requires_approval = (
            strategy == ExecutionStrategy.INTERACTIVE
            or risk_level == "high"
            or any(not s.is_reversible for s in steps)
        )

        return ExecutionPlan(
            steps=steps,
            strategy=strategy,
            estimated_duration=self._estimate_duration(steps),
            risk_level=risk_level,
            requires_user_approval=requires_approval,
            parallel_groups=parallel_groups,
        )

    def _extract_from_analysis(self, analysis: AnalysisOutput) -> List[ExecutionStep]:
        """Extract steps from task analysis"""
        steps = []

        if not analysis.decomposition:
            return steps

        for i, item in enumerate(analysis.decomposition):
            # Parse action from decomposition item
            action, params = self._parse_action(item)
            if action:
                step = ExecutionStep(
                    id=self._generate_step_id(),
                    description=item,
                    tool_name=self.ACTION_TO_TOOL.get(action, "bashtool"),
                    tool_params=params,
                    expected_outcome=f"Complete: {item}",
                    confidence=analysis.confidence_score or 0.7,
                )
                steps.append(step)

        return steps

    def _extract_from_decision(self, decision: DecisionOutput) -> List[ExecutionStep]:
        """Extract steps from decision phase"""
        steps = []

        if not decision.action_items:
            return steps

        for item in decision.action_items:
            action, params = self._parse_action(item)
            if action:
                step = ExecutionStep(
                    id=self._generate_step_id(),
                    description=item,
                    tool_name=self.ACTION_TO_TOOL.get(action, "bashtool"),
                    tool_params=params,
                    expected_outcome=f"Action completed: {item}",
                    confidence=0.85,  # Decision phase = higher confidence
                )
                steps.append(step)

        return steps

    def _extract_from_verification(self, verification: VerificationOutput) -> List[ExecutionStep]:
        """Extract verification steps"""
        steps = []

        if verification.validation_steps:
            for item in verification.validation_steps:
                action, params = self._parse_action(item)
                if action:
                    step = ExecutionStep(
                        id=self._generate_step_id(),
                        description=f"Verify: {item}",
                        tool_name=self.ACTION_TO_TOOL.get(action, "readtool"),
                        tool_params=params,
                        expected_outcome=f"Verified: {item}",
                        confidence=0.9,
                        is_reversible=True,  # Verification steps are safe
                    )
                    steps.append(step)

        return steps

    def _parse_action(self, text: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Parse action and parameters from text.

        Returns:
            (action_name, parameters) tuple
        """
        import re

        text_lower = text.lower()
        params = {}

        # Find action verb
        for action in self.ACTION_TO_TOOL.keys():
            if action in text_lower:
                # Try to extract file paths
                file_match = re.search(
                    r"[\w/\\.-]+\.(?:py|js|ts|json|yaml|yml|md|txt|html|css)", text, re.IGNORECASE
                )
                if file_match:
                    params["file_path"] = file_match.group(0)

                # Try to extract patterns
                pattern_match = re.search(r'"([^"]+)"|\'([^\']+)\'', text)
                if pattern_match:
                    params["pattern"] = pattern_match.group(1) or pattern_match.group(2)

                # Try to extract commands
                if action in ["execute", "run", "test"]:
                    cmd_match = re.search(r"`([^`]+)`", text)
                    if cmd_match:
                        params["command"] = cmd_match.group(1)

                return action, params

        return None, {}

    def _determine_strategy(self, reasoning: ReasoningOutput) -> ExecutionStrategy:
        """Determine execution strategy from reasoning"""
        confidence = reasoning.quality_score()

        if confidence >= 0.8:
            return ExecutionStrategy.CONFIDENT
        elif confidence >= 0.5:
            return ExecutionStrategy.CAUTIOUS
        elif confidence >= 0.3:
            return ExecutionStrategy.EXPLORATORY
        else:
            return ExecutionStrategy.INTERACTIVE

    def _identify_parallel_groups(self, steps: List[ExecutionStep]) -> List[List[str]]:
        """Identify steps that can run in parallel"""
        # Build dependency graph
        groups = []
        remaining = set(s.id for s in steps)
        step_map = {s.id: s for s in steps}

        while remaining:
            # Find steps with no unresolved dependencies
            parallel = []
            for step_id in remaining:
                step = step_map[step_id]
                if all(dep not in remaining for dep in step.dependencies):
                    parallel.append(step_id)

            if parallel:
                groups.append(parallel)
                remaining -= set(parallel)
            else:
                # Circular dependency, add remaining sequentially
                groups.append(list(remaining))
                break

        return groups

    def _assess_risk(self, steps: List[ExecutionStep], reasoning: ReasoningOutput) -> str:
        """Assess overall risk level"""
        high_risk_tools = {"writetool", "edittool", "bashtool", "multiedittool"}

        risky_steps = sum(1 for s in steps if s.tool_name in high_risk_tools)
        irreversible = sum(1 for s in steps if not s.is_reversible)

        if irreversible > 0 or risky_steps > 5:
            return "high"
        elif risky_steps > 2:
            return "medium"
        else:
            return "low"

    def _estimate_duration(self, steps: List[ExecutionStep]) -> float:
        """Estimate execution duration in seconds"""
        # Rough estimates per tool type
        tool_times = {
            "readtool": 0.5,
            "writetool": 1.0,
            "edittool": 1.0,
            "greptool": 2.0,
            "globtool": 1.5,
            "bashtool": 5.0,
            "webfetchtool": 3.0,
            "websearchtool": 2.0,
        }

        return sum(tool_times.get(s.tool_name, 2.0) for s in steps)


class ReasoningDrivenExecutor:
    """
    Executes plans guided by reasoning output.

    Features:
    - Adaptive execution based on strategy
    - Step-by-step validation
    - Automatic rollback on failures
    - Progress tracking
    """

    def __init__(
        self,
        tool_executor: Any,  # ToolExecutor or similar
        on_step_start: Optional[Callable[[ExecutionStep], None]] = None,
        on_step_complete: Optional[Callable[[ExecutionStep, bool], None]] = None,
        on_rollback: Optional[Callable[[ExecutionStep], None]] = None,
    ):
        """
        Initialize executor.

        Args:
            tool_executor: Tool execution interface
            on_step_start: Callback when step starts
            on_step_complete: Callback when step completes (step, success)
            on_rollback: Callback when rollback occurs
        """
        self.tool_executor = tool_executor
        self.on_step_start = on_step_start
        self.on_step_complete = on_step_complete
        self.on_rollback = on_rollback

        self._bridge = ReasoningToExecutionBridge()
        self._execution_history: List[ExecutionResult] = []

    async def execute_with_refinement(
        self,
        initial_reasoning: ReasoningOutput,
        reasoning_manager: Any,  # EnhancedThinkingManager
        max_retries: int = 3,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute with automatic refinement loop on failure.
        
        If execution fails, it feeds the error back into the reasoning engine
        to generate a refined plan.
        """
        current_reasoning = initial_reasoning
        attempts = 0
        
        while attempts < max_retries:
            attempts += 1
            
            # Execute current plan
            result = await self.execute_from_reasoning(current_reasoning, **kwargs)
            
            if result.success:
                return result
                
            # If failed, check if we should refine
            if attempts >= max_retries:
                break
                
            # Trigger refinement
            # This assumes reasoning_manager has a method to refine based on feedback
            if hasattr(reasoning_manager, "refine_reasoning"):
                new_reasoning = await reasoning_manager.refine_reasoning(
                    previous_reasoning=current_reasoning,
                    execution_result=result
                )
                if new_reasoning:
                    current_reasoning = new_reasoning
                    continue
            
            break
            
        return result

    async def execute_from_reasoning(
        self,
        reasoning: ReasoningOutput,
        auto_approve: bool = False,
        approval_callback: Optional[Callable[[ExecutionPlan], bool]] = None,
    ) -> ExecutionResult:
        """
        Execute based on reasoning output.

        Args:
            reasoning: Reasoning output to execute
            auto_approve: Skip user approval
            approval_callback: Optional callback for approval

        Returns:
            ExecutionResult
        """
        # Translate reasoning to plan
        plan = self._bridge.translate_reasoning(reasoning)

        # Check if approval needed
        if plan.requires_user_approval and not auto_approve:
            if approval_callback:
                approved = approval_callback(plan)
                if not approved:
                    return ExecutionResult(
                        plan=plan,
                        completed_steps=[],
                        failed_steps=[],
                        skipped_steps=[s.id for s in plan.steps],
                        total_duration=0,
                        success=False,
                        error="User did not approve execution",
                    )
            else:
                # No callback, skip execution
                return ExecutionResult(
                    plan=plan,
                    completed_steps=[],
                    failed_steps=[],
                    skipped_steps=[s.id for s in plan.steps],
                    total_duration=0,
                    success=False,
                    error="Approval required but no callback provided",
                )

        # Execute plan
        return await self._execute_plan(plan)

    async def _execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute the plan according to strategy"""
        start_time = time.time()
        completed = []
        failed = []
        skipped = []

        step_map = {s.id: s for s in plan.steps}

        try:
            if plan.strategy == ExecutionStrategy.CONFIDENT:
                # Execute in parallel where possible
                for group in plan.parallel_groups:
                    results = await self._execute_parallel([step_map[sid] for sid in group])
                    for step_id, success in results.items():
                        if success:
                            completed.append(step_id)
                        else:
                            failed.append(step_id)

            elif plan.strategy == ExecutionStrategy.CAUTIOUS:
                # Execute sequentially with validation
                for step in plan.steps:
                    if self.on_step_start:
                        self.on_step_start(step)

                    success = await self._execute_step(step)

                    if self.on_step_complete:
                        self.on_step_complete(step, success)

                    if success:
                        completed.append(step.id)
                    else:
                        failed.append(step.id)
                        # In cautious mode, stop on first failure
                        skipped.extend(
                            s.id for s in plan.steps if s.id not in completed and s.id not in failed
                        )
                        break

            elif plan.strategy == ExecutionStrategy.EXPLORATORY:
                # Execute read-only steps first, then proceed cautiously
                read_only_tools = {"readtool", "greptool", "globtool", "lstool"}

                for step in plan.steps:
                    if step.tool_name in read_only_tools:
                        if self.on_step_start:
                            self.on_step_start(step)

                        success = await self._execute_step(step)

                        if self.on_step_complete:
                            self.on_step_complete(step, success)

                        if success:
                            completed.append(step.id)
                        else:
                            failed.append(step.id)
                    else:
                        skipped.append(step.id)

            else:  # INTERACTIVE
                # Return plan without execution
                skipped = [s.id for s in plan.steps]

            success = len(failed) == 0 and len(completed) > 0

            result = ExecutionResult(
                plan=plan,
                completed_steps=completed,
                failed_steps=failed,
                skipped_steps=skipped,
                total_duration=time.time() - start_time,
                success=success,
            )

            self._execution_history.append(result)
            return result

        except Exception as e:
            # Attempt rollback
            rollback_performed = await self._rollback(completed, step_map)

            return ExecutionResult(
                plan=plan,
                completed_steps=completed,
                failed_steps=failed,
                skipped_steps=[
                    s.id for s in plan.steps if s.id not in completed and s.id not in failed
                ],
                total_duration=time.time() - start_time,
                success=False,
                error=str(e),
                rollback_performed=rollback_performed,
            )

    async def _execute_step(self, step: ExecutionStep) -> bool:
        """Execute a single step"""
        try:
            result = await self.tool_executor.execute_tool(step.tool_name, **step.tool_params)

            step.executed = True
            step.success = result.success if hasattr(result, "success") else True
            step.result = result

            return step.success

        except Exception as e:
            step.executed = True
            step.success = False
            step.error = str(e)
            return False

    async def _execute_parallel(self, steps: List[ExecutionStep]) -> Dict[str, bool]:
        """Execute multiple steps in parallel"""
        results = {}

        async def execute_and_record(step: ExecutionStep):
            if self.on_step_start:
                self.on_step_start(step)

            success = await self._execute_step(step)

            if self.on_step_complete:
                self.on_step_complete(step, success)

            results[step.id] = success

        await asyncio.gather(*[execute_and_record(s) for s in steps])
        return results

    async def _rollback(
        self, completed_step_ids: List[str], step_map: Dict[str, ExecutionStep]
    ) -> bool:
        """Attempt to rollback completed steps"""
        rollback_success = True

        # Rollback in reverse order
        for step_id in reversed(completed_step_ids):
            step = step_map.get(step_id)
            if not step or not step.rollback_action:
                continue

            if self.on_rollback:
                self.on_rollback(step)

            try:
                await self.tool_executor.execute_tool(
                    step.rollback_action.get("tool", "bashtool"),
                    **step.rollback_action.get("params", {}),
                )
            except Exception:
                rollback_success = False

        return rollback_success

    def get_history(self) -> List[ExecutionResult]:
        """Get execution history"""
        return self._execution_history.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self._execution_history:
            return {"total_executions": 0, "success_rate": 0.0, "average_duration": 0.0}

        successful = sum(1 for r in self._execution_history if r.success)
        total_duration = sum(r.total_duration for r in self._execution_history)

        return {
            "total_executions": len(self._execution_history),
            "success_rate": successful / len(self._execution_history),
            "average_duration": total_duration / len(self._execution_history),
            "total_steps_completed": sum(len(r.completed_steps) for r in self._execution_history),
            "total_steps_failed": sum(len(r.failed_steps) for r in self._execution_history),
        }


# =============================================================================
# REASONING VALIDATOR
# =============================================================================


class ReasoningExecutionValidator:
    """
    Validates execution results against reasoning expectations.
    """

    def __init__(self):
        self._validation_history: List[Dict[str, Any]] = []

    def validate(self, reasoning: ReasoningOutput, result: ExecutionResult) -> Dict[str, Any]:
        """
        Validate execution result against reasoning.

        Args:
            reasoning: Original reasoning output
            result: Execution result

        Returns:
            Validation report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "reasoning_quality": reasoning.quality_score(),
            "execution_success": result.success,
            "alignment_score": 0.0,
            "issues": [],
            "recommendations": [],
        }

        # Check if execution matched reasoning confidence
        expected_success = reasoning.quality_score() > 0.5
        if expected_success != result.success:
            if expected_success:
                report["issues"].append("High-confidence reasoning led to failed execution")
                report["recommendations"].append(
                    "Review reasoning decomposition for missed edge cases"
                )
            else:
                report["issues"].append("Low-confidence reasoning unexpectedly succeeded")

        # Check step completion ratio
        total_steps = len(result.plan.steps)
        completed_ratio = len(result.completed_steps) / max(total_steps, 1)

        if completed_ratio < 0.5 and reasoning.quality_score() > 0.7:
            report["issues"].append(
                f"Only {completed_ratio:.0%} of steps completed despite high reasoning confidence"
            )

        # Calculate alignment score
        report["alignment_score"] = self._calculate_alignment(
            reasoning.quality_score(), completed_ratio, result.success
        )

        self._validation_history.append(report)
        return report

    def _calculate_alignment(
        self, reasoning_score: float, completion_ratio: float, success: bool
    ) -> float:
        """Calculate alignment between reasoning and execution"""
        # Perfect alignment: high reasoning -> high completion and success
        expected_completion = reasoning_score

        # Penalize mismatch
        completion_diff = abs(expected_completion - completion_ratio)
        success_match = 1.0 if (reasoning_score > 0.5) == success else 0.0

        return (1.0 - completion_diff) * 0.7 + success_match * 0.3

    def get_alignment_trend(self) -> float:
        """Get average alignment score over history"""
        if not self._validation_history:
            return 0.0
        return sum(v["alignment_score"] for v in self._validation_history) / len(
            self._validation_history
        )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ExecutionStrategy",
    "ExecutionPhase",
    "ExecutionStep",
    "ExecutionPlan",
    "ExecutionResult",
    "ReasoningToExecutionBridge",
    "ReasoningDrivenExecutor",
    "ReasoningExecutionValidator",
]
