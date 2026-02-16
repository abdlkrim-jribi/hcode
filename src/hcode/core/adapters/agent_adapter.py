"""
Adapter for bridging new SOLID components with existing HcodeAgent.

This allows gradual migration without breaking existing code.
"""

import os
from typing import Any, Optional, Dict

from ..classification import TaskClassifier
from ..orchestration import PhaseManager, AgentOrchestrator
from ..phases import (
    PlanningPhaseHandler,
    ExecutionPhaseHandler,
    VerificationPhaseHandler,
)
from ..services import ArtifactManager


class AgentAdapter:
    """
    Adapter that connects new SOLID components to HcodeAgent.

    The HcodeAgent can delegate to this adapter, which handles
    the new PEV workflow orchestration.
    """

    def __init__(
            self,
            provider: Any,
            tool_executor: Any,
            context_manager: Any,
            working_dir: Optional[str] = None,
            console: Optional[Any] = None,
    ):
        """Initialize adapter with existing components."""
        self.provider = provider
        self.tool_executor = tool_executor
        self.context_manager = context_manager
        self.working_dir = working_dir or os.getcwd()
        self.console = console

        # Create new components
        self.task_classifier = TaskClassifier()
        self.artifact_manager = ArtifactManager()

        # Create phase handlers with console for modern UI
        handler_deps = {
            "artifact_manager": self.artifact_manager,
            "provider": provider,
            "tool_executor": tool_executor,
            "context_manager": context_manager,
            "console": console,  # Pass console for HcodeDisplay integration
        }

        self.handlers = {
            "planning": PlanningPhaseHandler(**handler_deps),
            "execution": ExecutionPhaseHandler(**handler_deps),
            "verification": VerificationPhaseHandler(**handler_deps),
        }

        # Create phase manager
        self.phase_manager = PhaseManager(self.handlers)

        # Create orchestrator
        self.orchestrator = AgentOrchestrator(
            phase_manager=self.phase_manager,
            task_classifier=self.task_classifier,
            working_dir=self.working_dir,
            console=self.console,
        )

    async def execute_task(
            self,
            task: str,
            session_id: str,
            stream_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute task through new PEV workflow.

        This is the main entry point that HcodeAgent can call.
        """
        return await self.orchestrator.execute_task(
            task, session_id, stream_callback
        )

    def should_use_pev_workflow(self, task: str) -> bool:
        """
        Determine if task should use PEV workflow.

        ALWAYS returns True because PEV workflow is mandatory for all tasks.
        This ensures consistent quality through:
        - Planning: Create task.md and implementation_plan.md
        - Execution: Implement the plan using tools
        - Verification: Test and create walkthrough.md

        Args:
            task: User's task description (used for classification metadata only)

        Returns:
            Always True - PEV is enforced for all tasks
        """
        # PEV is ALWAYS required - no exceptions
        # Task classification is for metadata/optimization only, not workflow control
        return True

    def get_task_classification(self, task: str) -> Dict[str, Any]:
        """
        Get detailed task classification.

        Returns:
            Dict with task_type, complexity, confidence
        """
        task_type = self.task_classifier.classify(task)
        complexity = self.task_classifier.get_complexity(task)
        confidence = self.task_classifier.get_confidence()

        return {
            "task_type": task_type,
            "complexity": complexity,
            "confidence": confidence,
            "use_pev": self.should_use_pev_workflow(task),
        }
