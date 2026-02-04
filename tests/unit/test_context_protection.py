"""
Unit tests for context protection components.

Tests:
- ContextBudgetManager
- SmartGlobTool
- Result limiting
- Smart truncation
- Helpful guidance
"""

import pytest
import tempfile
from pathlib import Path

from src.hcode.core.context.budget_manager import ContextBudgetManager
from src.hcode.tools.files.smart_glob_tool import SmartGlobTool


class TestContextBudgetManager:
    """Test context budget manager."""

    def test_excluded_dirs(self):
        """Test that common directories are excluded."""
        manager = ContextBudgetManager()

        excluded_paths = [
            Path(".git/objects/abc123"),
            Path(".venv/lib/python3.11"),
            Path("node_modules/package"),
            Path("__pycache__/module.pyc"),
            Path("build/output"),
        ]

        for path in excluded_paths:
            assert manager.should_exclude_path(path) is True, f"{path} should be excluded"

    def test_included_dirs(self):
        """Test that source directories are included."""
        manager = ContextBudgetManager()

        included_paths = [
            Path("src/main.py"),
            Path("tests/test_main.py"),
            Path("docs/README.md"),
            Path("examples/example.py"),
        ]

        for path in included_paths:
            assert manager.should_exclude_path(path) is False, f"{path} should be included"

    def test_excluded_patterns(self):
        """Test that binary/temp files are excluded."""
        manager = ContextBudgetManager()

        excluded_files = [
            Path("module.pyc"),
            Path("library.so"),
            Path("app.exe"),
            Path("data.log"),
            Path(".DS_Store"),
        ]

        for path in excluded_files:
            assert manager.should_exclude_path(path) is True, f"{path} should be excluded"

    def test_filter_glob_results(self):
        """Test glob result filtering."""
        manager = ContextBudgetManager()

        # Create test paths (including some excluded)
        paths = [
            Path(f"src/file{i}.py") for i in range(50)
        ] + [
            Path(f".venv/lib/file{i}.py") for i in range(50)
        ] + [
            Path(f"__pycache__/file{i}.pyc") for i in range(50)
        ]

        filtered, was_truncated, guidance = manager.filter_glob_results(paths, "**/*.py")

        # Should filter out .venv and __pycache__
        assert len(filtered) == 50, "Should only include src/ files"
        assert not was_truncated, "Should not truncate 50 files"
        assert not guidance, "No guidance needed for small result set"

    def test_filter_glob_results_large(self):
        """Test glob result filtering with many results."""
        manager = ContextBudgetManager()

        # Create 2000 paths
        paths = [Path(f"src/file{i}.py") for i in range(2000)]

        filtered, was_truncated, guidance = manager.filter_glob_results(paths, "**/*.py")

        # Should truncate to MAX_GLOB_RESULTS
        assert len(filtered) == manager.MAX_GLOB_RESULTS
        assert was_truncated is True
        assert "WARNING" in guidance
        assert "more specific" in guidance

    def test_format_glob_output_small(self):
        """Test formatting small result sets."""
        manager = ContextBudgetManager()

        paths = [Path(f"src/file{i}.py") for i in range(10)]
        output = manager.format_glob_output(paths, Path.cwd())

        lines = output.split('\n')
        # 10 files + summary line
        assert len(lines) >= 10

    def test_format_glob_output_large(self):
        """Test formatting large result sets with truncation."""
        manager = ContextBudgetManager()

        paths = [Path(f"src/file{i}.py") for i in range(200)]
        output = manager.format_glob_output(paths, Path.cwd())

        # Should show first 50 + "... and N more" + last 50
        assert "... and" in output
        assert "more" in output

    def test_truncate_tool_output_small(self):
        """Test that small outputs are not truncated."""
        manager = ContextBudgetManager()

        small_output = "a" * 1000
        result, was_truncated = manager.truncate_tool_output(small_output, "TestTool")

        assert not was_truncated
        assert result == small_output

    def test_truncate_tool_output_large(self):
        """Test that large outputs are truncated."""
        manager = ContextBudgetManager()

        large_output = "a" * 100000
        result, was_truncated = manager.truncate_tool_output(large_output, "TestTool")

        assert was_truncated
        assert len(result) < len(large_output)
        assert "truncated" in result.lower()

    def test_estimate_tokens(self):
        """Test token estimation."""
        manager = ContextBudgetManager()

        # Rough estimate: 4 chars per token
        text = "a" * 400
        tokens = manager.estimate_tokens(text)

        assert tokens == 100  # 400 / 4

    def test_check_context_budget_ok(self):
        """Test context budget check with room available."""
        manager = ContextBudgetManager(context_window=1000)
        manager.current_usage = 500

        content = "a" * 400  # ~100 tokens
        can_add, warning = manager.check_context_budget(content)

        assert can_add is True
        # Should not warn at 60% usage (600/1000)
        assert warning is None

    def test_check_context_budget_warning(self):
        """Test context budget warning at 80%."""
        manager = ContextBudgetManager(context_window=1000)
        manager.current_usage = 700

        content = "a" * 400  # ~100 tokens -> 800/1000 = 80%
        can_add, warning = manager.check_context_budget(content)

        assert can_add is True
        assert warning is not None
        assert "WARNING" in warning

    def test_check_context_budget_exceeded(self):
        """Test context budget exceeded."""
        manager = ContextBudgetManager(context_window=1000)
        manager.current_usage = 900

        content = "a" * 800  # ~200 tokens -> 1100/1000 = exceeded
        can_add, warning = manager.check_context_budget(content)

        assert can_add is False
        assert warning is not None
        assert "ERROR" in warning

    def test_usage_stats(self):
        """Test usage statistics."""
        manager = ContextBudgetManager(context_window=1000)
        manager.current_usage = 700

        stats = manager.get_usage_stats()

        assert stats["current_tokens"] == 700
        assert stats["total_tokens"] == 1000
        assert stats["usage_percent"] == 70
        assert stats["remaining_tokens"] == 300
        assert stats["status"] in ["healthy", "warning", "critical"]


