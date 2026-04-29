"""
Unit tests for refactored SOLID components.

Tests the new architecture:
- TaskClassifier
- ArtifactManager
- Phase handlers
- PhaseManager
- AgentOrchestrator
"""

import pytest
import sys
import tempfile
from pathlib import Path

# Add src directory to path to avoid module import issues
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from hcode.core.protocols import AgentContext
from hcode.core.classification import TaskClassifier
from hcode.core.services import ArtifactManager
from hcode.core.phases import (
    PlanningPhaseHandler,
    ExecutionPhaseHandler,
    VerificationPhaseHandler,
)
from hcode.core.orchestration import PhaseManager, AgentOrchestrator


# ============================================================================
# TaskClassifier Tests
# ============================================================================

class TestTaskClassifier:
    """Test task classification with configurable patterns."""

    def test_classify_exploration_task(self):
        """Test classification of exploration tasks."""
        classifier = TaskClassifier()

        task = "What is the codebase structure?"
        result = classifier.classify(task)

        assert result == "exploration"
        assert classifier.get_confidence() > 0.5

    def test_classify_implementation_task(self):
        """Test classification of implementation tasks."""
        classifier = TaskClassifier()

        task = "Implement user authentication"
        result = classifier.classify(task)

        assert result == "implementation"

    def test_classify_debugging_task(self):
        """Test classification of debugging tasks."""
        classifier = TaskClassifier()

        task = "Fix the login bug"
        result = classifier.classify(task)

        assert result == "debugging"

    def test_classify_refactoring_task(self):
        """Test classification of refactoring tasks."""
        classifier = TaskClassifier()

        task = "Refactor the authentication module"
        result = classifier.classify(task)

        assert result == "refactoring"

    def test_is_read_only(self):
        """Test read-only task detection."""
        classifier = TaskClassifier()

        assert classifier.is_read_only("Show me all files") is True
        assert classifier.is_read_only("Create a new module") is False

    def test_is_action_task(self):
        """Test action task detection."""
        classifier = TaskClassifier()

        assert classifier.is_action_task("Implement feature X") is True
        assert classifier.is_action_task("Explain how auth works") is False

    def test_get_complexity(self):
        """Test complexity determination."""
        classifier = TaskClassifier()

        simple = classifier.get_complexity("Run tests")
        complex_task = classifier.get_complexity("Refactor entire authentication system")

        assert simple in ["simple", "moderate", "complex"]
        assert complex_task in ["moderate", "complex"]


# ============================================================================
# ArtifactManager Tests
# ============================================================================

