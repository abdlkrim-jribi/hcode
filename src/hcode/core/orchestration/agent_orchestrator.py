"""
Agent orchestrator for coordinating execution.

The orchestrator is the main coordinator that:
- Initializes context
- Manages the PEV workflow via PhaseManager
- Handles execution lifecycle
- Delegates to appropriate services
"""

import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from ..protocols import (
    AgentOrchestratorProtocol,
    PhaseManagerProtocol,
    TaskClassifierProtocol,
    AgentContext,
    PhaseResult,
)
from ..loop.agent_loop import AgentLoopController, Phase, StopReason

logger = logging.getLogger(__name__)


class AgentOrchestrator(AgentOrchestratorProtocol):
    """
    Orchestrates agent execution through PEV workflow.

    This is the main coordinator that replaces much of the complex
    logic in the old HcodeAgent class.

    Responsibilities:
    - Initialize execution context
    - Coordinate with PhaseManager for workflow
    - Track overall execution state
    - Handle errors and retries
    """

    def __init__(
        self,
        phase_manager: PhaseManagerProtocol,
        task_classifier: TaskClassifierProtocol,
        working_dir: Optional[str] = None,
        max_iterations: int = 50,
        console: Any = None,
        debug_mode: bool = False,
    ):
        """
        Initialize orchestrator.

        Args:
            phase_manager: Manager for PEV phases
            task_classifier: Classifier for task types
            working_dir: Working directory (default: current dir)
            max_iterations: Maximum iterations per phase
            console: Rich console for output
            debug_mode: Enable debug output
        """
        self.phase_manager = phase_manager
        self.task_classifier = task_classifier
        self.working_dir = working_dir or str(Path.cwd())
        self.max_iterations = max_iterations
        self.console = console
        self.debug_mode = debug_mode

        # Initialize loop controller
        self.loop_controller = AgentLoopController(
            console=console,
            debug_mode=debug_mode,
            max_iterations=max_iterations,
        )

    async def execute_task(
        self,
        task: str,
        session_id: str,
        stream_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Execute a user task through the PEV workflow.

        Uses AgentLoopController for state management and phase transitions.

        Args:
            task: User's task description
            session_id: Session identifier
            stream_callback: Optional callback for streaming

        Returns:
            Dict with execution results
        """
        # Reset loop controller for new task
        self.loop_controller.reset()

        # Initialize context
        context = self.initialize_context(task, session_id)

        # Classify task
        task_type = self.task_classifier.classify(task)
        complexity = self.task_classifier.get_complexity(task)

        context.metadata["task_type"] = task_type
        context.metadata["complexity"] = complexity

        # Execute workflow
        results = {
            "success": False,
            "output": "",
            "modified_files": [],
            "artifacts": {},
            "phase_results": [],
            "task_type": task_type,
            "complexity": complexity,
        }

        try:
            # Main execution loop
            while self.loop_controller.should_continue():
                # Tick iteration
                if not self.loop_controller.tick():
                    # Loop stopped due to limits or stuck detection
                    break

                # Sync loop state with context
                context.iteration = self.loop_controller.state.iteration

                # Execute current phase
                phase_result = await self.execute_phase_iteration(context)
                results["phase_results"].append(phase_result)

                # Record response in loop controller
                if phase_result.output:
                    self.loop_controller.record_response(phase_result.output)

                # Handle phase result
                if not phase_result.success:
                    # Record error
                    if not self.loop_controller.record_error():
                        # Circuit breaker triggered
                        results["output"] = "Too many consecutive errors"
                        results["error"] = phase_result.error
                        break

                    results["output"] = phase_result.output
                    results["error"] = phase_result.error
                    continue

                # Stream callback if provided
                if stream_callback and phase_result.output:
                    await self._safe_callback(stream_callback, phase_result.output)

                # Attempt phase transition
                if phase_result.can_transition:
                    current_phase = self.phase_manager.get_current_phase()
                    transitioned = self.phase_manager.transition_to_next_phase(context)

                    if transitioned:
                        # Update loop controller phase
                        new_phase = self.phase_manager.get_current_phase()
                        self._sync_loop_phase(new_phase)
                        logger.info(f"Transitioned from {current_phase} to {new_phase}")
                    elif current_phase == "verification":
                        # Verification complete means task is done
                        self.loop_controller.stop(StopReason.TASK_COMPLETE)
                        results["success"] = True
                        results["output"] = "Task completed successfully"
                        break

                # Sync modified files from context to loop controller
                for file_path in context.modified_files:
                    self.loop_controller.state.modified_files.add(file_path)

            # Collect final results
            loop_summary = self.loop_controller.get_summary()
            results["modified_files"] = context.modified_files
            results["artifacts"] = context.artifacts
            results["final_phase"] = self.phase_manager.get_current_phase()
            results["iterations"] = loop_summary["iterations"]
            results["stop_reason"] = loop_summary["stop_reason"]

            # If we exited cleanly, mark success
            if self.phase_manager.can_complete(context):
                results["success"] = True
                if not results["output"]:
                    results["output"] = "Task completed successfully"

        except Exception as e:
            logger.exception(f"Execution failed: {e}")
            results["success"] = False
            results["output"] = f"Execution failed: {str(e)}"
            results["error"] = str(e)

        return results

    def _sync_loop_phase(self, phase_name: str) -> None:
        """
        Sync loop controller phase with phase manager.

        Args:
            phase_name: Name of current phase
        """
        phase_map = {
            "planning": Phase.PLANNING,
            "execution": Phase.EXECUTION,
            "verification": Phase.VERIFICATION,
        }
        if phase_name in phase_map:
            self.loop_controller.transition(phase_map[phase_name])

    async def _safe_callback(self, callback: Callable, data: Any) -> None:
        """
        Safely execute callback, handling both sync and async callbacks.

        Args:
            callback: Callback function
            data: Data to pass to callback
        """
        try:
            import asyncio
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logger.warning(f"Stream callback failed: {e}")

    def initialize_context(self, task: str, session_id: str) -> AgentContext:
        """
        Initialize agent context for new task.

        Args:
            task: User's task
            session_id: Session identifier

        Returns:
            Initialized AgentContext
        """
        return AgentContext(
            task=task,
            session_id=session_id,
            working_dir=self.working_dir,
            iteration=0,
            modified_files=[],
            completed_actions=[],
            artifacts={},
            metadata={
                "started_at": self._get_timestamp(),
            }
        )

    async def execute_phase_iteration(
        self,
        context: AgentContext,
    ) -> PhaseResult:
        """
        Execute one iteration of current phase.

        Args:
            context: Current agent context

        Returns:
            PhaseResult from phase execution
        """
        result = await self.phase_manager.execute_current_phase(
            context, self.loop_controller
        )

        # Record actions in loop controller
        if result.metadata:
            for action in result.metadata.get("actions", []):
                self.loop_controller.record_action(
                    tool=action.get("tool", "unknown"),
                    args=action.get("arguments", {}),
                    success=action.get("success", False),
                )

        return result

    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_execution_summary(self, context: AgentContext) -> Dict[str, Any]:
        """
        Get summary of execution progress.

        Args:
            context: Current agent context

        Returns:
            Summary dict
        """
        phase_progress = self.phase_manager.get_phase_progress()

        return {
            "iteration": context.iteration,
            "phase": self.phase_manager.get_current_phase(),
            "phase_progress": phase_progress,
            "modified_files_count": len(context.modified_files),
            "completed_actions_count": len(context.completed_actions),
            "artifacts_created": list(context.artifacts.keys()),
        }

    def should_continue_execution(self, context: AgentContext) -> bool:
        """
        Determine if execution should continue.

        Args:
            context: Current agent context

        Returns:
            True if should continue iterating
        """
        # Stop if reached max iterations
        if context.iteration >= self.max_iterations:
            return False

        # Stop if workflow is complete
        if self.phase_manager.can_complete(context):
            return False

        return True
