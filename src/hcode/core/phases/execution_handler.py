"""
Execution phase handler.

Responsible for:
- Loading and executing the implementation plan
- Making file modifications
- Tracking progress against plan
- Updating task.md with completion status
"""

import re
import logging
from typing import List, Any, Dict, Optional
from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult
from hcode.config.core_prompts.core import CorePromptLoader

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
        2. Execute tools to implement plan
        3. Track modified files
        4. Update task.md with progress
        5. Determine if implementation is complete

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

            # Build execution prompt
            prompt = self._build_execution_prompt(context, plan_content)

            # Generate and execute (will call AI provider)
            # response = await self._generate_response(prompt, context)
            # tool_calls = self._extract_tool_calls(response)
            # results = await self._execute_tools(tool_calls, context)

            # For now, return placeholder result
            # TODO: Implement actual execution logic

            # Check if any files were modified
            has_modifications = len(context.modified_files) > 0

            # Check if can transition (implementation sufficient)
            can_transition = self._check_execution_complete(context)

            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output=f"Execution phase in progress. Modified {len(context.modified_files)} files.",
                can_transition=can_transition,
                metadata={
                    "modified_files": context.modified_files,
                    "completed_actions": len(context.completed_actions),
                }
            )

        except Exception as e:
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                output=f"Execution phase failed: {str(e)}",
                can_transition=False,
                error=str(e),
            )

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

        Args:
            context: Current agent context

        Returns:
            True if execution phase is done
        """
        # For now, simple heuristic:
        # - At least one file modified
        # - At least one action completed
        has_modifications = len(context.modified_files) > 0
        has_actions = len(context.completed_actions) > 0

        # TODO: Add more sophisticated completion detection
        # - Parse implementation_plan.md and check if steps are done
        # - Check for agent's explicit completion signal
        # - Verify critical files were modified

        return has_modifications or has_actions

    def _build_execution_prompt(self, context: AgentContext, plan_content: str) -> str:
        """
        Build prompt for execution phase.

        Args:
            context: Current agent context
            plan_content: Content of implementation_plan.md

        Returns:
            Execution prompt
        """
        loader = CorePromptLoader()
        return loader.build_execution_prompt(
            plan_content=plan_content,
            modified_files_count=len(context.modified_files),
            completed_actions_count=len(context.completed_actions),
            iteration=context.iteration,
        )

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
