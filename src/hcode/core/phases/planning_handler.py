"""
Planning Phase Handler
=======================

This module implements the *Planning* phase of the PEV (Planning → Execution → Verification) workflow used by the Hcode engine.

The handler is responsible for:

- **Deep analysis of user requirements** – parsing the initial prompt, extracting goals, and identifying constraints.
- **Research and understanding of the codebase** – locating relevant modules, classes, and functions, and building a mental model of the project structure.
- **Generating `task.md`** – a checklist of concrete tasks (with unique IDs) that guides subsequent phases.
- **Creating `implementation_plan.md`** – a step‑by‑step plan that outlines how each task will be tackled, including any required resources.
- **Determining completion** – the handler decides when the planning stage is sufficient to move on to execution.

The module currently provides only utility imports; the actual handler class/function will be added in future iterations. The enhanced docstring ensures that developers immediately understand the intended responsibilities and integration points.
"""

import json
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


# ═══════════════════════════════════════════════════════════════════════════════
# PLANNING PHASE HANDLER
# ═══════════════════════════════════════════════════════════════════════════════


class PlanningPhaseHandler(BasePhaseHandler):
    """
    Handler for the Planning phase of PEV workflow.

    Creates:
    - .hcode/task.md: Task understanding and subtasks with checkbox format
    - .hcode/implementation_plan.md: Implementation steps with file paths

    The planning phase follows this workflow:
    1. Deep analysis of user requirements
    2. Research codebase to identify relevant files
    3. Create task breakdown with trackable subtasks
    4. Create detailed implementation plan with:
       - Goal description
       - User review required items
       - Proposed changes grouped by component
       - Verification plan

    Transition criteria:
    - Both artifacts exist and have valid content
    - Plan has concrete steps with file paths
    - Agent confirms plan is ready for user review
    """

    phase_name = "planning"

    # ──────────────────────────────────────────────────────────
    # Round configuration for multi-round thinking
    # ──────────────────────────────────────────────────────────
    MAX_ROUNDS = 20  # Maximum rounds for planning (increased from 8 to allow agent autonomy)

    # Research thresholds

    # ──────────────────────────────────────────────────────────
    # Allowed write targets during the planning phase.
    # Any Write/Edit to a path outside this set is rejected and
    # reported back to the AI so it can self-correct.
    # ──────────────────────────────────────────────────────────
    _PLANNING_WRITE_ALLOWED = (".hcode/task.md", ".hcode/implementation_plan.md")

    def __init__(self, artifact_manager, provider, tool_executor, context_manager, console=None):
        """
        Initialize planning phase handler with meta-cognitive trackers.
        
        Args:
            artifact_manager: Manager for phase artifacts
            provider: AI provider for generating responses
            tool_executor: Executor for tool calls
            context_manager: Context manager
            console: Rich console for output (optional)
        """
        super().__init__(artifact_manager, provider, tool_executor, context_manager, console)

    def get_required_artifacts(self) -> List[str]:
        """Get artifacts this phase should produce."""
        return ["task.md", "implementation_plan.md"]

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Prioritize <output> tags for tool extraction."""
        if not response:
            return []

        # Check for <output>
        output_pattern = r'<output>(.*?)</output>'
        output_matches = re.findall(output_pattern, response, re.DOTALL | re.IGNORECASE)

        if output_matches:
            for output_content in output_matches:
                tool_calls = super()._extract_tool_calls(output_content.strip())
                if tool_calls:
                    return tool_calls

        return super()._extract_tool_calls(response)

    async def _execute_tools(self, tool_calls: List[Dict[str, Any]], context: AgentContext) -> List[Dict[str, Any]]:
        """Enforce write gate."""
        gated_calls = []
        results = []

        for tc in tool_calls:
            tool_name = (tc.get("tool") or "").lower()
            arguments = tc.get("arguments", {})

            if tool_name in ("write", "writetool"):
                target = (
                        arguments.get("file_path") or
                        arguments.get("TargetFile") or ""
                )
                norm_target = target.replace("\\", "/").rstrip("/")
                allowed = any(norm_target.endswith(a) for a in self._PLANNING_WRITE_ALLOWED)

                if not allowed:
                    results.append({
                        "tool": tc.get("tool"),
                        "success": False,
                        "error": f"PLANNING SCOPE: Cannot write '{target}'. Only {self._PLANNING_WRITE_ALLOWED} allowed.",
                    })
                    continue

            gated_calls.append(tc)

        if gated_calls:
            results.extend(await super()._execute_tools(gated_calls, context))

        return results

    def _build_continuation_prompt(
            self,
            round_results: List[Dict[str, Any]],
            all_results: List[Dict[str, Any]],
            round_num: int,
            context: Any = None,
    ) -> str:
        """
        5-Phase aware continuation prompt for GPT-OSS-120B.

        Detects the current phase and provides specific guidance to steer the AI
        from exploration to high-quality artifact generation.
        """
        # Detect state
        wrote_task = any(
            r.get("success") and "task.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        wrote_plan = any(
            r.get("success") and "implementation_plan.md" in str(r.get("file_path", ""))
            for r in all_results
        )

        read_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() == "read"
        )
        grep_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() == "grep"
        )
        glob_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() in ["glob", "globtool", "smartglobtool"]
        )

        # Check for errors
        recent_errors = [r for r in round_results if not r.get("success")]

        # ── PARAMETER FORMAT ERROR DETECTION ──────────────────────
        parameter_errors = [
            r for r in round_results
            if not r.get("success") and "Missing required parameter" in str(r.get("error", ""))
        ]

        if parameter_errors:
            error_details = parameter_errors[0].get("error", "")
            return f"""⚠️ TOOL FORMAT ERROR DETECTED

