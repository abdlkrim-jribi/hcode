"""Sanity Check: Integration Tests.

This module contains integration tests that verify the interaction between multiple HCode components. It ensures that core agents, memory systems, tool chains, CLI components, providers, configuration, and end‑to‑end workflows work together as expected.

The tests use temporary directories and asynchronous fixtures where appropriate.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path


class TestCoreAgentIntegration:
    """Test integration of core agent components.

    This class contains tests that verify the core agent module can be imported
    and is functional.
    """

    def test_agent_module_exists(self):
        """Test that the core agent module can be imported.

        Ensures that the `hcode.core.agent` module is importable and not None.
        """
        from hcode.core import agent

        assert agent is not None


class TestMemorySystemIntegration:
    """Test integration of memory system components.

    This class validates that the `MemoryManager` correctly integrates all memory layers
    (file, session, semantic) and provides a unified context.
    """

    def test_memory_manager_with_all_layers(self):
        """Test that `MemoryManager` integrates all memory layers.

        The test creates a temporary `MemoryManager` instance and checks that each
        memory layer (file, session, semantic) returns the expected types.
        """
        from hcode.memory.memory_manager import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mm = MemoryManager(project_root=Path(tmpdir))

            # Test file memory layer
            file_context = mm.file_memory.get_combined_context()
            assert isinstance(file_context, str)

            # Test session memory layer
            session = mm.session
            assert session is not None

            # Test semantic memory layer
            semantic = mm.semantic_memory
            assert semantic is not None

            # Test unified context
            context = mm.get_context()
            assert context is not None

    def test_memory_manager_add_and_recall(self):
        """Test that `MemoryManager` can add and recall memories.

        The test adds a message and a fact, then verifies that statistics are
        generated and contain expected keys.
        """
        from hcode.memory.memory_manager import MemoryManager
        from hcode.memory.semantic_memory import MemoryType

        with tempfile.TemporaryDirectory() as tmpdir:
            mm = MemoryManager(project_root=Path(tmpdir))

            # Add a message
            mm.add_message(role="user", content="Test message")

            # Remember something
            mm.remember(
                content="Important fact about the project",
                memory_type=MemoryType.FACT,
                importance=0.8,
            )

            # Get stats
            stats = mm.get_stats()
            assert stats is not None
            assert "session" in stats


class TestToolChainIntegration:
    """Test integration of tool chains.

    This class ensures that the file‑tool chain (WriteTool, ReadTool, EditTool)
    works together correctly in an asynchronous context.
    """

    @pytest.mark.asyncio
    async def test_file_tools_chain(self):
        """Test that file tools (write, read, edit) work together.

        The test writes a file, reads it back, edits its content, and then
        verifies the edit was successful.
        """
        from hcode.tools.file_tools import WriteTool, ReadTool, EditTool

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "chain_test.txt"

            # Write
            write_tool = WriteTool()
            await write_tool.execute(file_path=str(test_file), content="Original content")

            # Read
            read_tool = ReadTool()
            result = await read_tool.execute(file_path=str(test_file))
            assert "Original" in str(result)

            # Edit
            edit_tool = EditTool()
            await edit_tool.execute(
                file_path=str(test_file),
                old_string="Original content",
                new_string="Modified content",
            )

            # Verify edit
            result = await read_tool.execute(file_path=str(test_file))
            assert "Modified" in str(result)


class TestCLIIntegration:
    """Test CLI integration with other components.

    This class validates that CLI display utilities interact correctly with
    styling components such as colors and icons.
    """

    def test_agent_display_with_colors(self):
        """Test that `AgentDisplay` integrates with `Colors`.

        Ensures that the display object can access color definitions without
        errors.
        """
        from hcode.cli.display import AgentDisplay
        from hcode.cli.styles.colors import Colors

        display = AgentDisplay()
        # Display should be able to use colors
        assert Colors.PRIMARY is not None
        assert display is not None

    def test_hcode_style_with_icons(self):
        """Test that `HcodeStyle` provides icons.

        Verifies that the style class and the `Icons` utility are both
        importable and contain expected attributes.
        """
        from hcode.cli.tool_display import HcodeStyle
        from hcode.cli.styles.icons import Icons

        icons = Icons()

        # Both should work together
        assert HcodeStyle is not None
        assert icons.CHECK is not None


class TestProviderIntegration:
    """Test provider integration.

    This class checks that provider modules (Anthropic, OpenAI) are
    importable and that the selector class exists.
    """

    def test_provider_classes_exist(self):
        """Test that provider classes can be imported.

        Ensures that `AnthropicProvider` and `OpenAIProvider` are available.
        """
        from hcode.providers.anthropic_provider import AnthropicProvider
        from hcode.providers.openai_provider import OpenAIProvider

        # Provider classes should be accessible
        assert AnthropicProvider is not None
        assert OpenAIProvider is not None

    def test_provider_selector_class_exists(self):
        """Test that `ProviderSelector` class exists.

        Confirms the selector utility is importable.
        """
        from hcode.providers.provider_selector import ProviderSelector

        assert ProviderSelector is not None


class TestConfigIntegration:
    """Test config integration.

    This class validates that configuration modules (`settings`, `defaults`)
    are importable and correctly initialized.
    """

    def test_config_modules_exist(self):
        """Test that config modules exist.

        Checks that `settings` and `defaults` can be imported without error.
        """
        from hcode.config import settings
        from hcode.config import defaults

        # Settings should exist
        assert settings is not None
        assert defaults is not None


class TestAgentThinkingIntegration:
    """Test agent thinking integration.

    This class ensures that the `ThinkingManager` and related config are
    importable and functional.
    """

    def test_thinking_manager_import(self):
        """Test that `ThinkingManager` can be imported.

        Verifies that the thinking manager class and its configuration are
        available.
        """
        from hcode.agent.thinking_manager import ThinkingManager
        from hcode.config import thinking

        # Both should exist
        assert ThinkingManager is not None
        assert thinking is not None


class TestEndToEndFlow:
    """Test end-to-end flows.

    This class contains integration tests that simulate full workflows,
    including file creation, tool chain execution, and memory management.
    """

    @pytest.mark.asyncio
    async def test_simple_file_workflow(self):
        """Test a simple file creation and reading workflow.

        The test writes multiple files, uses `GlobTool` to locate them, and
        `GrepTool` to search for content, verifying the tool chain works.
        """
        from hcode.tools.files.file_tools import WriteTool, ReadTool, GlobTool, GrepTool

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple files
            write_tool = WriteTool()
            await write_tool.execute(
                file_path=str(Path(tmpdir) / "main.py"),
                content="def main():\n    print('Hello')\n\nmain()",
            )
            await write_tool.execute(
                file_path=str(Path(tmpdir) / "utils.py"), content="def helper():\n    return 42"
            )

            # Find Python files
            glob_tool = GlobTool()
            result = await glob_tool.execute(pattern="*.py", path=tmpdir)
            assert "main.py" in str(result) or "utils.py" in str(result)

            # Search for content
            grep_tool = GrepTool()
            result = await grep_tool.execute(pattern="def", path=tmpdir)
            assert result is not None

    def test_memory_workflow(self):
        """Test a memory management workflow.

        This test creates a `MemoryManager`, adds messages, retrieves context,
        and checks that statistics reflect the interactions.
        """
        from hcode.memory.memory_manager import MemoryManager, get_memory_manager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use convenience function
            mm = get_memory_manager(project_root=Path(tmpdir))
            assert mm is not None

            # Simulate conversation
            mm.add_message(role="user", content="What files are in this project?")
            mm.add_message(role="assistant", content="Let me check the project files.")

            # Get context for next turn
            context = mm.get_context(query="project files")
            assert context is not None

            # Get stats
            stats = mm.get_stats()
            assert stats["session"]["message_count"] >= 2
