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

import logging
import re
from pathlib import Path
from typing import List, Any, Dict

from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult

# FileAction enum for HcodeDisplay tracking
try:
    from hcode.ui.hcode_display import FileAction
except ImportError:
    FileAction = None

logger = logging.getLogger(__name__)


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
    # Allowed write targets during the planning phase.
    # Any Write/Edit to a path outside this set is rejected and
    # reported back to the AI so it can self-correct.
    # ──────────────────────────────────────────────────────────
    _PLANNING_WRITE_ALLOWED = (".hcode/task.md", ".hcode/implementation_plan.md")

    def get_required_artifacts(self) -> List[str]:
        """Get artifacts this phase should produce."""
        return ["task.md", "implementation_plan.md"]

    async def _execute_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext,
    ) -> List[Dict[str, Any]]:
        """
        Planning-phase gate: reject Write/Edit calls that target files
        outside `.hcode/`.  Read-only tools (Read, LS, SmartGlob, Grep, Bash)
        pass through unchanged.

        Blocked writes are returned as failed results with a clear message
        so the multi-turn loop feeds the error back to the AI.
        """
        gated_calls = []
        results = []

        for tc in tool_calls:
            tool_name = (tc.get("tool") or "").lower()
            arguments = tc.get("arguments", {})

            # Only gate write-like tools
            if tool_name in ("write", "writetool"):
                target = (
                    arguments.get("TargetFile")
                    or arguments.get("file_path")
                    or arguments.get("path")
                    or ""
                )
                # Normalise path separators and check if target ends with an allowed artifact
                norm_target = target.replace("\\", "/").rstrip("/")
                allowed = any(norm_target.endswith(a) for a in self._PLANNING_WRITE_ALLOWED)
                if not allowed:
                    # Block and record
                    self._display(
                        f"  [>] {tc.get('tool')}: {target}  ← BLOCKED (planning scope)",
                        style="error",
                    )
                    results.append({
                        "tool": tc.get("tool"),
                        "success": False,
                        "output": None,
                        "error": (
                            f"PLANNING SCOPE VIOLATION: Write to '{target}' is not allowed "
                            f"during the planning phase. Only .hcode/task.md and "
                            f".hcode/implementation_plan.md may be written. "
                            f"Implementation files must be created in the Execution phase."
                        ),
                        "file_path": target,
                    })
                    logger.warning(f"Blocked planning-phase write to: {target}")
                    continue  # skip — don't add to gated_calls

            gated_calls.append(tc)

        # Execute the allowed calls via the parent implementation
        if gated_calls:
            parent_results = await super()._execute_tools(gated_calls, context)
            results.extend(parent_results)

        return results

    def _build_continuation_prompt(
        self,
        round_results: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]],
        round_num: int,
        context: Any = None,
    ) -> str:
        """
        Planning-phase continuation: track progress and steer toward
        the next required action.

        Enforcement rules applied at every round:
        - At least 2 successful Read calls before any artifact write
        - After task.md is written, demand implementation_plan.md with
          full granularity (targets, pseudocode, imports, dependencies)
        - After both are written, stop
        """
        working_dir = context.working_dir if context else "."

        # ── Audit what has happened across ALL rounds ──
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
            if r.get("success") and r.get("tool", "").lower() in ("read",)
        )

        # ── Both artifacts done ──
        if wrote_task and wrote_plan:
            return (
                "Both .hcode/task.md and .hcode/implementation_plan.md have been written. "
                "Planning is complete. Stop here — do not create any more files."
            )

        # ── task.md written but plan missing — demand granular detail ──
        if wrote_task and not wrote_plan:
            return (
                "✓ task.md has been written.\n\n"
                "⚠️  implementation_plan.md is STILL MISSING. You MUST write it NOW.\n"
                f"Use the Write tool with TargetFile = `{working_dir}/.hcode/implementation_plan.md`.\n\n"
                "The plan MUST be granular — not high-level headings. Every detail matters:\n"
                "  - Every [MODIFY] block must name the exact target: function/class name AND line number\n"
                "  - Include current behavior (what the code does RIGHT NOW — from what you Read)\n"
                "  - Include before/after pseudocode or code snippets for each change\n"
                "  - List every import that needs to be added\n"
                "  - Every [NEW] block must show the file structure (classes, functions, purpose)\n"
                "  - State dependencies between changes — what must happen first\n"
                "  - Add an Execution Context section: conventions, interfaces, error patterns, test infra\n"
                "  - Verification Plan must have exact shell commands (language-appropriate)\n\n"
                "Base everything on the files you already Read. Do NOT speculate.\n"
                "Do NOT stop. Write implementation_plan.md NOW."
            )

        # ── Neither artifact yet — enforce minimum reads before writing ──
        if read_count < 2:
            return (
                f"[Round {round_num}] You have completed {read_count} Read call(s) so far.\n"
                "⚠️  You MUST read at least 2 relevant files before writing any artifact.\n"
                "Continue reading files directly relevant to the user's request.\n"
                "After each Read, explain concretely what you learned and how it affects the plan.\n\n"
                "Both artifacts are still required:\n"
                f"  1. {working_dir}/.hcode/task.md\n"
                f"  2. {working_dir}/.hcode/implementation_plan.md"
            )

        # ── Enough reads done — nudge toward synthesis and writing ──
        return (
            f"[Round {round_num}] You have read {read_count} file(s).\n"
            "If you now understand the code well enough, proceed to SYNTHESIZE and write task.md.\n"
            "If you still need information, read one more file — but do not over-explore.\n\n"
            "Reminder — your artifacts must be granular:\n"
            "  - task.md: each subtask names a specific file + function/class + acceptance criteria\n"
            "  - implementation_plan.md: each change has target, current behavior, before/after, imports\n"
            "  - implementation_plan.md needs Execution Context: conventions, interfaces, test infra\n\n"
            "You MUST produce both:\n"
            f"  1. {working_dir}/.hcode/task.md\n"
            f"  2. {working_dir}/.hcode/implementation_plan.md"
        )

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute planning phase — single unified multi-turn exchange.

        The AI does everything in one conversation:
          Round 1-N  : Explore the codebase (Read, Glob, Grep, LS …)
          Round N+1  : Write .hcode/task.md
          Round N+2+ : Write .hcode/implementation_plan.md
        The continuation prompt steers the AI after each round so it doesn't
        stop prematurely.  Fallbacks fire only if the AI exhausts max_rounds
        without producing an artifact.

        Args:
            context: Current agent context
            loop_controller: Loop controller

        Returns:
            PhaseResult with planning outcome
        """
        try:
            artifacts_created = []
            analysis_insights: Dict[str, Any] = {}

            logger.info(f"Planning phase iteration {context.iteration} for task: {context.task[:50]}...")

            # =====================================================================
            # CLEAN SLATE – delete stale artifacts from previous tasks
            # =====================================================================
            for _art in ("task.md", "implementation_plan.md", "walkthrough.md"):
                _path = self.artifact_manager._get_artifact_path(_art, context)
                if _path.exists():
                    _path.unlink()
                    logger.info(f"Removed stale artifact: {_art}")

            # =====================================================================
            # PROGRAMMATIC EXPLORATION – ground the prompt with real data
            # =====================================================================
            exploration_context = self._explore_codebase(context)
            self._display("Exploring codebase...", style="info")

            # =====================================================================
            # SINGLE UNIFIED PROMPT – explore then create artifacts
            # =====================================================================
            unified_prompt = self._build_unified_planning_prompt(context, exploration_context)

            response = ""
            tool_results: List[Dict[str, Any]] = []

            if self.provider is not None:
                self._display("Planning…", style="info")

                if self._hcode_display:
                    self._hcode_display.start_thinking()

                response, tool_results = await self._generate_and_execute(
                    unified_prompt,
                    context,
                    system_prompt=self._get_planning_system_prompt(context),
                    max_rounds=20,   # deep reads + synthesis + 2 writes + confirmation
                    max_tokens=16384, # gpt-oss-120b — deep reasoning + code snippets
                )

                if self._hcode_display:
                    self._hcode_display.end_thinking()

                # Track which artifacts the AI actually wrote
                for result in tool_results:
                    if not result.get("success"):
                        continue
                    fp = str(result.get("file_path", ""))
                    if "task.md" in fp and "task.md" not in artifacts_created:
                        artifacts_created.append("task.md")
                        if self._hcode_display and FileAction:
                            self._hcode_display.track_file(".hcode/task.md", FileAction.CREATED)
                    if "implementation_plan.md" in fp and "implementation_plan.md" not in artifacts_created:
                        artifacts_created.append("implementation_plan.md")
                        if self._hcode_display and FileAction:
                            self._hcode_display.track_file(".hcode/implementation_plan.md", FileAction.CREATED)

                # Extract insights from the response (used by fallback if needed)
                analysis_insights = self._extract_analysis_insights(response)

            else:
                logger.warning("No AI provider configured for planning phase")
                self._display("No AI provider configured for planning!", style="error")

            # =====================================================================
            # FALLBACK SAFETY NET – only fires if AI failed to write an artifact
            # after all rounds.  Should be rare with the continuation steering.
            # =====================================================================
            if not self.artifact_manager.artifact_exists("task.md", context):
                self._display("  [!] task.md missing — generating fallback", style="info")
                fallback = self._create_fallback_task_md(context, analysis_insights)
                if fallback:
                    self.artifact_manager.create_artifact("task.md", fallback, context)
                    self._display("  Created task.md (fallback)", style="success")
                    artifacts_created.append("task.md")

            if not self.artifact_manager.artifact_exists("implementation_plan.md", context):
                self._display("  [!] implementation_plan.md missing — generating fallback", style="info")
                fallback = self._create_fallback_implementation_plan(context, analysis_insights)
                if fallback:
                    self.artifact_manager.create_artifact("implementation_plan.md", fallback, context)
                    self._display("  Created implementation_plan.md (fallback)", style="success")
                    artifacts_created.append("implementation_plan.md")

            # =====================================================================
            # VALIDATE & TRANSITION
            # =====================================================================
            valid, error = self.validate_artifacts(context)
            if not valid:
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output=f"Planning phase validation failed: {error}",
                    artifacts_created=artifacts_created,
                    can_transition=False,
                    error=error,
                    metadata={"tool_results": tool_results, "analysis_insights": analysis_insights},
                )

            can_transition = self.can_transition_to_next(context)

            is_exploration = context.metadata.get("task_type") == "exploration"
            output = response if (is_exploration and response) else (
                f"Planning phase complete. Created: {', '.join(artifacts_created) or 'no new artifacts'}"
            )

            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output=output,
                artifacts_created=artifacts_created,
                can_transition=can_transition,
                metadata={"tool_results": tool_results, "analysis_insights": analysis_insights, "response": response},
            )

        except Exception as e:
            logger.exception(f"Planning phase failed: {e}")
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                output=f"Planning phase failed: {str(e)}",
                can_transition=False,
                error=str(e),
            )

    def _get_planning_system_prompt(self, context: AgentContext) -> str:
        """
        Get system prompt for planning phase.

        Uses core prompts from phases.yaml.

        Args:
            context: Current agent context

        Returns:
            Complete system prompt for planning
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            # Get identity and tool format
            identity = loader.get_identity()
            tool_format = loader.get_tool_format()

            # Get planning instruction from core prompts
            planning_prompt = loader.build_planning_prompt(task=context.task)

            # Load artifact templates from perfect_prompts for reference
            artifact_templates = self._get_artifact_templates()

            # Build system prompt with identity, tool format, and templates
            system_base = f"""{identity}

{tool_format}

---

{planning_prompt}

---

## ARTIFACT REFERENCE TEMPLATES

Follow these templates EXACTLY when creating task.md and implementation_plan.md:

{artifact_templates}"""

            # ── Load project knowledge from /init ──────────────────
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
                else "(Run /init first to generate project knowledge.)"
            )

            # Add context information
            context_info = f"""
## PROJECT KNOWLEDGE  (generated by /init — read this before anything else)

{pk_section}

---

## Hcode Context

Working Directory: {context.working_dir}
Artifact Directory: .hcode
Current Iteration: {context.iteration}

### PEV Workflow (ALWAYS ENFORCED)

1. **PLANNING** ← you are here: create task.md and implementation_plan.md
2. **EXECUTION**: implement the plan
3. **VERIFICATION**: test and create walkthrough.md

### Communication Rules

1. Provide TEXT explanations of your reasoning at every step
2. Use JSON tool calls in code blocks for file operations
3. After each Read, state what you learned and why it matters

### TOOL CALL FORMAT

```json
{{"tool": "ToolName", "arguments": {{"param": "value"}}}}
```

**Tools you should use in planning:**
- Read: `{{"tool": "Read", "arguments": {{"AbsolutePath": "/full/path"}}}}`  ← primary tool
- Grep: `{{"tool": "Grep", "arguments": {{"Query": "pattern", "SearchPath": "."}}}}`  ← find symbols
- Write: `{{"tool": "Write", "arguments": {{"TargetFile": "/full/path", "CodeContent": "content"}}}}`  ← artifacts only

**Tools you should NOT need in planning:**
- LS / SmartGlob: project structure is already in PROJECT KNOWLEDGE above.
  Use them only if you genuinely need to discover something not covered there.

### Artifact Detail Requirements

Each artifact must be granular — the execution phase reads these to know
exactly what to do.  Generic placeholders are not acceptable.

**task.md** must contain:
  • A `## Goal` section (1-2 sentences)
  • 4-8 subtasks, each naming a specific file + function/class
  • Acceptance criteria after every subtask
  • A `## Risks / Edge Cases` section

**implementation_plan.md** must contain:
  • Each `[MODIFY]` block: exact target (function/line), current behavior,
    before/after pseudocode, imports to add, and a one-line "Why"
  • Each `[NEW]` block: purpose, file-structure outline, what imports it
  • A `## Execution Context` section: conventions, interfaces, error patterns, test infra
  • A `## Dependencies Between Changes` section
  • Exact verification commands — language-appropriate (syntax check, tests, smoke test)

### Example — think first, then read, then plan:

I need to add error logging to CLI startup.  From the project knowledge
I can see the CLI entry is `src/hcode/main_cli.py` and observability lives
in `src/hcode/core/observability/`.  Let me read the actual files before
deciding anything.

```json
{{"tool": "Read", "arguments": {{"AbsolutePath": "{context.working_dir}/src/hcode/main_cli.py"}}}}
```

(… receives file contents …)

The startup sequence is at line 42 — a bare try block with no logging.
Now let me check how the logger factory works:

```json
{{"tool": "Read", "arguments": {{"AbsolutePath": "{context.working_dir}/src/hcode/core/observability/logger.py"}}}}
```

(… receives file contents …)

`get_logger(name)` returns a stdlib Logger.  I now know the exact import,
the call site, and what the current code does.  Writing task.md:

```json
{{"tool": "Write", "arguments": {{"TargetFile": "{context.working_dir}/.hcode/task.md", "CodeContent": "# Task\\n\\nAdd error logging to CLI startup\\n\\n## Goal\\n\\nErrors during CLI initialisation are captured by the observability logger.\\n\\n## Subtasks\\n\\n- [ ] Add `from hcode.core.observability.logger import get_logger` to main_cli.py <!-- id: 0 -->\\n  - Acceptance: `python -m py_compile src/hcode/main_cli.py` exits 0\\n- [ ] Insert `logger.error(exc)` in the except block at startup (line 42) <!-- id: 1 -->\\n  - Acceptance: error path produces a log entry in output\\n- [ ] Run `pytest tests/unit/test_cli.py -v` <!-- id: 2 -->\\n  - Acceptance: all tests pass\\n\\n## Risks\\n\\n- Logger must be initialised before the call site at line 42"}}}}
```

task.md written.  Now writing implementation_plan.md with full detail:

```json
{{"tool": "Write", "arguments": {{"TargetFile": "{context.working_dir}/.hcode/implementation_plan.md", "CodeContent": "# Add error logging to CLI startup\\n\\nThe CLI startup at line 42 does not log errors — they propagate uncaught.\\nThis change adds a logger call so failures are captured.\\n\\n## Approach\\n\\n`get_logger` in the observability layer is the project convention.\\nReuse it — no new abstractions needed.\\n\\n## Execution Context\\n\\n- **Import convention:** absolute imports, one per line\\n- **Error handling:** try/except + logger.error()\\n- **Test framework:** pytest\\n- **Key interfaces:** none affected by this change\\n\\n## Proposed Changes\\n\\n### CLI Entry Point\\n\\n#### [MODIFY] `src/hcode/main_cli.py`\\n\\n**Target:** startup block, line 42\\n**Current behavior:** exceptions during init propagate uncaught (bare except)\\n**Required change:**\\n- Add import: `from hcode.core.observability.logger import get_logger`\\n- Add `logger = get_logger(__name__)` after existing imports\\n- In the except block at line 42: add `logger.error(\\\"Startup failed\\\", exc_info=True)`\\n**Why:** observability layer is the project convention for error capture\\n\\n## Dependencies Between Changes\\n\\nSingle file changed — no ordering constraints.\\n\\n## Verification Plan\\n\\n- `python -m py_compile src/hcode/main_cli.py`\\n- `pytest tests/unit/test_cli.py -v`\\n- `python -m hcode --help` — confirm no crash"}}}}
```

Both artifacts written.  Planning complete.

⚠️  SCOPE BOUNDARY: In planning mode you ONLY create `.hcode/task.md` and `.hcode/implementation_plan.md`.
Do NOT create any implementation / source files. Those are created during EXECUTION.
"""
            return system_base + context_info

        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            # Fallback to basic prompt
            return f"""You are Hcode, an AI coding assistant in PLANNING mode.

Your task: {context.task}

Working Directory: {context.working_dir}

## Instructions

1. Analyze the user's request
2. Explore the codebase using tools (LS, Glob, Read)
3. Create .hcode/task.md with task breakdown
4. Create .hcode/implementation_plan.md with implementation approach

IMPORTANT: Always provide text explanations along with tool usage.
DO NOT just output JSON silently.
"""

    def _explore_codebase(self, context: AgentContext) -> str:
        """
        Language-agnostic file-path index for the planning prompt.

        Single rglob pass: discovers source, config, web, and doc files
        across all supported languages/frameworks.  Groups output by
        extension with source files first so the AI can target Read
        calls with precise paths.  Project knowledge (architecture,
        conventions) lives in the system prompt via hcode.md — this
        method only provides the file inventory.
        """
        from collections import defaultdict

        working_dir = Path(context.working_dir)
        lines = [f"Working directory: {context.working_dir}\n"]

        _EXCLUDE = {'.git', '.venv', 'node_modules', '__pycache__', '.idea',
                    'dist', 'build', '.mypy_cache', '.next', '.cache'}

        # ── Extension sets (language-agnostic) ──
        _SOURCE = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.mjs', '.cjs',
            '.go', '.rs', '.java', '.rb', '.cs', '.swift', '.kt', '.kts',
            '.scala', '.c', '.cpp', '.h', '.hpp', '.cc', '.cxx',
            '.vue', '.svelte', '.php', '.lua', '.sh', '.bash',
        }
        _CONFIG = {'.yaml', '.yml', '.json', '.toml', '.cfg', '.ini', '.env'}
        _WEB    = {'.html', '.css', '.scss', '.sass', '.less'}
        _DOC    = {'.md', '.rst', '.txt'}
        _ALL    = _SOURCE | _CONFIG | _WEB | _DOC

        by_ext: Dict[str, List[Path]] = defaultdict(list)
        for p in sorted(working_dir.rglob("*")):
            if not p.is_file():
                continue
            if any(ex in p.parts for ex in _EXCLUDE):
                continue
            ext = p.suffix.lower()
            if ext in _ALL:
                by_ext[ext].append(p)

        # Priority: source → config → web → docs; within tier sort by count desc
        def _priority(ext):
            if ext in _SOURCE: return 0
            if ext in _CONFIG: return 1
            if ext in _WEB:    return 2
            return 3

        for ext, files in sorted(by_ext.items(), key=lambda kv: (_priority(kv[0]), -len(kv[1]))):
            lines.append(f"{ext} files ({len(files)}):")
            for f in files[:35]:
                lines.append(f"  {f.relative_to(working_dir)}")
            if len(files) > 35:
                lines.append(f"  ... and {len(files) - 35} more")
            lines.append("")

        return "\n".join(lines)

    def _build_unified_planning_prompt(self, context: AgentContext, exploration_context: str) -> str:
        """
        Build the single unified prompt that drives the entire planning phase.

        The system prompt already contains the full project knowledge
        (hcode.md).  This prompt drives a think → read → synthesize →
        write flow.  No repo-discovery rounds — the AI already knows the
        project; it must only read the *specific* files relevant to this
        task before writing artifacts.
        """
        task_template = self._get_task_template_guide()
        plan_template = self._get_plan_template_guide()

        return f"""You are an expert AI developer in PLANNING mode.  You already know the
project structure and conventions from the PROJECT KNOWLEDGE in your system
prompt.  Your job: understand this specific request deeply, read the files
that matter, then produce two planning artifacts — and NOTHING else.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context.task}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE INDEX  (use these paths in Read calls — do NOT run LS or Glob)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{exploration_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — THINK  (write this out before calling any tool)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before touching any tool, reason through:

  • What exactly does the user want to happen?
  • Which existing files are directly involved?  (use your project knowledge)
  • Is this an addition, a modification, or a removal?
  • What are the likely risks or edge cases?
  • Which files do I need to READ to make confident decisions?

Write this reasoning out loud.  Every line of reasoning here saves a wasted
round later.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — READ  (tools: Read and Grep only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Open every file your Step 1 identified as relevant.  Use Read with
absolute paths.  Use Grep only if you need to locate a specific symbol
or pattern inside a file.

⚠️  Do NOT use LS or SmartGlob — the file index above and the
    PROJECT KNOWLEDGE in the system prompt already cover the layout.
⚠️  Do NOT assume file contents.  Read first, decide second.
⚠️  After each Read, state concretely what you learned and how it
    affects the plan.  This reasoning feeds directly into the artifacts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — SYNTHESIZE  (text only, no tools)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Now that you have read the real code, pin down:

  • Exactly which functions / classes / lines need changing?
  • What new files or code blocks are needed?
  • What imports, signatures, or interfaces must be respected?
  • What tests should verify correctness?  (exact commands)
  • What conventions / patterns must execution follow? (imports, error handling, naming, tests)
  • Any dependencies between changes — ordering matters.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — WRITE task.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Path: {context.working_dir}/.hcode/task.md

{task_template}

Rules:
  • Every subtask gets a unique `<!-- id: N -->` comment.
  • Use `- [ ]` for pending, `- [/]` for in-progress, `- [x]` for done.
  • Break work into 4-8 concrete subtasks grounded in what you Read.
  • Every subtask MUST name the specific file + function/class it touches.
  • Include acceptance criteria after each subtask (what proves it is done).
  • Add a ## Goal section (1-2 sentences: what success looks like).
  • Add a ## Risks / Edge Cases section with findings from your reads.
  • No generic boilerplate — if you cannot tie a subtask to real code, omit it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — WRITE implementation_plan.md  (immediately after task.md)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Path: {context.working_dir}/.hcode/implementation_plan.md

{plan_template}

Rules:
  • Approach: WHY this approach — reference real code / patterns you Read.
  • Every file that will be created or modified must have a [NEW] or
    [MODIFY] marker with an absolute path.
  • Each [MODIFY] block MUST contain:
      – Exact target: function/class name and line number
      – Current behavior: what the code does RIGHT NOW (from your Reads)
      – Required change: before/after pseudocode or code snippets
      – Imports to add (if any)
      – Why: one sentence linking this change to the goal
  • Each [NEW] block MUST contain:
      – Purpose: why this file is needed
      – Structure: outline of classes/functions it will contain
      – What other files will import from it
  • Include a ## Execution Context section: conventions, interfaces, error patterns,
      test framework details the execution phase must follow — no re-reading required.
  • Include a ## Dependencies Between Changes section: ordering constraints.
  • Verification Plan: exact shell commands for syntax, unit, and integration tests.
  • Nothing in this plan may be speculation — every claim must trace
    back to something you actually Read.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE RULES  (hard boundaries)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  You may ONLY write two files:
      {context.working_dir}/.hcode/task.md
      {context.working_dir}/.hcode/implementation_plan.md
    Any write to any other path will be BLOCKED by the system.

⚠️  Do NOT create implementation files (scripts, modules, configs).
    Those are created during the Execution phase.

⚠️  Do NOT stop until BOTH artifacts have been written.
    The system will tell you after each tool round whether an artifact
    is still missing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BEGIN.  Start with Step 1 — think out loud before calling any tool.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


    def _get_task_template_guide(self) -> str:
        """Get task.md template guide — atomic subtasks with acceptance criteria."""
        return """```markdown
# Task

[Restate the user's request in your own words]

## Goal

[1-2 sentences: what success looks like after this task is complete]

## Subtasks

- [ ] Read and understand `path/to/file.py` — `ClassName.method` (lines N-M) <!-- id: 0 -->
  - Acceptance: can describe what the code does and where changes are needed
- [ ] Add import / require / include for `ModuleName` in `path/to/source_file` <!-- id: 1 -->
  - Acceptance: syntax check passes for the modified file
- [ ] Modify `ClassName.method` in `path/to/source_file` to [specific change] <!-- id: 2 -->
  - Acceptance: [exact observable condition that proves correctness]
- [ ] Create `path/to/new_file` with [purpose] <!-- id: 3 -->
  - Acceptance: [exact condition — e.g., relevant test passes]
- [ ] Run verification: `<test-runner command for the changed component>` <!-- id: 4 -->
  - Acceptance: exits 0, expected output observed

## Risks / Edge Cases

- [risk or edge case identified while reading the code]
- [dependency ordering issue, if any]

## Notes

- [key findings from code reading that the execution phase needs]
```"""

    def _get_plan_template_guide(self) -> str:
        """Get implementation_plan.md template guide — full granularity per change."""
        return '''```markdown
# [Goal: one-line summary of the change]

[2-3 sentences: problem statement and what the change accomplishes]

## User Review Required

> [!IMPORTANT]
> [Any decisions that need sign-off before execution.
>  If none, write "No decisions pending — proceed to execution."]

## Approach

[2-4 sentences: WHY this approach. Reference patterns or conventions
observed in the code you Read. Note any trade-offs considered.]

## Execution Context

The execution phase reads this section to follow project conventions
without re-reading source files.  Fill in from what you observed:

- **Import / module system:** [e.g., absolute imports / CommonJS require / ES modules]
- **Error handling pattern:** [e.g., try/except + logger.error() / throw custom errors]
- **Naming conventions:** [e.g., snake_case / camelCase / PascalCase rules observed]
- **Test framework & fixtures:** [e.g., pytest + conftest.py / Jest + setupTests / Go testing]
- **Key interfaces / base classes:** [e.g., all handlers extend BaseHandler; must implement handle()]
- **Config / env access:** [e.g., Settings() singleton / process.env / config package]

## Proposed Changes

### [Component / Module Name]

[1 sentence: what this group of changes achieves]

#### [MODIFY] `absolute/path/to/file`

**Target:** `ClassName.method_name` at line N  (or top-level `func_name` at line N)

**Current behavior:** [What the code does right now — from what you Read, 1-2 sentences]

**Required change:**
```
# BEFORE (current code at line N):
    existing_code_line_1()
    existing_code_line_2()

# AFTER:
    existing_code_line_1()
    new_logic(param)          # added
    existing_code_line_2()
```

**Imports to add:** `[import statement — use the project's language convention]`

**Why:** [1 sentence linking this change to the goal]

---

#### [NEW] `absolute/path/to/new_file`

**Purpose:** [What this file does and why it is needed]

**Structure:**
```
# Outline — execution phase fills in the bodies:
ClassName / struct / interface (use project convention):
    constructor(deps) -> instance
    method_1(args) -> ReturnType  # [what this does]
    method_2(args) -> ReturnType  # [what this does]
```

**Imported by:**
- `path/to/other_file` will need: `[import statement in the project's language]`

---

### [Another Component — repeat the pattern above]

## Dependencies Between Changes

1. [Change A] must complete before [Change B] because [reason]
2. [Change C] is independent — can proceed in any order

## Verification Plan

### Syntax Check
- `<syntax check command for each modified / new file>`
  (Python: `python -m py_compile` | JS/TS: `npx tsc --noEmit` | Go: `go build ./...` | Rust: `cargo check`)

### Unit Tests
- `<test-runner command targeting the changed component>`
  (Python: `pytest tests/X.py -v` | JS: `npx jest X.test.js` | Go: `go test -run TestX` | Rust: `cargo test`)

### Integration / Smoke Test
- `[exact command]` → expect `[exact output]`

### Manual Verification
- [step-by-step what to verify manually, if needed]
```'''

    def _extract_analysis_insights(self, response: str) -> Dict[str, Any]:
        """
        Extract analysis insights from AI response.

        Parses the <analysis> block from the AI's deep analysis.

        Args:
            response: AI response containing analysis

        Returns:
            Dict with extracted insights
        """
        insights = {
            "understanding": "",
            "relevant_files": [],
            "components": [],
            "dependencies": [],
            "questions": [],
            "approach": "",
        }

        if not response:
            return insights

        # Try to extract analysis block
        analysis_match = re.search(
            r'<analysis>(.*?)</analysis>',
            response,
            re.DOTALL | re.IGNORECASE
        )

        if analysis_match:
            analysis_content = analysis_match.group(1)
        else:
            # Use full response if no block found
            analysis_content = response

        # Extract understanding section
        understanding_match = re.search(
            r'##\s*Understanding\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if understanding_match:
            insights["understanding"] = understanding_match.group(1).strip()

        # Extract relevant files
        files_match = re.search(
            r'##\s*Relevant Files?\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if files_match:
            files_text = files_match.group(1)
            file_lines = re.findall(r'-\s*([^\n:]+)', files_text)
            insights["relevant_files"] = [f.strip() for f in file_lines if f.strip()]

        # Extract components
        components_match = re.search(
            r'##\s*Components?\s*(?:Affected)?\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if components_match:
            components_text = components_match.group(1)
            component_lines = re.findall(r'-\s*([^\n]+)', components_text)
            insights["components"] = [c.strip() for c in component_lines if c.strip()]

        # Extract approach
        approach_match = re.search(
            r'##\s*(?:Recommended\s*)?Approach\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if approach_match:
            insights["approach"] = approach_match.group(1).strip()

        # Extract questions/ambiguities
        questions_match = re.search(
            r'##\s*(?:Questions?|Ambiguities?)\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if questions_match:
            questions_text = questions_match.group(1)
            question_lines = re.findall(r'-\s*([^\n]+)', questions_text)
            insights["questions"] = [q.strip() for q in question_lines if q.strip()]

        return insights

    def _create_fallback_task_md(self, context: AgentContext, analysis_insights: Dict[str, Any]) -> str:
        """
        Build task.md programmatically when AI fails to produce it.

        Uses the task description and any analysis insights gathered
        during the deep-analysis round.
        """
        subtasks = []
        idx = 0

        # If we have relevant files from analysis, create subtasks from them
        relevant_files = analysis_insights.get("relevant_files", [])
        if relevant_files:
            subtasks.append(f"- [ ] Explore relevant files <!-- id: {idx} -->")
            idx += 1

        # Default subtasks based on task type
        subtasks.append(f"- [ ] Implement required changes <!-- id: {idx} -->")
        idx += 1
        subtasks.append(f"- [ ] Verify implementation works <!-- id: {idx} -->")
        idx += 1

        notes = ""
        if analysis_insights.get("questions"):
            notes = "\n## Notes\n\n" + "\n".join(f"- {q}" for q in analysis_insights["questions"])

        return (
            f"# Task\n\n"
            f"{context.task}\n\n"
            f"## Subtasks\n\n"
            + "\n".join(subtasks)
            + notes
        )

    def _create_fallback_implementation_plan(self, context: AgentContext, analysis_insights: Dict[str, Any]) -> str:
        """
        Build implementation_plan.md programmatically when AI fails to produce it.

        Constructs a concrete plan from the analysis insights that were
        gathered in the deep-analysis round.  This ensures execution always
        has a real plan to work from, even if the AI hallucinated a Write
        call it never actually made.
        """
        # Heading / goal – derive from the task
        goal_line = context.task[:120]

        # Approach section
        approach = analysis_insights.get("approach", "Implement the requested changes step by step.")

        # Build steps from relevant files
        relevant_files = analysis_insights.get("relevant_files", [])
        steps = []
        step_num = 1

        if relevant_files:
            files_list = "\n".join(f"   - `{f.strip()}`" for f in relevant_files[:10])
            steps.append(
                f"{step_num}. **Explore relevant files**\n{files_list}"
            )
            step_num += 1

        steps.append(
            f"{step_num}. **Implement changes**\n"
            f"   - Apply changes according to the approach above\n"
            f"   - Create or modify files as needed"
        )
        step_num += 1

        steps.append(
            f"{step_num}. **Verify**\n"
            f"   - Check that new/modified files are syntactically correct\n"
            f"   - Run the result to confirm it works"
        )

        steps_text = "\n\n".join(steps)

        # Files to modify/create
        files_section = ""
        if relevant_files:
            files_section = "\n## Files to Modify\n\n" + "\n".join(
                f"- `{f.strip()}`: review and apply changes" for f in relevant_files[:10]
            )

        # Testing strategy – keep it proportional
        testing = (
            "\n## Testing Strategy\n\n"
            "- Syntax check: `<language-appropriate syntax check for each file>`\n"
            "- Run / test the changed component to verify output"
        )

        # Execution Context – placeholder; execution phase should fill from codebase
        components = analysis_insights.get("components", [])
        exec_ctx_items = [
            "- **Import / module system:** [identify from codebase before implementing]",
            "- **Error handling pattern:** [identify from codebase before implementing]",
            "- **Test framework & fixtures:** [identify from codebase before implementing]",
            "- **Key interfaces / base classes:** " + (
                ", ".join(f"`{c}`" for c in components[:5]) if components else "[identify from codebase]"
            ),
        ]
        exec_context = "\n## Execution Context\n\n" + "\n".join(exec_ctx_items)

        return (
            f"# {goal_line}\n\n"
            f"{context.task}\n\n"
            f"## Approach\n\n"
            f"{approach}\n"
            f"{exec_context}\n\n"
            f"## Steps\n\n"
            f"{steps_text}\n"
            f"{files_section}\n"
            f"{testing}\n"
        )

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

    def _get_artifact_templates(self) -> str:
        """
        Get artifact templates from CorePromptLoader (templates.yaml).

        These templates provide guidelines for creating high-quality
        task.md and implementation_plan.md files.

        Returns:
            Combined templates as a string
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            task_template = loader.get_template("task_md") or ""
            plan_template = loader.get_template("implementation_plan_md") or ""

            if task_template or plan_template:
                templates = []
                if task_template:
                    templates.append("### task.md Template\n\n" + task_template)
                if plan_template:
                    templates.append("### implementation_plan.md Template\n\n" + plan_template)
                return "\n\n---\n\n".join(templates)

        except Exception as e:
            logger.warning(f"Failed to load artifact templates: {e}")

        # Fallback: inline templates matching the granular style
        return """### task.md Template

```markdown
# Task

[Restate request in your own words]

## Goal

[1-2 sentences: what success looks like]

## Subtasks

- [ ] [Action] in `path/to/file` — `ClassName.method` (line N) <!-- id: 0 -->
  - Acceptance: [exact condition]
- [ ] [Next action] <!-- id: 1 -->
  - Acceptance: [exact condition]

## Risks / Edge Cases

- [identified risk]

## Notes

- [key finding for execution phase]
```

### implementation_plan.md Template

```markdown
# [Goal: one-line summary]

[2-3 sentences: problem + what changes]

## Approach

[WHY this approach — reference code patterns you Read]

## Execution Context

- **Import / module system:** [project convention]
- **Error handling:** [project convention]
- **Test framework:** [framework + fixtures]
- **Key interfaces:** [base classes / protocols]

## Proposed Changes

### [Component]

#### [MODIFY] `absolute/path/to/file`

**Target:** `ClassName.method` at line N
**Current behavior:** [what it does now]
**Required change:**
- [specific change with pseudocode]
**Imports to add:** `[import statement in the project's language]`
**Why:** [link to goal]

#### [NEW] `absolute/path/to/new_file`

**Purpose:** [why needed]
**Structure:** classes/functions outline
**Imported by:** `[import statement]` in `[which files]`

## Dependencies Between Changes

1. [ordering constraint]

## Verification Plan

- `<syntax check for each file>` (Python: py_compile | JS/TS: tsc | Go: go build)
- `<test-runner for changed component>` (Python: pytest | JS: jest | Go: go test)
```
"""