You called a tool with WRONG parameter format.

Error: {error_details}

**CORRECT FORMAT (copy this exactly):**

```json
{{"tool": "Glob", "arguments": {{"pattern": "**/*.py"}}}}
{{"tool": "Read", "arguments": {{"file_path": "path/file.py"}}}}
{{"tool": "Write", "arguments": {{"file_path": ".hcode/task.md", "content": "..."}}}}
{{"tool": "LS", "arguments": {{"path": "src/"}}}}
{{"tool": "Grep", "arguments": {{"pattern": "search", "path": "."}}}}
```

**COMMON MISTAKES (don't do this):**
❌ `{{"tool": "Glob"}}` - Missing arguments wrapper
❌ `{{"tool": "Glob", "arguments": {{"Pattern": "..."}}}}` - Uppercase parameter name
❌ `{{"Pattern": "..."}}` - Missing tool key
❌ `{{"tool": "Glob", "parameters": {{"pattern": "..."}}}}` - Use 'arguments' not 'parameters'
❌ `{{"tool": "Glob", "pattern": "..."}}` - Missing 'arguments' wrapper

**Your next action:**
Retry your last tool call using the CORRECT format from the table above.
Use LOWERCASE parameter names: pattern, file_path, content, path (not Pattern, AbsolutePath, etc)."""

        # ── LOOP DETECTION ────────────────────────────────────────
        # Detect if same tool called 2+ times with same args
        last_three_calls = []
        for result in all_results[-3:]:
            if result.get("success") and "tool" in result:
                # Create a signature of tool + arguments
                tool_name = result.get("tool", "")
                arguments = result.get("arguments", {})
                try:
                    args_str = json.dumps(arguments, sort_keys=True)
                    last_three_calls.append((tool_name, args_str))
                except:
                    pass

        # Check for duplicate calls
        if len(last_three_calls) >= 2:
            if last_three_calls[-1] == last_three_calls[-2]:
                tool_name = last_three_calls[-1][0]
                return f"""⚠️  LOOP DETECTED: You called {tool_name} with identical arguments twice in a row.

Recovery:
1. If Glob: STOP globbing. List what you found. Move to Read.
2. If Read failed: Check if file exists with a different path.
3. If stuck: Write artifacts with assumptions and flag them.

DO NOT call the same tool again. Progress to the next phase.

Status: Reads: {read_count}, Globs: {glob_count}, Greps: {grep_count}"""

        # ── ERROR RECOVERY ────────────────────────────────────────
        if recent_errors:
            return self._build_planning_error_recovery(recent_errors)

        # ── PHASE 0: START ─────────────────────────────────────────
        if read_count == 0 and glob_count == 0 and not wrote_task:
            return """📍 PHASE 0: Requirements Deconstruction

    You are at the start of planning.

    **Action:**
    1. Analyze the user's task request.
    2. Identify what you need to know.
    3. Formulate a search strategy (Glob/Grep).
    4. Begin Phase 1: Deep Code Investigation.

    **Do NOT write artifacts yet. You must read code first.**"""

        # ── PHASE 1: INVESTIGATION ────────────────────────────────
        if not wrote_task and not wrote_plan:
            # Agent is in exploration/investigation mode

            # If agent has read enough files, push toward design
            if read_count >= 3:
                return f"""📍 PHASE 1 → PHASE 2: Evidence Gathered

    Excellent! You have read {read_count} files.

    **Action:**
    1. Stop reading.
    2. Proceed to **Phase 2: Solution Crystallization**.
    3. Design your solution based on the evidence you gathered.
    4. Think about dependencies, risks, and atomicity.
    5. Do NOT write artifacts yet—wait for the next prompt to draft `task.md`.

    **Remember:**
    - Base your design on [Evidence: file.py:line].
    - Identify exact line numbers for changes."""

            # If agent hasn't read much, encourage it
            return f"""📍 PHASE 1: Deep Code Investigation

    You are gathering evidence. Reads: {read_count}, Globs: {glob_count}.

    **Action:**
    - Use **Glob** to find relevant files.
    - Use **Read** to inspect target files.
    - Use **Grep** to find usages/dependencies.
    - Extract context: Naming conventions, error handling, imports.

    **CRITICAL:** 
    - Do NOT guess file structures. Read them.
    - Cite evidence in your thinking: [Evidence: file.py:line].
    - Don't proceed to design until you understand the codebase.

    Target: Read at least 3-4 key files before designing."""

        # ── PHASE 3: WRITE task.md ─────────────────────────────────
        if wrote_task and not wrote_plan:
            # Validate task.md quality roughly before writing plan
            return """📍 PHASE 3 → PHASE 4: Task.md Complete

    You have created `task.md`. Now create the detailed blueprint.

    **Action:**
    Write `.hcode/implementation_plan.md` using the Write tool.

    **Required Structure:**
    1. **4-Dimension Deep Analysis** (Architecture, Dependencies, Quality, Context)
    2. **Proposed Changes** (Group by file)
       - [MODIFY] `file.py`
         - Target: function_name at line X [Evidence: file.py:X]
         - Current Behavior: ...
         - Required Change: ...
         - Why: ...
    3. **Verification Plan** (Exact commands)

    **Quality Check:**
    - Does every claim have [Evidence: file.py:line]?
    - Are changes specific (line numbers, function names)?
    - Is the verification command copy-pasteable?

    Write the plan now."""

        # ── PHASE 4: COMPLETE ──────────────────────────────────────
        if wrote_task and wrote_plan:
            return """✓ PLANNING COMPLETE

    Both artifacts have been created.
    - [x] task.md
    - [x] implementation_plan.md

    **Self-Check:**
    - [ ] Are subtasks atomic (doable in one session)?
    - [ ] Is the plan detailed enough for an agent to execute without research?
    - [ ] Are all changes backed by [Evidence: file.py:line]?

    If satisfied, you may end the phase."""

        # ── TIMEOUT / STUCK ─────────────────────────────────────────
        if round_num > 15:
            return f"""⚠️ ROUND LIMIT WARNING (Round {round_num + 1}/{self.MAX_ROUNDS})

    You have been researching for {round_num + 1} rounds.

    **Decision Time:**
    1. If you have read >= 3 files: Proceed to design (Phase 2) immediately.
    2. Write `task.md` now.
    3. Write `implementation_plan.md` now.
    4. Do not continue researching.

    Force the artifacts to be written now."""

        # Default fallback
        return "Continue with the 5-phase protocol. Read code, gather evidence, design solution, write artifacts."

    def _build_planning_error_recovery(self, errors: List[Dict[str, Any]]) -> Optional[str]:
        """
        Build specific error recovery for planning phase.

        FIXED: Removed incorrect super() call.
        """
        if not errors:
            return None

        # 1. Check for "Missing required parameter" (The current blocker)
        param_errors = [
            e for e in errors
            if 'missing required parameter' in str(e.get('error', '')).lower()
               or 'missing required parameter' in str(e.get('output', '')).lower()
        ]

        if param_errors:
            err_msg = param_errors[0].get('error', '')

            # Try to guess which tool failed from the error message
            tool_name = "Tool"
            if "pattern" in err_msg.lower():
                tool_name = "Glob"
            elif "TargetFile" in err_msg or "file_path" in err_msg:
                tool_name = "Read"

            return (
                f"🔴 CRITICAL ERROR: Tool Call Malformed\n\n"
                f"You tried to call `{tool_name}` but missed required arguments.\n\n"
                f"**IMMEDIATE FIX:**\n"
                f"You MUST use the exact JSON format below:\n\n"
                f"```json\n"
                f'{{"tool": "{tool_name}", "arguments": {{"pattern": "src/**/*.py"}}}}\n' if tool_name == "Glob" else \
                    f'{{"tool": "{tool_name}", "arguments": {{"file_path": "path/to/file"}}}}\n'
                    f"```\n\n"
                    f"**Do NOT use just parameters.**\n"
                    f"- ❌ Wrong: {{\"pattern\": \"...\"}}\n"
                    f"- ✅ Right: {{\"tool\": \"Glob\", \"arguments\": {{\"pattern\": \"...\"}}}}\n\n"
                    f"Retry the tool call with the CORRECT format."
            )

        # 2. Check for "File not found" (Hallucinated paths)
        file_not_found_errors = [
            e for e in errors
            if 'file not found' in str(e.get('error', '')).lower()
        ]

        if file_not_found_errors:
            bad_files = set()
            for e in file_not_found_errors:
                path = e.get('file_path', '')
                if path:
                    bad_files.add(path.split('/')[-1])

            return (
                f"🔴 FATAL ERROR: Files Do Not Exist\n\n"
                f"You tried to read: {', '.join(list(bad_files)[:3])}\n\n"
                f"**IMMEDIATE ACTION REQUIRED:**\n"
                f"1. STOP trying to read these files. They do not exist.\n"
                f"2. DO NOT run Glob again to find them. You already have the file list.\n"
                f"3. Only use files found in initial Glob results.\n"
                f"4. Proceed to write artifacts based on files you HAVE read.\n\n"
                f"Write task.md NOW."
            )

        # 3. Check for "Write Gate" violations
        write_gate_errors = [
            e for e in errors
            if 'write gate' in str(e.get('error', '')).lower()
               or 'planning scope' in str(e.get('error', '')).lower()
        ]

        if write_gate_errors:
            return (
                "🔴 ERROR: Write Gate Violation\n\n"
                "You tried to write a file that is not allowed.\n\n"
                "PLANNING RULES:\n"
                "- You can ONLY write `.hcode/task.md` and `.hcode/implementation_plan.md`\n"
                "- Do NOT write implementation code files yet.\n\n"
                "Focus on reading files and gathering evidence (Phase 1)."
            )

        # 4. Generic Fallback (Previously the crashing super() call)
        err_details = []
        for e in errors[:2]:
            err_details.append(f"- {e.get('tool', 'Unknown')}: {str(e.get('error', ''))[:50]}")

        return (
            "🔴 ERROR DETECTED\n\n"
            "Review the error messages above:\n"
            f"{chr(10).join(err_details)}\n\n"
            "Common Fixes:\n"
            "- Ensure JSON has 'tool' and 'arguments' keys.\n"
            "- Ensure arguments match tool definition (e.g., pattern for Glob).\n"
            "- Ensure paths are correct and files exist."
        )

    async def handle(
            self,
            context: AgentContext,
            loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute planning phase — 5-Phase Reasoning Protocol.
        """
        try:
            # Clean slate
            for _art in ("task.md", "implementation_plan.md", "walkthrough.md"):
                _path = self.artifact_manager._get_artifact_path(_art, context)
                if _path.exists():
                    _path.unlink()

            logger.info("Starting 5-Phase Planning Protocol...")

            artifacts_created = []

            # Build prompt
            unified_prompt = self._build_unified_planning_prompt(context)

            response = ""
            tool_results: List[Dict[str, Any]] = []

            if self.provider is not None:

                if self._hcode_display:
                    self._hcode_display.start_thinking()

                # Use standard execution loop with history injection
                response, tool_results = await self._generate_and_execute(
                    prompt=unified_prompt,
                    context=context,
                    system_prompt=self._get_planning_system_prompt(context),
                    max_rounds=self.MAX_ROUNDS,
                    max_tokens=8192,
                    timeout_seconds=900,
                    include_history=True,
                )

                if self._hcode_display:
                    self._hcode_display.end_thinking()

                # Track artifacts
                for result in tool_results:
                    if result.get("success"):
                        fp = str(result.get("file_path", ""))
                        if "task.md" in fp and "task.md" not in artifacts_created:
                            artifacts_created.append("task.md")
                            if self._hcode_display and FileAction:
                                self._hcode_display.track_file(".hcode/task.md", FileAction.CREATED)
                        if "implementation_plan.md" in fp and "implementation_plan.md" not in artifacts_created:
                            artifacts_created.append("implementation_plan.md")
                            if self._hcode_display and FileAction:
                                self._hcode_display.track_file(".hcode/implementation_plan.md", FileAction.CREATED)

            # Validation
            if not self.artifact_manager.artifact_exists("task.md", context):
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output="Failed: task.md not created.",
                    can_transition=False,
                    error="task.md missing",
                )

            if not self.artifact_manager.artifact_exists("implementation_plan.md", context):
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output="Failed: implementation_plan.md not created.",
                    can_transition=False,
                    error="implementation_plan.md missing",
                )

            # Quality Validation
            valid, error = self.validate_artifacts(context)
            if not valid:
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output=f"Validation failed: {error}",
                    can_transition=False,
                    error=error,
                )

            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output=f"Planning complete. Created: {', '.join(artifacts_created)}",
                artifacts_created=artifacts_created,
                can_transition=True,
                metadata={"tool_results": tool_results}
            )

        except Exception as e:
            logger.exception(f"Planning phase failed: {e}")
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                output=f"Planning failed: {str(e)}",
                can_transition=False,
                error=str(e),
            )

    def _get_planning_system_prompt(self, context: AgentContext) -> str:
        """
        Get system prompt for planning phase.

        Uses core prompts from phases.yaml and MD files.

        Args:
            context: Current agent context

        Returns:
            Complete system prompt for planning
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            # 1. Identity & Tool Format
            identity = loader.get_identity()
            tool_format = loader.get_tool_format()

            # Inject dynamic tool documentation (includes Skills)
            try:
                if hasattr(self.tool_executor, "tool_manager"):
                    tool_docs = self.tool_executor.tool_manager.get_tool_documentation()
                    tool_format += f"\n\n## Available Tools\n\n{tool_docs}"
            except Exception as e:
                logger.warning(f"Failed to inject tool docs: {e}")

            # 2. Planning Mode Protocol (The 5-Phase Protocol)
            planning_mode = loader.get_planning_mode()

            # 3. Artifact Guidance
            task_guidance = loader.get_task_guidance()
            plan_guidance = loader.get_implementation_plan_guidance()

            # 4. Project Knowledge (from /init)
            project_knowledge = ""
            try:
                _hcode_md = Path(context.working_dir) / ".hcode" / "hcode.md"
                if _hcode_md.exists():
                    project_knowledge = _hcode_md.read_text(encoding='utf-8')
            except Exception:
                pass

            pk_section = (
                project_knowledge
                if project_knowledge
                else "(Run /init commands to generate project knowledge if needed.)"
            )

            # 5. Task Memory
            task_memory = self._load_hcode_memory(context)

            # Construct the full system prompt
            system_prompt = f"""{identity}

