"""
Sanity Check: Core Components Tests.

Tests the basic functionality of core HCode components.
"""

import pytest
import tempfile
import os
from pathlib import Path


class TestFilesystemComponent:
    """Test filesystem component basic functionality."""

    def test_filesystem_import(self):
        """Test filesystem module imports."""
        from hcode.core.filesystem import FileSystem

        assert FileSystem is not None

    def test_filesystem_instantiation(self):
        """Test FileSystem can be instantiated."""
        from hcode.core.filesystem import FileSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            fs = FileSystem(root_path=Path(tmpdir))
            assert fs is not None

    def test_filesystem_read_write(self):
        """Test FileSystem can read and write files."""
        from hcode.core.filesystem import FileSystem

        with tempfile.TemporaryDirectory() as tmpdir:
            fs = FileSystem(root_path=Path(tmpdir))
            test_file = Path(tmpdir) / "test.txt"
            test_content = "Hello, HCode!"

            # Write
            fs.write_file(test_file, test_content)
            assert test_file.exists()

            # Read
            content = fs.read_file(test_file)
            assert content == test_content


class TestSafetyComponent:
    """Test safety component basic functionality."""

    def test_safety_import(self):
        """Test safety module imports."""
        from hcode.core.safety import SafetyChecker

        assert SafetyChecker is not None

    def test_safety_instantiation(self):
        """Test SafetyChecker can be instantiated."""
        from hcode.core.safety import SafetyChecker

        checker = SafetyChecker()
        assert checker is not None


class TestContextComponent:
    """Test context component basic functionality."""

    def test_context_import(self):
        """Test context module imports."""
        from hcode.core.context import Context

        assert Context is not None


class TestContinuationComponent:
    """Test continuation component basic functionality."""

    def test_continuation_import(self):
        """Test continuation module imports."""
        from hcode.core.continuation import ContinuationManager

        assert ContinuationManager is not None


class TestOutputHandlerComponent:
    """Test output handler component basic functionality."""

    def test_output_handler_import(self):
        """Test output_handler module imports."""
        from hcode.core.output_handler import OutputHandler

        assert OutputHandler is not None

    def test_output_handler_instantiation(self):
        """Test OutputHandler can be instantiated."""
        from hcode.core.output_handler import OutputHandler

        handler = OutputHandler()
        assert handler is not None


class TestInteractionLoggerComponent:
    """Test interaction logger component basic functionality."""

    def test_interaction_logger_import(self):
        """Test interaction_logger module imports."""
        from hcode.core.interaction_logger import InteractionLogger

        assert InteractionLogger is not None

    def test_interaction_logger_instantiation(self):
        """Test InteractionLogger can be instantiated."""
        from hcode.core.interaction_logger import InteractionLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = InteractionLogger(log_dir=Path(tmpdir))
            assert logger is not None


class TestHCodeContextComponent:
    """Test HCode context component basic functionality."""

    def test_hcode_context_import(self):
        """Test hcode_context module imports."""
        from hcode.core.hcode_context import HCodeContext

        assert HCodeContext is not None
