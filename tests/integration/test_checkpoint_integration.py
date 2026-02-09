"""
Integration tests for checkpoint serialization during PEV workflow.

Task #14: Add checkpoint serialization for AgentContext resume-on-failure

These tests validate that:
- Checkpoints are saved after each phase transition
- Failed tasks can be resumed from last checkpoint
- Checkpoint contains all necessary context to resume
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from hcode.core.orchestration.agent_orchestrator import AgentOrchestrator
from hcode.core.orchestration.phase_manager import PhaseManager
from hcode.core.classification.task_classifier import TaskClassifier
from hcode.core.services.checkpoint import get_checkpoint_manager


class TestCheckpointIntegration:
    """Integration tests for checkpoint functionality in PEV workflow."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .hcode directory
            hcode_dir = Path(tmpdir) / ".hcode"
            hcode_dir.mkdir(parents=True, exist_ok=True)
            yield tmpdir

    @pytest.fixture
    def mock_phase_handlers(self):
        """Create mock phase handlers."""
        planning_handler = AsyncMock()
        execution_handler = AsyncMock()
        verification_handler = AsyncMock()

        # Mock phase names
        planning_handler.phase_name = "planning"
        execution_handler.phase_name = "execution"
        verification_handler.phase_name = "verification"

        # Mock artifact requirements
        planning_handler.get_required_artifacts.return_value = ["task.md", "implementation_plan.md"]
        execution_handler.get_required_artifacts.return_value = []
        verification_handler.get_required_artifacts.return_value = ["walkthrough.md"]

        # Mock validation
        planning_handler.validate_artifacts.return_value = (True, None)
        execution_handler.validate_artifacts.return_value = (True, None)
        verification_handler.validate_artifacts.return_value = (True, None)

        # Mock transition checks
        planning_handler.can_transition_to_next.return_value = True
        execution_handler.can_transition_to_next.return_value = True
        verification_handler.can_transition_to_next.return_value = True

        return planning_handler, execution_handler, verification_handler

    @pytest.mark.asyncio
    async def test_checkpoint_saved_after_planning_phase(
        self, temp_workspace, mock_phase_handlers
    ):
        """Verify checkpoint is saved after planning phase completes."""
        planning_handler, execution_handler, verification_handler = mock_phase_handlers

        # Mock planning phase result
        from hcode.core.protocols import PhaseResult

        planning_result = PhaseResult(
            phase_name="planning",
            success=True,
            output="Planning complete",
            artifacts_created=["task.md", "implementation_plan.md"],
            can_transition=True,
        )

        planning_handler.handle.return_value = planning_result

        # Create phase manager
        phase_manager = PhaseManager(
            handlers={
                "planning": planning_handler,
                "execution": execution_handler,
                "verification": verification_handler,
            },
        )

        # Create orchestrator with checkpoints enabled
        task_classifier = TaskClassifier()
        orchestrator = AgentOrchestrator(
            phase_manager=phase_manager,
            task_classifier=task_classifier,
            working_dir=temp_workspace,
            max_iterations=5,
            enable_checkpoints=True,
        )

        # Execute just planning phase
        # Set execution handler to stop after one iteration
        execution_handler.handle.return_value = PhaseResult(
            phase_name="execution",
            success=True,
            output="Execution complete",
            can_transition=False,  # Don't transition yet
        )

        # Run task (will only complete planning and start execution)
        result = await orchestrator.execute_task(
            task="Test task",
            session_id="test_checkpoint_001",
        )

        # Verify checkpoint was created
        checkpoint_manager = get_checkpoint_manager()
        checkpoints = checkpoint_manager.list_checkpoints(
            session_id="test_checkpoint_001",
            working_dir=temp_workspace,
        )

        # Should have at least one checkpoint from planning phase
        assert len(checkpoints) >= 1

        # Verify checkpoint contains planning phase
        checkpoint_phases = [c["phase"] for c in checkpoints]
        assert "planning" in checkpoint_phases

    @pytest.mark.asyncio
    async def test_checkpoint_contains_full_context(
        self, temp_workspace, mock_phase_handlers
    ):
        """Verify checkpoint contains all AgentContext fields."""
        planning_handler, execution_handler, verification_handler = mock_phase_handlers

        from hcode.core.protocols import PhaseResult

        # Mock planning result with modified files
        planning_result = PhaseResult(
            phase_name="planning",
            success=True,
            output="Created task.md",
            artifacts_created=["task.md", "implementation_plan.md"],
            can_transition=True,
        )

        planning_handler.handle.return_value = planning_result

        # Mock execution to stop quickly
        execution_handler.handle.return_value = PhaseResult(
            phase_name="execution",
            success=True,
            output="Done",
            can_transition=False,
        )

        # Create phase manager
        phase_manager = PhaseManager(
            handlers={
                "planning": planning_handler,
                "execution": execution_handler,
                "verification": verification_handler,
            },
        )

        # Create orchestrator
        task_classifier = TaskClassifier()
        orchestrator = AgentOrchestrator(
            phase_manager=phase_manager,
            task_classifier=task_classifier,
            working_dir=temp_workspace,
            enable_checkpoints=True,
        )

        # Execute
        await orchestrator.execute_task(
            task="Implement feature X",
            session_id="test_checkpoint_002",
        )

        # Load checkpoint
        checkpoint_manager = get_checkpoint_manager()
        restored = checkpoint_manager.load_checkpoint(
            session_id="test_checkpoint_002",
            working_dir=temp_workspace,
        )

        # Verify all fields present
        assert restored is not None
        assert restored.task == "Implement feature X"
        assert restored.session_id == "test_checkpoint_002"
        assert restored.working_dir == temp_workspace
        assert isinstance(restored.iteration, int)
        assert isinstance(restored.modified_files, list)
        assert isinstance(restored.completed_actions, list)
        assert isinstance(restored.artifacts, dict)
        assert isinstance(restored.metadata, dict)
        assert isinstance(restored.tokens_used, dict)
        assert restored.token_budget == 500000

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint_restores_state(
        self, temp_workspace, mock_phase_handlers
    ):
        """Verify resume_from_checkpoint restores AgentContext."""
        planning_handler, execution_handler, verification_handler = mock_phase_handlers

        from hcode.core.protocols import PhaseResult

        planning_result = PhaseResult(
            phase_name="planning",
            success=True,
            output="Planning done",
            artifacts_created=["task.md"],
            can_transition=True,
        )

        planning_handler.handle.return_value = planning_result

        execution_handler.handle.return_value = PhaseResult(
            phase_name="execution",
            success=True,
            output="Done",
            can_transition=False,
        )

        # Create orchestrator
        phase_manager = PhaseManager(
            handlers={
                "planning": planning_handler,
                "execution": execution_handler,
                "verification": verification_handler,
            },
        )

        task_classifier = TaskClassifier()
        orchestrator = AgentOrchestrator(
            phase_manager=phase_manager,
            task_classifier=task_classifier,
            working_dir=temp_workspace,
            enable_checkpoints=True,
        )

        # Execute task (will save checkpoint)
        await orchestrator.execute_task(
            task="Original task",
            session_id="test_resume_001",
        )

        # Resume from checkpoint
        restored_context = orchestrator.resume_from_checkpoint(
            session_id="test_resume_001"
        )

        # Verify restoration
        assert restored_context is not None
        assert restored_context.task == "Original task"
        assert restored_context.session_id == "test_resume_001"
        assert restored_context.working_dir == temp_workspace

    @pytest.mark.asyncio
    async def test_checkpoints_disabled_when_flag_false(
        self, temp_workspace, mock_phase_handlers
    ):
        """Verify checkpoints are not saved when enable_checkpoints=False."""
        planning_handler, execution_handler, verification_handler = mock_phase_handlers

        from hcode.core.protocols import PhaseResult

        planning_result = PhaseResult(
            phase_name="planning",
            success=True,
            output="Done",
            can_transition=True,
        )

        planning_handler.handle.return_value = planning_result

        execution_handler.handle.return_value = PhaseResult(
            phase_name="execution",
            success=True,
            output="Done",
            can_transition=False,
        )

        # Create orchestrator with checkpoints DISABLED
        phase_manager = PhaseManager(
            handlers={
                "planning": planning_handler,
                "execution": execution_handler,
                "verification": verification_handler,
            },
        )

        task_classifier = TaskClassifier()
        orchestrator = AgentOrchestrator(
            phase_manager=phase_manager,
            task_classifier=task_classifier,
            working_dir=temp_workspace,
            enable_checkpoints=False,  # Disabled
        )

        # Execute task
        await orchestrator.execute_task(
            task="Test task",
            session_id="test_disabled_001",
        )

        # Verify no checkpoints created
        checkpoint_manager = get_checkpoint_manager()
        checkpoints = checkpoint_manager.list_checkpoints(
            session_id="test_disabled_001",
            working_dir=temp_workspace,
        )

        assert len(checkpoints) == 0

    @pytest.mark.asyncio
    async def test_checkpoint_cleanup_after_multiple_iterations(
        self, temp_workspace, mock_phase_handlers
    ):
        """Verify old checkpoints can be cleaned up."""
        planning_handler, execution_handler, verification_handler = mock_phase_handlers

        from hcode.core.protocols import PhaseResult

        # Mock handlers to complete quickly
        planning_handler.handle.return_value = PhaseResult(
            phase_name="planning",
            success=True,
            output="Done",
            can_transition=True,
        )

        execution_handler.handle.return_value = PhaseResult(
            phase_name="execution",
            success=True,
            output="Done",
            can_transition=True,
        )

        verification_handler.handle.return_value = PhaseResult(
            phase_name="verification",
            success=True,
            output="Done",
            can_transition=False,  # Last phase
        )

        # Create orchestrator
        phase_manager = PhaseManager(
            handlers={
                "planning": planning_handler,
                "execution": execution_handler,
                "verification": verification_handler,
            },
        )

        task_classifier = TaskClassifier()
        orchestrator = AgentOrchestrator(
            phase_manager=phase_manager,
            task_classifier=task_classifier,
            working_dir=temp_workspace,
            enable_checkpoints=True,
        )

        # Execute task (creates multiple checkpoints)
        await orchestrator.execute_task(
            task="Test task",
            session_id="test_cleanup_001",
        )

        # Cleanup old checkpoints, keep 2
        checkpoint_manager = get_checkpoint_manager()
        deleted_count = checkpoint_manager.cleanup_old_checkpoints(
            session_id="test_cleanup_001",
            working_dir=temp_workspace,
            keep_count=2,
        )

        # Verify cleanup happened
        remaining = checkpoint_manager.list_checkpoints(
            session_id="test_cleanup_001",
            working_dir=temp_workspace,
        )

        assert len(remaining) <= 2
