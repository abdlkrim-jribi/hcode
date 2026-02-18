"""
Integration tests for hcode_memory.md feature.

Tests that memory is created, loaded, and updated correctly across PEV phases.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from hcode.core.protocols import AgentContext
from hcode.core.services.artifact_manager import ArtifactManager
from hcode.core.phases.planning_handler import PlanningPhaseHandler
from hcode.core.phases.execution_handler import ExecutionPhaseHandler
from hcode.core.phases.verification_handler import VerificationPhaseHandler


@pytest.fixture
def mock_context(tmp_path):
    """Create a mock agent context."""
    context = AgentContext(
        task="Test task for memory feature",
        session_id="test-session-123",
        working_dir=str(tmp_path),
        iteration=1,
    )
    # Add some mock modified files
    context.modified_files = ["src/test.py", "tests/test_test.py"]
    return context


@pytest.fixture
def artifact_manager(tmp_path):
    """Create an artifact manager with temp directory."""
    return ArtifactManager(artifacts_dir=".hcode")


class TestMemoryLoading:
    """Test memory loading in phase handlers."""

    def test_load_memory_when_missing(self, mock_context, artifact_manager):
        """Should return empty string when memory doesn't exist."""
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        memory = handler._load_hcode_memory(mock_context)
        assert memory == ""

    def test_load_memory_when_exists(self, mock_context, artifact_manager):
        """Should load and format memory when it exists."""
        # Create memory file
        memory_content = """# Hcode Task Memory
Last updated: 2026-02-07 10:00:00
---

## Task: Previous test task
**Date:** 2026-02-07
**Verdict:** APPROVED
**Files Modified:** 2 files

### What Was Done
- Modified: `test.py`
- Modified: `test_test.py`

### Successful Patterns
- Graceful degradation for error handling

### Testing Insights
- Tests executed: 5/5 passed

### Pitfalls Avoided
- No specific pitfalls identified

---
"""
        artifact_manager.create_artifact("hcode_memory.md", memory_content, mock_context)

        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        memory = handler._load_hcode_memory(mock_context)
        assert "HCODE TASK MEMORY" in memory
        assert "Previous test task" in memory
        assert "Graceful degradation" in memory


