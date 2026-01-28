import asyncio
import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


# =============================================================================
# PARALLEL TOOL EXECUTOR
# =============================================================================

@dataclass
class ToolCall:
    tool_name: str
    parameters: Dict[str, Any]
    call_id: str = ""

    def __post_init__(self):
        if not self.call_id:
            self.call_id = hashlib.md5(
                f"{self.tool_name}:{json.dumps(self.parameters, sort_keys=True)}".encode()
            ).hexdigest()[:12]

@dataclass
class ToolResult:
    call_id: str
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: int = 0

class ParallelToolExecutor:
    """Executes independent tools in parallel."""

    WRITE_TOOLS = {"writetool", "edittool", "multiedittool", "diffpreviewtool"}
    READ_TOOLS = {"readtool", "globtool", "greptool", "lstool"}
    INDEPENDENT_TOOLS = {"websearchtool", "webfetchtool", "askuserquestiontool"}

    def __init__(self, tool_manager, max_parallel: int = 5):
        self.tool_manager = tool_manager
        self.max_parallel = max_parallel
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._file_locks: Dict[str, asyncio.Lock] = {}
        self._total_calls = 0
        self._parallel_batches = 0
        self._time_saved_ms = 0

    def _get_file_path(self, tool_name: str, params: Dict[str, Any]) -> Optional[str]:
        for key in ["file_path", "path", "filepath"]:
            if key in params:
                return str(params[key])
        return None

    def _get_file_lock(self, file_path: str) -> asyncio.Lock:
        if file_path not in self._file_locks:
            self._file_locks[file_path] = asyncio.Lock()
        return self._file_locks[file_path]

    def _group_by_independence(self, calls: List[ToolCall]) -> List[List[ToolCall]]:
        groups: List[List[ToolCall]] = []
        current_group: List[ToolCall] = []
        files_in_group: Set[str] = set()

        for call in calls:
            tool_lower = call.tool_name.lower()
            file_path = self._get_file_path(call.tool_name, call.parameters)
            can_add = True
            if tool_lower in self.WRITE_TOOLS and file_path:
                if file_path in files_in_group:
                    can_add = False
            if not can_add:
                if current_group:
                    groups.append(current_group)
                current_group = [call]
                files_in_group = {file_path} if file_path else set()
            else:
                current_group.append(call)
                if file_path:
                    files_in_group.add(file_path)
        if current_group:
            groups.append(current_group)
        return groups

    async def _execute_single(self, call: ToolCall) -> ToolResult:
        tool_lower = call.tool_name.lower()
        file_path = self._get_file_path(call.tool_name, call.parameters)
        start_time = time.time()
        try:
            async with self._semaphore:
                if file_path and tool_lower in self.WRITE_TOOLS:
                    async with self._get_file_lock(file_path):
                        result = await self.tool_manager.execute_tool(
                            call.tool_name, **call.parameters
                        )
                else:
                    result = await self.tool_manager.execute_tool(call.tool_name, **call.parameters)
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=result.success,
                output=result.output,
                error=result.error,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                success=False,
                output=None,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def execute_parallel(self, calls: List[ToolCall]) -> List[ToolResult]:
        if not calls:
            return []
        self._total_calls += len(calls)
        groups = self._group_by_independence(calls)
        self._parallel_batches += len(groups)
        results_map: Dict[str, ToolResult] = {}
        start_time = time.time()
        sequential_estimate = 0
        for group in groups:
            if len(group) == 1:
                result = await self._execute_single(group[0])
                results_map[group[0].call_id] = result
                sequential_estimate += result.duration_ms
            else:
                group_results = await asyncio.gather(
                    *[self._execute_single(call) for call in group]
                )
                for result in group_results:
                    results_map[result.call_id] = result
                    sequential_estimate += result.duration_ms
        actual_time = int((time.time() - start_time) * 1000)
        self._time_saved_ms += max(0, sequential_estimate - actual_time)
        return [results_map[call.call_id] for call in calls]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_calls": self._total_calls,
            "parallel_batches": self._parallel_batches,
            "time_saved_ms": self._time_saved_ms,
            "avg_parallelism": self._total_calls / max(1, self._parallel_batches),
        }
