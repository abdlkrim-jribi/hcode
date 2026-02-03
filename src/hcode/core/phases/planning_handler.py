"""
Planning phase handler.

Responsible for:
- Understanding the user's task
- Creating task.md with task breakdown
- Creating implementation_plan.md with concrete steps
- Determining when planning is complete
"""

from typing import List, Any
from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult
from hcode.config.core_prompts.core import CorePromptLoader


class PlanningPhaseHandler(BasePhaseHandler):
    """
    Handler for the Planning phase of PEV workflow.

    Creates:
    - .hcode/task.md: Task understanding and subtasks
    - .hcode/implementation_plan.md: Implementation steps with file paths

    Transition criteria:
    - Both artifacts exist and have valid content
    - Plan has concrete steps (not just placeholders)
    """

    phase_name = "planning"

    def get_required_artifacts(self) -> List[str]:
        """Get artifacts this phase should produce."""
        return ["task.md", "implementation_plan.md"]

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute planning phase.

        Steps:
        1. Generate task understanding (task.md)
        2. Generate implementation plan (implementation_plan.md)
        3. Validate artifacts
        4. Determine if ready to transition

        Args:
            context: Current agent context
            loop_controller: Loop controller

        Returns:
            PhaseResult with planning outcome
        """
        try:
            # Build planning prompt
            prompt = self._build_planning_prompt(context)

            # Generate response (will call AI provider)
            # response = await self._generate_response(prompt, context)

            # For now, create placeholder artifacts
            # TODO: This will be implemented to actually generate from AI
            artifacts_created = []

            # Check if artifacts already exist
            task_md_exists = self.artifact_manager.artifact_exists("task.md", context)
            plan_md_exists = self.artifact_manager.artifact_exists("implementation_plan.md", context)

            if not task_md_exists:
                # Create task.md
                task_content = self._create_task_md_template(context)
                self.artifact_manager.create_artifact("task.md", task_content, context)
                artifacts_created.append("task.md")

            if not plan_md_exists:
                # Create implementation_plan.md
                plan_content = self._create_plan_md_template(context)
                self.artifact_manager.create_artifact("implementation_plan.md", plan_content, context)
                artifacts_created.append("implementation_plan.md")

            # Validate artifacts
            valid, error = self.validate_artifacts(context)

            if not valid:
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output=f"Planning phase validation failed: {error}",
                    artifacts_created=artifacts_created,
                    can_transition=False,
                    error=error,
                )

            # Check if can transition
            can_transition = self.can_transition_to_next(context)

            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output="Planning phase complete",
                artifacts_created=artifacts_created,
                can_transition=can_transition,
            )

        except Exception as e:
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                output=f"Planning phase failed: {str(e)}",
                can_transition=False,
                error=str(e),
            )

    def _build_planning_prompt(self, context: AgentContext) -> str:
        """
        Build prompt for planning phase.

        Args:
            context: Current agent context

        Returns:
            Planning prompt
        """
        loader = CorePromptLoader()
        return loader.build_planning_prompt(task=context.task)

    def _create_task_md_template(self, context: AgentContext) -> str:
        """
        Create a template for task.md.

        Args:
            context: Current agent context

        Returns:
            Template content
        """
        loader = CorePromptLoader()
        return loader.build_task_md(task=context.task)

    def _create_plan_md_template(self, context: AgentContext) -> str:
        """
        Create a template for implementation_plan.md.

        Args:
            context: Current agent context

        Returns:
            Template content
        """
        loader = CorePromptLoader()
        return loader.build_implementation_plan_md()
