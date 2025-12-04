"""
Sanity Check: Utils Components Tests.

Tests the basic functionality of utility components.
"""

import pytest
import tempfile
from pathlib import Path


class TestValidatorsComponent:
    """Test validators component."""

    def test_validators_import(self):
        """Test validators module imports."""
        from hcode.utils import validators

        assert validators is not None

    def test_has_validation_functions(self):
        """Test validators has validation functions."""
        from hcode.utils import validators

        # Check for common validation functions
        assert (
            callable(getattr(validators, "validate_path", None))
            or callable(getattr(validators, "is_valid_path", None))
            or hasattr(validators, "PathValidator")
        )


class TestFormattingComponent:
    """Test formatting component."""

    def test_formatting_import(self):
        """Test formatting module imports."""
        from hcode.utils import formatting

        assert formatting is not None

    def test_has_formatting_functions(self):
        """Test formatting has formatting functions."""
        from hcode.utils import formatting

        # Should have some formatting utilities
        assert len(dir(formatting)) > 0


class TestUtilsConfigComponent:
    """Test utils config component."""

    def test_utils_config_import(self):
        """Test utils config module imports."""
        from hcode.utils import config

        assert config is not None


class TestProjectAnalyzerComponent:
    """Test project analyzer component."""

    def test_project_analyzer_import(self):
        """Test project_analyzer module imports."""
        from hcode.utils.project_analyzer import ProjectAnalyzer

        assert ProjectAnalyzer is not None

    def test_project_analyzer_instantiation(self):
        """Test ProjectAnalyzer can be instantiated."""
        from hcode.utils.project_analyzer import ProjectAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = ProjectAnalyzer(project_path=Path(tmpdir))
            assert analyzer is not None

    def test_project_analyzer_analyze(self):
        """Test ProjectAnalyzer can analyze a project."""
        from hcode.utils.project_analyzer import ProjectAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple Python file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("print('hello')")

            analyzer = ProjectAnalyzer(project_path=Path(tmpdir))
            result = analyzer.analyze()
            assert result is not None


class TestUtilsPackageExports:
    """Test utils package exports."""

    def test_utils_package_import(self):
        """Test utils package imports."""
        from hcode import utils

        assert utils is not None
