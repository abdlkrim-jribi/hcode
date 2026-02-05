"""
Execution phase handler.

Responsible for:
- Loading and executing the implementation plan
- Making file modifications based on the plan
- Tracking progress against plan
- Updating task.md with completion status
- Maintaining the checkbox format with unique IDs
"""

import re
import logging
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

    Executes:
    - Reads implementation_plan.md
    - Makes file modifications according to plan
    - Tracks modified files
    - Updates task.md with progress

    Transition criteria:
    - All planned steps completed OR agent declares implementation sufficient
    - At least one file modified (for implementation tasks)
    - No critical errors
    """

    phase_name = "execution"

    def get_required_artifacts(self) -> List[str]:
        """
        Get artifacts this phase requires (not produces).

        Execution phase doesn't produce new artifacts, but requires
        the planning artifacts to exist.
        """
        return []  # No new artifacts, but validates plan exists

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute implementation phase.

        Steps:
        1. Load implementation_plan.md
        2. Find next incomplete step
        3. Generate AI response for execution
        4. Execute tool calls from response
        5. Track modified files
        6. Update task.md with progress
        7. Determine if implementation is complete

        Args:
            context: Current agent context
            loop_controller: Loop controller

        Returns:
            PhaseResult with execution outcome
        """
        try:
            # Load implementation plan
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

            # Find next incomplete step
            next_step = self._get_next_incomplete_step(plan_content, context)
            step_info = ""
            if next_step:
                step_info = f"Working on: {next_step.get('name', 'Step ' + str(next_step.get('number', '?')))}"
                logger.info(step_info)

            # Build execution prompt
            prompt = self._build_execution_prompt(context, plan_content)

            # Add step-specific context to prompt
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
                    prompt, context, system_prompt=self._get_execution_system_prompt(context)
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

    def _get_execution_system_prompt(self, context: AgentContext) -> str:
        """
        Get system prompt for execution phase.

        Uses core prompts from phases.yaml.

        Args:
            context: Current agent context

        Returns:
            Complete system prompt for execution
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            # Get identity and tool format
            identity = loader.get_identity()
            tool_format = loader.get_tool_format()

            # Load implementation plan for context
            plan_content = self.artifact_manager.load_artifact(
                "implementation_plan.md", context
            ) or "(No plan loaded)"

            # Get execution instruction from core prompts
            execution_prompt = loader.build_execution_prompt(
                plan_content=plan_content,
                modified_files_count=len(context.modified_files),
                completed_actions_count=len(context.completed_actions),
                iteration=context.iteration,
            )

            # Build system prompt with identity and tool format
            system_base = f"""{identity}

{tool_format}

---

{execution_prompt}"""

            # Add critical instructions
            critical_instructions = f"""
## HCODE EXECUTION MODE

Working directory: {context.working_dir}
Artifacts directory: .hcode

### CRITICAL: Communication Rules

**YOU MUST**:
1. Explain what you're doing in plain text
2. Use JSON tool calls in code blocks for file operations
3. Describe changes before and after making them
4. Report results after tool execution

### TOOL CALL FORMAT (CRITICAL!)

When you need to use a tool, output JSON in this EXACT format inside a code block:

```json
{{"tool": "ToolName", "arguments": {{"param": "value"}}}}
```

**Available tools:**
- LS: `{{"tool": "LS", "arguments": {{"DirectoryPath": "."}}}}`
- Read: `{{"tool": "Read", "arguments": {{"AbsolutePath": "/full/path"}}}}`
- Write: `{{"tool": "Write", "arguments": {{"TargetFile": "/full/path", "CodeContent": "content"}}}}`
- Edit: `{{"tool": "Edit", "arguments": {{"TargetFile": "/path", "TargetContent": "old text", "ReplacementContent": "new text"}}}}`
- SmartGlob: `{{"tool": "SmartGlob", "arguments": {{"Pattern": "**/*.py"}}}}`
- Grep: `{{"tool": "Grep", "arguments": {{"Query": "pattern", "SearchPath": "."}}}}`
- Bash: `{{"tool": "Bash", "arguments": {{"CommandLine": "command", "description": "what it does"}}}}`

### Example Good Response:

I'll now create the markdown counting script.

First, let me check the current directory:

```json
{{"tool": "LS", "arguments": {{"DirectoryPath": "."}}}}
```

Good. Now I'll create the script:

```json
{{"tool": "Write", "arguments": {{"TargetFile": "{context.working_dir}/count_md.py", "CodeContent": "#!/usr/bin/env python3\\nimport glob\\n\\ndef main():\\n    files = glob.glob('**/*.md', recursive=True)\\n    lines = sum(len(open(f).readlines()) for f in files)\\n    print(f'Found {{len(files)}} .md files with {{lines}} total lines')\\n\\nif __name__ == '__main__':\\n    main()"}}}}
```

Script created! Now updating task.md:

```json
{{"tool": "Edit", "arguments": {{"TargetFile": ".hcode/task.md", "TargetContent": "- [ ] Create script <!-- id: 0 -->", "ReplacementContent": "- [x] Create script <!-- id: 0 -->"}}}}
```

