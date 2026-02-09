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

import re
import logging
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
                    max_rounds=12,
                    max_tokens=16384,
                    temperature=0.3,  # Deterministic code generation
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

    def _get_thinking_instructions(self) -> str:
        """
        Override base thinking instructions with 4-phase execution protocol.

        Uses XML-tagged reasoning, numbered steps, and anti-hallucination
        checkpoints optimized for GPT OSS 120B.
        """
        return """### 4-PHASE EXECUTION THINKING PROTOCOL

Before EVERY action, you MUST think through one of these phases:

**Phase 0 — TASK SELECTION:**
<thinking>
Step 1: Read task.md — Find all unchecked `- [ ]` items.
Step 2: Read implementation_plan.md — Find the corresponding plan section.
Step 3: Check dependencies — Does this task depend on another uncompleted task?
Step 4: Assess readiness — Do I have all the information needed?
Therefore: The next task to execute is [task] because [reason].
</thinking>

**Phase 1 — PRE-IMPLEMENTATION ANALYSIS:**
<thinking>
Step 1: READ all target files — Extract current structure, patterns, imports.
Step 2: UNDERSTAND surrounding code — What calls this? What does this call?
Step 3: IDENTIFY exact modification points — Line numbers, function boundaries.
Step 4: CHECK for side effects — Will this change break callers? Tests? Imports?
Step 5: PLAN the exact diff — What old text becomes what new text?
Step 6: ANTI-HALLUCINATION — Am I referencing code I haven't read? If yes: STOP and READ.
Therefore: I am confident in the exact change because [evidence].
</thinking>

**Phase 2 — CODE GENERATION (3-Pass):**
<thinking>
Pass 1 (Skeleton): Create structural skeleton — classes, functions, signatures, imports.
Pass 2 (Logic): Fill in function bodies — happy path, then error handling.
Pass 3 (Polish): Check cross-file references, naming consistency, cleanup.
Therefore: Code is complete and consistent with project patterns.
</thinking>

**Phase 3 — SELF-VALIDATION:**
<thinking>
Step 1: RE-READ every modified file — Does it look correct?
Step 2: TRACE execution path — Walk through code mentally with sample input.
Step 3: CHECK the plan — Does every plan step have a corresponding change?
Step 4: VERIFY task.md — Are completed subtasks marked [x]?
Step 5: LIST remaining issues — Any known issues or limitations?
Therefore: Implementation is [complete/incomplete] because [evidence].
</thinking>

CRITICAL RULES:
- NEVER show code in response text without using Write/Edit tools
- ALWAYS read files before editing them
- VERIFY assumptions before acting on them
- ONE change at a time, verify each before proceeding

"""

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
            # Try to load from the core prompts directory
            prompt_dir = Path(__file__).parent.parent.parent / "config" / "core_prompts" / "core"
            protocol_path = prompt_dir / "execution_handler.md"

            if protocol_path.exists():
                return protocol_path.read_text(encoding="utf-8")

            logger.warning("execution_handler.md not found, using inline protocol")
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
- Iteration: {context.iteration}
- Modified files ({len(context.modified_files)}):
{modified_files_list}
- Recent actions:
{actions_summary}

### INSTRUCTIONS:

Begin with **Phase 0: Task Selection**.

1. Identify the next unchecked `- [ ]` task in task.md
2. Cross-reference with the implementation plan for details
3. Mark it as in-progress: `- [/]`
4. Proceed to Phase 1: read ALL files you need to modify
5. Then Phase 2: make the code changes (3-pass: skeleton → logic → polish)
6. Then Phase 3: re-read modified files, trace execution, update task.md with [x]

Remember:
- READ BEFORE WRITE — always read files before editing
- ONE TASK AT A TIME — complete each subtask fully before moving on
- USE TOOLS — all code changes must use Write/Edit, never raw text
- TRACK PROGRESS — update task.md after each completed subtask

