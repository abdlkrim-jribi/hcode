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
import os
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
    MAX_ROUNDS = 35  # High enough for multi-task execution (5-7 tasks)
    MAX_RETRIES = 4  # Max re-entries when tasks remain incomplete
    TIMEOUT_SECONDS = 1800  # 30 minutes for execution phase

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

        # Track files already read this session to prevent unnecessary re-reads
        self._files_read_this_session = set()  # Set of file paths already read
        self._cache_ttl = 60  # seconds

        # GPT OSS 120B specific tracking
        self._current_phase_state = 'phase0'
        self._phase_transition_history = []
        self._reasoning_depth = 0

        # Track unresolved bash/command failures across rounds
        # Each entry: {"command": str, "exit_code": int, "error": str}
        self._failed_commands = []

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
                if step_info:
                    self._display(step_info, style="thinking")

                # Display task progress via HcodeDisplay if available
                if self._hcode_display and task_stats['total'] > 0:
                    progress_msg = f"Executing: Task {task_stats['current']}/{task_stats['total']}"
                    self._display(progress_msg, style="info")

                # Start execution thinking display
                if self._hcode_display:
                    self._hcode_display.start_thinking()

                system_prompt = self._get_execution_system_prompt(context)

                response_text, tool_results = await self._generate_and_execute(
                    prompt,
                    context,
                    system_prompt=system_prompt,
                    max_rounds=GPTOSSConfig.MAX_ROUNDS,
                    max_tokens=GPTOSSConfig.MAX_TOKENS,
                    temperature=GPTOSSConfig.TEMPERATURE,
                    timeout_seconds=GPTOSSConfig.TIMEOUT_SECONDS,
                    include_history=True,
                )

                # ── Track failed commands from this execution round ──
                self._track_command_failures(tool_results)

                # ── Track files read to prevent redundant re-reads ──
                self._track_read_files(tool_results)

                # ── RETRY LOOP: Re-enter if tasks remain unchecked ──
                # When the AI stops producing tool calls (summary mode),
                # check task.md. If unchecked tasks remain, re-invoke with
                # a focused prompt to continue the next task.
                for retry in range(GPTOSSConfig.MAX_RETRIES):
                    remaining = self._count_remaining_tasks(context)
                    has_unresolved = len(self._failed_commands) > 0
                    if remaining == 0 and not has_unresolved:
                        break

                    issue_parts = []
                    if remaining > 0:
                        issue_parts.append(f"{remaining} unchecked task(s)")
                    if has_unresolved:
                        issue_parts.append(f"{len(self._failed_commands)} failed command(s)")
                    issue_summary = " and ".join(issue_parts)

                    logger.info(
                        f"[execution] Retry {retry + 1}/{GPTOSSConfig.MAX_RETRIES}: "
                        f"{issue_summary} remain — re-entering"
                    )
                    self._display(
                        f"  {issue_summary} remaining — continuing execution",
                        style="info"
                    )

                    # Refresh task.md for the continuation prompt
                    fresh_task = self.artifact_manager.load_artifact(
                        "task.md", context
                    ) or ""

                    # Build retry prompt with failed-command context
                    retry_prompt = ""
                    if has_unresolved:
                        failure_details = "\n".join(
                            f"- `{fc['command']}` failed (exit code {fc.get('exit_code', '?')}): "
                            f"{fc.get('error', 'unknown error')[:200]}"
                            for fc in self._failed_commands
                        )
                        retry_prompt += (
                            f"⚠️ CRITICAL: The following command(s) FAILED and you MUST fix them "
                            f"before marking any task as complete:\n{failure_details}\n\n"
                            f"DO NOT mark a task as `[x]` if its verification command failed. "
                            f"Investigate the failure, fix the root cause, and re-run the command.\n\n"
                        )
                    if remaining > 0:
                        retry_prompt += (
                            f"You stopped but there are still {remaining} unchecked "
                            f"task(s) in `.hcode/task.md`. You MUST complete them all.\n\n"
                        )
                    retry_prompt += (
                        f"Current task.md:\n{fresh_task}\n\n"
                        f"Continue with Phase 0: find the next unchecked `- [ ]` task, "
                        f"mark it `[/]`, implement it (Phases 1-2-3), then check for more."
                    )

                    retry_text, retry_results = await self._generate_and_execute(
                        retry_prompt,
                        context,
                        system_prompt=system_prompt,
                        max_rounds=GPTOSSConfig.MAX_ROUNDS,
                        max_tokens=GPTOSSConfig.MAX_TOKENS,
                        temperature=GPTOSSConfig.TEMPERATURE,
                        timeout_seconds=GPTOSSConfig.TIMEOUT_SECONDS,
                    )

                    response_text = retry_text
                    tool_results.extend(retry_results)

                    # Update failure tracking after retry round
                    self._track_command_failures(retry_results)
                    self._track_read_files(retry_results)

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

            # NOTE: Do NOT call _update_task_progress here.
            # The AI manages task markers via its own Edit calls on task.md.
            # Auto-updating behind its back causes state desync and Edit failures.

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
        Execution-phase tool executor.

        Delegates entirely to the parent implementation. Tool execution
        status messages are shown (e.g., "[>] Read: file.py").
        Thinking blocks are displayed before tool execution.
        The Edit tool itself provides helpful error messages with file
        context when edits fail. Only adds cache invalidation for
        subsequent reads.
        """
        results = await super()._execute_tools(tool_calls, context, silent=False)

        # Post-processing: invalidate cache when files are modified
        for result in results:
            if result.get("success"):
                tool_name = result.get("tool", "").lower()
                if tool_name in ("write", "writetool", "edit", "edittool"):
                    file_path = result.get("file_path", "")
                    if file_path in self._file_cache:
                        del self._file_cache[file_path]

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

            self.artifact_manager.load_artifact(
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

    def _load_execution_protocol(self) -> str:
        """
        Load execution_handler.md prompt file.

        Returns:
            Content of execution_handler.md, or a condensed fallback.
        """
        try:
            # We assume config is available at proper location
            # If prompt loader fails, we fallback to inline
            # This is just a helper, actual loading done in _get_execution_system_prompt
            pass
        except:
             pass

        try:
             # Basic file read attempt if module import fails
            prompt_dir = (
                    Path(__file__).parent.parent.parent
                    / "config" / "core_prompts" / "core" / "pev_prompts"
            )
            protocol_path = prompt_dir / "execution_handler.md"

            if protocol_path.exists():
                return protocol_path.read_text(encoding="utf-8")
        except Exception:
            pass

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
- READ BEFORE Edit — always
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

        return f"""## EXECUTION PHASE

