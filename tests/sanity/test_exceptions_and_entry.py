"""
Sanity Check: Exceptions and Entry Point Tests.

Tests the exceptions module and main entry points.
"""

import pytest


class TestExceptionsModule:
    """Test exceptions module."""

    def test_exceptions_import(self):
        """Test exceptions module imports."""
        from hcode import exceptions

        assert exceptions is not None

    def test_base_exception_exists(self):
        """Test base HCode exception exists."""
        from hcode import exceptions

        # Check for base exception class
        assert (
            hasattr(exceptions, "HCodeError")
            or hasattr(exceptions, "HCodeException")
            or hasattr(exceptions, "BaseError")
        )

    def test_common_exceptions_exist(self):
        """Test common exception types exist."""
        from hcode import exceptions

        # Check for common exception types
        exc_types = dir(exceptions)
        # Should have at least a few exception classes
        exception_count = sum(
            1 for name in exc_types if name.endswith("Error") or name.endswith("Exception")
        )
        assert exception_count >= 1


class TestMainModule:
    """Test main module entry point."""

    def test_main_module_import(self):
        """Test __main__ module imports."""
        from hcode import __main__

        assert __main__ is not None

    def test_main_function_exists(self):
        """Test main function exists."""
        from hcode import __main__

        assert hasattr(__main__, "main")


class TestHCodePackage:
    """Test main hcode package."""

    def test_hcode_import(self):
        """Test hcode package imports."""
        import hcode

        assert hcode is not None

    def test_hcode_version(self):
        """Test hcode has version info."""
        import hcode

        assert hasattr(hcode, "__version__") or hasattr(hcode, "VERSION")


class TestHCodeChatModule:
    """Test hcode_chat module."""

    def test_hcode_chat_import(self):
        """Test hcode_chat module imports."""
        from hcode import hcode_chat

        assert hcode_chat is not None

    def test_hcode_chat_has_chat_function(self):
        """Test hcode_chat has main chat functionality."""
        from hcode import hcode_chat

        # Should have some chat-related function or class
        assert (
            hasattr(hcode_chat, "HCodeChat")
            or hasattr(hcode_chat, "chat")
            or hasattr(hcode_chat, "main")
        )


class TestCLIModule:
    """Test CLI module."""

    def test_cli_import(self):
        """Test cli module imports."""
        from hcode import cli

        assert cli is not None

    def test_cli_has_main(self):
        """Test CLI has main entry point."""
        from hcode import cli

        assert hasattr(cli, "main") or hasattr(cli, "cli") or hasattr(cli, "app")


class TestCLIEnhancedModule:
    """Test enhanced CLI module."""

    def test_cli_enhanced_import(self):
        """Test cli_enhanced module imports."""
        from hcode import cli_enhanced

        assert cli_enhanced is not None
