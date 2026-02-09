"""
Unit tests for checkpoint serialization.

Task #14: Add checkpoint serialization for AgentContext resume-on-failure

These tests validate that:
- AgentContext can be saved to JSON checkpoints
- Checkpoints can be loaded and restore exact state
- Old checkpoints are cleaned up properly
- Checkpoint listing works correctly
"""

import pytest
import json
import tempfile
from pathlib import Path
from hcode.core.services.checkpoint import CheckpointManager, get_checkpoint_manager
from hcode.core.protocols import AgentContext


class TestCheckpointManager:
    """Tests for CheckpointManager."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def checkpoint_manager(self):
        """Create a checkpoint manager for testing."""
        return CheckpointManager()

    @pytest.fixture
    def sample_context(self, temp_workspace):
        """Create a sample AgentContext for testing."""
        return AgentContext(
            task="Implement user authentication",
            session_id="test_session_123",
            working_dir=temp_workspace,
            iteration=3,
            modified_files=["src/auth.py", "tests/test_auth.py"],
            completed_actions=[
                {"tool": "Write", "success": True, "file": "src/auth.py"},
                {"tool": "Write", "success": True, "file": "tests/test_auth.py"},
            ],
            artifacts={
                "task.md": ".hcode/task.md",
                "implementation_plan.md": ".hcode/implementation_plan.md",
            },
            metadata={"complexity": "moderate", "estimated_subtasks": 5},
            tokens_used={"planning": 12000, "execution": 35000},
            token_budget=500000,
        )

    # ===== SAVE CHECKPOINT TESTS =====

    def test_save_checkpoint_creates_file(self, checkpoint_manager, sample_context):
        """Verify save_checkpoint creates a checkpoint file."""
        checkpoint_path = checkpoint_manager.save_checkpoint(
            sample_context,
            phase_name="execution",
        )

        assert Path(checkpoint_path).exists()
        assert "checkpoint_test_session_123" in checkpoint_path
        assert "iter3" in checkpoint_path
        assert "execution" in checkpoint_path

    def test_save_checkpoint_serializes_all_fields(
        self, checkpoint_manager, sample_context
    ):
        """Verify all AgentContext fields are serialized."""
        checkpoint_path = checkpoint_manager.save_checkpoint(sample_context)

        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Verify all fields present
        assert data["task"] == "Implement user authentication"
        assert data["session_id"] == "test_session_123"
        assert data["iteration"] == 3
        assert len(data["modified_files"]) == 2
        assert "src/auth.py" in data["modified_files"]
        assert len(data["completed_actions"]) == 2
        assert data["artifacts"]["task.md"] == ".hcode/task.md"
        assert data["metadata"]["complexity"] == "moderate"
        assert data["tokens_used"]["planning"] == 12000
        assert data["tokens_used"]["execution"] == 35000
        assert data["token_budget"] == 500000

    def test_save_checkpoint_includes_metadata(
        self, checkpoint_manager, sample_context
    ):
        """Verify checkpoint includes metadata (timestamp, phase)."""
        checkpoint_path = checkpoint_manager.save_checkpoint(
            sample_context,
            phase_name="verification",
        )

        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert "checkpoint_time" in data
        assert data["phase"] == "verification"

    def test_save_checkpoint_without_phase(self, checkpoint_manager, sample_context):
        """Verify checkpoint can be saved without phase name."""
        checkpoint_path = checkpoint_manager.save_checkpoint(sample_context)

        assert Path(checkpoint_path).exists()
        # Should not have phase in filename
        assert "_planning_" not in checkpoint_path
        assert "_execution_" not in checkpoint_path

        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["phase"] is None

    # ===== LOAD CHECKPOINT TESTS =====

    def test_load_checkpoint_restores_context(
        self, checkpoint_manager, sample_context
    ):
        """Verify load_checkpoint restores exact AgentContext state."""
        # Save checkpoint
        checkpoint_manager.save_checkpoint(sample_context, phase_name="execution")

        # Load checkpoint
        restored = checkpoint_manager.load_checkpoint(
            session_id="test_session_123",
            working_dir=sample_context.working_dir,
        )

        # Verify all fields match
        assert restored is not None
        assert restored.task == sample_context.task
        assert restored.session_id == sample_context.session_id
        assert restored.working_dir == sample_context.working_dir
        assert restored.iteration == sample_context.iteration
        assert restored.modified_files == sample_context.modified_files
        assert restored.completed_actions == sample_context.completed_actions
        assert restored.artifacts == sample_context.artifacts
        assert restored.metadata == sample_context.metadata
        assert restored.tokens_used == sample_context.tokens_used
        assert restored.token_budget == sample_context.token_budget

    def test_load_checkpoint_latest_by_default(
        self, checkpoint_manager, sample_context, temp_workspace
    ):
        """Verify load_checkpoint loads most recent checkpoint."""
        import time

        # Save multiple checkpoints
        sample_context.iteration = 1
        checkpoint_manager.save_checkpoint(sample_context)

        time.sleep(0.1)  # Ensure different timestamps

        sample_context.iteration = 2
        checkpoint_manager.save_checkpoint(sample_context)

        time.sleep(0.1)

        sample_context.iteration = 3
        checkpoint_manager.save_checkpoint(sample_context)

        # Load without specifying iteration
        restored = checkpoint_manager.load_checkpoint(
            session_id="test_session_123",
            working_dir=temp_workspace,
        )

        # Should load iteration 3 (latest)
        assert restored is not None
        assert restored.iteration == 3

    def test_load_checkpoint_specific_iteration(
        self, checkpoint_manager, sample_context, temp_workspace
    ):
        """Verify load_checkpoint can load specific iteration."""
        # Save multiple checkpoints
        sample_context.iteration = 1
        checkpoint_manager.save_checkpoint(sample_context)

        sample_context.iteration = 2
        checkpoint_manager.save_checkpoint(sample_context)

        sample_context.iteration = 3
        checkpoint_manager.save_checkpoint(sample_context)

        # Load iteration 2 specifically
        restored = checkpoint_manager.load_checkpoint(
            session_id="test_session_123",
            working_dir=temp_workspace,
            iteration=2,
        )

        assert restored is not None
        assert restored.iteration == 2

    def test_load_checkpoint_nonexistent_returns_none(
        self, checkpoint_manager, temp_workspace
    ):
        """Verify load_checkpoint returns None for nonexistent session."""
        restored = checkpoint_manager.load_checkpoint(
            session_id="nonexistent_session",
            working_dir=temp_workspace,
        )

        assert restored is None

    def test_load_checkpoint_no_directory_returns_none(self, checkpoint_manager):
        """Verify load_checkpoint returns None if checkpoint dir doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            restored = checkpoint_manager.load_checkpoint(
                session_id="any_session",
                working_dir=tmpdir,
            )

        assert restored is None

    # ===== LIST CHECKPOINTS TESTS =====

    def test_list_checkpoints_returns_all(
        self, checkpoint_manager, sample_context, temp_workspace
    ):
        """Verify list_checkpoints returns all checkpoints for session."""
        # Save multiple checkpoints
        sample_context.iteration = 1
        checkpoint_manager.save_checkpoint(sample_context, phase_name="planning")

        sample_context.iteration = 2
        checkpoint_manager.save_checkpoint(sample_context, phase_name="execution")

        sample_context.iteration = 3
        checkpoint_manager.save_checkpoint(sample_context, phase_name="verification")

        # List checkpoints
        checkpoints = checkpoint_manager.list_checkpoints(
            session_id="test_session_123",
            working_dir=temp_workspace,
        )

        assert len(checkpoints) == 3

        # Verify metadata
        # Most recent first (reverse chronological)
        assert checkpoints[0]["iteration"] == 3
        assert checkpoints[0]["phase"] == "verification"
        assert checkpoints[1]["iteration"] == 2
        assert checkpoints[1]["phase"] == "execution"
        assert checkpoints[2]["iteration"] == 1
        assert checkpoints[2]["phase"] == "planning"

    def test_list_checkpoints_includes_metadata(
        self, checkpoint_manager, sample_context, temp_workspace
    ):
        """Verify list_checkpoints includes useful metadata."""
        checkpoint_manager.save_checkpoint(sample_context, phase_name="execution")

        checkpoints = checkpoint_manager.list_checkpoints(
            session_id="test_session_123",
            working_dir=temp_workspace,
        )

        assert len(checkpoints) == 1
        checkpoint = checkpoints[0]

        assert "file" in checkpoint
        assert "iteration" in checkpoint
        assert "phase" in checkpoint
        assert "timestamp" in checkpoint
        assert "tokens_used" in checkpoint
        assert "modified_files" in checkpoint

        assert checkpoint["tokens_used"] == 47000  # 12000 + 35000
        assert checkpoint["modified_files"] == 2

    def test_list_checkpoints_empty_for_nonexistent_session(
        self, checkpoint_manager, temp_workspace
    ):
        """Verify list_checkpoints returns empty list for nonexistent session."""
        checkpoints = checkpoint_manager.list_checkpoints(
            session_id="nonexistent",
            working_dir=temp_workspace,
        )

        assert checkpoints == []

    # ===== CLEANUP TESTS =====

    def test_cleanup_old_checkpoints_keeps_recent(
        self, checkpoint_manager, sample_context, temp_workspace
    ):
        """Verify cleanup keeps N most recent checkpoints."""
        import time

        # Save 10 checkpoints
        for i in range(10):
            sample_context.iteration = i
            checkpoint_manager.save_checkpoint(sample_context)
            time.sleep(0.05)  # Ensure different timestamps

        # Cleanup, keep 5
        deleted_count = checkpoint_manager.cleanup_old_checkpoints(
            session_id="test_session_123",
            working_dir=temp_workspace,
            keep_count=5,
        )

        assert deleted_count == 5

        # Verify 5 remain
        checkpoints = checkpoint_manager.list_checkpoints(
            session_id="test_session_123",
            working_dir=temp_workspace,
        )

        assert len(checkpoints) == 5

        # Verify most recent kept
        iterations = [c["iteration"] for c in checkpoints]
        assert set(iterations) == {5, 6, 7, 8, 9}

    def test_cleanup_old_checkpoints_no_op_if_under_limit(
        self, checkpoint_manager, sample_context, temp_workspace
    ):
        """Verify cleanup does nothing if checkpoint count under limit."""
        # Save 3 checkpoints
        for i in range(3):
            sample_context.iteration = i
            checkpoint_manager.save_checkpoint(sample_context)

        # Cleanup with keep_count=5
        deleted_count = checkpoint_manager.cleanup_old_checkpoints(
            session_id="test_session_123",
            working_dir=temp_workspace,
            keep_count=5,
        )

        assert deleted_count == 0

        # Verify all 3 still exist
        checkpoints = checkpoint_manager.list_checkpoints(
            session_id="test_session_123",
            working_dir=temp_workspace,
        )

        assert len(checkpoints) == 3

    # ===== INTEGRATION TESTS =====

    def test_save_and_load_round_trip(self, checkpoint_manager, sample_context):
        """Test full save -> load -> verify round trip."""
        # Save
        checkpoint_path = checkpoint_manager.save_checkpoint(
            sample_context,
            phase_name="execution",
        )

        assert Path(checkpoint_path).exists()

        # Load
        restored = checkpoint_manager.load_checkpoint(
            session_id=sample_context.session_id,
            working_dir=sample_context.working_dir,
        )

        # Verify exact match
        assert restored is not None
        assert restored.task == sample_context.task
        assert restored.session_id == sample_context.session_id
        assert restored.iteration == sample_context.iteration
        assert restored.modified_files == sample_context.modified_files
        assert restored.tokens_used == sample_context.tokens_used

    def test_get_checkpoint_manager_singleton(self):
        """Verify get_checkpoint_manager returns manager instance."""
        manager = get_checkpoint_manager()

        assert isinstance(manager, CheckpointManager)
        assert manager.checkpoint_dir == ".hcode/checkpoints"

    def test_checkpoint_manager_custom_directory(self, temp_workspace):
        """Verify CheckpointManager works with custom directory."""
        manager = CheckpointManager(checkpoint_dir=".custom_checkpoints")

        context = AgentContext(
            task="test task",
            session_id="session_456",
            working_dir=temp_workspace,
            iteration=1,
        )

        checkpoint_path = manager.save_checkpoint(context)

        assert ".custom_checkpoints" in checkpoint_path
        assert Path(checkpoint_path).exists()
