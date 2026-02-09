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
    ) -> Dict[str, Any]:
        """
        Execute a user task through the PEV workflow.

        IMPORTANT: PEV workflow is ALWAYS enforced regardless of task complexity.
        Every task goes through:
        1. PLANNING: Create task.md and implementation_plan.md
        2. EXECUTION: Implement the plan using tools
        3. VERIFICATION: Test and create walkthrough.md

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

        # Reset phase manager to ensure we ALWAYS start with planning
        # PEV is enforced for ALL tasks regardless of complexity
        self.phase_manager.reset(initial_phase="planning")

        # Initialize context
        context = self.initialize_context(task, session_id)

        # Classify task (for metadata only - does NOT affect PEV enforcement)
        task_type = self.task_classifier.classify(task)
        complexity = self.task_classifier.get_complexity(task)

        # Log that PEV is being enforced
        logger.info(f"Executing task with PEV workflow (type={task_type}, complexity={complexity})")

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
                    self.console.print(f"[bold cyan]▸ Phase: {phase_name.capitalize()}[/bold cyan]")

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

    def resume_from_checkpoint(
        self,
        session_id: str,
        iteration: Optional[int] = None,
    ) -> Optional[AgentContext]:
        """
        Resume AgentContext from checkpoint.

        Args:
            session_id: Session ID to resume
            iteration: Specific iteration to load (None = latest)

        Returns:
            Restored AgentContext or None if checkpoint doesn't exist
        """
        if not self.checkpoint_manager:
            logger.warning("Checkpoints disabled, cannot resume")
            return None

        restored = self.checkpoint_manager.load_checkpoint(
            session_id=session_id,
            working_dir=self.working_dir,
            iteration=iteration,
        )

        if restored:
            logger.info(f"Resumed session {session_id} from iteration {restored.iteration}")

        return restored

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
