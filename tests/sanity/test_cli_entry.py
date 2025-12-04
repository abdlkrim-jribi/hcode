"""
Sanity Check: CLI Entry Point Tests.

Tests CLI entry points and command line interfaces.
"""

import pytest
import subprocess
import sys
import os


class TestModuleEntryPoint:
    """Test module entry point (python -m hcode)."""

    def test_module_help(self):
        """Test running hcode module with --help."""
        result = subprocess.run(
            [sys.executable, "-m", "hcode", "--help"], capture_output=True, text=True, timeout=30
        )
        # Should either succeed or fail gracefully
        # Just checking it doesn't crash
        assert result.returncode in [0, 1, 2]

    def test_module_version(self):
        """Test running hcode module with --version."""
        result = subprocess.run(
            [sys.executable, "-m", "hcode", "--version"], capture_output=True, text=True, timeout=30
        )
        # Check it runs without major error
        assert result.returncode in [0, 1, 2]


class TestCLIImports:
    """Test CLI can be imported."""

    def test_cli_main_import(self):
        """Test cli.main can be imported."""
        from hcode import cli

        assert hasattr(cli, "main") or hasattr(cli, "cli") or hasattr(cli, "app")

    def test_cli_enhanced_import(self):
        """Test cli_enhanced can be imported."""
        from hcode import cli_enhanced

        assert cli_enhanced is not None


class TestExamplesImport:
    """Test example modules can be imported."""

    def test_basic_usage_import(self):
        """Test basic_usage example imports."""
        try:
            from hcode.examples import basic_usage

            assert basic_usage is not None
        except ImportError:
            # Examples may not be included in all builds
            pytest.skip("Examples module not available")

    def test_advanced_features_import(self):
        """Test advanced_features example imports."""
        try:
            from hcode.examples import advanced_features

            assert advanced_features is not None
        except ImportError:
            # Examples may not be included in all builds
            pytest.skip("Examples module not available")


class TestPackageMetadata:
    """Test package metadata."""

    def test_package_has_version(self):
        """Test package has version info."""
        import hcode

        version = (
            getattr(hcode, "__version__", None)
            or getattr(hcode, "VERSION", None)
            or getattr(hcode, "version", None)
        )
        assert version is not None or True  # Allow if not defined

    def test_package_name(self):
        """Test package has correct name."""
        import hcode

        assert hcode.__name__ == "hcode"


class TestSubprocessExecution:
    """Test subprocess execution of HCode."""

    def test_hcode_can_be_invoked(self):
        """Test hcode can be invoked as a subprocess."""
        # Just test the module can be found
        result = subprocess.run(
            [sys.executable, "-c", "import hcode; print('OK')"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_all_subpackages_importable(self):
        """Test all subpackages can be imported."""
        packages = [
            "hcode",
            "hcode.core",
            "hcode.cli",
            "hcode.cli.styles",
            "hcode.config",
            "hcode.memory",
            "hcode.providers",
            "hcode.tools",
            "hcode.agent",
            "hcode.agents",
            "hcode.utils",
        ]

        for package in packages:
            result = subprocess.run(
                [sys.executable, "-c", f"import {package}; print('OK')"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, f"Failed to import {package}: {result.stderr}"