Execute the implementation plan one task at a time: Phase 0 (select) → 1 (analyze) → 2 (implement) → 3 (validate).

### Implementation Plan:
{plan_content}

### Session State:
- Working Directory: {context.working_dir}
- Iteration: {context.iteration}
- Modified files: {modified_files_list}
- Recent actions: {actions_summary}

### KEY RULES:
- Artifacts are at `.hcode/task.md` and `.hcode/implementation_plan.md` (NOT in root)
- Glob first → Read → then Write/Edit. Never invent filenames.
- THINK deeply between every tool call — explain what you learned and why you're taking the next action.

BEGIN Phase 0:
1. Read `.hcode/task.md` to see CURRENT state of all tasks
2. Find next task to work on:
   - If you see a task with `[/]` (in-progress), continue working on it (skip to step 4)
   - If no `[/]` tasks, find first `[ ]` (unchecked) task
3. ONLY if task is currently `[ ]`: Mark it as `[/]` via Edit
4. Understand the task from the plan, then proceed to Phase 1."""

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

    def _build_task_progress_message(self, context: Any) -> str:
        """
        Build a task progress message showing the EXACT state of every task.

        Enhanced with:
        - Exact per-task state listing ([x], [/], [ ])
        - File-existence verification for completed tasks (ghost completion guard)
        - "Already read" file list to prevent redundant re-reads
        """
        if context is None:
            return ""

        try:
            task_content = self.artifact_manager.load_artifact("task.md", context)
            if not task_content:
                return ""

            # Parse task lines with their exact markers
            task_lines = re.findall(
                r'^\s*-\s*\[([ x/!])\]\s*(.+?)\s*$',
                task_content, re.MULTILINE
            )

            if not task_lines:
                return ""

            # ── Verify completed tasks actually delivered their files ──
            ghost_warnings = []
            verified_task_lines = []
            for marker, text in task_lines:
                clean_text = re.sub(r'\s*<!--.*?-->\s*$', '', text).strip()
                if marker == 'x':
                    # Extract backtick-quoted file paths from the task description
                    mentioned_files = re.findall(r'`([^`]+\.[a-z]{1,4})`', clean_text)
                    missing = []
                    for mf in mentioned_files:
                        # Resolve relative to project root
                        if context and hasattr(context, 'project_root') and context.project_root:
                            full_path = os.path.join(context.project_root, mf)
                        else:
                            full_path = mf
                        if not os.path.exists(full_path):
                            missing.append(mf)
                    if missing:
                        # Ghost completion detected — file marked done but never created
                        ghost_warnings.append(clean_text)
                        verified_task_lines.append(('!', text))  # Downgrade to failed
                        logger.warning(
                            f"[execution] Ghost completion: task marked [x] but file(s) "
                            f"not found: {missing}"
                        )
                    else:
                        verified_task_lines.append((marker, text))
                else:
                    verified_task_lines.append((marker, text))

            total = len(verified_task_lines)
            done = sum(1 for m, _ in verified_task_lines if m == 'x')
            in_progress = sum(1 for m, _ in verified_task_lines if m == '/')
            unchecked = sum(1 for m, _ in verified_task_lines if m == ' ')
            failed = sum(1 for m, _ in verified_task_lines if m == '!')

            if unchecked == 0 and in_progress == 0 and failed == 0:
                return (
                    f"\n\nALL TASKS COMPLETED ({done}/{total}). "
                    f"All subtasks in `.hcode/task.md` are marked `[x]`. "
                    f"Provide a brief summary of what was accomplished and stop."
                )

            # Build detailed task state listing
            state_lines = []
            for marker, text in verified_task_lines:
                text = text.strip()
                text = re.sub(r'\s*<!--.*?-->\s*$', '', text).strip()
                if marker == 'x':
                    state_lines.append(f"  [x] {text}")
                elif marker == '/':
                    state_lines.append(f"  [/] {text}  ← IN PROGRESS")
                elif marker == '!':
                    state_lines.append(f"  [!] {text}  ← FILE NOT CREATED")
                else:
                    state_lines.append(f"  [ ] {text}")
            task_listing = "\n".join(state_lines)

            progress = (
                f"\n\n📋 TASK PROGRESS: {done}/{total} completed, "
                f"{unchecked} remaining"
            )
            if in_progress:
                progress += f", {in_progress} in-progress"
            if failed:
                progress += f", {failed} FAILED (file not created)"
            progress += f".\nCurrent task states:\n{task_listing}"

            # ── Ghost completion warnings ──
            if ghost_warnings:
                progress += (
                    f"\n\n🚨 GHOST COMPLETION DETECTED: {len(ghost_warnings)} task(s) were "
                    f"marked [x] but the output file was NEVER CREATED. "
                    f"You MUST actually create the file using the Write tool before "
                    f"marking the task complete. Fix these tasks FIRST."
                )

            # Add specific guidance based on state
            if in_progress > 0:
                progress += (
                    f"\n\n⚠️ You have {in_progress} task(s) marked [/]. "
                    "Complete the in-progress task first (mark [x]) before starting a new one."
                )
            elif failed == 0:
                progress += (
                    "\n\nContinue to the next unchecked `- [ ]` task "
                    "— mark it `[/]`, implement it, then mark `[x]`."
                )

            progress += (
                "\n⚠️ ALWAYS Read `.hcode/task.md` BEFORE editing it "
                "— the file state may differ from what you expect."
            )

            # ── Already-read files (prevent redundant re-reads) ──
            if self._files_read_this_session:
                # Only show non-artifact files to keep it relevant
                non_artifact_reads = [
                    p for p in sorted(self._files_read_this_session)
                    if '.hcode' not in p
                    and 'task.md' not in p
                    and 'implementation_plan.md' not in p
                ]
                if non_artifact_reads:
                    read_list = "\n".join(f"  - {p}" for p in non_artifact_reads[:15])
                    progress += (
                        f"\n\n📂 Files already read this session (do NOT re-read unless modified):\n"
                        f"{read_list}"
                    )

            return progress

        except Exception as e:
            logger.debug(f"[execution] Task progress check failed: {e}")
            return ""

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
        - Task progress injection (remaining task count after every round)
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

        # ── TASK PROGRESS INJECTION ──
        # After every round, tell the AI exactly how many tasks remain.
        # This prevents the AI from stopping early after completing just one task.
        task_progress = self._build_task_progress_message(context)

        # Check for errors in recent rounds
        recent_errors = [
            r for r in round_results[-3:]
            if not r.get('success')
        ]

        if recent_errors:
            error_msg = self._build_error_recovery_prompt(recent_errors)
            if error_msg:
                return error_msg + task_progress

        # Phase-specific continuation
        phase_msg = ""
        if current_phase == 'phase0':
            phase_msg = self._phase0_continuation(round_num, all_results)
        elif current_phase == 'phase1':
            phase_msg = self._phase1_continuation(round_num, all_results)
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
            phase_msg = self._phase2_continuation(round_num, all_results, context, plan_content)
        elif current_phase == 'phase3':
            phase_msg = self._phase3_continuation(round_num, all_results)

        if phase_msg:
            return phase_msg + task_progress

        # Round limit push
        if round_num >= 20:
            return (
                "Approaching round limit. Wrap up now:\n"
                "1. Finish pending code changes\n"
                "2. Update `.hcode/task.md` with current status\n"
                "3. Summarize what was accomplished and what remains"
            ) + task_progress

        return (
            f"Continue (phase: {current_phase}). "
            "THINK about what you learned so far and what's next. "
            "Read before Edit. Cite evidence. Update `.hcode/task.md` when done."
        ) + task_progress

    def _build_error_recovery_prompt(
            self, errors: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Build targeted error recovery prompt based on error types."""
        if not errors:
            return None

        error_types = []
        edit_failures = 0
        bash_failures = []
        for error in errors:
            tool = error.get('tool', '').lower()
            err_msg = str(error.get('error', error.get('output', '')) or '')

            if tool in ('edit', 'edittool') and not error.get('success', True):
                edit_failures += 1

            # Detect bash/command execution failures
            if tool in ('bash', 'bashtool') and not error.get('success', True):
                error_types.append('command_failed')
                bash_failures.append(error)

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

        # ── COMMAND FAILURE (highest priority) ──
        # A bash command failed — the AI MUST NOT mark the related task done.
        if 'command_failed' in error_types and bash_failures:
            failure_details = []
            for bf in bash_failures:
                cmd_err = str(bf.get('error', 'unknown error'))[:300]
                cmd_out = str(bf.get('output', ''))[:300]
                failure_details.append(
                    f"  Error: {cmd_err}"
                    + (f"\n  Output: {cmd_out}" if cmd_out.strip() else "")
                )
            details_str = "\n".join(failure_details)
            return (
                f"⚠️ COMMAND FAILED — A bash command exited with a non-zero status.\n"
                f"{details_str}\n\n"
                f"You MUST:\n"
                f"1. Investigate WHY the command failed (read error output carefully)\n"
                f"2. Fix the root cause (edit code, fix imports, resolve errors)\n"
                f"3. Re-run the command to verify the fix\n"
                f"4. Do NOT mark any task as `[x]` until the command passes successfully\n"
                f"5. If the task says the command should pass, it MUST pass before completion"
            )

        # Retry limit exceeded
        if 'retry_limit' in error_types or edit_failures >= 3:
            return (
                "STOP: Edit failed multiple times. "
                "Re-read the target file fresh, then CHANGE your approach. "
                "Consider using Write to replace the entire file instead of Edit."
            )

        if 'edit_params' in error_types:
            return (
                'Edit requires: {"tool": "Edit", "arguments": '
                '{"file_path": "...", "old_string": "...", "new_string": "..."}}'
            )

        if 'edit_duplicate' in error_types:
            return (
                "old_string appears multiple times. Add more surrounding context "
                "to make it unique, or use replace_all=True."
            )

        if 'file_not_found' in error_types:
            return (
                "File not found. Use Glob to discover actual file paths. "
                "Never invent filenames."
            )

        if 'edit_mismatch' in error_types:
            return (
                "Edit failed: old_string not found in file. "
                "Read the file to see CURRENT content, verify what state it's in, "
                "then use exact text from the file."
            )

        return (
            "Tool call failed. THINK about the error message. "
            "Diagnose the root cause, then fix it before continuing."
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
                "You haven't started yet. Read `.hcode/task.md` to see CURRENT task states.\n\n"
                "Find next task:\n"
                "- If you see `[/]` (in-progress), continue with that task (skip to Phase 1)\n"
                "- If no `[/]`, find first `[ ]` (unchecked) and mark it `[/]`\n\n"
                "ONLY mark a task if it's currently `[ ]`. If already `[/]`, just continue.\n\n"
                "THINK: What does this task involve? What files will it touch?"
            )

        return (
            "Task selected. Now THINK deeply before touching any code:\n\n"
            "- What files does the plan say to modify? Use Glob to find them.\n"
            "- What do you expect to find in those files?\n"
            "- What patterns should you follow from existing code?\n\n"
            "Read ALL target files before any modifications."
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
                "You need to understand the code before changing it. "
                "Use Glob to discover files, then Read each one.\n\n"
                "THINK: What structure do you expect? What patterns should "
                "your implementation follow? What imports will you need?"
            )

        if write_count == 0:
            return (
                "You've been reading files. Before you start writing code, PAUSE and think:\n\n"
                "- What did you learn from the files you read?\n"
                "- What exact changes will you make? (old text → new text)\n"
                "- What could go wrong? Are there callers that need updating?\n"
                "- Does your planned approach match the implementation plan?\n\n"
                "When you have clear answers, proceed to implement."
            )

        return (
            "You're implementing code. Continue with the 3-pass approach:\n"
            "Pass 1 (skeleton) → Pass 2 (logic) → Pass 3 (polish).\n\n"
            "After each change, briefly explain what you did and why. "
            "Verify each Edit succeeded before moving on."
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
                f"{progress_summary}\n"
                "Time to write code. THINK about each change before making it:\n\n"
                "- What's the simplest correct implementation?\n"
                "- Does it match what the plan specifies?\n"
                "- What edge cases matter?\n\n"
                "Use Write for new files, Edit for modifications. "
                "After each change, explain what you did and verify it succeeded."
            )

        if task_edit_count == 1:
            return (
                f"Good progress — {write_count} file(s) modified.\n"
                f"{progress_summary}\n\n"
                "REFLECT: Is the implementation complete for this task? "
                "Re-read your changes. Do they match the plan? "
                "Any edge cases missed?\n\n"
                "If complete, proceed to Phase 3 validation. "
                "If not, continue implementing."
            )

        return (
            "Implementation looks done. Now VALIDATE before marking complete:\n\n"
            "1. **Review** the code (mentally) — does the final code look correct?\n"
            "2. Mental trace — walk through with a test input\n"
            "3. Plan check — did you cover everything the plan asked for?\n"
            "4. Mark `[x]` in `.hcode/task.md` only if confident\n\n"
            "WARNING: Do NOT re-read files you already read — review from memory."
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

        # Check if any actual files were modified (not just task.md)
        file_modifications = sum(
            1 for r in all_results
            if r.get('success')
            and '.hcode' not in str(r.get('file_path', ''))
            and r.get('tool', '').lower() in ['write', 'edit', 'writetool', 'edittool']
        )

        if task_edit_count == 1:
            if file_modifications == 0:
                return (
                    "ERROR: You marked a task in-progress but haven't modified any files!\n\n"
                    "You CANNOT mark a task as complete without using Write or Edit tools.\n"
                    "You've only read files. Now you must:\n"
                    "1. Use Write or Edit to create/modify the required files\n"
                    "2. THEN mark the task [x] in task.md\n\n"
                    "DO NOT mark [x] again until you've actually written code."
                )
            return (
                "Validate before marking complete:\n\n"
                "1. **Review** the code you wrote (mentally, from memory) — is it correct?\n"
                "2. Mental trace with sample input — does execution flow correctly?\n"
                "3. Check plan compliance — did you implement everything asked?\n"
                "4. If any deliverable is missing, keep task as [/]\n\n"
                "THINK: What could I have missed? Are there any subtle bugs?"
            )

        return (
            "Task validated! Read `.hcode/task.md` for remaining tasks.\n\n"
            "If more tasks exist, start Phase 0 for the next one.\n"
            "If all done, provide a summary of files modified, "
            "changes made, and any deviations from the plan."
        )

    # ═══════════════════════════════════════════════════════════════════════
    # TRANSITION LOGIC
    # ═══════════════════════════════════════════════════════════════════════

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """Check if ready to transition to verification phase."""
        return self._check_execution_complete(context)

    def _check_execution_complete(self, context: AgentContext) -> bool:
        """
        Check if execution is complete.

        Returns True only when:
        1. At least one non-artifact file was modified, AND
        2. No unchecked tasks remain in task.md (all are [x] or [/]), AND
        3. No unresolved command failures exist
        """
        # Block completion if there are unresolved command failures
        if self._failed_commands:
            logger.info(
                f"[execution] {len(self._failed_commands)} unresolved command failure(s) "
                f"— execution NOT complete"
            )
            return False

        # Must have modified at least one real file
        non_artifact_files = [
            f for f in context.modified_files
            if ".hcode" not in f and not f.endswith("task.md")
               and not f.endswith("implementation_plan.md")
               and not f.endswith("walkthrough.md")
        ]

        if not non_artifact_files:
            # Also check completed actions as fallback
            has_non_artifact_action = False
            for a in context.completed_actions:
                if a.get("tool", "").lower() in ["write", "edit", "writetool", "edittool"]:
                    args = a.get("arguments", {})
                    target_file = (
                            args.get("TargetFile", "")
                            or args.get("file_path", "")
                            or a.get("file_path", "")
                    )
                    if target_file and ".hcode" not in str(target_file):
                        has_non_artifact_action = True
                        break
            if not has_non_artifact_action:
                return False

        # Check task.md for remaining unchecked or in-progress items
        task_content = self.artifact_manager.load_artifact("task.md", context)
        if task_content:
            unchecked = re.findall(r'^\s*-\s*\[ \]', task_content, re.MULTILINE)
            in_progress = re.findall(r'^\s*-\s*\[/\]', task_content, re.MULTILINE)
            incomplete = len(unchecked) + len(in_progress)
            if incomplete:
                logger.info(
                    f"[execution] {len(unchecked)} unchecked + {len(in_progress)} "
                    f"in-progress tasks remain in task.md — execution NOT complete"
                )
                return False

        return True

    def _count_remaining_tasks(self, context: AgentContext) -> int:
        """Count incomplete tasks (unchecked [ ] and in-progress [/]) in task.md."""
        task_content = self.artifact_manager.load_artifact("task.md", context)
        if not task_content:
            return 0
        unchecked = re.findall(r'^\s*-\s*\[ \]', task_content, re.MULTILINE)
        in_progress = re.findall(r'^\s*-\s*\[/\]', task_content, re.MULTILINE)
        return len(unchecked) + len(in_progress)

    def _track_command_failures(self, tool_results: List[Dict[str, Any]]) -> None:
        """Track and resolve bash/command failures across rounds.

        - Adds new failures when a bash command returns success=False.
        - Removes (resolves) a previously-failed command when a subsequent
          execution of a similar command succeeds.
        """
        for result in tool_results:
            tool = result.get("tool", "").lower()
            if tool not in ("bash", "bashtool"):
                continue

            cmd = str(result.get("arguments", {}).get("command", "")
                      or result.get("arguments", {}).get("CommandLine", "")
                      or "")

            if result.get("success", True):
                # Command succeeded — clear matching failures
                self._failed_commands = [
                    fc for fc in self._failed_commands
                    if fc.get("command", "") != cmd
                ]
            else:
                # Command failed — record if not already tracked
                already_tracked = any(
                    fc.get("command", "") == cmd
                    for fc in self._failed_commands
                )
                if not already_tracked:
                    exit_code = None
                    metadata = result.get("metadata", {})
                    if isinstance(metadata, dict):
                        exit_code = metadata.get("exit_code")
                    self._failed_commands.append({
                        "command": cmd,
                        "exit_code": exit_code,
                        "error": str(result.get("error", ""))[:500],
                    })
                    logger.warning(
                        f"[execution] Tracked command failure: {cmd[:100]} "
                        f"(exit code {exit_code})"
                    )

    def _track_read_files(self, tool_results: List[Dict[str, Any]]) -> None:
        """Track files that the AI has read to prevent redundant re-reads.

        Scans tool results for Read/Glob operations and adds their file paths
        to _files_read_this_session. The progress message then includes this
        list so the AI knows not to re-read files it already processed.
        """
        read_tools = {'read', 'readtool'}
        for result in tool_results:
            tool = result.get("tool", "").lower()
            if tool not in read_tools:
                continue
            if not result.get("success", False):
                continue

            file_path = result.get("file_path", "")
            if file_path:
                # Normalize to relative path for cleaner display
                try:
                    rel = os.path.relpath(file_path)
                    self._files_read_this_session.add(rel)
                except ValueError:
                    # On Windows, relpath fails across drives
                    self._files_read_this_session.add(file_path)

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
        """Update task.md with current progress.

        Does NOT auto-complete tasks if there are unresolved command failures,
        since a task should only be marked done when all its deliverables
        (including passing verification commands) are confirmed.
        """
        task_content = self.artifact_manager.load_artifact("task.md", context)
        if not task_content:
            logger.warning("task.md not found, cannot update progress")
            return

        # If there are unresolved command failures, skip auto-completion
        # to avoid falsely marking tasks as done.
        if self._failed_commands:
            logger.info(
                f"[execution] Skipping task auto-completion: "
                f"{len(self._failed_commands)} unresolved command failure(s)"
            )
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