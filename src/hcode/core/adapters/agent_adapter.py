"""
Adapter for bridging new SOLID components with existing HcodeAgent.

This allows gradual migration without breaking existing code.
"""

import os
from typing import Any, Optional, Dict

from ..classification import TaskClassifier
from ..orchestration import PhaseManager, AgentOrchestrator
from ..phases import (
    FastModeHandler,
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

        # Fast mode handler — used when use_planning=False (bypasses PhaseManager)
        self.fast_handler = FastModeHandler(**handler_deps)

        # Create phase manager (PEV workflow)
        self.phase_manager = PhaseManager(self.handlers)

        # Create orchestrator
        self.orchestrator = AgentOrchestrator(
            phase_manager=self.phase_manager,
            task_classifier=self.task_classifier,
            working_dir=self.working_dir,
            console=self.console,
            fast_handler=self.fast_handler,
        )

    async def execute_task(
            self,
            task: str,
            session_id: str,
            stream_callback: Optional[Any] = None,
            use_planning: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute task through the EV or PEV workflow.

        Args:
            use_planning: If True, start from planning phase (full PEV).
                          If False, skip planning and start from execution (EV).
        """
        return await self.orchestrator.execute_task(
            task, session_id, stream_callback, use_planning=use_planning
        )

    def should_use_pev_workflow(self, task: str) -> bool:
        """
        Determine if task should use the planning phase.

        Returns True when the task is complex enough to need upfront planning
        (i.e., classified as "complex" by the task classifier).

        Args:
            task: User's task description

        Returns:
            True if planning phase is needed
        """
        return self.task_classifier.requires_pev_workflow(task)

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