Done! Created count_md.py with file discovery and line counting.
"""
            return system_base + "\n" + critical_instructions

        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            return self._get_fallback_execution_prompt(context)

    def _get_fallback_execution_prompt(self, context: AgentContext) -> str:
        """Fallback execution prompt when Fast Prompt not available."""
        return f"""## EXECUTION MODE

You are Hcode in EXECUTION mode. Your goal is to implement the changes outlined in the implementation plan.

Working directory: {context.working_dir}
Artifacts directory: .hcode

### Execution Rules:
1. Follow the implementation_plan.md exactly
2. Use the Write/Edit tools to make file changes
3. Update task.md to mark tasks as complete ([x]) as you finish them
4. Keep the same task IDs - don't renumber them
5. If you encounter issues, update the plan and notify the user

### Task.md Update Format:
When completing a task, change:
- [ ] Task description <!-- id: N -->
To:
- [x] Task description <!-- id: N -->

For in-progress tasks:
- [/] Task description <!-- id: N -->

### Anti-Hallucination:
- NEVER show code blocks without using Write/Edit tool
- ALWAYS use tools to make actual changes
- Read files before editing to ensure correct content
"""

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """
        Check if ready to transition to verification phase.

        Criteria:
        - At least one file modified (for implementation tasks) OR
        - Agent declares implementation complete

        Args:
            context: Current agent context

        Returns:
            True if execution is complete
        """
        return self._check_execution_complete(context)

    def _check_execution_complete(self, context: AgentContext) -> bool:
        """
        Check if execution is complete.

        Execution is complete when:
        - At least one NON-ARTIFACT file has been modified (actual code, not .hcode files)
        - OR the implementation plan has been fully executed

        Args:
            context: Current agent context

        Returns:
            True if execution phase is done
        """
        # Filter out artifact files (.hcode directory) from modified files
        # Execution should create actual code files, not just update artifacts
        non_artifact_files = [
            f for f in context.modified_files
            if ".hcode" not in f and not f.endswith("task.md")
            and not f.endswith("implementation_plan.md")
            and not f.endswith("walkthrough.md")
        ]

        # Also check for actions that created/modified non-artifact files
        non_artifact_actions = []
        for a in context.completed_actions:
            if a.get("tool", "").lower() in ["write", "edit", "writetool", "edittool"]:
                # Get file path from various argument names
                args = a.get("arguments", {})
                target_file = args.get("TargetFile", "") or args.get("file_path", "") or a.get("file_path", "")
                if target_file and ".hcode" not in str(target_file):
                    non_artifact_actions.append(a)

        has_code_modifications = len(non_artifact_files) > 0
        has_code_actions = len(non_artifact_actions) > 0

        # Execution is complete only if actual code was created/modified
        return has_code_modifications or has_code_actions

    def _build_execution_prompt(self, context: AgentContext, plan_content: str) -> str:
        """
        Build prompt for execution phase.

        Args:
            context: Current agent context
            plan_content: Content of implementation_plan.md

        Returns:
            Execution prompt
        """
        # Build list of modified files for context
        modified_files_list = "\n".join(f"  - {f}" for f in context.modified_files) if context.modified_files else "  (none yet)"

        # Build recent actions summary
        recent_actions = context.completed_actions[-5:] if context.completed_actions else []
        actions_summary = "\n".join(
            f"  - {a.get('tool', 'unknown')}: {'[OK]' if a.get('success') else '[FAIL]'}"
            for a in recent_actions
        ) if recent_actions else "  (none yet)"

        return f"""## EXECUTION PHASE

You are executing the implementation plan. Continue with the next step.

### CRITICAL THINKING PROTOCOL

Before EVERY action, you MUST think through:

<thinking>
=== PRE-EXECUTION ANALYSIS ===
What is the next step in the plan?
Have I read all files I'm about to modify?
Do I understand the existing code structure?
What exact changes will I make?

=== ANTI-HALLUCINATION CHECK ===
□ Am I about to write code I haven't verified exists? -> READ FIRST
□ Am I assuming imports/dependencies exist? -> CHECK FIRST
□ Am I guessing function signatures? -> READ THE FILE FIRST
□ Am I making changes based on memory alone? -> RE-READ TO VERIFY

=== CHANGE SPECIFICATION ===
File to modify: [exact path]
Location in file: [function/class/line]
Change type: [add/modify/delete]
Exact change: [what will be different]
Why this change: [rationale]

=== VERIFICATION PLAN ===
How will I verify this change worked?
What should I check after making the change?
</thinking>

### Implementation Plan:
{plan_content}

### Current Session State:
- Iteration: {context.iteration}
- Modified files ({len(context.modified_files)}):
{modified_files_list}
- Recent actions:
{actions_summary}

### EXECUTION RULES:

**Rule 1: READ BEFORE WRITE**
- NEVER edit a file you haven't read in this session
- ALWAYS verify the current content before making changes
- If you're unsure about current content, READ IT FIRST