class TestSmartGlobTool:
    """Test smart glob tool."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create source files
            (root / "src").mkdir()
            for i in range(10):
                (root / "src" / f"file{i}.py").touch()

            # Create test files
            (root / "tests").mkdir()
            for i in range(5):
                (root / "tests" / f"test_{i}.py").touch()

            # Create excluded directories
            (root / ".venv").mkdir()
            (root / ".venv" / "lib").mkdir()
            for i in range(100):
                (root / ".venv" / "lib" / f"module{i}.py").touch()

            (root / "__pycache__").mkdir()
            for i in range(50):
                (root / "__pycache__" / f"file{i}.pyc").touch()

            yield root

    @pytest.mark.asyncio
    async def test_basic_glob(self, temp_project):
        """Test basic glob pattern."""
        tool = SmartGlobTool(root_dir=str(temp_project))

        result = await tool.execute(Pattern="**/*.py")

        assert result.success is True
        # Check for files (OS-independent)
        assert "file" in result.output
        assert "test_" in result.output

    @pytest.mark.asyncio
    async def test_excludes_venv(self, temp_project):
        """Test that .venv is excluded."""
        tool = SmartGlobTool(root_dir=str(temp_project))

        result = await tool.execute(Pattern="**/*.py")

        assert result.success is True
        # Should NOT include .venv files
        assert ".venv" not in result.output

    @pytest.mark.asyncio
    async def test_excludes_pycache(self, temp_project):
        """Test that __pycache__ is excluded."""
        tool = SmartGlobTool(root_dir=str(temp_project))

        result = await tool.execute(Pattern="**/*")

        assert result.success is True
        # Should NOT include __pycache__ files
        assert "__pycache__" not in result.output

    @pytest.mark.asyncio
    async def test_result_metadata(self, temp_project):
        """Test that metadata is included."""
        tool = SmartGlobTool(root_dir=str(temp_project))

        result = await tool.execute(Pattern="**/*.py")

        assert result.success is True
        assert "total_matches" in result.metadata
        assert "filtered_matches" in result.metadata
        assert "excluded_count" in result.metadata

    @pytest.mark.asyncio
    async def test_no_matches_help(self, temp_project):
        """Test helpful message when no matches."""
        tool = SmartGlobTool(root_dir=str(temp_project))

        result = await tool.execute(Pattern="**/*.nonexistent")

        assert result.success is True
        assert "No files found" in result.output
        assert "Available directories" in result.output or "Try patterns" in result.output

    @pytest.mark.asyncio
    async def test_specific_directory(self, temp_project):
        """Test searching in specific directory."""
        tool = SmartGlobTool(root_dir=str(temp_project))

        result = await tool.execute(
            Pattern="*.py",
            SearchDirectory=str(temp_project / "src")
        )

        assert result.success is True
        assert "file" in result.output
        # Should only search in src/
        assert result.output.count("\n") <= 12  # 10 files + summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
