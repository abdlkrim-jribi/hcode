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
        Planning-phase continuation: inspect what was just written and
        steer the AI toward the next required action.

        - If neither artifact exists yet  → push to keep exploring OR write task.md
        - If task.md was just written      → explicitly demand implementation_plan.md next
        - If both exist                    → tell it to stop
        """
        working_dir = context.working_dir if context else "."

        # Scan all results for successful writes to our artifacts
        wrote_task = any(
            r.get("success") and "task.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        wrote_plan = any(
            r.get("success") and "implementation_plan.md" in str(r.get("file_path", ""))
            for r in all_results
        )

        if wrote_task and wrote_plan:
            return (
                "Both .hcode/task.md and .hcode/implementation_plan.md have been written. "
                "Planning is complete. Stop here — do not create any more files."
            )

        if wrote_task and not wrote_plan:
            return (
                "✓ task.md has been written.\n\n"
                "⚠️  implementation_plan.md is STILL MISSING. You MUST write it now.\n"
                f"Use the Write tool with TargetFile = `{working_dir}/.hcode/implementation_plan.md`.\n"
                "The plan MUST include:\n"
                "  - A `# heading` describing the goal\n"
                "  - `## Approach` — high-level strategy\n"
                "  - `## Steps` — numbered concrete steps\n"
                "  - File paths with [NEW] or [MODIFY] markers\n"
                "  - `## Verification Plan` — exact commands to test\n\n"
                "Do NOT stop. Write implementation_plan.md NOW."
            )

        # Neither artifact written yet — check if this is early exploration
        has_exploration = any(
            r.get("tool", "").lower() in ("read", "smartglob", "ls", "grep", "bash", "smartglobtool")
            for r in round_results
        )
        if has_exploration and round_num < 3:
            return (
                "Good — you've gathered some information. Continue exploring if you need more context, "
                "but remember you must eventually create BOTH artifacts:\n"
                f"  1. {working_dir}/.hcode/task.md\n"
                f"  2. {working_dir}/.hcode/implementation_plan.md\n"
                "When you have enough understanding, start writing them. Do not stop until both are written."
            )

        return (
            "Continue exploring or start creating the planning artifacts. "
            f"You MUST produce both {working_dir}/.hcode/task.md and {working_dir}/.hcode/implementation_plan.md. "
            "Do not stop until both are written."
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
                    max_rounds=12,   # generous — exploration + 2 writes + confirmation
                    max_tokens=8192, # deep thinking needs room
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

            # Add context information
            context_info = f"""
## Hcode Context

Working Directory: {context.working_dir}
Artifact Directory: .hcode
Current Iteration: {context.iteration}

### PEV Workflow (ALWAYS ENFORCED)

The PEV (Planning → Execution → Verification) workflow is ALWAYS executed.
Every task goes through:

1. **PLANNING**: Create task.md and implementation_plan.md
2. **EXECUTION**: Implement the plan using tools
3. **VERIFICATION**: Test and create walkthrough.md

### CRITICAL: Communication Rules

**YOU MUST**:
1. Provide TEXT explanations of what you're doing
2. Use JSON tool calls in code blocks for file operations
3. Summarize your findings and progress in plain text

### TOOL CALL FORMAT (CRITICAL!)

When you need to use a tool, output JSON in this EXACT format inside a code block:

```json
{{"tool": "ToolName", "arguments": {{"param": "value"}}}}
```

**Available tools:**
- LS: `{{"tool": "LS", "arguments": {{"DirectoryPath": "."}}}}`
- Read: `{{"tool": "Read", "arguments": {{"AbsolutePath": "/full/path"}}}}`
- Write: `{{"tool": "Write", "arguments": {{"TargetFile": "/full/path", "CodeContent": "content"}}}}`
- Edit: `{{"tool": "Edit", "arguments": {{"TargetFile": "/path", "TargetContent": "old", "ReplacementContent": "new"}}}}`
- SmartGlob: `{{"tool": "SmartGlob", "arguments": {{"Pattern": "**/*.py"}}}}`
- Grep: `{{"tool": "Grep", "arguments": {{"Query": "pattern", "SearchPath": "."}}}}`
- Bash: `{{"tool": "Bash", "arguments": {{"CommandLine": "command", "description": "what it does"}}}}`

### Example Good Response:

I'll help you create a script to count markdown files.  Let me first explore
the project to understand its structure and conventions.