{tool_format}

---

# PLANNING MODE PROTOCOL

{planning_mode}

---

# ARTIFACT GUIDANCE

## valid `task.md`
{task_guidance}

## valid `implementation_plan.md`
{plan_guidance}

---

# CONTEXT & KNOWLEDGE

## Project Knowledge
{pk_section}

## Task Memory
{task_memory}

## Current Context
Working Directory: {context.working_dir}
Artifact Directory: .hcode
Current Iteration: {context.iteration}
"""
            return system_prompt

        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            # Fallback to basic prompt
            return f"""You are Hcode, an AI coding assistant in PLANNING mode.

Your task: {context.task}

Working Directory: {context.working_dir}

## Protocol
1. Analyze request
2. Explore codebase (Glob/Read) - DO NOT GUESS PATHS
3. Create .hcode/task.md
4. Create .hcode/implementation_plan.md

Use format: {{"tool": "ToolName", "arguments": {{...}}}}
"""

    def _build_unified_planning_prompt(self, context: AgentContext) -> str:
        """
        Build a simplified user prompt for the planning phase.
        
        The protocol is now fully contained in the system prompt (from planning_mode.md).
        This prompt just provides the user's specific request and context.
        """
        return f"""# PLANNING REQUEST

## User Task
{context.task}

## Context
Working Directory: {context.working_dir}