class TestArtifactManager:
    """Test artifact management for PEV workflow."""

    @pytest.fixture
    def temp_context(self):
        """Create temporary context for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = AgentContext(
                task="Test task",
                session_id="test-session",
                working_dir=tmpdir,
                iteration=0,
            )
            yield context

    def test_create_artifact(self, temp_context):
        """Test artifact creation."""
        manager = ArtifactManager()

        path = manager.create_artifact(
            "task.md",
            "# Test Task\nContent here",
            temp_context
        )

        assert Path(path).exists()
        assert "task.md" in temp_context.artifacts

    def test_load_artifact(self, temp_context):
        """Test artifact loading."""
        manager = ArtifactManager()

        # Create artifact
        manager.create_artifact(
            "task.md",
            "# Test Content",
            temp_context
        )

        # Load it
        content = manager.load_artifact("task.md", temp_context)

        assert content == "# Test Content"

    def test_artifact_exists(self, temp_context):
        """Test artifact existence check."""
        manager = ArtifactManager()

        assert manager.artifact_exists("task.md", temp_context) is False

        manager.create_artifact("task.md", "Content", temp_context)

        assert manager.artifact_exists("task.md", temp_context) is True

    def test_validate_artifact_content(self):
        """Test artifact content validation."""
        manager = ArtifactManager()

        # Valid task.md
        valid, error = manager.validate_artifact_content(
            "task.md",
            "# Task\n\nThis is a task with enough content to be valid."
        )
        assert valid is True

        # Invalid (too short)
        valid, error = manager.validate_artifact_content(
            "task.md",
            "# Task"
        )
        assert valid is False

        # Empty
        valid, error = manager.validate_artifact_content(
            "task.md",
            ""
        )
        assert valid is False


# ============================================================================
# Phase Handler Tests
# ============================================================================

class TestPhaseHandlers:
    """Test phase handlers."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for handlers."""
        artifact_manager = ArtifactManager()
        provider = None  # Mock provider
        tool_executor = None  # Mock tool executor
        context_manager = None  # Mock context manager

        return {
            "artifact_manager": artifact_manager,
            "provider": provider,
            "tool_executor": tool_executor,
            "context_manager": context_manager,
        }

    @pytest.fixture
    def temp_context(self):
        """Create temporary context for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = AgentContext(
                task="Test implementation task",
                session_id="test-session",
                working_dir=tmpdir,
                iteration=0,
            )
            yield context

    def test_planning_handler_required_artifacts(self, mock_dependencies):
        """Test planning handler artifact requirements."""
        handler = PlanningPhaseHandler(**mock_dependencies)

        artifacts = handler.get_required_artifacts()

        assert "task.md" in artifacts
        assert "implementation_plan.md" in artifacts

    @pytest.mark.asyncio
    async def test_planning_handler_execution(self, mock_dependencies, temp_context):
        """Test planning handler execution."""
        handler = PlanningPhaseHandler(**mock_dependencies)

        result = await handler.handle(temp_context, None)

        # Should have proper phase name
        assert result.phase_name == "planning"

        # With no provider, handler requires AI to generate artifacts
        # Success depends on whether artifacts are created
        # The test verifies the handler returns a result structure

    def test_execution_handler_required_artifacts(self, mock_dependencies):
        """Test execution handler artifact requirements."""
        handler = ExecutionPhaseHandler(**mock_dependencies)

        artifacts = handler.get_required_artifacts()

        # Execution doesn't produce new artifacts
        assert len(artifacts) == 0

    def test_verification_handler_required_artifacts(self, mock_dependencies):
        """Test verification handler artifact requirements."""
        handler = VerificationPhaseHandler(**mock_dependencies)

        artifacts = handler.get_required_artifacts()

        assert "walkthrough.md" in artifacts


# ============================================================================
# PhaseManager Tests
# ============================================================================

class TestPhaseManager:
    """Test phase manager."""

    @pytest.fixture
    def mock_handlers(self):
        """Create mock handlers."""
        from unittest.mock import Mock

        planning = Mock()
        planning.phase_name = "planning"
        planning.can_transition_to_next.return_value = True
        planning.get_required_artifacts.return_value = ["task.md", "implementation_plan.md"]

        execution = Mock()
        execution.phase_name = "execution"
        execution.can_transition_to_next.return_value = True
        execution.get_required_artifacts.return_value = []

        verification = Mock()
        verification.phase_name = "verification"
        verification.can_transition_to_next.return_value = True
        verification.get_required_artifacts.return_value = ["walkthrough.md"]

        return {
            "planning": planning,
            "execution": execution,
            "verification": verification,
        }

    @pytest.fixture
    def temp_context(self):
        """Create temporary context for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = AgentContext(
                task="Test task",
                session_id="test-session",
                working_dir=tmpdir,
                iteration=0,
            )
            yield context

    def test_phase_manager_initialization(self, mock_handlers):
        """Test phase manager initialization."""
        manager = PhaseManager(mock_handlers)

        assert manager.get_current_phase() == "planning"

    def test_phase_transitions(self, mock_handlers, temp_context):
        """Test phase transitions."""
        manager = PhaseManager(mock_handlers)

        assert manager.get_current_phase() == "planning"

        # Transition to execution
        success = manager.transition_to_next_phase(temp_context)
        assert success is True
        assert manager.get_current_phase() == "execution"

        # Transition to verification
        success = manager.transition_to_next_phase(temp_context)
        assert success is True
        assert manager.get_current_phase() == "verification"

        # Can't transition beyond verification
        success = manager.transition_to_next_phase(temp_context)
        assert success is False

    def test_can_complete(self, mock_handlers, temp_context):
        """Test workflow completion detection."""
        manager = PhaseManager(mock_handlers)

        # Not complete in planning phase
        assert manager.can_complete(temp_context) is False

        # Transition to verification
        manager.force_phase("verification")

        # Should be complete if verification is done
        assert manager.can_complete(temp_context) is True

    def test_get_phase_progress(self, mock_handlers):
        """Test phase progress tracking."""
        manager = PhaseManager(mock_handlers)

        progress = manager.get_phase_progress()

        assert progress["current_phase"] == "planning"
        assert progress["phase_index"] == 0
        assert progress["total_phases"] == 3
        assert "progress_percent" in progress


# ============================================================================
# AgentOrchestrator Tests
# ============================================================================

class TestAgentOrchestrator:
    """Test agent orchestrator."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        from unittest.mock import Mock

        phase_manager = Mock()
        phase_manager.get_current_phase.return_value = "planning"
        phase_manager.can_complete.return_value = False
        phase_manager.transition_to_next_phase.return_value = True

        task_classifier = TaskClassifier()

        return {
            "phase_manager": phase_manager,
            "task_classifier": task_classifier,
        }

    def test_initialize_context(self, mock_dependencies):
        """Test context initialization."""
        orchestrator = AgentOrchestrator(**mock_dependencies)

        context = orchestrator.initialize_context(
            "Test task",
            "test-session"
        )

        assert context.task == "Test task"
        assert context.session_id == "test-session"
        assert context.iteration == 0

    def test_get_execution_summary(self, mock_dependencies):
        """Test execution summary."""
        orchestrator = AgentOrchestrator(**mock_dependencies)

        context = orchestrator.initialize_context("Test", "session")
        context.modified_files = ["file1.py", "file2.py"]
        context.completed_actions = [{"tool": "Write"}]

        summary = orchestrator.get_execution_summary(context)

        assert summary["iteration"] == 0
        assert summary["modified_files_count"] == 2
        assert summary["completed_actions_count"] == 1

    def test_should_continue_execution(self, mock_dependencies):
        """Test execution continuation logic."""
        orchestrator = AgentOrchestrator(
            **mock_dependencies,
            max_iterations=10
        )

        context = orchestrator.initialize_context("Test", "session")

        # Should continue initially
        assert orchestrator.should_continue_execution(context) is True

        # Should stop at max iterations
        context.iteration = 10
        assert orchestrator.should_continue_execution(context) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