```json
{{"tool": "LS", "arguments": {{"DirectoryPath": "."}}}}
```

(… receives directory listing …)

Let me check if there are any existing utility scripts to follow the same style:

```json
{{"tool": "SmartGlob", "arguments": {{"Pattern": "*.py"}}}}
```

(… receives list of .py files …)

Let me read an existing script to understand import style and conventions:

```json
{{"tool": "Read", "arguments": {{"AbsolutePath": "{context.working_dir}/some_existing_script.py"}}}}
```

(… receives file contents, analyses conventions …)

Good.  Now I understand the codebase.  Creating task.md:

```json
{{"tool": "Write", "arguments": {{"TargetFile": "{context.working_dir}/.hcode/task.md", "CodeContent": "# Task\\n\\nCreate a script to count .md files in the repo.\\n\\n## Subtasks\\n\\n- [ ] Explore repo structure <!-- id: 0 -->\\n- [ ] Implement counter script <!-- id: 1 -->\\n- [ ] Test the script <!-- id: 2 -->"}}}}
```

task.md written.  Now creating implementation_plan.md:

```json
{{"tool": "Write", "arguments": {{"TargetFile": "{context.working_dir}/.hcode/implementation_plan.md", "CodeContent": "# Count markdown files in repo\\n\\nCreate a utility script that recursively counts .md files and their total lines.\\n\\n## Approach\\n\\nUse pathlib.Path.rglob to discover .md files, excluding .git and .venv directories. This mirrors the pattern used in existing scripts in this repo.\\n\\n## Steps\\n\\n1. **Create script** [NEW] `{context.working_dir}/count_md.py` — main counting logic\\n2. **Test** — run the script and verify output\\n\\n## Verification Plan\\n\\n- Syntax: `python -m py_compile count_md.py`\\n- Run: `python count_md.py`"}}}}
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
        Programmatic exploration of the working directory.

        Gathers directory listing, Python/MD/config file counts and paths
        so the AI analysis prompt is grounded even if the AI calls no tools.

        Args:
            context: Current agent context

        Returns:
            Formatted exploration summary string
        """
        working_dir = Path(context.working_dir)
        lines = [f"Working directory: {context.working_dir}\n"]

        # Root-level listing (skip deep hidden dirs)
        lines.append("Root contents:")
        try:
            for item in sorted(working_dir.iterdir()):
                if item.name.startswith('.') and item.name not in ('.hcode', '.claude', '.git'):
                    continue
                marker = "📁" if item.is_dir() else "📄"
                lines.append(f"  {marker} {item.name}")
        except OSError:
            lines.append("  (could not list directory)")

        # File-type inventories
        _EXCLUDE = {'.git', '.venv', 'node_modules', '__pycache__', '.idea'}

        def _rglob_filtered(pattern):
            return [
                p for p in working_dir.rglob(pattern)
                if not any(ex in p.parts for ex in _EXCLUDE)
            ]

        py_files = sorted(_rglob_filtered("*.py"))
        md_files = sorted(_rglob_filtered("*.md"))

        lines.append(f"\nPython files ({len(py_files)}):")
        for f in py_files[:30]:
            lines.append(f"  - {f.relative_to(working_dir)}")
        if len(py_files) > 30:
            lines.append(f"  ... and {len(py_files) - 30} more")

        lines.append(f"\nMarkdown files ({len(md_files)}):")
        for f in md_files[:15]:
            lines.append(f"  - {f.relative_to(working_dir)}")
        if len(md_files) > 15:
            lines.append(f"  ... and {len(md_files) - 15} more")

        return "\n".join(lines)

    def _build_unified_planning_prompt(self, context: AgentContext, exploration_context: str) -> str:
        """
        Build the single unified prompt that drives the entire planning phase.

        The AI is expected to:
          1. Read and understand the codebase (multiple tool calls)
          2. Write .hcode/task.md
          3. Write .hcode/implementation_plan.md

        The continuation steering in _build_continuation_prompt handles
        nudging the AI between these stages.  This prompt sets up the
        expectations and provides all context the AI needs.
        """
        task_template = self._get_task_template_guide()
        plan_template = self._get_plan_template_guide()

        return f"""You are an expert AI developer in PLANNING mode.  Your job is to thoroughly
understand the user's request, explore the codebase, and produce two planning
artifacts — and NOTHING else.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context.task}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CODEBASE SNAPSHOT  (pre-scanned — use this as your starting map)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{exploration_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — UNDERSTAND & EXPLORE  (do this FIRST, before any writes)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Think carefully about what the user needs.  Then use tools to verify
your understanding against reality — do NOT assume.

Required exploration steps:
  a) Use Read to open any files that are directly relevant to the task.
     Read their ACTUAL contents before making decisions.
  b) Use SmartGlob or Grep to find files matching patterns relevant to the task.
  c) If there are existing similar scripts or modules, Read them to understand
     conventions, imports, and style used in this repo.
  d) Identify exactly which files will need to be created or modified, and why.

Think out loud as you explore.  Explain what you found and what it means
for the implementation plan.  This reasoning is critical — be thorough.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — WRITE task.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After you have explored enough to understand the task, write task.md.

Path: {context.working_dir}/.hcode/task.md

Format:
{task_template}

Rules:
  • Every subtask gets a unique `<!-- id: N -->` comment.
  • Use `- [ ]` for pending, `- [/]` for in-progress, `- [x]` for done.
  • Break complex work into 3-7 concrete subtasks.
  • The subtasks must reflect what you actually discovered during exploration —
    not generic boilerplate.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3 — WRITE implementation_plan.md  (IMMEDIATELY after task.md)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After task.md is confirmed written, write implementation_plan.md.

Path: {context.working_dir}/.hcode/implementation_plan.md

Format:
{plan_template}

Rules:
  • The Approach section must describe WHY you chose this approach
    (not just what you will do).
  • Every file that will be created or modified must appear with a
    [NEW] or [MODIFY] marker and an absolute path.
  • Steps must be in execution order — what depends on what.
  • The Verification Plan must contain the exact shell commands that
    will be run to test the implementation.
  • Base your plan on what you actually READ during exploration —
    not on assumptions.

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
BEGIN.  Start by exploring, then write task.md, then implementation_plan.md.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


    def _get_task_template_guide(self) -> str:
        """Get task.md template guide."""
        return """```markdown