## Objective
Follow the **5-Phase Reasoning Protocol** (defined in system prompt) to:
1.  Explore the codebase (Glob -> Read)
2.  Understand the architecture and patterns
3.  Create `.hcode/task.md` (roadmap)
4.  Create `.hcode/implementation_plan.md` (technical blueprint)

**Rules:**
-   **Evidence-First**: Do not write plans without reading code.
-   **Correct Tool Syntax**: Use `{{'tool': 'Tool', 'arguments': {{'param': 'val'}}}}`
-   **No Hallucinations**: Only use paths you have verified exist.

Begin with **Phase 0: Requirements Deconstruction**.
"""

    # NOTE: The agent generates task.md and implementation_plan.md directly from
    # the guidance prompts in src/hcode/config/core_prompts/core/task.md and
    # implementation_plan.md. Template methods have been removed.

    # NOTE: _extract_read_insights, _create_fallback_task_md, and _create_fallback_implementation_plan
    # have been removed. The agent generates artifacts directly from the guidance prompts.

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """
        Check if ready to transition to execution phase.

        Criteria:
        - Both task.md and implementation_plan.md exist
        - Both have valid content
        - Plan has concrete steps (not just placeholders)

        Args:
            context: Current agent context

        Returns:
            True if planning is complete
        """
        # Check if required artifacts exist
        if not self.artifact_manager.artifact_exists("task.md", context):
            return False

        if not self.artifact_manager.artifact_exists("implementation_plan.md", context):
            return False

        # Validate content
        valid, _ = self.validate_artifacts(context)
        if not valid:
            return False

        # Check plan has concrete steps (accept multiple plan formats)
        plan_content = self.artifact_manager.load_artifact("implementation_plan.md", context)
        if plan_content:
            has_concrete_steps = (
                    "file://" in plan_content or
                    "[MODIFY]" in plan_content or
                    "[NEW]" in plan_content or
                    "####" in plan_content or
                    "## Steps" in plan_content or
                    "## Proposed Changes" in plan_content or
                    "## Files to Modify" in plan_content or
                    "## Approach" in plan_content or
                    ".py" in plan_content or
                    ".js" in plan_content or
                    ".ts" in plan_content
            )
            if not has_concrete_steps:
                return False

        return True
