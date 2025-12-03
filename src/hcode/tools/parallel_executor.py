"""
Parallel Tool Executor for Hcode.
Supports concurrent tool execution with proper dependency management.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from .base_tool import BaseTool, ToolResult, ToolRegistry


class ExecutionStatus(Enum):
    """Tool execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolCall:
    """Represents a single tool call"""
    id: str
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: Set[str] = field(default_factory=set)
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[ToolResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """Execution plan for multiple tool calls"""
    id: str
    tool_calls: List[ToolCall]
    parallel_groups: List[List[str]]  # Groups of tool IDs that can run in parallel
    created_at: datetime
    completed_at: Optional[datetime] = None


class ParallelToolExecutor:
    """
    Execute tools in parallel when possible, respecting dependencies.

    Features:
    - Automatic dependency detection
    - Parallel execution optimization
    - Progress tracking
    - Error handling with partial results
    - Execution planning and visualization
    """

    def __init__(self, tool_registry: ToolRegistry, max_parallel: int = 5):
        """
        Initialize parallel executor.

        Args:
            tool_registry: Registry containing available tools
            max_parallel: Maximum number of parallel executions
        """
        self.tool_registry = tool_registry
        self.max_parallel = max_parallel
        self.execution_history: List[ExecutionPlan] = []
        self.active_executions: Dict[str, ToolCall] = {}

    async def execute_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
        auto_detect_dependencies: bool = True
    ) -> List[ToolResult]:
        """
        Execute multiple tool calls in parallel when possible.

        Args:
            tool_calls: List of tool call specifications
            auto_detect_dependencies: Automatically detect dependencies

        Returns:
            List of results in the same order as input
        """
        # Create execution plan
        plan = self._create_execution_plan(tool_calls, auto_detect_dependencies)
        self.execution_history.append(plan)

        # Execute plan
        results = await self._execute_plan(plan)

        # Mark plan as completed
        plan.completed_at = datetime.now()

        return results

    def _create_execution_plan(
        self,
        tool_calls_spec: List[Dict[str, Any]],
        auto_detect_dependencies: bool
    ) -> ExecutionPlan:
        """Create execution plan with dependency analysis"""
        plan_id = str(uuid.uuid4())
        tool_calls = []

        # Create ToolCall objects
        for spec in tool_calls_spec:
            call = ToolCall(
                id=str(uuid.uuid4()),
                tool_name=spec.get("tool"),
                parameters=spec.get("parameters", {}),
                dependencies=set(spec.get("dependencies", []))
            )
            tool_calls.append(call)

        # Auto-detect dependencies if enabled
        if auto_detect_dependencies:
            self._detect_dependencies(tool_calls)

        # Create parallel execution groups
        parallel_groups = self._create_parallel_groups(tool_calls)

        return ExecutionPlan(
            id=plan_id,
            tool_calls=tool_calls,
            parallel_groups=parallel_groups,
            created_at=datetime.now()
        )

    def _detect_dependencies(self, tool_calls: List[ToolCall]):
        """
        Automatically detect dependencies between tool calls.

        Rules:
        - Write operations on the same file must be sequential
        - Read after write must be sequential
        - Tool calls that reference output of previous calls
        """
        for i, call in enumerate(tool_calls):
            for j in range(i):
                prev_call = tool_calls[j]

                # Check file operation dependencies
                if self._has_file_dependency(prev_call, call):
                    call.dependencies.add(prev_call.id)

                # Check output dependencies
                if self._has_output_dependency(prev_call, call):
                    call.dependencies.add(prev_call.id)

    def _has_file_dependency(self, call1: ToolCall, call2: ToolCall) -> bool:
        """Check if two calls have file operation dependencies"""
        file_tools = {"readtool", "writetool", "edittool"}

        if call1.tool_name.lower() not in file_tools:
            return False
        if call2.tool_name.lower() not in file_tools:
            return False

        # Get file paths
        path1 = call1.parameters.get("file_path", "")
        path2 = call2.parameters.get("file_path", "")

        if not path1 or not path2:
            return False

        # Same file operations must be sequential
        if path1 == path2:
            # Write operations must be sequential
            if call1.tool_name.lower() in ["writetool", "edittool"]:
                return True
            # Read after write must be sequential
            if call2.tool_name.lower() == "readtool":
                return True

        return False

    def _has_output_dependency(self, call1: ToolCall, call2: ToolCall) -> bool:
        """Check if call2 depends on output of call1"""
        # Check if call2 parameters reference call1's output
        # This is a simplified check - in production, you'd have more sophisticated analysis

        # For now, check if parameters contain references like ${tool_id} or similar
        params_str = json.dumps(call2.parameters)
        return f"${{{call1.id}}}" in params_str or f"$tool_{call1.id}" in params_str

    def _create_parallel_groups(self, tool_calls: List[ToolCall]) -> List[List[str]]:
        """
        Create groups of tool calls that can execute in parallel.

        Uses topological sorting to identify parallel execution opportunities.
        """
        # Build dependency graph
        graph = {call.id: call.dependencies for call in tool_calls}
        in_degree = {call.id: 0 for call in tool_calls}

        for deps in graph.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        # Topological sort with level tracking
        groups = []
        while in_degree:
            # Find all nodes with no dependencies
            current_group = [
                node for node, degree in in_degree.items() if degree == 0
            ]

            if not current_group:
                # Circular dependency detected
                raise ValueError("Circular dependency detected in tool calls")

            groups.append(current_group)

            # Remove processed nodes
            for node in current_group:
                del in_degree[node]
                # Update in-degrees
                for other_node in in_degree:
                    if node in graph.get(other_node, set()):
                        in_degree[other_node] -= 1

        return groups

    async def _execute_plan(self, plan: ExecutionPlan) -> List[ToolResult]:
        """Execute the plan with parallel groups"""
        results_map = {}

        for group in plan.parallel_groups:
            # Get tool calls for this group
            group_calls = [
                call for call in plan.tool_calls if call.id in group
            ]

            # Execute group in parallel
            group_results = await self._execute_group(group_calls)

            # Store results
            for call, result in zip(group_calls, group_results):
                results_map[call.id] = result
                call.result = result
                call.status = ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED
                call.completed_at = datetime.now()

        # Return results in original order
        return [results_map[call.id] for call in plan.tool_calls]

    async def _execute_group(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute a group of tool calls in parallel"""
        # Limit parallelism
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def execute_with_semaphore(call: ToolCall) -> ToolResult:
            async with semaphore:
                return await self._execute_single(call)

        # Execute all calls in parallel
        tasks = [execute_with_semaphore(call) for call in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to ToolResult
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                final_results.append(ToolResult(
                    success=False,
                    output="",
                    error=str(result)
                ))
            else:
                final_results.append(result)

        return final_results

    async def _execute_single(self, call: ToolCall) -> ToolResult:
        """Execute a single tool call"""
        call.status = ExecutionStatus.RUNNING
        call.started_at = datetime.now()
        self.active_executions[call.id] = call

        try:
            # Get the tool
            tool = self.tool_registry.get_tool(call.tool_name)
            if not tool:
                raise ValueError(f"Tool not found: {call.tool_name}")

            # Execute the tool
            result = await self.tool_registry.execute_tool(
                call.tool_name,
                **call.parameters
            )

            return result

        except Exception as e:
            call.error = str(e)
            return ToolResult(
                success=False,
                output="",
                error=str(e)
            )
        finally:
            del self.active_executions[call.id]

    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        return {
            "active": len(self.active_executions),
            "active_tools": [
                {
                    "id": call.id,
                    "tool": call.tool_name,
                    "status": call.status.value,
                    "started_at": call.started_at.isoformat() if call.started_at else None
                }
                for call in self.active_executions.values()
            ],
            "history_count": len(self.execution_history)
        }

    def visualize_plan(self, plan: ExecutionPlan) -> str:
        """
        Create a visual representation of the execution plan.

        Returns:
            ASCII art representation of the plan
        """
        lines = []
        lines.append(f"Execution Plan: {plan.id}")
        lines.append(f"Created: {plan.created_at.isoformat()}")
        lines.append("")

        for i, group in enumerate(plan.parallel_groups):
            lines.append(f"Stage {i + 1} (Parallel):")
            for tool_id in group:
                tool_call = next(tc for tc in plan.tool_calls if tc.id == tool_id)
                status_icon = self._get_status_icon(tool_call.status)
                lines.append(f"  {status_icon} {tool_call.tool_name} [{tool_call.id[:8]}]")

                if tool_call.dependencies:
                    deps = ", ".join(dep[:8] for dep in tool_call.dependencies)
                    lines.append(f"      Dependencies: {deps}")

            lines.append("")

        return "\n".join(lines)

    def _get_status_icon(self, status: ExecutionStatus) -> str:
        """Get icon for status"""
        icons = {
            ExecutionStatus.PENDING: "[PENDING]",
            ExecutionStatus.RUNNING: "[RUNNING]",
            ExecutionStatus.COMPLETED: "[DONE]",
            ExecutionStatus.FAILED: "[FAILED]",
            ExecutionStatus.CANCELLED: "[CANCELLED]"
        }
        return icons.get(status, "[UNKNOWN]")

    def get_execution_summary(self, plan_id: str) -> Dict[str, Any]:
        """Get summary of a specific execution plan"""
        plan = next((p for p in self.execution_history if p.id == plan_id), None)
        if not plan:
            return {"error": "Plan not found"}

        total_tools = len(plan.tool_calls)
        completed = sum(1 for tc in plan.tool_calls if tc.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for tc in plan.tool_calls if tc.status == ExecutionStatus.FAILED)

        duration = None
        if plan.completed_at:
            duration = (plan.completed_at - plan.created_at).total_seconds()

        return {
            "id": plan.id,
            "total_tools": total_tools,
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / total_tools * 100) if total_tools > 0 else 0,
            "parallel_stages": len(plan.parallel_groups),
            "duration_seconds": duration,
            "created_at": plan.created_at.isoformat(),
            "completed_at": plan.completed_at.isoformat() if plan.completed_at else None
        }


class HcodeToolExecutor(ParallelToolExecutor):
    """
    Hcode-specific tool executor with full features.

    Additional features:
    - Tool call streaming
    - Real-time progress updates
    - Intelligent retry logic
    - Cost tracking
    """

    def __init__(self, tool_registry: ToolRegistry, max_parallel: int = 5):
        super().__init__(tool_registry, max_parallel)
        self.cost_tracker = {}
        self.retry_config = {
            "max_retries": 3,
            "backoff_factor": 2,
            "retriable_errors": ["timeout", "rate_limit", "temporary_failure"]
        }

    async def execute_with_streaming(
        self,
        tool_calls: List[Dict[str, Any]],
        on_progress: Optional[callable] = None
    ) -> List[ToolResult]:
        """
        Execute tools with streaming progress updates.

        Args:
            tool_calls: List of tool calls
            on_progress: Callback for progress updates

        Returns:
            List of results
        """
        plan = self._create_execution_plan(tool_calls, auto_detect_dependencies=True)

        # Stream execution progress
        for i, group in enumerate(plan.parallel_groups):
            if on_progress:
                await on_progress({
                    "stage": i + 1,
                    "total_stages": len(plan.parallel_groups),
                    "tools_in_stage": len(group),
                    "message": f"Executing stage {i + 1}/{len(plan.parallel_groups)}"
                })

            # Execute group
            group_calls = [tc for tc in plan.tool_calls if tc.id in group]
            results = await self._execute_group_with_retry(group_calls)

            # Update results
            for call, result in zip(group_calls, results):
                call.result = result
                call.status = ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED

        return [tc.result for tc in plan.tool_calls]

    async def _execute_group_with_retry(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute group with retry logic"""
        results = []

        for call in tool_calls:
            retries = 0
            backoff = 1

            while retries < self.retry_config["max_retries"]:
                result = await self._execute_single(call)

                if result.success or not self._is_retriable(result.error):
                    results.append(result)
                    break

                retries += 1
                await asyncio.sleep(backoff)
                backoff *= self.retry_config["backoff_factor"]
            else:
                # Max retries exceeded
                results.append(ToolResult(
                    success=False,
                    output="",
                    error=f"Max retries exceeded: {result.error}"
                ))

        return results

    def _is_retriable(self, error: Optional[str]) -> bool:
        """Check if error is retriable"""
        if not error:
            return False

        error_lower = error.lower()
        return any(
            err in error_lower
            for err in self.retry_config["retriable_errors"]
        )

    def estimate_cost(self, tool_calls: List[Dict[str, Any]]) -> float:
        """Estimate cost of tool execution"""
        # This would calculate actual API costs
        base_cost = 0.0001  # Base cost per tool call
        return base_cost * len(tool_calls)

    def get_cost_summary(self) -> Dict[str, float]:
        """Get cost summary"""
        return self.cost_tracker.copy()