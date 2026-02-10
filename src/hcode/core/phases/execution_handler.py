"""
Execution Phase Handler — 4-Phase Implementation Protocol
==========================================================

Implements the *Execution* phase of the PEV workflow with a structured
4-phase protocol optimized for GPT OSS 120B reasoning:

- **Phase 0: Task Selection** — Parse task.md, select next optimal subtask
- **Phase 1: Pre-Implementation Analysis** — Deep analysis before coding
- **Phase 2: Iterative Code Generation** — 3-pass: skeleton → logic → polish
- **Phase 3: Self-Validation** — Verify correctness before handoff

The handler loads execution_handler.md as the primary prompt template and
uses phase-aware continuation prompts to steer the AI through each phase.
"""

import logging
import re
from pathlib import Path
from typing import List, Any, Dict, Optional

from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult

# FileAction enum for HcodeDisplay tracking
try:
    from hcode.ui.hcode_display import FileAction
except ImportError:
    FileAction = None

logger = logging.getLogger(__name__)


class ExecutionPhaseHandler(BasePhaseHandler):
    """
    Handler for the Execution phase of PEV workflow.

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

    def get_required_artifacts(self) -> List[str]:
        """Execution phase doesn't produce new artifacts."""
        return []

    # ═══════════════════════════════════════════════════════════════════════
    # MAIN HANDLER
    # ═══════════════════════════════════════════════════════════════════════

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute implementation phase using the 4-phase protocol.

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

            # Find next incomplete step for display
            next_step = self._get_next_incomplete_step(plan_content, context)
            step_info = ""
            if next_step:
                step_info = f"Working on: {next_step.get('name', 'Step ' + str(next_step.get('number', '?')))}"
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

                # Start execution thinking display
                if self._hcode_display:
                    self._hcode_display.start_thinking()

                response_text, tool_results = await self._generate_and_execute(
                    prompt,
                    context,
                    system_prompt=self._get_execution_system_prompt(context),
                    max_rounds=20,  # Increased from 12 to match planning phase capacity
                    max_tokens=16384,
                    temperature=0.3,  # Deterministic code generation
                    timeout_seconds=900,  # 15 minutes for execution phase
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
                                action = FileAction.CREATED if tool_name in ['write', 'writetool'] else FileAction.EDITED
                                self._hcode_display.track_file(file_path, action)

            # Update task.md with progress after tool execution
            if tool_results:
                self._update_task_progress(context)

            # Check if can transition (implementation sufficient)
            can_transition = self._check_execution_complete(context)

            # Build output message
            actions_count = len(tool_results)
            files_count = len(context.modified_files)
            output_msg = f"Execution iteration complete. {actions_count} actions, {files_count} files modified."
            if step_info:
                output_msg = f"{step_info}. {output_msg}"

            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output=output_msg,
                can_transition=can_transition,
                metadata={
                    "modified_files": list(context.modified_files),
                    "completed_actions": len(context.completed_actions),
                    "tool_results": tool_results,
                    "current_step": next_step,
                    "response": response_text[:500] if response_text else "",
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
    # THINKING INSTRUCTIONS (GPT OSS 120B OPTIMIZED)
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Override to prioritize tool calls inside <output> tags for GPT OSS 120B.

        Extraction strategy:
        1. First, try to extract from <output>...</output> tags
        2. Fall back to parent class extraction (code blocks + inline JSON)

        This ensures that when GPT OSS 120B wraps tool calls in <output> tags,
        we extract from there first before looking at the entire response.
        """
        if not response:
            return []

        # Strategy 1: Extract content from <output> tags
        output_pattern = r'<output>(.*?)</output>'
        output_matches = re.findall(output_pattern, response, re.DOTALL | re.IGNORECASE)

        if output_matches:
            # Try to extract tool calls from output tag content
            for output_content in output_matches:
                tool_calls = super()._extract_tool_calls(output_content.strip())
                if tool_calls:
                    logger.info(f"[execution] Extracted {len(tool_calls)} tool calls from <output> tags")
                    return tool_calls

        # Strategy 2: Fall back to standard extraction from full response
        tool_calls = super()._extract_tool_calls(response)
        if tool_calls:
            logger.info(f"[execution] Extracted {len(tool_calls)} tool calls from full response")
        return tool_calls

    def _get_thinking_instructions(self) -> str:
        """
        Override base thinking instructions with 4-phase execution protocol.

        Uses XML-tagged reasoning, numbered steps, evidence citations, and
        anti-hallucination checkpoints optimized for GPT OSS 120B.
        """
        return """### DEEP REASONING PROTOCOL (GPT-OSS-120B Optimized)

    Use `<thinking>` and `<output>` tags to structure your reasoning and actions for each phase.

    **Critical Requirements**:
    - Use `[Evidence: file.py:line]` to cite ALL code references
    - Include self-validation checkpoints before proceeding to next phase
    - Use Glob to discover files BEFORE reading them
    - NEVER invent filenames not returned by Glob
    - Follow the 4-phase protocol sequentially: Phase 0 → 1 → 2 → 3
    - Complete all checkpoints in a phase before transitioning

    **Phase Structure Template**:
    ```
    <thinking>
    [Phase Number]: [Phase Name]

    Step 1: [Clear description of what you're analyzing]
      → Result: [what you found]
      → Evidence: [file:line]

    Step 2: [Next analysis step]
      → Result: [what you found]
      → Evidence: [file:line]

    ...

    Self-validation checkpoint:
    - [ ] Checkpoint 1 completed
    - [ ] Checkpoint 2 completed
    - [ ] All requirements met for this phase

    Therefore: [Clear conclusion stating you're ready to proceed]
    </thinking>

    <output>
    [Brief summary of what you're about to do]
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
    4. If you're unsure, READ the file to verify

    **Error Recovery**:
    If a tool fails, STOP and:
    1. Read the error message
    2. Diagnose the root cause
    3. Apply the correct recovery action
    4. Re-run the tool to verify

    See the full execution_handler.md protocol for detailed phase-by-phase instructions.

    """
    # ═══════════════════════════════════════════════════════════════════════
    # EXECUTION WRITE GATE (Security Boundary)
    # ═══════════════════════════════════════════════════════════════════════

    def _extract_planned_files(self, plan_content: str) -> set:
        """
        Extract allowed file paths and patterns from implementation plan.

        Parses the plan for [MODIFY], [NEW], and [DELETE] markers to build
        a whitelist of files that execution is allowed to modify. Also extracts
        pattern-based allowances from plan descriptions (e.g., "tests/unit/*.py").

        Args:
            plan_content: Content of implementation_plan.md

        Returns:
            Set of file paths and patterns that are allowed to be written/edited
        """
        import re

        allowed = set()

        # [MODIFY] /path/to/file pattern
        allowed.update(re.findall(r'\[MODIFY\]\s+([^\s]+)', plan_content))

        # [NEW] /path/to/file pattern
        allowed.update(re.findall(r'\[NEW\]\s+([^\s]+)', plan_content))

        # file:///path markdown links (less common but valid)
        allowed.update(re.findall(r'file:///([^\)]+)', plan_content))

        # Extract backtick paths from plan (e.g., `tests/unit/test_utils.py`)
        backtick_paths = re.findall(r'`([^`]+\.(py|txt|json|yaml|yml|md))`', plan_content)
        allowed.update(path for path, _ in backtick_paths)

        # Always allow task.md updates
        allowed.add(".hcode/task.md")

        # Pattern-based allowances for common test/task file patterns
        # These patterns are checked separately in _is_path_allowed()
        allowed.add("tests/**/*.py")  # Any test file
        allowed.add("tests/conftest.py")  # Pytest fixtures
        allowed.add("tasks/**/*.txt")  # Intermediate task tracking files
        allowed.add("tasks/**/*.md")  # Task documentation

        logger.debug(f"Execution write gate: {len(allowed)} paths/patterns allowed from plan")
        return allowed

    def _is_path_allowed(self, target_path: str, allowed_files: set) -> bool:
        """
        Check if a target path is allowed by write gate.

        Supports both exact path matching and pattern-based matching (glob-style).

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
            # Convert glob pattern to fnmatch pattern
            if "**" in allowed:
                # tests/**/*.py -> tests/*/*.py, tests/*/*/*.py, etc.
                # Simplified: just check if path starts with base and ends with suffix
                parts = allowed.split("**/")
                if len(parts) == 2:
                    base, suffix = parts
                    suffix_pattern = suffix.replace("*", ".*")  # Convert glob * to regex .*
                    if norm_target.startswith(base) and re.match(suffix_pattern, norm_target.split("/")[-1]):
                        return True
            elif "*" in allowed:
                # Simple glob pattern (e.g., tests/*.py)
                if fnmatch.fnmatch(norm_target, allowed):
                    return True

        return False

    async def _execute_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext,
    ) -> List[Dict[str, Any]]:
        """
        Execution-phase write gate: reject Write/Edit calls that target files
        not listed in implementation_plan.md.

        This is a critical security boundary - execution must follow the plan
        and not write arbitrary files. Read-only tools pass through unchanged.

        Blocked writes are returned as failed results so the multi-turn loop
        feeds the error back to the AI.

        Args:
            tool_calls: List of tool calls to execute
            context: Current agent context

        Returns:
            List of tool execution results
        """
        # Load plan and extract allowed files
        plan = self.artifact_manager.load_artifact("implementation_plan.md", context)
        allowed_files = self._extract_planned_files(plan) if plan else set()

        gated_calls = []
        results = []

        for tc in tool_calls:
            tool_name = (tc.get("tool") or "").lower()
            arguments = tc.get("arguments", {})

            # Only gate write-like tools
            if tool_name in ("write", "writetool", "edit", "edittool"):
                target = (
                    arguments.get("TargetFile")
                    or arguments.get("file_path")
                    or arguments.get("path")
                    or ""
                )

                # Check if target matches any allowed file or pattern
                is_allowed = self._is_path_allowed(target, allowed_files)

                if not is_allowed:
                    # Block and record
                    self._display(
                        f"  [>] {tc.get('tool')}: {target}  ← BLOCKED (not in plan)",
                        style="error",
                    )
                    results.append({
                        "tool": tc.get("tool"),
                        "success": False,
                        "output": None,
                        "error": (
                            f"EXECUTION WRITE GATE VIOLATION: Write to '{target}' is not allowed. "
                            f"File not found in implementation_plan.md. "
                            f"Allowed files: {', '.join(sorted(allowed_files)) if allowed_files else 'None (empty plan?)'}"
                        ),
                        "file_path": target,
                    })
                    logger.warning(f"Execution write gate blocked: {target}")
                    continue  # Skip - don't add to gated_calls

            gated_calls.append(tc)

        # Execute the allowed calls via the parent implementation
        if gated_calls:
            parent_results = await super()._execute_tools(gated_calls, context)
            results.extend(parent_results)

        return results

    # ═══════════════════════════════════════════════════════════════════════
    # SYSTEM PROMPT
    # ═══════════════════════════════════════════════════════════════════════

    def _get_execution_system_prompt(self, context: AgentContext) -> str:
        """
        Build system prompt for execution phase.

        Loads execution_handler.md as the primary protocol, then adds
        identity, tool format, plan content, and working context.
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            # Core identity and tool format
            identity = loader.get_identity()
            tool_format = loader.get_tool_format()

            # Load execution_handler.md protocol
            execution_protocol = self._load_execution_protocol()

            # Load plan and task content for context
            plan_content = self.artifact_manager.load_artifact(
                "implementation_plan.md", context
            ) or "(No plan loaded)"

            task_content = self.artifact_manager.load_artifact(
                "task.md", context
            ) or "(No task.md found)"

            # Build system prompt
            system_prompt = f"""{identity}

{tool_format}

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

### TOOL CALL FORMAT (CRITICAL!)

Output JSON tool calls in code blocks: `{{"tool": "ToolName", "arguments": {{"param": "value"}}}}`
(See tool_format.md for complete documentation)
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
            # Try to load from the core prompts directory (pev_prompts subdirectory)
            prompt_dir = Path(__file__).parent.parent.parent / "config" / "core_prompts" / "core" / "pev_prompts"
            protocol_path = prompt_dir / "execution_handler.md"

            if protocol_path.exists():
                return protocol_path.read_text(encoding="utf-8")

            logger.warning(f"execution_handler.md not found at {protocol_path}, using inline protocol")
        except Exception as e:
            logger.warning(f"Failed to load execution_handler.md: {e}")

        # Condensed inline fallback
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
        # Build modified files list
        modified_files_list = "\n".join(
            f"  - {f}" for f in context.modified_files
        ) if context.modified_files else "  (none yet)"

        # Build recent actions summary
        recent_actions = context.completed_actions[-5:] if context.completed_actions else []
        actions_summary = "\n".join(
            f"  - {a.get('tool', 'unknown')}: {'[OK]' if a.get('success') else '[FAIL]'}"
            for a in recent_actions
        ) if recent_actions else "  (none yet)"

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
    # CONTINUATION PROMPTS (Phase-Aware Steering)
    # ═══════════════════════════════════════════════════════════════════════

    def _detect_current_phase(
            self,
            all_results: List[Dict[str, Any]],
            round_num: int,
    ) -> str:
        """
        Detect which phase the AI should be in based on session state.

        Uses hybrid detection: combines tool call patterns with round-based hints
        to provide more robust phase detection.

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
            and r.get('tool', '').lower() in ['read', 'readtool']
        )

        file_writes = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['write', 'writetool', 'edit', 'edittool']
            and '.hcode' not in str(r.get('file_path', ''))
        )

        # Round-based phase hints (helps when tool counts are ambiguous)
        if round_num <= 3:
            expected_phase = 'phase0'  # Task selection
        elif round_num <= 8:
            expected_phase = 'phase1'  # Analysis
        elif round_num <= 15:
            expected_phase = 'phase2'  # Implementation
        else:
            expected_phase = 'phase3'  # Validation

        # Tool-based phase detection (primary)
        if task_md_edits == 0 and file_reads == 0 and file_writes == 0:
            return 'phase0'  # Need to start by reading task.md
        elif task_md_edits > 0 and file_reads == 0 and file_writes == 0:
            return 'phase1'  # Task selected, now read target files
        elif file_reads > 0 and file_writes == 0:
            return 'phase1'  # Still in analysis phase
        elif file_writes > 0 and task_md_edits == 1:
            return 'phase2'  # Started writing code, need to finish
        elif file_writes > 0 and task_md_edits >= 2:
            return 'phase3'  # Code done, now validate
        elif task_md_edits >= 2 and file_reads > 0:
            return 'phase3'  # Re-reading for validation

        # Fall back to round-based hint if tool counts are ambiguous
        return expected_phase

    def _build_continuation_prompt(
        self,
        round_results: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]],
        round_num: int,
        context: Any = None,
    ) -> str:
        """
        Build phase-aware continuation prompt with explicit steering for GPT-OSS-120B.

        Enhanced with:
        - Explicit phase detection
        - Clear phase-specific instructions
        - Error recovery guidance
        - Anti-hallucination reminders
        """
        # Detect current phase
        current_phase = self._detect_current_phase(all_results, round_num)

        # Extract key metrics
        write_count = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['write', 'edit', 'writetool', 'edittool']
            and '.hcode' not in str(r.get('file_path', ''))
        )

        read_count = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['read', 'readtool']
        )

        task_edit_count = sum(
            1 for r in all_results
            if r.get('success')
            and 'task.md' in str(r.get('file_path', ''))
            and r.get('tool', '').lower() in ['edit', 'edittool']
        )

        # Check for errors in recent rounds
        recent_errors = [
            r for r in round_results[-3:]
            if not r.get('success')
        ]

        # ── ERROR RECOVERY PROMPTS ────────────────────────────────────────
        if recent_errors:
            error_msg = self._build_error_recovery_prompt(recent_errors)
            if error_msg:
                return error_msg

        # ── PHASE-SPECIFIC CONTINUATION ───────────────────────────────────

        if current_phase == 'phase0':
            return self._phase0_continuation(round_num, all_results)

        elif current_phase == 'phase1':
            return self._phase1_continuation(round_num, read_count, write_count)

        elif current_phase == 'phase2':
            return self._phase2_continuation(round_num, write_count, task_edit_count)

        elif current_phase == 'phase3':
            return self._phase3_continuation(round_num, write_count, task_edit_count)

        # ── ROUND LIMIT PUSH ───────────────────────────────────────────────
        if round_num >= 15:
            return (
                "⚠️ You are approaching the execution round limit. "
                "Complete your current work immediately:\n\n"
                "1. Finish any pending code changes\n"
                "2. Re-read modified files for verification\n"
                "3. Update `.hcode/task.md` with current status\n"
                "4. Provide a summary of what was accomplished\n\n"
                "If the task is incomplete, clearly state what remains."
            )

        # ── DEFAULT CONTINUATION ───────────────────────────────────────────
        return (
            f"Continue with the 4-phase protocol (detected: {current_phase}).\n\n"
            "Remember:\n"
            "- Use Glob to discover files BEFORE reading them\n"
            "- ALWAYS read files before editing\n"
            "- Update `.hcode/task.md` after completing each subtask\n"
            "- Use [Evidence: file:line] citations for all claims\n"
            "- One change at a time — verify before proceeding"
        )

    def _build_error_recovery_prompt(self, errors: List[Dict[str, Any]]) -> Optional[str]:
        """Build targeted error recovery prompt based on error types."""
        if not errors:
            return None

        error_types = []
        for error in errors:
            tool = error.get('tool', '').lower()
            err_msg = error.get('error', error.get('output', ''))

            if 'file not found' in err_msg.lower():
                error_types.append('file_not_found')
            elif 'old text not found' in err_msg.lower():
                error_types.append('edit_mismatch')
            elif 'write gate' in err_msg.lower():
                error_types.append('write_gate')
            elif 'import' in err_msg.lower():
                error_types.append('import_error')

        if 'file_not_found' in error_types:
            return (
                "🔴 ERROR RECOVERY: File Not Found\n\n"
                "You tried to access a file that doesn't exist.\n\n"
                "RECOVERY STEPS:\n"
                "1. STOP — don't continue with incorrect paths\n"
                "2. Use Glob tool to discover actual files in the target directory\n"
                "3. Use ONLY filenames returned by Glob\n"
                "4. Read the file first, then proceed\n\n"
                "Example:\n"
                '{"tool": "Glob", "arguments": {"Pattern": "src/**/*.py"}}\n\n'
                "NEVER invent filenames like 'file1.py' or 'example.py'."
            )

        elif 'edit_mismatch' in error_types:
            return (
                "🔴 ERROR RECOVERY: Edit Failed — Old Text Not Found\n\n"
                "The content you tried to edit doesn't match the file.\n\n"
                "RECOVERY STEPS:\n"
                "1. Re-read the file with Read tool to get actual content\n"
                "2. Copy the exact text you want to replace\n"
                "3. Retry the Edit with correct OldText\n\n"
                "Make sure to include proper indentation and surrounding context."
            )

        elif 'write_gate' in error_types:
            return (
                "🔴 ERROR RECOVERY: Write Gate Violation\n\n"
                "You tried to write to a file not listed in the implementation plan.\n\n"
                "RECOVERY STEPS:\n"
                "1. Read `.hcode/implementation_plan.md` to find allowed files\n"
                "2. Only modify files explicitly listed in the plan\n"
                "3. If you need to modify a file not in plan, flag it with reasoning\n\n"
                "The write gate is a security boundary — follow the plan."
            )

        elif 'import_error' in error_types:
            return (
                "🔴 ERROR RECOVERY: Import Error\n\n"
                "Your code change introduced an import error.\n\n"
                "RECOVERY STEPS:\n"
                "1. Read similar files to see correct import patterns\n"
                "2. Verify imported modules exist (use Glob if needed)\n"
                "3. Fix the import statement\n"
                "4. Re-run to verify the fix\n\n"
                "Use [Evidence: file:line] to show where you found correct import patterns."
            )

        # Generic error recovery
        return (
            "🔴 ERROR DETECTED\n\n"
            "Recent tool calls failed. Please:\n\n"
            "1. Review the error messages above\n"
            "2. Diagnose the root cause\n"
            "3. Apply the appropriate recovery action\n"
            "4. Re-run the failed tool to verify the fix\n\n"
            "Don't continue with broken state — fix errors first."
        )

    def _phase0_continuation(self, round_num: int, all_results: List[Dict]) -> str:
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

    def _phase1_continuation(self, round_num: int, read_count: int, write_count: int) -> str:
        """Phase 1: Pre-Implementation Analysis continuation."""
        if read_count == 0:
            return (
                "📍 PHASE 1: Pre-Implementation Analysis\n\n"
                "You MUST read files before making changes:\n\n"
                "1. Use Glob to discover actual files: `{\"tool\": \"Glob\", \"arguments\": {\"Pattern\": \"**/*.py\"}}`\n"
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

    def _phase2_continuation(self, round_num: int, write_count: int, task_edit_count: int) -> str:
        """Phase 2: Code Generation continuation."""
        if write_count == 0:
            return (
                "📍 PHASE 2: Code Generation\n\n"
                "Begin implementing your changes:\n\n"
                "Pass 1: Create structure\n"
                "- Add classes/function signatures\n"
                "- Add necessary imports\n"
                "- Match existing code patterns\n\n"
                "Pass 2: Add logic\n"
                "- Implement function bodies\n"
                "- Handle errors and edge cases\n"
                "- Integrate with existing code\n\n"
                "Pass 3: Polish\n"
                "- Add docstrings\n"
                "- Check naming consistency\n"
                "- Verify style matches\n\n"
                "Remember: Use Write/Edit tools, never raw code text!"
            )

        if task_edit_count == 1:
            return (
                "📍 PHASE 2 CONTINUE: Implementation In Progress\n\n"
                f"Good progress — {write_count} file modification(s) made.\n\n"
                "Continue with Phase 2 until all code changes are complete:\n"
                "- Finish Pass 2 logic if needed\n"
                "- Apply Pass 3 polish\n"
                "- Verify no TODOs remain\n\n"
                "When code is complete, proceed to Phase 3: Self-Validation."
            )

        return (
            "📍 PHASE 2 → PHASE 3: Implementation Complete\n\n"
            "Code changes are done. Now proceed to Phase 3:\n\n"
            "1. Re-read ALL modified files\n"
            "2. Trace execution with sample inputs\n"
            "3. Cross-check against implementation_plan.md\n"
            "4. Mark task as [x] in `.hcode/task.md`\n\n"
            "Validate thoroughly before marking complete!"
        )

    def _phase3_continuation(self, round_num: int, write_count: int, task_edit_count: int) -> str:
        """Phase 3: Self-Validation continuation."""
        if task_edit_count == 1:
            return (
                "📍 PHASE 3: Self-Validation\n\n"
                "Code changes are done. Now validate:\n\n"
                "1. Re-read all modified files\n"
                "2. Walk through execution mentally:\n"
                "   - Test case 1 (happy path): [input] → [expected output]\n"
                "   - Test case 2 (edge case): [input] → [expected behavior]\n"
                "   - Test case 3 (error case): [input] → [expected handling]\n"
                "3. Verify against implementation_plan.md\n"
                "4. Mark task as [x] in `.hcode/task.md`\n\n"
                "Provide validation results in output."
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
        """
        Check if execution is complete.

        Execution is complete when at least one NON-ARTIFACT file has
        been modified (actual code, not .hcode files).
        """
        # Filter out artifact files
        non_artifact_files = [
            f for f in context.modified_files
            if ".hcode" not in f and not f.endswith("task.md")
            and not f.endswith("implementation_plan.md")
            and not f.endswith("walkthrough.md")
        ]

        # Also check completed actions for non-artifact file writes
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

    def _parse_plan_steps(self, plan_content: str) -> List[Dict[str, Any]]:
        """
        Parse steps from implementation plan with enhanced pattern matching.

        Supports multiple plan formats:
        - Numbered steps: "1. **Step Name**: Description"
        - Bullet lists: "- [ ] Task description"
        - Section headers: "## Section Name"
        """
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

        # Pattern 3: Section headers as step markers
        section_pattern = r'^##\s+(\d+\.?\s*)?(.+)$'
        section_matches = re.findall(section_pattern, plan_content, re.MULTILINE)

        for i, (num, name) in enumerate(section_matches):
            if name.lower() not in ['summary', 'notes', 'metadata']:
                steps.append({
                    "number": len(step_matches) + len(task_matches) + i + 1,
                    "name": name.strip(),
                    "description": f"Section: {name.strip()}",
                    "files": [],
                    "actions": [],
                    "completed": False,
                    "is_section": True,
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

        # Find content between this step and next step
        step_marker = f"{step_num}."
        step_start = plan_content.find(step_marker)
        next_step_marker = f"{step_num + 1}."
        next_step_pos = plan_content.find(next_step_marker, step_start)
        step_end = next_step_pos if next_step_pos != -1 else len(plan_content)
        step_content = plan_content[step_start:step_end]

        # Extract file paths from various formats
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
                    # Check if it looks like a file path
                    if '/' in normalized or '\\' in normalized or '.' in normalized.split('/')[-1]:
                        step["files"].append(normalized)

        # Extract action descriptions
        action_patterns = [
            r'(?:Action|action):\s*([^\n]+)',
            r'(?:Do|do):\s*([^\n]+)',
            r'^\s*[-*]\s+(.+)$',  # Bullet points
        ]

        for pattern in action_patterns:
            action_matches = re.findall(pattern, step_content, re.MULTILINE)
            for action in action_matches:
                action = action.strip()
                if action and action not in step["actions"]:
                    step["actions"].append(action)

        return step

    def _update_task_progress(self, context: AgentContext) -> None:
        """
        Update task.md with current progress.

        Marks subtasks as complete based on modified files and completed actions.
        """
        task_content = self.artifact_manager.load_artifact("task.md", context)
        if not task_content:
            logger.warning("task.md not found, cannot update progress")
            return

        plan_content = self.artifact_manager.load_artifact("implementation_plan.md", context)
        plan_steps = self._parse_plan_steps(plan_content) if plan_content else []

        completed_files = set(context.modified_files)

        # Update checkbox items
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

        # Add progress summary
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
