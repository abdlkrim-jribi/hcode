"""
Agent orchestrator for coordinating execution.

The orchestrator is the main coordinator that:
- Initializes context
- Manages the PEV workflow via PhaseManager
- Handles execution lifecycle
- Delegates to appropriate services
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from ..loop.agent_loop import AgentLoopController, Phase, StopReason
from ..protocols import (
    AgentOrchestratorProtocol,
    PhaseManagerProtocol,
    TaskClassifierProtocol,
    AgentContext,
    PhaseResult,
)
from ..services.checkpoint import get_checkpoint_manager

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
            enable_checkpoints: bool = True,
            fast_handler: Any = None,
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
            enable_checkpoints: Enable checkpoint serialization (default: True)
        """
        self.phase_manager = phase_manager
        self.task_classifier = task_classifier
        self.working_dir = working_dir or str(Path.cwd())
        self.max_iterations = max_iterations
        self.console = console
        self.debug_mode = debug_mode
        self.enable_checkpoints = enable_checkpoints
        self.fast_handler = fast_handler  # Used when use_planning=False

        # Initialize loop controller
        self.loop_controller = AgentLoopController(
            console=console,
            debug_mode=debug_mode,
            max_iterations=max_iterations,
        )

        # Initialize checkpoint manager if enabled
        self.checkpoint_manager = get_checkpoint_manager() if enable_checkpoints else None

    async def execute_task(
            self,
            task: str,
            session_id: str,
            stream_callback: Optional[Callable] = None,
            use_planning: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a user task through the EV or PEV workflow.

        When use_planning=True (full PEV):
          1. PLANNING: Create task.md and implementation_plan.md
          2. EXECUTION: Implement the plan using tools
          3. VERIFICATION: Test and create walkthrough.md

        When use_planning=False (EV only):
          1. EXECUTION: Implement directly using tools
          2. VERIFICATION: Test and create walkthrough.md

        Args:
            task: User's task description
            session_id: Session identifier
            stream_callback: Optional callback for streaming
            use_planning: Whether to run the planning phase (default: True)

        Returns:
            Dict with execution results
        """
        # Reset loop controller for new task
        self.loop_controller.reset()

        # Initialize context
        context = self.initialize_context(task, session_id)

        # Classify task for metadata
        task_type = self.task_classifier.classify(task)
        complexity = self.task_classifier.get_complexity(task)

        # Fast mode: single-handler flow (understand → todo.md → implement → summary)
        if not use_planning and self.fast_handler:
            logger.info(f"Executing task with Fast mode (type={task_type}, complexity={complexity})")
            if self.console:
                self.console.print("[bold cyan]> Fast Mode: Understand · Plan · Implement · Summarize[/bold cyan]")
            try:
                phase_result = await self.fast_handler.handle(context, self.loop_controller)
                return {
                    "success": phase_result.success,
                    "output": phase_result.output or "Task complete.",
                    "modified_files": context.modified_files,
                    "artifacts": context.artifacts,
                    "phase_results": [phase_result],
                    "task_type": task_type,
                    "complexity": complexity,
                    "final_phase": "fast",
                    "iterations": 1,
                    "stop_reason": "task_complete" if phase_result.success else "error",
                    "error": phase_result.error if not phase_result.success else None,
                }
            except Exception as e:
                logger.exception(f"Fast mode execution failed: {e}")
                return {
                    "success": False,
                    "output": f"Fast mode failed: {e}",
                    "modified_files": [],
                    "artifacts": {},
                    "phase_results": [],
                    "task_type": task_type,
                    "complexity": complexity,
                    "error": str(e),
                }

        # Full PEV mode (or EV without fast_handler)
        initial_phase = "planning" if use_planning else "execution"
        self.phase_manager.reset(initial_phase=initial_phase)

        workflow = "PEV" if use_planning else "EV"
        logger.info(f"Executing task with {workflow} workflow (type={task_type}, complexity={complexity})")

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
                    break

                # Sync loop state with context
                context.iteration = self.loop_controller.state.iteration

                # Execute current phase
                phase_name = self.phase_manager.get_current_phase()
                if self.console:
                    self.console.print(f"[bold cyan]> Phase: {phase_name.capitalize()}[/bold cyan]")

                phase_result = await self.execute_phase_iteration(context)
                logger.debug(f"Phase result: success={phase_result.success}, can_transition={phase_result.can_transition}")
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

                    # Preserve any existing output if it's more than just a status message
                    if phase_result.output and "phase complete" not in phase_result.output.lower():
                        results["output"] = phase_result.output

                    results["error"] = phase_result.error
                    continue

                # Stream callback if provided
                if stream_callback and phase_result.output:
                    await self._safe_callback(stream_callback, phase_result.output)

                # If the phase result has a meaningful output (e.g. from exploration), store it
                # We prioritize output that DOES NOT look like a generic status message
                # Or if metadata contains the full response, use that as the source of truth
                is_generic = any(s in phase_result.output.lower() for s in ["phase complete", "iteration complete", "task is done", "already exist"])

                phase_response = phase_result.metadata.get("response") if phase_result.metadata else None

                if phase_response:
                    results["output"] = phase_response
                elif phase_result.output and (not is_generic or not results["output"]):
                    results["output"] = phase_result.output

                # Attempt phase transition
                if phase_result.can_transition:
                    current_phase = self.phase_manager.get_current_phase()
                    transitioned = self.phase_manager.transition_to_next_phase(context)

                    if transitioned:
                        # Save checkpoint after successful phase completion
                        if self.checkpoint_manager:
                            try:
                                self.checkpoint_manager.save_checkpoint(context, phase_name=current_phase)
                                logger.debug(f"Saved checkpoint after {current_phase} phase")
                            except Exception as e:
                                logger.warning(f"Failed to save checkpoint: {e}")

                        # Update loop controller phase
                        new_phase = self.phase_manager.get_current_phase()
                        self._sync_loop_phase(new_phase)
                        logger.info(f"Transitioned from {current_phase} to {new_phase}")

                    elif current_phase == "verification":
                        # Check if verification found incomplete tasks (NEEDS REVISION)
                        verdict = (phase_result.metadata or {}).get("verdict", "")
                        needs_revision = "NEEDS REVISION" in verdict or "REJECTED" in verdict

                        if needs_revision and context.iteration < self.max_iterations - 5:
                            # Recovery: go back to execution for remaining tasks
                            logger.info(
                                f"Verification verdict: {verdict} — "
                                f"looping back to execution for remaining tasks"
                            )
                            if self.console:
                                self.console.print(
                                    "\n[bold yellow]⟳ Verification found incomplete tasks — "
                                    "returning to execution[/bold yellow]"
                                )
                            self.phase_manager.force_phase("execution")
                            self._sync_loop_phase("execution")
                            continue

                        # Verification complete means task is done
                        if self.console:
                            self.console.print("\n[bold green]✓ Task completed successfully![/bold green]")
                        else:
                            print("\n[Hcode] Task completed successfully!")

                        # Save final checkpoint
                        if self.checkpoint_manager:
                            try:
                                self.checkpoint_manager.save_checkpoint(context, phase_name="completed")
                                logger.debug("Saved final checkpoint after task completion")
                            except Exception as e:
                                logger.warning(f"Failed to save final checkpoint: {e}")

                        self.loop_controller.stop(StopReason.TASK_COMPLETE)
                        results["success"] = True
                        if not results["output"] or results["output"] == "Task completed successfully":
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