# Task

[User's original request]

## Subtasks

- [ ] Task 1 <!-- id: 0 -->
- [ ] Task 2 <!-- id: 1 -->
  - [ ] Subtask 2.1 <!-- id: 2 -->
  - [ ] Subtask 2.2 <!-- id: 3 -->
- [ ] Task 3 <!-- id: 4 -->

## Notes

[Any notes or findings]
```"""

    def _get_plan_template_guide(self) -> str:
        """Get implementation_plan.md template guide."""
        return """```markdown
# [Goal Description]

Brief description of the problem and what the change accomplishes.

## User Review Required

> [!IMPORTANT]
> Critical items needing user approval

## Proposed Changes

### [Component Name]

Summary of changes to this component

#### [MODIFY] [filename.py](file:///absolute/path/to/file.py)

- What will change in this file

#### [NEW] [newfile.py](file:///absolute/path/to/newfile.py)

- What this new file will contain

## Verification Plan

### Automated Tests
- Exact command: `pytest tests/specific_test.py -v`

### Manual Verification
- Steps to verify manually
```"""

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
            "- Syntax check: `python -m py_compile <file>`\n"
            "- Run script to verify output"
        )

        return (
            f"# {goal_line}\n\n"
            f"{context.task}\n\n"
            f"## Approach\n\n"
            f"{approach}\n\n"
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

        # Fallback: inline templates matching templates.yaml structure
        return """### task.md Template

```markdown
# Task

[User's original request]

## Subtasks

- [ ] Subtask 1 <!-- id: 0 -->
- [ ] Subtask 2 <!-- id: 1 -->
  - [ ] Subtask 2.1 <!-- id: 2 -->
- [ ] Subtask 3 <!-- id: 3 -->

## Notes

[Any findings or notes]
```

### implementation_plan.md Template

```markdown
# [Goal Description]

Brief description of the problem and what the change accomplishes.

## Approach

[High-level approach and strategy]

## Steps

1. **Step 1**: [Description]
   - File: `path/to/file.py`
   - Action: [What to do]

2. **Step 2**: [Description]
   - File: `path/to/file.py`
   - Action: [What to do]

## Files to Modify

- `file1.py`: [What changes to make]

## Files to Create

- `new_file.py`: [What it should contain]

## Testing Strategy

- Run tests: `pytest tests/`
- Manual verification: [Steps]
```
"""
