"""
Execution Phase Handler — 4-Phase Implementation Protocol (GPT OSS 120B Optimized)
====================================================================================

Implements the *Execution* phase of the PEV workflow with a structured
4-phase protocol optimized for GPT OSS 120B reasoning:

- **Phase 0: Task Selection** — Parse task.md, select next optimal subtask
- **Phase 1: Pre-Implementation Analysis** — Deep analysis before coding
- **Phase 2: Iterative Code Generation** — 3-pass: skeleton → logic → polish
- **Phase 3: Self-Validation** — Verify correctness before handoff

GPT OSS 120B Optimizations:
- Enhanced chain-of-thought with explicit state tracking
- Stronger tool call extraction with multiple fallback patterns
- Temperature tuned for code generation (0.2)
- Increased max_tokens for complex reasoning (24576)
- Multi-strategy tool call extraction
- Improved phase detection with behavioral hints
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import List, Any, Dict, Optional, Tuple

from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult

# FileAction enum for HcodeDisplay tracking
try:
    from hcode.ui.hcode_display import FileAction
except ImportError:
    FileAction = None

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# GPT OSS 120B OPTIMIZED CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class GPTOSSConfig:
    """Configuration constants optimized for GPT OSS 120B model."""

    # Model parameters
    TEMPERATURE = 0.2  # Lower for more deterministic code generation
    MAX_TOKENS = 24576  # Increased for complex reasoning chains
    TOP_P = 0.95

    # Execution limits
    MAX_ROUNDS = 25  # Increased for complex tasks
    TIMEOUT_SECONDS = 1200  # 20 minutes for execution phase

    # Tool extraction patterns (GPT OSS specific)
    TOOL_PATTERNS = [
        # Standard JSON in code blocks
        r'```json\s*(\{.*?\})\s*```',
        r'```(?:tool)?\s*(\{.*?\})\s*```',
        # Inline JSON
        r'\{"tool"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^}]*\}\s*\}',
        # GPT OSS may output without code blocks
        r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\})\s*\}',
    ]

    # Phase state keywords for detection
    PHASE_KEYWORDS = {
        'phase0': ['task selection', 'read task.md', 'identify next', 'mark as in-progress'],
        'phase1': ['pre-implementation', 'analysis', 'read file', 'glob', 'understand structure'],
        'phase2': ['code generation', 'implementing', 'skeleton', 'logic', 'polish'],
        'phase3': ['validation', 'verify', 'trace', 'deviation report', 'mark complete'],
    }


class ExecutionPhaseHandler(BasePhaseHandler):
    """
    Handler for the Execution phase of PEV workflow (GPT OSS 120B Optimized).

    Uses a 4-phase protocol:
    - Phase 0: Task Selection — identify next unchecked task from task.md
    - Phase 1: Pre-Implementation Analysis — read and understand target files
    - Phase 2: Code Generation — 3-pass skeleton → logic → polish
    - Phase 3: Self-Validation — re-read, trace, cross-check plan

    Transition criteria:
    - At least one non-artifact file modified
    - OR the implementation plan has been fully executed
    """

    phase_name = "execution"

    def __init__(self, artifact_manager, provider, tool_executor, context_manager, console=None):
        """Initialize execution handler with caching and tracking."""
        super().__init__(artifact_manager, provider, tool_executor, context_manager, console)

        # File read cache to avoid redundant operations
        self._file_cache = {}  # path -> (content, timestamp)
        self._cache_ttl = 60  # seconds

        # Tool failure tracking for better error recovery
        self._tool_failures = {}  # tool_name -> failure_count
        self._max_retries = 3

        # Task completion tracking
        self._completed_files = set()  # Track verified file creations

        # GPT OSS 120B specific tracking
        self._current_phase_state = 'phase0'
        self._phase_transition_history = []
        self._reasoning_depth = 0

    def get_required_artifacts(self) -> List[str]:
        """Execution phase doesn't produce new artifacts."""
        return []

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER METHODS (Caching, Validation, Retry Logic)
    # ═══════════════════════════════════════════════════════════════════════

    def _read_with_cache(self, file_path: str, context: AgentContext) -> Optional[str]:
        """
        Read file with caching to avoid redundant operations.

        Args:
            file_path: Path to file (absolute or relative to working_dir)
            context: Agent context

        Returns:
            File content or None if file doesn't exist
        """
        # Check cache
        if file_path in self._file_cache:
            content, timestamp = self._file_cache[file_path]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"[execution] Cache hit for {file_path}")
                return content

        # Cache miss or stale - read fresh
        try:
            # Resolve path correctly (handles both absolute and relative paths)
            resolved_path = Path(file_path)

            # If relative, resolve against working directory
            if not resolved_path.is_absolute():
                resolved_path = Path(context.working_dir) / file_path

            # Check if file exists
            if not resolved_path.exists() or not resolved_path.is_file():
                logger.debug(f"[execution] File not found or not a file: {file_path}")
                return None

            # Read the file
            content = resolved_path.read_text(encoding='utf-8')
            self._file_cache[file_path] = (content, time.time())
            return content

        except Exception as e:
            logger.debug(f"[execution] Read failed for {file_path}: {e}")
            return None

    def _validate_edit_params(
            self, file_path: str, old_string: str, new_string: str, context: AgentContext
    ) -> Tuple[bool, str]:
        """
        Validate Edit tool parameters before execution.

        Args:
            file_path: Path to file
            old_string: Text to replace
            new_string: Replacement text
            context: Agent context

        Returns:
            (is_valid, error_message) tuple
        """
        # Check new_string exists
        if not new_string:
            return False, "new_string is required for Edit tool"

        # Read current file content
        content = self._read_with_cache(file_path, context)
        if content is None:
            return False, f"File not found: {file_path}"

        # Check old_string exists
        count = content.count(old_string)
        if count == 0:
            return False, f"old_string not found in {file_path}"

        # Warn if multiple occurrences (suggest replace_all=True)
        if count > 1:
            return False, (
                f"old_string appears {count} times in {file_path}. "
                f"Use replace_all=True or provide more context to make it unique."
            )

        return True, ""

    def _track_tool_failure(self, tool_name: str) -> bool:
        """
        Track tool failures and determine if retry limit exceeded.

        Args:
            tool_name: Name of tool that failed

        Returns:
            True if should continue retrying, False if limit exceeded
        """
        if tool_name not in self._tool_failures:
            self._tool_failures[tool_name] = 0

        self._tool_failures[tool_name] += 1

        if self._tool_failures[tool_name] >= self._max_retries:
            logger.warning(
                f"[execution] Tool {tool_name} exceeded retry limit ({self._max_retries})"
            )
            return False

        return True

    def _reset_tool_failures(self, tool_name: str):
        """Reset failure counter for a tool after success."""
        if tool_name in self._tool_failures:
            self._tool_failures[tool_name] = 0

    def _verify_task_deliverables(
            self, expected_files: List[str], context: AgentContext
    ) -> Tuple[bool, List[str]]:
        """
        Verify that expected files were created/modified.

        Args:
            expected_files: List of file paths that should exist
            context: Agent context

        Returns:
            (all_exist, missing_files) tuple
        """
        missing = []
        for file_path in expected_files:
            # Check if file exists via read
            content = self._read_with_cache(file_path, context)
            if content is None:
                # Try fresh read (bypass cache)
                try:
                    content = self.artifact_manager.load_artifact(
                        file_path.replace("\\", "/"), context
                    )
                except Exception:
                    pass

            if not content:
                missing.append(file_path)

        return len(missing) == 0, missing

    # ═══════════════════════════════════════════════════════════════════════
    # MAIN HANDLER
    # ═══════════════════════════════════════════════════════════════════════

    async def handle(
            self,
            context: AgentContext,
            loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute implementation phase using the 4-phase protocol (GPT OSS 120B Optimized).

        The AI is given the full execution_handler.md protocol as its system
        prompt, along with the implementation plan and task.md content. It
        runs in a multi-turn loop where each round includes phase-aware
        continuation prompts that steer it through Phase 0 → 1 → 2 → 3.

        Args:
            context: Current agent context
            loop_controller: Loop controller

        Returns:
            PhaseResult with execution outcome
        """
        try:
            # Load required artifacts
            plan_content = self.artifact_manager.load_artifact(
                "implementation_plan.md", context
            )
            if not plan_content:
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output="Cannot execute: implementation_plan.md not found",
                    can_transition=False,
                    error="Missing implementation plan",
                )

            task_content = self.artifact_manager.load_artifact(
                "task.md", context
            ) or "(No task.md found)"

            # Get task statistics for multi-task visibility
            task_stats = self._get_task_statistics(task_content)

            # Find next incomplete step for display
            next_step = self._get_next_incomplete_step(plan_content, context)
            step_info = ""
            if next_step:
                # Enhanced display with task counter
                task_counter = (
                    f"Task {task_stats['current']}/{task_stats['total']}"
                    if task_stats['total'] > 0
                    else ""
                )
                step_name = next_step.get(
                    'name', 'Step ' + str(next_step.get('number', '?'))
                )
                step_info = (
                    f"{task_counter} - {step_name}"
                    if task_counter
                    else f"Working on: {step_name}"
                )
                logger.info(step_info)

            # Build the execution prompt with 4-phase protocol
            prompt = self._build_execution_prompt(context, plan_content, task_content)

            # Add step-specific context
            if next_step:
                prompt += f"\n\nCurrent step to implement:\n- {next_step.get('name')}: {next_step.get('description', '')}"
                if next_step.get('files'):
                    prompt += f"\n- Files to modify: {', '.join(next_step.get('files', []))}"

            # Generate AI response and execute tool calls
            tool_results = []
            response_text = ""

            if self.provider is not None:
                self._display("Executing implementation...", style="info")
                if step_info:
                    self._display(step_info, style="thinking")

                # Display task progress via HcodeDisplay if available
                if self._hcode_display and task_stats['total'] > 0:
                    progress_msg = f"Executing: Task {task_stats['current']}/{task_stats['total']}"
                    self._display(progress_msg, style="info")

                # Start execution thinking display
                if self._hcode_display:
                    self._hcode_display.start_thinking()

                response_text, tool_results = await self._generate_and_execute(
                    prompt,
                    context,
                    system_prompt=self._get_execution_system_prompt(context),
                    max_rounds=GPTOSSConfig.MAX_ROUNDS,
                    max_tokens=GPTOSSConfig.MAX_TOKENS,
                    temperature=GPTOSSConfig.TEMPERATURE,
                    timeout_seconds=GPTOSSConfig.TIMEOUT_SECONDS,
                )

                # End thinking display
                if self._hcode_display:
                    self._hcode_display.end_thinking()

                # Track modified files with HcodeDisplay
                if tool_results and self._hcode_display and FileAction:
                    for result in tool_results:
                        if result.get("success"):
                            tool_name = result.get('tool', '').lower()
                            file_path = result.get('file_path', '')
                            if file_path and tool_name in ['write', 'edit', 'writetool', 'edittool']:
                                action = (
                                    FileAction.CREATED
                                    if tool_name in ['write', 'writetool']
                                    else FileAction.EDITED
                                )
                                self._hcode_display.track_file(file_path, action)

            # Update task.md with progress after tool execution
            if tool_results:
                self._update_task_progress(context)

            # Check for critical tool failures (Bash, verification commands)
            critical_failures = [
                r for r in tool_results
                if not r.get("success", True)
                   and r.get("tool", "").lower() in ("bash", "bashtool")
            ]

            # Determine success based on critical failures
            execution_success = len(critical_failures) == 0

            # Check if can transition (implementation sufficient)
            can_transition = self._check_execution_complete(context) and execution_success

            # Build output message
            actions_count = len(tool_results)
            files_count = len(context.modified_files)
            if critical_failures:
                failure_details = "; ".join(
                    f"{r['tool']}: {r.get('error', 'unknown')}"
                    for r in critical_failures[:3]
                )
                output_msg = (
                    f"⚠️  Execution FAILED - {len(critical_failures)} "
                    f"critical failures: {failure_details}"
                )
            else:
                output_msg = (
                    f"Execution iteration complete. "
                    f"{actions_count} actions, {files_count} files modified."
                )
            if step_info:
                output_msg = f"{step_info}. {output_msg}"

            return PhaseResult(
                phase_name=self.phase_name,
                success=execution_success,
                output=output_msg,
                can_transition=can_transition,
                metadata={
                    "modified_files": list(context.modified_files),
                    "completed_actions": len(context.completed_actions),
                    "tool_results": tool_results,
                    "current_step": next_step,
                    "response": response_text[:500] if response_text else "",
                    "phase_state": self._current_phase_state,
                }
            )

        except Exception as e:
            logger.exception(f"Execution phase failed: {e}")
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                output=f"Execution phase failed: {str(e)}",
                can_transition=False,
                error=str(e),
            )

    # ═══════════════════════════════════════════════════════════════════════
    # GPT OSS 120B OPTIMIZED TOOL EXTRACTION
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        GPT OSS 120B optimized tool call extraction with multiple strategies.

        GPT OSS 120B may output tool calls in various formats. This method
        tries multiple extraction strategies in order of preference.

        Extraction Strategy:
        1. Extract from <output> tags (primary for GPT OSS)
        2. Extract from JSON code blocks
        3. Extract inline JSON tool calls
        4. Fall back to parent class extraction

        Args:
            response: Full AI response text

        Returns:
            List of extracted tool call dictionaries
        """
        if not response:
            return []

        all_tool_calls = []

        # Strategy 1: Extract from <output> tags (GPT OSS primary format)
        output_pattern = r'<output>(.*?)</output>'
        output_matches = re.findall(output_pattern, response, re.DOTALL | re.IGNORECASE)

        for output_content in output_matches:
            tool_calls = self._extract_tools_from_text(output_content.strip())
            if tool_calls:
                logger.info(
                    f"[execution] Extracted {len(tool_calls)} tool calls from <output> tags"
                )
                all_tool_calls.extend(tool_calls)

        # Strategy 2: Extract from <thinking> tags for embedded tool calls
        thinking_pattern = r'<thinking>(.*?)</thinking>'
        thinking_matches = re.findall(thinking_pattern, response, re.DOTALL | re.IGNORECASE)

        for thinking_content in thinking_matches:
            tool_calls = self._extract_tools_from_text(thinking_content.strip())
            if tool_calls:
                logger.info(
                    f"[execution] Extracted {len(tool_calls)} tool calls from <thinking> tags"
                )
                all_tool_calls.extend(tool_calls)

        # Strategy 3: Extract from full response if no tags found
        if not all_tool_calls:
            tool_calls = self._extract_tools_from_text(response)
            if tool_calls:
                logger.info(
                    f"[execution] Extracted {len(tool_calls)} tool calls from full response"
                )
                all_tool_calls.extend(tool_calls)

        # Deduplicate tool calls by content hash
        seen = set()
        unique_tool_calls = []
        for tc in all_tool_calls:
            tc_hash = json.dumps(tc, sort_keys=True)
            if tc_hash not in seen:
                seen.add(tc_hash)
                unique_tool_calls.append(tc)

        return unique_tool_calls

    def _extract_tools_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from text using multiple patterns.

        Args:
            text: Text to search for tool calls

        Returns:
            List of extracted tool call dictionaries
        """
        tool_calls = []

        # Pattern 1: JSON code blocks with tool
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        for match in re.finditer(json_block_pattern, text, re.DOTALL):
            try:
                parsed = json.loads(match.group(1))
                if 'tool' in parsed and 'arguments' in parsed:
                    tool_calls.append(parsed)
            except json.JSONDecodeError:
                pass

        # Pattern 2: Inline JSON with tool and arguments
        inline_pattern = r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\})\s*\}'
        for match in re.finditer(inline_pattern, text, re.DOTALL):
            try:
                tool_name = match.group(1)
                arguments = json.loads(match.group(2))
                tool_calls.append({"tool": tool_name, "arguments": arguments})
            except json.JSONDecodeError:
                pass

        # Pattern 3: GPT OSS may output nested arguments
        nested_pattern = r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{(?:[^{}]|\{[^{}]*\})*\})\s*\}'
        for match in re.finditer(nested_pattern, text, re.DOTALL):
            try:
                tool_name = match.group(1)
                arguments = json.loads(match.group(2))
                tool_calls.append({"tool": tool_name, "arguments": arguments})
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _get_thinking_instructions(self) -> str:
        """
        GPT OSS 120B optimized thinking instructions.

        Uses explicit state tracking and structured reasoning format
        that aligns with GPT OSS 120B's strengths in step-by-step reasoning.
        """
        return """### DEEP REASONING PROTOCOL (GPT OSS 120B Optimized)

Use `<thinking>` and `<output>` tags to structure your reasoning and actions.

**CRITICAL: State Tracking in Every Thinking Block**

```
<thinking>
## STATE AWARENESS
- Current Phase: [0/1/2/3]
- Task Being Executed: [ID and description]
- Files Modified So Far: [list or "none"]
- Last Action Result: [success/failure]

## ANALYSIS STEPS
Step 1: [Clear description]
  → Result: [what you found]
  → Evidence: [file:line]

Step 2: [Next analysis step]
  → Result: [what you found]
  → Evidence: [file:line]

## DECISION
Based on analysis, I will: [clear action statement]

## CHECKPOINT VERIFICATION
- [ ] All files have been read before modification
- [ ] Change location is precisely identified
- [ ] Plan alignment is verified
</thinking>

<output>
[Brief summary]
[Tool calls in JSON format]
</output>
```

**Tool Call Format**:
```json
{"tool": "ToolName", "arguments": {"param": "value"}}
```

**Anti-Hallucination Rules**:
1. Never reference a file you haven't read
2. Never use a filename not returned by Glob
3. Always cite evidence for every claim
4. If unsure, READ the file to verify

**Error Recovery**:
If a tool fails, STOP and:
1. Read the error message
2. Diagnose the root cause
3. Apply the correct recovery action
4. Re-run the tool to verify
"""

    # ═══════════════════════════════════════════════════════════════════════
    # EXECUTION WRITE GATE (Security Boundary)
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_planned_files(self, plan_content: str) -> set:
        """
        Extract allowed file paths and patterns from implementation plan.

        Parses the plan for [MODIFY], [NEW], and [DELETE] markers to build
        a whitelist of files that execution is allowed to modify.

        Args:
            plan_content: Content of implementation_plan.md

        Returns:
            Set of file paths and patterns that are allowed to be written/edited
        """
        allowed = set()

        # [MODIFY] /path/to/file pattern (strip backticks if present)
        modify_paths = re.findall(r'\[MODIFY\]\s+([^\s]+)', plan_content)
        allowed.update(p.strip('`') for p in modify_paths)

        # [NEW] /path/to/file pattern (strip backticks if present)
        new_paths = re.findall(r'\[NEW\]\s+([^\s]+)', plan_content)
        allowed.update(p.strip('`') for p in new_paths)

        # [DELETE] /path/to/file pattern (strip backticks if present)
        delete_paths = re.findall(r'\[DELETE\]\s+([^\s]+)', plan_content)
        allowed.update(p.strip('`') for p in delete_paths)

        # file:///path markdown links
        allowed.update(re.findall(r'file:///([^\)]+)', plan_content))

        # Extract backtick paths from plan
        backtick_paths = re.findall(
            r'`([^`]+\.(py|txt|json|yaml|yml|md))`', plan_content
        )
        allowed.update(path for path, _ in backtick_paths)

        # Always allow task.md updates
        allowed.add(".hcode/task.md")

        # Pattern-based allowances
        allowed.add("tests/**/*.py")
        allowed.add("tests/conftest.py")
        allowed.add("tasks/**/*.txt")
        allowed.add("tasks/**/*.md")

        logger.debug(
            f"Execution write gate: {len(allowed)} paths/patterns allowed from plan"
        )
        return allowed

    def _is_path_allowed(self, target_path: str, allowed_files: set) -> bool:
        """
        Check if a target path is allowed by write gate.

        Supports both exact path matching and pattern-based matching.

        Args:
            target_path: Path to check
            allowed_files: Set of allowed paths and patterns

        Returns:
            True if path is allowed, False otherwise
        """
        import fnmatch

        # Normalize path separators
        norm_target = target_path.replace("\\", "/").strip()

        for allowed in allowed_files:
            # Exact match or substring match
            if allowed in norm_target or norm_target in allowed:
                return True

            # Pattern matching (supports ** for recursive globs)
            if "**" in allowed:
                parts = allowed.split("**/")
                if len(parts) == 2:
                    base, suffix = parts
                    suffix_pattern = suffix.replace("*", ".*")
                    if (
                            norm_target.startswith(base)
                            and re.match(suffix_pattern, norm_target.split("/")[-1])
                    ):
                        return True
            elif "*" in allowed:
                if fnmatch.fnmatch(norm_target, allowed):
                    return True

        return False

    async def _execute_tools(
            self,
            tool_calls: List[Dict[str, Any]],
            context: AgentContext,
    ) -> List[Dict[str, Any]]:
        """
        Enhanced execution-phase tool executor with validation and retry logic.

        Features:
        - Write gate: reject Write/Edit calls not in implementation_plan.md
        - Edit validation: check parameters before execution
        - Failure tracking: detect retry loops and abort early
        - Cache invalidation: clear cache when files are modified

        Args:
            tool_calls: List of tool calls to execute
            context: Current agent context

        Returns:
            List of tool execution results
        """
        # Write gate REMOVED - agent has full autonomy
        results = []

        for tc in tool_calls:
            tool_name = (tc.get("tool") or "").lower()
            arguments = tc.get("arguments", {})

            # VALIDATION FOR EDIT TOOL
            if tool_name in ("edit", "edittool"):
                target = (
                        arguments.get("file_path")
                        or arguments.get("TargetFile")
                        or ""
                )
                old_string = (
                        arguments.get("old_string")
                        or arguments.get("OldText")
                        or ""
                )
                new_string = (
                        arguments.get("new_string")
                        or arguments.get("NewText")
                        or ""
                )

                # CRITICAL: Validate task.md checkbox updates
                if (
                        "task.md" in target
                        and "- [ ]" in old_string
                        and "- [x]" in new_string
                ):
                    recent_failures = [
                        r for r in results[-10:] if not r.get("success", True)
                    ]
                    if recent_failures:
                        failure_list = "\n".join(
                            f"  • {r.get('tool', 'unknown')}: "
                            f"{r.get('error', 'unknown error')}"
                            for r in recent_failures[-3:]
                        )
                        error_msg = (
                            f"⚠️  Cannot mark task complete - "
                            f"recent operations failed:\n{failure_list}\n\n"
                            f"Fix these failures before marking the task as complete."
                        )
                        self._display(
                            f"  [>] Edit: {target}  ← BLOCKED (task not complete)",
                            style="error"
                        )
                        results.append({
                            "tool": tc.get("tool"),
                            "success": False,
                            "error": error_msg,
                            "file_path": target,
                        })
                        continue

                # Validate parameters
                is_valid, error_msg = self._validate_edit_params(
                    target, old_string, new_string, context
                )

                if not is_valid:
                    if not self._track_tool_failure("Edit"):
                        error_msg = (
                            f"⚠️  Edit operation failed {self._max_retries} times. "
                            f"Error: {error_msg}\n\n"
                            f"Recovery suggestion:\n"
                            f"1. Re-read {target} to get fresh content\n"
                            f"2. Verify the old_string still exists\n"
                            f"3. If old_string appears multiple times, "
                            f"use replace_all=True\n"
                            f"4. Provide more context to make old_string unique"
                        )

                    self._display(
                        f"  [>] Edit: {target}  ← VALIDATION FAILED",
                        style="error"
                    )
                    results.append({
                        "tool": tc.get("tool"),
                        "success": False,
                        "output": None,
                        "error": error_msg,
                        "file_path": target,
                    })
                    logger.warning(f"Edit validation failed: {error_msg}")
                    continue

            # WRITE GATE REMOVED - Agent has full autonomy to fix issues
            # The plan may be incomplete or issues may require unexpected file changes
            # Trust the agent to make correct decisions during execution

        # Execute all calls via the parent implementation (no gate)
        if tool_calls:
            parent_results = await super()._execute_tools(tool_calls, context)

            # Post-processing: invalidate cache and reset failure counters
            for result in parent_results:
                if result.get("success"):
                    tool_name = result.get("tool", "").lower()

                    self._reset_tool_failures(tool_name)

                    if tool_name in ("write", "writetool", "edit", "edittool"):
                        file_path = result.get("file_path", "")
                        if file_path in self._file_cache:
                            del self._file_cache[file_path]
                            logger.debug(
                                f"[execution] Cache invalidated for {file_path}"
                            )

            results.extend(parent_results)

        return results

    # ═══════════════════════════════════════════════════════════════════════
    # SYSTEM PROMPT (GPT OSS 120B Optimized)
    # ═══════════════════════════════════════════════════════════════════════

    def _get_execution_system_prompt(self, context: AgentContext) -> str:
        """
        Build system prompt for execution phase (GPT OSS 120B Optimized).

        Loads execution_handler.md as the primary protocol, then adds
        identity, tool format, plan content, and working context.
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            identity = loader.get_identity()
            tool_format = loader.get_tool_format()

            execution_protocol = self._load_execution_protocol()

            plan_content = self.artifact_manager.load_artifact(
                "implementation_plan.md", context
            ) or "(No plan loaded)"

            task_content = self.artifact_manager.load_artifact(
                "task.md", context
            ) or "(No task.md found)"

            # GPT OSS 120B specific context injection
            system_prompt = f"""{identity}

{tool_format}

{self._load_user_memory(context)}
{self._load_claude_md(context)}
{self._load_hcode_architecture(context)}
---

{execution_protocol}

---
{self._load_hcode_memory(context)}
## CURRENT CONTEXT

Working directory: {context.working_dir}
Artifacts directory: .hcode
Iteration: {context.iteration}
Modified files: {len(context.modified_files)}
Completed actions: {len(context.completed_actions)}

### CURRENT task.md:
{task_content}
"""
            return system_prompt

        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            return self._get_fallback_execution_prompt(context)

    def _load_execution_protocol(self) -> str:
        """
        Load execution_handler.md prompt file.

        Returns:
            Content of execution_handler.md, or a condensed fallback.
        """
        try:
            prompt_dir = (
                    Path(__file__).parent.parent.parent
                    / "config" / "core_prompts" / "core" / "pev_prompts"
            )
            protocol_path = prompt_dir / "execution_handler.md"

            if protocol_path.exists():
                return protocol_path.read_text(encoding="utf-8")

            logger.warning(
                f"execution_handler.md not found at {protocol_path}, "
                f"using inline protocol"
            )
        except Exception as e:
            logger.warning(f"Failed to load execution_handler.md: {e}")

        # Condensed inline fallback (GPT OSS optimized)
        return """# Hcode Execution Mode — 4-Phase Implementation Protocol

## THE 4-PHASE PROTOCOL

### Phase 0: Task Selection
Parse task.md, find next unchecked `- [ ]` item, cross-reference with plan.

### Phase 1: Pre-Implementation Analysis
READ every file before modifying. Understand structure, imports, callers.
Specify exact change: file, location, old text → new text.

### Phase 2: Code Generation (3-Pass)
Pass 1: Skeleton — structure, signatures, imports.
Pass 2: Logic — function bodies, error handling.
Pass 3: Polish — cross-file references, naming, cleanup.

### Phase 3: Self-Validation
RE-READ modified files. Trace execution mentally. Check plan coverage.
Update task.md: [x] for completed, [/] for in-progress.

## RULES
- READ BEFORE WRITE — always
- ONE CHANGE AT A TIME — verify each
- NO CODE IN RESPONSE TEXT — use Write/Edit tools
- TRACK PROGRESS — update task.md checkboxes
"""

    def _load_claude_md(self, context: AgentContext) -> str:
        """Load user's project-specific instructions from CLAUDE.md."""
        try:
            for path_str in [".hcode/CLAUDE.md", "CLAUDE.md"]:
                try:
                    file_path = Path(context.working_dir) / path_str
                    if file_path.exists():
                        content = file_path.read_text(encoding="utf-8")
                        if content.strip():
                            logger.debug(f"Loaded project instructions from {path_str}")
                            return f"""
---

## PROJECT INSTRUCTIONS (CLAUDE.md)

{content.strip()}

---
"""
                except Exception:
                    continue

            return ""
        except Exception:
            return ""

    def _load_user_memory(self, context: AgentContext) -> str:
        """Load user's global memory from ~/.claude/projects/.../memory/MEMORY.md."""
        try:
            home = Path.home()
            claude_dir = home / ".claude" / "projects"

            if not claude_dir.exists():
                return ""

            for project_folder in claude_dir.iterdir():
                if project_folder.is_dir():
                    memory_file = project_folder / "memory" / "MEMORY.md"
                    if memory_file.exists():
                        content = memory_file.read_text(encoding="utf-8")
                        if content.strip():
                            logger.debug(f"Loaded user memory from {memory_file}")
                            return f"""
---

## USER MEMORY (Cross-Session Learnings)

{content.strip()}

---
"""
                        break

            return ""
        except Exception:
            return ""

    def _load_hcode_architecture(self, context: AgentContext) -> str:
        """
        Load project architecture documentation from .hcode/hcode.md.

        This file is generated by /init and contains comprehensive architecture
        documentation including annotated repository structure, component descriptions,
        technology stack, and design patterns.

        Args:
            context: Current agent context

        Returns:
            Formatted architecture documentation or empty string if unavailable
        """
        try:
            # Load hcode.md (architecture documentation)
            arch_content = self.artifact_manager.load_artifact(
                "hcode.md", context
            )

            if not arch_content or not arch_content.strip():
                return ""

            logger.debug("Loaded project architecture from .hcode/hcode.md")
            return f"""
---

## PROJECT ARCHITECTURE (.hcode/hcode.md)

{arch_content.strip()}

---
"""
        except Exception as e:
            logger.debug(f"Architecture documentation loading failed: {e}")
            return ""

    def _get_fallback_execution_prompt(self, context: AgentContext) -> str:
        """Fallback execution prompt when core prompts are unavailable."""
        return f"""## EXECUTION MODE

You are Hcode in EXECUTION mode. Implement changes from the implementation plan.

Working directory: {context.working_dir}
Artifacts directory: .hcode

### Rules:
1. Follow implementation_plan.md exactly
2. READ files before editing — no exceptions
3. Use Write/Edit tools for all changes
4. Update task.md: [x] completed, [/] in progress
5. Keep task IDs — don't renumber

### Anti-Hallucination:
- NEVER show code without using Write/Edit tool
- ALWAYS read files before editing
- VERIFY all assumptions by reading actual code
"""

    # ═══════════════════════════════════════════════════════════════════════
    # EXECUTION PROMPT
    # ═══════════════════════════════════════════════════════════════════════

    def _build_execution_prompt(
            self,
            context: AgentContext,
            plan_content: str,
            task_content: str = "",
    ) -> str:
        """
        Build the user prompt for execution phase.

        Embeds plan content, task content, and session state,
        then instructs the AI to begin with Phase 0: Task Selection.
        """
        modified_files_list = (
            "\n".join(f"  - {f}" for f in context.modified_files)
            if context.modified_files
            else "  (none yet)"
        )

        recent_actions = (
            context.completed_actions[-5:]
            if context.completed_actions
            else []
        )
        actions_summary = (
            "\n".join(
                f"  - {a.get('tool', 'unknown')}: "
                f"{'[OK]' if a.get('success') else '[FAIL]'}"
                for a in recent_actions
            )
            if recent_actions
            else "  (none yet)"
        )

        return f"""## EXECUTION PHASE — 4-Phase Protocol

You are executing the implementation plan using the 4-phase protocol.
Follow Phases 0 → 1 → 2 → 3 for each subtask.

### Implementation Plan:
{plan_content}

### Current task.md:
{task_content}

### Session State:
- Working Directory: {context.working_dir}
- Artifacts Directory: .hcode (RELATIVE to working directory)
- Iteration: {context.iteration}
- Modified files ({len(context.modified_files)}):
{modified_files_list}
- Recent actions:
{actions_summary}

### CRITICAL REMINDERS:

**Artifact Locations:**
- Task list is at: `.hcode/task.md` (NOT `task.md` in root)
- Implementation plan is at: `.hcode/implementation_plan.md` (NOT in root)

**File Discovery:**
- Use Glob to discover actual files FIRST
- ONLY reference files that Glob returned
- NEVER invent filenames like "file1.py" or "example.py"

### INSTRUCTIONS:

Begin with **Phase 0: Task Selection**.

1. Read `.hcode/task.md` (note the .hcode/ prefix!)
2. Identify the next unchecked `- [ ]` task
3. Cross-reference with `.hcode/implementation_plan.md` for details
4. Mark task as in-progress: `- [/]` using Edit tool on `.hcode/task.md`
5. Proceed to Phase 1: Use Glob to discover files, then READ all targets
6. Then Phase 2: make the code changes (3-pass: skeleton → logic → polish)
7. Then Phase 3: re-read modified files, trace execution, update `.hcode/task.md` with [x]

Remember:
- CORRECT PATH: `.hcode/task.md` (NOT `D:/workshops/Hcaude/task.md`)
- USE GLOB FIRST: Discover actual files before reading them
- READ BEFORE WRITE: Always read files before editing
- ONE TASK AT A TIME: Complete each subtask fully before moving on
- USE TOOLS: All code changes must use Write/Edit, never raw text
- TRACK PROGRESS: Update `.hcode/task.md` after each completed subtask

NOW BEGIN Phase 0. Read `.hcode/task.md` and identify the next task to implement."""

    # ═══════════════════════════════════════════════════════════════════════
    # CONTINUATION PROMPTS (Phase-Aware Steering - GPT OSS Optimized)
    # ═══════════════════════════════════════════════════════════════════════

    def _detect_current_phase(
            self,
            all_results: List[Dict[str, Any]],
            round_num: int,
    ) -> str:
        """
        Detect which phase the AI should be in based on session state.

        GPT OSS 120B Optimized: Uses both tool patterns and content analysis.

        Returns one of: 'phase0', 'phase1', 'phase2', 'phase3', 'complete'
        """
        # Count tool types
        task_md_edits = sum(
            1 for r in all_results
            if r.get('success')
            and 'task.md' in str(r.get('file_path', ''))
            and r.get('tool', '').lower() in ['edit', 'edittool']
        )

        file_reads = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['read', 'readtool', 'glob', 'globtool']
        )

        file_writes = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['write', 'writetool', 'edit', 'edittool']
            and '.hcode' not in str(r.get('file_path', ''))
        )

        # Update internal phase state
        if task_md_edits == 0 and file_reads == 0 and file_writes == 0:
            self._current_phase_state = 'phase0'
        elif task_md_edits > 0 and file_writes == 0:
            self._current_phase_state = 'phase1'
        elif file_writes > 0 and task_md_edits == 1:
            self._current_phase_state = 'phase2'
        elif file_writes > 0 and task_md_edits >= 2:
            self._current_phase_state = 'phase3'

        return self._current_phase_state

    def _build_continuation_prompt(
            self,
            round_results: List[Dict[str, Any]],
            all_results: List[Dict[str, Any]],
            round_num: int,
            context: Any = None,
    ) -> str:
        """
        Build phase-aware continuation prompt (GPT OSS 120B Optimized).

        Enhanced with:
        - Explicit phase detection and state tracking
        - Clear phase-specific instructions
        - Error recovery guidance
        - Anti-hallucination reminders
        """
        current_phase = self._detect_current_phase(all_results, round_num)

        # Track phase transitions
        if self._phase_transition_history:
            last_phase = self._phase_transition_history[-1]
            if last_phase != current_phase:
                logger.info(
                    f"[execution] Phase transition: {last_phase} → {current_phase}"
                )
        self._phase_transition_history.append(current_phase)

        # Check for errors in recent rounds
        recent_errors = [
            r for r in round_results[-3:]
            if not r.get('success')
        ]

        if recent_errors:
            error_msg = self._build_error_recovery_prompt(recent_errors)
            if error_msg:
                return error_msg

        # Phase-specific continuation
        if current_phase == 'phase0':
            return self._phase0_continuation(round_num, all_results)
        elif current_phase == 'phase1':
            return self._phase1_continuation(round_num, all_results)
        elif current_phase == 'phase2':
            plan_content = ""
            try:
                plan_content = (
                        self.artifact_manager.load_artifact(
                            "implementation_plan.md", context
                        ) or ""
                )
            except Exception:
                pass
            return self._phase2_continuation(round_num, all_results, context, plan_content)
        elif current_phase == 'phase3':
            return self._phase3_continuation(round_num, all_results)

        # Round limit push
        if round_num >= 20:
            return (
                "⚠️ You are approaching the execution round limit. "
                "Complete your current work immediately:\n\n"
                "1. Finish any pending code changes\n"
                "2. Re-read modified files for verification\n"
                "3. Update `.hcode/task.md` with current status\n"
                "4. Provide a summary of what was accomplished\n\n"
                "If the task is incomplete, clearly state what remains."
            )

        return (
            f"Continue with the 4-phase protocol (detected: {current_phase}).\n\n"
            "Remember:\n"
            "- Use Glob to discover files BEFORE reading them\n"
            "- ALWAYS read files before editing\n"
            "- Update `.hcode/task.md` after completing each subtask\n"
            "- Use [Evidence: file:line] citations for all claims\n"
            "- One change at a time — verify before proceeding"
        )

    def _build_error_recovery_prompt(
            self, errors: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Build targeted error recovery prompt based on error types."""
        if not errors:
            return None

        error_types = []
        edit_failures = 0
        for error in errors:
            tool = error.get('tool', '').lower()
            err_msg = error.get('error', error.get('output', ''))

            if tool in ('edit', 'edittool') and not error.get('success', True):
                edit_failures += 1

            if 'file not found' in err_msg.lower():
                error_types.append('file_not_found')
            elif 'old text not found' in err_msg.lower() or 'old_string' in err_msg.lower():
                error_types.append('edit_mismatch')
            elif 'appears' in err_msg.lower() and 'times' in err_msg.lower():
                error_types.append('edit_duplicate')
            elif 'new_string' in err_msg.lower() and 'required' in err_msg.lower():
                error_types.append('edit_params')
            elif 'retry limit' in err_msg.lower() or 'exceeded' in err_msg.lower():
                error_types.append('retry_limit')
            elif 'write gate' in err_msg.lower() or 'violation' in err_msg.lower():
                error_types.append('write_gate')

        # Retry limit exceeded
        if 'retry_limit' in error_types or edit_failures >= 3:
            return (
                "🛑 STOP: Edit Retry Limit Exceeded\n\n"
                f"You've attempted Edit operations {edit_failures} times with failures.\n\n"
                "**MANDATORY RECOVERY PROTOCOL**:\n"
                "1. **STOP** trying the same Edit approach\n"
                "2. **READ** the target file fresh to see current state\n"
                "3. **ANALYZE** what changed (did previous Edits partially succeed?)\n"
                "4. **CHANGE STRATEGY**:\n"
                "   - If old_string appears multiple times, use replace_all=True\n"
                "   - If old_string not found, verify it still exists in the file\n"
                "   - Consider using Write instead of multiple Edits\n"
                "5. **DOCUMENT** the issue if unresolvable\n\n"
                "⚠️  Do NOT retry the same Edit without re-reading the file first!"
            )

        if 'edit_params' in error_types:
            return (
                "🔴 ERROR: Edit Tool Parameter Missing\n\n"
                "Your Edit call is missing required parameters.\n\n"
                "**REQUIRED PARAMETERS**:\n"
                '```json\n'
                '{"tool": "Edit", "arguments": {\n'
                '  "file_path": "path/to/file",  // REQUIRED\n'
                '  "old_string": "text to replace",  // REQUIRED\n'
                '  "new_string": "replacement text",  // REQUIRED\n'
                '  "replace_all": false  // OPTIONAL\n'
                '}}\n'
                '```\n\n'
                "⚠️  Both old_string AND new_string are required!"
            )

        if 'edit_duplicate' in error_types:
            return (
                "🔴 ERROR: Old String Appears Multiple Times\n\n"
                "The text you're trying to replace appears more than once.\n\n"
                "**SOLUTIONS**:\n"
                "1. **Add more context** to make old_string unique\n"
                "2. **Use replace_all=True** to change all occurrences\n"
                "3. **Re-read the file** to verify current content"
            )

        if 'file_not_found' in error_types:
            return (
                "🔴 ERROR RECOVERY: File Not Found\n\n"
                "You tried to access a file that doesn't exist.\n\n"
                "RECOVERY STEPS:\n"
                "1. STOP — don't continue with incorrect paths\n"
                "2. Use Glob tool to discover actual files\n"
                "3. Use ONLY filenames returned by Glob\n"
                "4. Read the file first, then proceed\n\n"
                "NEVER invent filenames like 'file1.py' or 'example.py'."
            )

        if 'edit_mismatch' in error_types:
            return (
                "🔴 ERROR RECOVERY: Edit Failed — Old Text Not Found\n\n"
                "The content you tried to edit doesn't match the file.\n\n"
                "RECOVERY STEPS:\n"
                "1. Re-read the file with Read tool to get actual content\n"
                "2. Copy the exact text you want to replace\n"
                "3. Retry the Edit with correct old_string\n\n"
                "Include proper indentation and surrounding context."
            )

        if 'write_gate' in error_types:
            return (
                "🔴 ERROR RECOVERY: Write Gate Violation\n\n"
                "You tried to write to a file not listed in the implementation plan.\n\n"
                "RECOVERY STEPS:\n"
                "1. Read `.hcode/implementation_plan.md` for allowed files\n"
                "2. Only modify files explicitly listed in the plan\n"
                "3. If you need to modify a file not in plan, flag it with reasoning\n\n"
                "The write gate is a security boundary — follow the plan."
            )

        return (
            "🔴 ERROR DETECTED\n\n"
            "Recent tool calls failed. Please:\n\n"
            "1. Review the error messages above\n"
            "2. Diagnose the root cause\n"
            "3. Apply the appropriate recovery action\n"
            "4. Re-run the failed tool to verify the fix\n\n"
            "Don't continue with broken state — fix errors first."
        )

    def _phase0_continuation(
            self, round_num: int, all_results: List[Dict]
    ) -> str:
        """Phase 0: Task Selection continuation."""
        task_edits = sum(
            1 for r in all_results
            if 'task.md' in str(r.get('file_path', ''))
            and r.get('tool', '').lower() in ['edit', 'edittool']
        )

        if task_edits == 0:
            return (
                "📍 PHASE 0: Task Selection\n\n"
                "You need to start by reading the task list:\n\n"
                "1. Read `.hcode/task.md` (note the .hcode/ prefix!)\n"
                "2. Find the next unchecked `- [ ]` item\n"
                "3. Read `.hcode/implementation_plan.md` for details\n"
                "4. Mark the task as in-progress: change `- [ ]` to `- [/]`\n"
                "5. Use Edit tool on `.hcode/task.md` to update\n\n"
                "Remember: path is `.hcode/task.md` NOT `task.md`!"
            )

        return (
            "📍 PHASE 0 → PHASE 1: Task Selected\n\n"
            "Good! Task marked as in-progress. Now proceed to Phase 1:\n\n"
            "1. Use Glob to discover actual files in target directories\n"
            "2. Read ALL files you plan to modify\n"
            "3. Understand existing code patterns and structure\n"
            "4. Plan exact changes with evidence citations\n\n"
            "Remember: ONLY use files discovered by Glob!"
        )

    def _phase1_continuation(
            self, round_num: int, all_results: List[Dict]
    ) -> str:
        """Phase 1: Pre-Implementation Analysis continuation."""
        read_count = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['read', 'readtool', 'glob', 'globtool']
        )
        write_count = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['write', 'edit', 'writetool', 'edittool']
            and '.hcode' not in str(r.get('file_path', ''))
        )

        if read_count == 0:
            return (
                "📍 PHASE 1: Pre-Implementation Analysis\n\n"
                "You MUST read files before making changes:\n\n"
                "1. Use Glob: `{\"tool\": \"Glob\", \"arguments\": {\"pattern\": \"**/*.py\"}}`\n"
                "2. Read each file you plan to modify\n"
                "3. Understand the existing code structure\n"
                "4. Identify exact modification points\n"
                "5. Use [Evidence: file:line] for all claims\n\n"
                "⚠️ NEVER invent filenames — only use what Glob returns!"
            )

        if write_count == 0:
            return (
                "📍 PHASE 1 CONTINUE: Analysis In Progress\n\n"
                "Good — you're reading files. Continue analysis:\n\n"
                "1. Use Glob for any remaining files you need\n"
                "2. Read ALL target files before editing\n"
                "3. Document the exact change locations\n"
                "4. Plan the diff: old text → new text\n\n"
                "When analysis is complete, proceed to Phase 2: Code Generation."
            )

        return (
            "📍 PHASE 1 → PHASE 2: Analysis Complete\n\n"
            "You've started writing code. Continue with Phase 2:\n\n"
            "Use the 3-pass strategy:\n"
            "Pass 1: Create skeleton (classes, signatures, imports)\n"
            "Pass 2: Implement logic (function bodies, error handling)\n"
            "Pass 3: Polish (docstrings, naming, consistency)\n\n"
            "One change at a time — verify each Edit before proceeding."
        )

    def _phase2_continuation(
            self,
            round_num: int,
            all_results: List[Dict],
            context: Optional[AgentContext] = None,
            plan_content: str = ""
    ) -> str:
        """Phase 2: Code Generation continuation with plan alignment."""
        write_count = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['write', 'edit', 'writetool', 'edittool']
            and '.hcode' not in str(r.get('file_path', ''))
        )
        task_edit_count = sum(
            1 for r in all_results
            if r.get('success')
            and 'task.md' in str(r.get('file_path', ''))
            and r.get('tool', '').lower() in ['edit', 'edittool']
        )

        progress_summary = ""
        if context and plan_content:
            progress_summary = self._get_plan_progress_summary(context, plan_content)

        if write_count == 0:
            return (
                "📍 PHASE 2: Code Generation (3-Pass Strategy) + Plan Verification\n\n"
                "**CRITICAL**: At each pass, VERIFY your changes align with "
                "`.hcode/implementation_plan.md`\n\n"
                f"{progress_summary}\n"
                "**3-Pass Implementation**:\n\n"
                "Pass 1: Structure + Plan Alignment Check\n"
                "- [ ] Create file structure (classes, functions, imports)\n"
                "- [ ] VERIFY: Does structure match plan expectations?\n"
                "- [ ] If deviating from plan, document WHY\n\n"
                "Pass 2: Logic Implementation + Plan Step Mapping\n"
                "- [ ] Implement function bodies\n"
                "- [ ] VERIFY: Which plan steps does this complete?\n"
                "- [ ] If approach differs from plan, explain reasoning\n\n"
                "Pass 3: Polish + Final Plan Cross-Check\n"
                "- [ ] Add error handling, edge cases\n"
                "- [ ] VERIFY: Are all relevant plan requirements satisfied?\n"
                "- [ ] Document any intentional deviations\n\n"
                "Remember: Use Write/Edit tools, never raw code text!"
            )

        if task_edit_count == 1:
            return (
                "📍 PHASE 2 CONTINUE: Implementation In Progress + Plan Alignment\n\n"
                f"Good progress — {write_count} file modification(s) made.\n\n"
                f"{progress_summary}\n"
                "Continue with Phase 2 until all code changes are complete:\n"
                "- [ ] Finish Pass 2 logic if needed\n"
                "- [ ] Apply Pass 3 polish\n"
                "- [ ] VERIFY: Does your code match the plan?\n"
                "- [ ] Document any deviations from the plan\n\n"
                "When code is complete, proceed to Phase 3: Self-Validation."
            )

        return (
            "📍 PHASE 2 → PHASE 3: Implementation Complete\n\n"
            "Code changes are done. Now proceed to Phase 3:\n\n"
            "1. Re-read ALL modified files\n"
            "2. Trace execution with sample inputs\n"
            "3. Cross-check against `.hcode/implementation_plan.md`\n"
            "4. Mark task as [x] in `.hcode/task.md`\n\n"
            "Validate thoroughly before marking complete!"
        )

    def _phase3_continuation(
            self, round_num: int, all_results: List[Dict]
    ) -> str:
        """Phase 3: Self-Validation continuation."""
        task_edit_count = sum(
            1 for r in all_results
            if r.get('success')
            and 'task.md' in str(r.get('file_path', ''))
            and r.get('tool', '').lower() in ['edit', 'edittool']
        )

        if task_edit_count == 1:
            return (
                "📍 PHASE 3: Self-Validation + Deviation Report + File Verification\n\n"
                "Code changes are done. Now validate:\n\n"
                "**Step 1: File Verification**\n"
                "- [ ] Verify ALL planned files were created/modified\n"
                "- [ ] Use Read tool to confirm files exist and have content\n"
                "- [ ] If any files are missing, do NOT mark task [x]\n\n"
                "**Step 2: Logic Validation**\n"
                "- [ ] Re-read all modified files\n"
                "- [ ] Walk through execution mentally with test cases\n\n"
                "**Step 3: Plan Compliance**\n"
                "- [ ] Verify against `.hcode/implementation_plan.md`\n"
                "- [ ] Did you complete ALL plan steps for this task?\n\n"
                "**Step 4: Deviation Report** (REQUIRED)\n"
                "- [ ] Document any deviations from plan\n\n"
                "**Step 5: Task Completion Decision**\n"
                "- [ ] If ALL verified: Mark task as [x] in `.hcode/task.md`\n"
                "- [ ] If incomplete: Keep task as [/] and document what remains\n\n"
                "⚠️  CRITICAL: Only mark [x] if task is truly complete!"
            )

        return (
            "📍 PHASE 3 COMPLETE / NEXT TASK\n\n"
            "Task validation complete! Check for more work:\n\n"
            "1. Read `.hcode/task.md` to see remaining unchecked items\n"
            "2. If tasks remain, start Phase 0 for the next task\n"
            "3. If all tasks complete, provide final summary\n\n"
            "Summary should include:\n"
            "- Files modified\n"
            "- Changes implemented\n"
            "- Deviations from plan (if any)\n"
            "- Known issues (if any)\n"
            "- Verification status"
        )

    # ═══════════════════════════════════════════════════════════════════════
    # TRANSITION LOGIC
    # ═══════════════════════════════════════════════════════════════════════

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """Check if ready to transition to verification phase."""
        return self._check_execution_complete(context)

    def _check_execution_complete(self, context: AgentContext) -> bool:
        """Check if execution is complete."""
        non_artifact_files = [
            f for f in context.modified_files
            if ".hcode" not in f and not f.endswith("task.md")
               and not f.endswith("implementation_plan.md")
               and not f.endswith("walkthrough.md")
        ]

        non_artifact_actions = []
        for a in context.completed_actions:
            if a.get("tool", "").lower() in ["write", "edit", "writetool", "edittool"]:
                args = a.get("arguments", {})
                target_file = (
                        args.get("TargetFile", "")
                        or args.get("file_path", "")
                        or a.get("file_path", "")
                )
                if target_file and ".hcode" not in str(target_file):
                    non_artifact_actions.append(a)

        return len(non_artifact_files) > 0 or len(non_artifact_actions) > 0

    # ═══════════════════════════════════════════════════════════════════════
    # PLAN PARSING & STEP TRACKING
    # ═══════════════════════════════════════════════════════════════════════

    def _get_task_statistics(self, task_content: str) -> Dict[str, int]:
        """Count total, completed, and current task from task.md."""
        try:
            if not task_content:
                return {
                    'total': 0, 'completed': 0,
                    'in_progress': 0, 'pending': 0, 'current': 1
                }

            lines = task_content.split('\n')

            total = sum(
                1 for line in lines
                if re.match(r'^\s*-\s*\[[ x/]\]', line)
            )
            completed = sum(1 for line in lines if '- [x]' in line)
            in_progress = sum(1 for line in lines if '- [/]' in line)
            pending = total - completed - in_progress

            current_num = (
                completed + 1
                if (pending > 0 or in_progress > 0)
                else total
            )

            return {
                'total': total,
                'completed': completed,
                'in_progress': in_progress,
                'pending': pending,
                'current': current_num
            }
        except Exception as e:
            logger.debug(f"Task statistics calculation failed: {e}")
            return {
                'total': 0, 'completed': 0,
                'in_progress': 0, 'pending': 0, 'current': 1
            }

    def _parse_plan_steps(self, plan_content: str) -> List[Dict[str, Any]]:
        """Parse steps from implementation plan with enhanced pattern matching."""
        steps = []
        if not plan_content:
            return steps

        # Pattern 1: Numbered steps with bold names
        step_pattern = r'(\d+)\.\s*\*\*([^*]+)\*\*\s*:?\s*([^\n]*)'
        step_matches = re.findall(step_pattern, plan_content)

        for match in step_matches:
            step_num = int(match[0])
            step_name = match[1].strip()
            description = match[2].strip()

            step = self._extract_step_details(
                plan_content, step_num, step_name, description
            )
            steps.append(step)

        # Pattern 2: Markdown task lists with checkboxes
        task_pattern = r'^\s*[-*]\s*\[([ x])\]\s*(.+?)(?:\s*<!--\s*id:\s*(\d+)\s*-->)?$'
        task_matches = re.findall(task_pattern, plan_content, re.MULTILINE)

        for i, (checkbox, description, task_id) in enumerate(task_matches):
            is_completed = checkbox.lower() == 'x'
            steps.append({
                "number": len(step_matches) + i + 1,
                "name": description[:50] if len(description) > 50 else description,
                "description": description,
                "files": [],
                "actions": [description],
                "completed": is_completed,
                "id": int(task_id) if task_id else None,
            })

        logger.debug(f"Parsed {len(steps)} steps from implementation plan")
        return steps

    def _extract_step_details(
            self,
            plan_content: str,
            step_num: int,
            step_name: str,
            description: str,
    ) -> Dict[str, Any]:
        """Extract file paths and actions for a given step."""
        step = {
            "number": step_num,
            "name": step_name,
            "description": description,
            "files": [],
            "actions": [],
            "completed": False,
        }

        step_marker = f"{step_num}."
        step_start = plan_content.find(step_marker)
        next_step_marker = f"{step_num + 1}."
        next_step_pos = plan_content.find(next_step_marker, step_start)
        step_end = next_step_pos if next_step_pos != -1 else len(plan_content)
        step_content = plan_content[step_start:step_end]

        file_patterns = [
            r'(?:File|file|Path|path):\s*`([^`]+)`',
            r'(?:\[NEW\]|\[MODIFY\]|\[DELETE\])\s*`([^`]+)`',
            r'`([^`]+\.(?:py|js|ts|tsx|jsx|java|go|rs|c|cpp|h|yaml|yml|json|md|txt))`',
        ]

        for pattern in file_patterns:
            file_matches = re.findall(pattern, step_content)
            for path in file_matches:
                normalized = path.strip().strip('`').strip()
                if normalized and normalized not in step["files"]:
                    if '/' in normalized or '\\' in normalized or '.' in normalized.split('/')[-1]:
                        step["files"].append(normalized)

        return step

    def _update_task_progress(self, context: AgentContext) -> None:
        """Update task.md with current progress."""
        task_content = self.artifact_manager.load_artifact("task.md", context)
        if not task_content:
            logger.warning("task.md not found, cannot update progress")
            return

        completed_files = set(context.modified_files)
        lines = task_content.split('\n')
        updated_lines = []

        for line in lines:
            checkbox_match = re.match(r'^(\s*-\s*)\[[ ]\]\s*(.+)$', line)

            if checkbox_match:
                prefix = checkbox_match.group(1)
                task_text = checkbox_match.group(2)

                should_complete = False

                for file_path in completed_files:
                    file_name = file_path.split('/')[-1].split('\\')[-1]
                    if file_name in task_text or file_path in task_text:
                        should_complete = True
                        break

                for action in context.completed_actions:
                    tool_name = action.get("tool", "").lower()
                    if tool_name in task_text.lower():
                        should_complete = True
                        break

                if should_complete:
                    updated_lines.append(f"{prefix}[x] {task_text}")
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        updated_content = '\n'.join(updated_lines)

        if updated_content != task_content:
            progress_section = f"""

## Progress Update

- Modified files: {len(context.modified_files)}
- Completed actions: {len(context.completed_actions)}
- Iteration: {context.iteration}
"""
            if "## Progress Update" not in updated_content:
                updated_content += progress_section

            self.artifact_manager.create_artifact("task.md", updated_content, context)
            logger.debug("Updated task.md with progress")

    def _check_step_completion(
            self,
            step: Dict[str, Any],
            context: AgentContext
    ) -> bool:
        """Check if a specific step is completed."""
        for file_path in step.get("files", []):
            normalized = file_path.replace('\\', '/').strip('`')
            for modified in context.modified_files:
                if normalized in modified or modified.endswith(normalized):
                    return True

        if step.get("completed", False):
            return True

        return False

    def _get_next_incomplete_step(
            self,
            plan_content: str,
            context: AgentContext
    ) -> Optional[Dict[str, Any]]:
        """Get the next step that hasn't been completed."""
        steps = self._parse_plan_steps(plan_content)

        for step in steps:
            if not self._check_step_completion(step, context):
                return step

        return None

    def _discover_codebase_structure(self, context: AgentContext) -> str:
        """Pre-discover codebase structure before execution starts."""
        try:
            cwd = Path(context.working_dir)

            dirs = []
            for d in cwd.rglob("*"):
                if d.is_dir() and not any(part.startswith(".") for part in d.parts):
                    try:
                        relative_path = d.relative_to(cwd)
                        dirs.append(str(relative_path))
                        if len(dirs) >= 20:
                            break
                    except ValueError:
                        continue

            py_files = []
            for f in cwd.rglob("*.py"):
                if not any(part.startswith(".") for part in f.parts):
                    try:
                        relative_path = f.relative_to(cwd)
                        py_files.append(str(relative_path))
                        if len(py_files) >= 30:
                            break
                    except ValueError:
                        continue

            config_extensions = ['json', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'md']
            config_files = []
            for ext in config_extensions:
                for f in cwd.glob(f"*.{ext}"):
                    if f.is_file():
                        config_files.append(f.name)
                        if len(config_files) >= 15:
                            break
                if len(config_files) >= 15:
                    break

            dir_list = ', '.join(dirs[:20]) if dirs else 'None'
            py_list = ', '.join(py_files[:10]) if py_files else 'None'
            py_more = f'... and {len(py_files) - 10} more' if len(py_files) > 10 else ''
            config_list = ', '.join(config_files) if config_files else 'None'

            return f"""
---

## CODEBASE STRUCTURE (Pre-Discovered)

**Key Directories ({len(dirs)})**: {dir_list}

**Python Files ({len(py_files)})**: {py_list} {py_more}

**Config Files ({len(config_files)})**: {config_list}

(Use Glob/Read tools to explore further)

---
"""
        except Exception as e:
            logger.debug(f"Codebase discovery failed: {e}")
            return ""

    def _get_plan_progress_summary(
            self, context: AgentContext, plan_content: str
    ) -> str:
        """Generate summary of plan step completion for AI awareness."""
        try:
            steps = self._parse_plan_steps(plan_content)
            if not steps:
                return ""

            total = len(steps)
            completed = sum(
                1 for step in steps
                if self._check_step_completion(step, context)
            )

            status_lines = []
            for i, step in enumerate(steps[:5], 1):
                status = "✓" if self._check_step_completion(step, context) else "○"
                step_name = step.get('name', 'Unnamed')
                status_lines.append(f"{status} Step {i}: {step_name}")

            more_indicator = '...' if total > 5 else ''

            return f"""
**Plan Progress**: {completed}/{total} steps complete
{chr(10).join(status_lines)}
{more_indicator}
"""
        except Exception as e:
            logger.debug(f"Plan progress summary failed: {e}")
            return ""