**Rule 2: ONE CHANGE AT A TIME**
- Make one logical change per tool call
- Verify each change before moving to the next
- If a change fails, understand why before retrying

**Rule 3: TRACK PROGRESS**
- Update task.md to mark completed subtasks with [x]
- Keep the same task IDs - don't renumber them
- Use [/] for tasks in progress

**Rule 4: NO CODE IN RESPONSE TEXT**
- NEVER show code blocks in your response without using Write/Edit tool
- If you want to show code, use the appropriate tool to write it
- All code must be in tool arguments, not in response text

### Task.md Update Format:
When completing a task, change:
- [ ] Task description <!-- id: N -->
To:
- [x] Task description <!-- id: N -->

For in-progress tasks:
- [/] Task description <!-- id: N -->

### EXECUTION WORKFLOW:

1. **THINK** - What is the next incomplete step?
2. **READ** - Read any files you need to understand
3. **PLAN** - Specify the exact change you'll make
4. **EXECUTE** - Use Write/Edit tool to make the change
5. **VERIFY** - Confirm the change was applied correctly
6. **UPDATE** - Mark the task as complete in task.md
7. **REPEAT** - Move to the next step

NOW EXECUTE THE NEXT STEP. Remember: THINK -> READ -> PLAN -> EXECUTE -> VERIFY."""

    def _parse_plan_steps(self, plan_content: str) -> List[Dict[str, Any]]:
        """
        Parse steps from implementation plan.

        Extracts numbered steps, file paths, and actions from the plan markdown.

        Args:
            plan_content: Content of implementation_plan.md

        Returns:
            List of step dicts with file, action, description, completed status
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

            # Extract file paths: - File: `path/to/file.py` or backtick paths
            file_pattern = r'(?:File|file|Path|path):\s*`([^`]+)`'
            file_matches = re.findall(file_pattern, step_content)
            step["files"] = file_matches

            # Also capture backtick paths that look like files
            backtick_pattern = r'`([^`]+\.[a-z]+)`'
            backtick_matches = re.findall(backtick_pattern, step_content)
            for path in backtick_matches:
                if path not in step["files"] and '/' in path or '\\' in path:
                    step["files"].append(path)

            # Extract actions: - Action: [description]
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

        Args:
            context: Current agent context
        """
        # Load current task.md
        task_content = self.artifact_manager.load_artifact("task.md", context)

        if not task_content:
            logger.warning("task.md not found, cannot update progress")
            return

        # Parse implementation plan to get expected steps
        plan_content = self.artifact_manager.load_artifact("implementation_plan.md", context)
        plan_steps = self._parse_plan_steps(plan_content) if plan_content else []

        # Determine completed steps based on modified files
        completed_files = set(context.modified_files)

        # Update checkbox items in task.md
        updated_content = task_content
        lines = updated_content.split('\n')
        updated_lines = []

        for line in lines:
            # Check for checkbox pattern: - [ ] or - [x]
            checkbox_match = re.match(r'^(\s*-\s*)\[[ ]\]\s*(.+)$', line)

            if checkbox_match:
                prefix = checkbox_match.group(1)
                task_text = checkbox_match.group(2)

                # Check if this task mentions any completed files
                should_complete = False

                for file_path in completed_files:
                    # Extract just the filename
                    file_name = file_path.split('/')[-1].split('\\')[-1]
                    if file_name in task_text or file_path in task_text:
                        should_complete = True
                        break

                # Check if actions match
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

        # Add progress summary at the end
        if updated_content != task_content:
            progress_section = f"""

## Progress Update

- Modified files: {len(context.modified_files)}
- Completed actions: {len(context.completed_actions)}
- Iteration: {context.iteration}
"""
            # Only add progress section if not already there
            if "## Progress Update" not in updated_content:
                updated_content += progress_section

            # Save updated task.md
            self.artifact_manager.create_artifact("task.md", updated_content, context)
            logger.debug("Updated task.md with progress")

    def _check_step_completion(
        self,
        step: Dict[str, Any],
        context: AgentContext
    ) -> bool:
        """
        Check if a specific step is completed.

        Args:
            step: Step dict from _parse_plan_steps
            context: Current agent context

        Returns:
            True if step appears to be completed
        """
        # Check if any of the step's files were modified
        for file_path in step.get("files", []):
            # Normalize path for comparison
            normalized = file_path.replace('\\', '/').strip('`')
            for modified in context.modified_files:
                if normalized in modified or modified.endswith(normalized):
                    return True

        # Check if step was explicitly marked complete
        if step.get("completed", False):
            return True

        return False

    def _get_next_incomplete_step(
        self,
        plan_content: str,
        context: AgentContext
    ) -> Optional[Dict[str, Any]]:
        """
        Get the next step that hasn't been completed.

        Args:
            plan_content: Content of implementation_plan.md
            context: Current agent context

        Returns:
            Next incomplete step or None if all complete
        """
        steps = self._parse_plan_steps(plan_content)

        for step in steps:
            if not self._check_step_completion(step, context):
                return step

        return None