NOW BEGIN Phase 0. Read task.md and identify the next task to implement."""

    # ═══════════════════════════════════════════════════════════════════════
    # CONTINUATION PROMPTS (Phase-Aware Steering)
    # ═══════════════════════════════════════════════════════════════════════

    def _build_continuation_prompt(
        self,
        round_results: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]],
        round_num: int,
        context: Any = None,
    ) -> str:
        """
        Build phase-aware continuation prompt after each tool round.

        Steers the AI through the 4-phase protocol based on what has
        been accomplished so far in the session.
        """
        # Count successful file modifications (non-artifact)
        write_count = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['write', 'edit', 'writetool', 'edittool']
            and '.hcode' not in str(r.get('file_path', ''))
        )

        # Count file reads
        read_count = sum(
            1 for r in all_results
            if r.get('success')
            and r.get('tool', '').lower() in ['read', 'readtool']
        )

        # Check if task.md was updated
        task_updated = any(
            'task.md' in str(r.get('file_path', ''))
            for r in round_results
            if r.get('success')
            and r.get('tool', '').lower() in ['edit', 'edittool']
        )

        # ── Round 0-1: Should be reading files (Phase 0 + Phase 1) ──
        if round_num <= 1 and write_count == 0:
            if read_count == 0:
                return (
                    "You MUST read files before making changes. "
                    "Begin Phase 0: read task.md to find the next task. "
                    "Then Phase 1: read ALL target files before any edits."
                )
            return (
                "Good — you're reading files. Continue Phase 1: "
                "read ALL files you plan to modify. Understand the existing "
                "code structure, imports, and patterns. Then proceed to "
                "Phase 2: make your code changes."
            )

        # ── Rounds 2-6: Should be writing code (Phase 2) ──
        if round_num <= 6 and write_count > 0 and not task_updated:
            return (
                "Good progress on code changes. Continue Phase 2 if more changes "
                "are needed. When all code changes for this subtask are complete, "
                "proceed to Phase 3: Self-Validation. "
                "RE-READ modified files to verify correctness, then update "
                "task.md to mark the subtask as [x] completed."
            )

        # ── Task.md was updated — check if more tasks remain ──
        if task_updated:
            return (
                "task.md updated. Check if there are more unchecked `- [ ]` "
                "items. If yes, start Phase 0 again for the next subtask. "
                "If all tasks are complete, provide a summary of what was "
                "implemented and declare execution complete."
            )

        # ── Late rounds: push toward completion ──
        if round_num >= 7:
            return (
                "You are running low on execution rounds. "
                "Complete your current changes and proceed to Phase 3: "
                "Self-Validation. Update task.md with the current status "
                "of all subtasks. Provide a summary of what was accomplished."
            )

        # Default: generic continuation
        return (
            "Continue with the 4-phase protocol. "
            "If you need to read more files, do so. "
            "If ready to make changes, proceed with Phase 2. "
            "Remember to update task.md after completing each subtask."
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
        Parse steps from implementation plan.

        Extracts numbered steps, file paths, and actions from plan markdown.
        """
        steps = []
        if not plan_content:
            return steps

        # Pattern for numbered steps: "1. **Step Name**: Description"
        step_pattern = r'(\d+)\.\s*\*\*([^*]+)\*\*\s*:?\s*([^\n]*)'
        step_matches = re.findall(step_pattern, plan_content)

        for match in step_matches:
            step_num = int(match[0])
            step_name = match[1].strip()
            description = match[2].strip()

            step = {
                "number": step_num,
                "name": step_name,
                "description": description,
                "files": [],
                "actions": [],
                "completed": False,
            }

            # Look for file paths after this step (before next step)
            step_start = plan_content.find(f"{step_num}.")
            next_step_match = re.search(rf'{step_num + 1}\.', plan_content[step_start + 3:])
            step_end = step_start + 3 + next_step_match.start() if next_step_match else len(plan_content)
            step_content = plan_content[step_start:step_end]

            # Extract file paths
            file_pattern = r'(?:File|file|Path|path):\s*`([^`]+)`'
            file_matches = re.findall(file_pattern, step_content)
            step["files"] = file_matches

            # Also capture backtick paths that look like files
            backtick_pattern = r'`([^`]+\.[a-z]+)`'
            backtick_matches = re.findall(backtick_pattern, step_content)
            for path in backtick_matches:
                if path not in step["files"] and ('/' in path or '\\' in path):
                    step["files"].append(path)

            # Extract actions
            action_pattern = r'(?:Action|action):\s*([^\n]+)'
            action_matches = re.findall(action_pattern, step_content)
            step["actions"] = action_matches

            steps.append(step)

        # Also parse bullet point items as simple steps
        bullet_pattern = r'^\s*[-*]\s*\[([x ])\]\s*(.+)$'
        bullet_matches = re.findall(bullet_pattern, plan_content, re.MULTILINE)

        for i, (checkbox, description) in enumerate(bullet_matches):
            is_completed = checkbox.lower() == 'x'
            steps.append({
                "number": len(step_matches) + i + 1,
                "name": description[:50],
                "description": description,
                "files": [],
                "actions": [description],
                "completed": is_completed,
            })

        logger.debug(f"Parsed {len(steps)} steps from implementation plan")
        return steps

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
