"""
Sanity Check: Module Import Tests.

Verifies that all HCode modules can be imported without errors.
This is crucial for validating both source and compiled distributions.
"""

import pytest
import importlib
import sys
from typing import List, Tuple


class TestCoreModuleImports:
    """Test imports of core modules."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "hcode",
            "hcode.core",
            "hcode.core.agent",
            "hcode.core.context",
            "hcode.core.response.continuation",
            "hcode.core.enhanced_agent",
            "hcode.core.filesystem",
            "hcode.core.hcode_context",
            "hcode.core.observability.logger",
            "hcode.core.response.output_handler",
            "hcode.core.safety",
        ],
    )
    def test_core_module_import(self, module_name: str):
        """Test that core modules import successfully."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestCLIModuleImports:
    """Test imports of CLI modules."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "hcode.cli",
            "hcode.cli_enhanced",
            "hcode.cli.display",
            "hcode.cli.shortcuts",
            "hcode.cli.tool_display",
        ],
    )
    def test_cli_module_import(self, module_name: str):
        """Test that CLI modules import successfully."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestCLIStylesModuleImports:
    """Test imports of CLI styles modules."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "hcode.cli.styles",
            "hcode.cli.styles.animations",
            "hcode.cli.styles.borders",
            "hcode.cli.styles.colors",
            "hcode.cli.styles.components",
            "hcode.cli.styles.icons",
        ],
    )
    def test_cli_styles_module_import(self, module_name: str):
        """Test that CLI styles modules import successfully."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestConfigModuleImports:
    """Test imports of config modules."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "hcode.config",
            "hcode.config.defaults",
            "hcode.config.prompts",
            "hcode.config.settings",
            "hcode.config.thinking",
            "hcode.config.tools",
        ],
    )
    def test_config_module_import(self, module_name: str):
        """Test that config modules import successfully."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestMemoryModuleImports:
    """Test imports of memory modules."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "hcode.memory",
            "hcode.memory.cli",
            "hcode.memory.config",
            "hcode.memory.embeddings",
            "hcode.memory.file_memory",
            "hcode.memory.memory_manager",
            "hcode.memory.semantic_memory",
            "hcode.memory.session_memory",
        ],
    )
    def test_memory_module_import(self, module_name: str):
        """Test that memory modules import successfully."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestProviderModuleImports:
    """Test imports of provider modules."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "hcode.providers",
            "hcode.providers.base",
            "hcode.providers.anthropic_provider",
            "hcode.providers.openai_provider",
            "hcode.providers.provider_selector",
        ],
    )
    def test_provider_module_import(self, module_name: str):
        """Test that provider modules import successfully."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestToolsModuleImports:
    """Test imports of tools modules."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "hcode.tools",
            "hcode.tools.system.agent_tools",
            "hcode.tools.base.base_tool",
            "hcode.tools.terminal.bash_tools",
            "hcode.tools.system.command_system",
            "hcode.tools.core.executor",
            "hcode.tools.files.file_tools",
            "hcode.tools.notebook.interactive_tools",
            "hcode.tools.notebook.notebook_tools",
            "hcode.tools.core.parallel_executor",
            "hcode.tools.todo.todo_write",
            "hcode.tools.core.tool_manager",
            "hcode.tools.web.web_tools",
        ],
    )
    def test_tools_module_import(self, module_name: str):
        """Test that tools modules import successfully."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")





class TestAgentsModuleImports:
    """Test imports of agents (sub-agent) modules."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "hcode.agents",
            "hcode.agents.sub_agent",
        ],
    )
    def test_agents_module_import(self, module_name: str):
        """Test that agents modules import successfully."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestUtilsModuleImports:
    """Test imports of utils modules."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "hcode.utils",
            "hcode.utils.config",
            "hcode.utils.formatting",
            "hcode.utils.validators",
        ],
    )
    def test_utils_module_import(self, module_name: str):
        """Test that utils modules import successfully."""
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


class TestExceptionsModuleImport:
    """Test imports of exceptions module."""

    def test_exceptions_import(self):
        """Test that exceptions module imports successfully."""
        try:
            from hcode import exceptions

            assert exceptions is not None
        except ImportError as e:
            pytest.fail(f"Failed to import hcode.exceptions: {e}")