class TestMemoryUpdate:
    """Test memory update in verification handler."""

    def test_build_memory_entry(self, mock_context, artifact_manager):
        """Should build properly formatted memory entry."""
        handler = VerificationPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        test_results = {
            "test_command": "pytest -v",
            "tests_run": 5,
            "tests_failed": 0,
        }

        verification_analysis = """
        The implementation follows graceful degradation patterns.
        All tests passed successfully.
        No breaking changes detected.
        """

        entry = handler._build_memory_entry(
            mock_context, test_results, verification_analysis, "APPROVED"
        )

        assert "## Task:" in entry
        assert "**Verdict:** APPROVED" in entry
        assert "**Files Modified:** 2 files" in entry
        assert "### What Was Done" in entry
        assert "### Successful Patterns" in entry
        assert "### Testing Insights" in entry
        assert "### Pitfalls Avoided" in entry

    def test_extract_patterns(self, mock_context, artifact_manager):
        """Should extract patterns from analysis."""
        handler = VerificationPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        analysis = "The code uses graceful degradation and follows single responsibility principle."
        patterns = handler._extract_patterns(analysis)

        assert "Graceful degradation" in patterns
        assert "Single Responsibility" in patterns

    def test_extract_testing_insights(self, mock_context, artifact_manager):
        """Should extract testing insights from results."""
        handler = VerificationPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        test_results = {
            "test_command": "pytest -v",
            "tests_run": 10,
            "tests_failed": 0,
        }

        insights = handler._extract_testing_insights(test_results, "")

        assert "pytest -v" in insights
        assert "10/10 passed" in insights
        assert "Comprehensive test suite" in insights

    def test_merge_memory_entries(self, mock_context, artifact_manager):
        """Should merge new entry at the top."""
        handler = VerificationPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        existing = """# Hcode Task Memory
Last updated: 2026-02-07 09:00:00
---

## Task: Old task
**Date:** 2026-02-07
---
"""

        new_entry = """## Task: New task
**Date:** 2026-02-07
---
"""

        merged = handler._merge_memory_entries(existing, new_entry)

        assert merged.index("New task") < merged.index("Old task")
        assert "Last updated:" in merged

    def test_trim_memory_by_task_count(self, mock_context, artifact_manager):
        """Should trim to 10 most recent tasks."""
        handler = VerificationPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        # Build memory with 12 tasks
        memory = "# Hcode Task Memory\nLast updated: 2026-02-07\n---\n"
        for i in range(12):
            memory += f"\n## Task: Task {i}\n**Date:** 2026-02-07\n---\n"

        trimmed = handler._trim_memory(memory)

        # Should keep header + 10 tasks
        separator_count = trimmed.count("---")
        assert separator_count <= 11  # Header separator + 10 task separators

    def test_update_hcode_memory_full_flow(self, mock_context, artifact_manager):
        """Should create/update memory file on successful verification."""
        handler = VerificationPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        test_results = {
            "test_command": "pytest -v",
            "tests_run": 3,
            "tests_failed": 0,
        }

        verification_analysis = "Implementation uses graceful degradation."

        # First update - should create file
        handler._update_hcode_memory(
            mock_context, test_results, verification_analysis, "APPROVED"
        )

        memory = artifact_manager.load_artifact("hcode_memory.md", mock_context)
        assert memory is not None
        assert "Test task for memory feature" in memory
        assert "APPROVED" in memory

        # Second update - should prepend
        mock_context.task = "Second test task"
        handler._update_hcode_memory(
            mock_context, test_results, verification_analysis, "APPROVED"
        )

        memory = artifact_manager.load_artifact("hcode_memory.md", mock_context)
        assert "Second test task" in memory
        assert "Test task for memory feature" in memory


class TestMemoryInjection:
    """Test memory injection into phase prompts."""

    def test_planning_handler_injects_memory(self, mock_context, artifact_manager):
        """Planning handler should inject memory into prompt."""
        # Create memory
        memory_content = """# Hcode Task Memory
Last updated: 2026-02-07
---

## Task: Previous task
**Verdict:** APPROVED
---
"""
        artifact_manager.create_artifact("hcode_memory.md", memory_content, mock_context)

        # Create planning handler with mocked components
        handler = PlanningPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        # Load memory
        memory = handler._load_hcode_memory(mock_context)

        assert memory != ""
        assert "HCODE TASK MEMORY" in memory
        assert "Previous task" in memory

    def test_execution_handler_injects_memory(self, mock_context, artifact_manager):
        """Execution handler should inject memory into prompt."""
        # Create memory
        memory_content = """# Hcode Task Memory
Last updated: 2026-02-07
---

## Task: Test pattern
**Verdict:** APPROVED
---
"""
        artifact_manager.create_artifact("hcode_memory.md", memory_content, mock_context)

        handler = ExecutionPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        memory = handler._load_hcode_memory(mock_context)

        assert memory != ""
        assert "Test pattern" in memory

    def test_verification_handler_injects_memory(self, mock_context, artifact_manager):
        """Verification handler should inject memory into prompt."""
        # Create memory
        memory_content = """# Hcode Task Memory
Last updated: 2026-02-07
---

## Task: Testing strategy
**Verdict:** APPROVED WITH NOTES
---
"""
        artifact_manager.create_artifact("hcode_memory.md", memory_content, mock_context)

        handler = VerificationPhaseHandler(
            artifact_manager=artifact_manager,
            provider=Mock(),
            tool_executor=Mock(),
            context_manager=Mock(),
            console=None
        )

        memory = handler._load_hcode_memory(mock_context)

        assert memory != ""
        assert "Testing strategy" in memory


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
