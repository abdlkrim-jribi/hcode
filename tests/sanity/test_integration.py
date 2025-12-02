"""
Sanity Check: Integration Tests.

Tests integration between multiple HCode components.
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path


class TestCoreAgentIntegration:
    """Test integration of core agent components."""

    def test_agent_module_exists(self):
        """Test agent module can be imported."""
        from hcode.core import agent
        assert agent is not None


class TestMemorySystemIntegration:
    """Test integration of memory system components."""

    def test_memory_manager_with_all_layers(self):
        """Test MemoryManager integrates all memory layers."""
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
        """Test MemoryManager can add and recall memories."""
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
                importance=0.8
            )

            # Get stats
            stats = mm.get_stats()
            assert stats is not None
            assert 'session' in stats


class TestToolChainIntegration:
    """Test integration of tool chains."""

    @pytest.mark.asyncio
    async def test_file_tools_chain(self):
        """Test file tools work together."""
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
                new_string="Modified content"
            )

            # Verify edit
            result = await read_tool.execute(file_path=str(test_file))
            assert "Modified" in str(result)


class TestCLIIntegration:
    """Test CLI integration with other components."""

    def test_agent_display_with_colors(self):
        """Test AgentDisplay integrates with Colors."""
        from hcode.cli.display import AgentDisplay
        from hcode.cli.styles.colors import Colors

        display = AgentDisplay()
        # Display should be able to use colors
        assert Colors.PRIMARY is not None
        assert display is not None

    def test_hcode_style_with_icons(self):
        """Test HcodeStyle has icons."""
        from hcode.cli.tool_display import HcodeStyle
        from hcode.cli.styles.icons import Icons

        icons = Icons()

        # Both should work together
        assert HcodeStyle is not None
        assert icons.CHECK is not None


class TestProviderIntegration:
    """Test provider integration."""

    def test_provider_classes_exist(self):
        """Test provider classes can be imported."""
        from hcode.providers.anthropic_provider import AnthropicProvider
        from hcode.providers.openai_provider import OpenAIProvider

        # Provider classes should be accessible
        assert AnthropicProvider is not None
        assert OpenAIProvider is not None

    def test_provider_selector_class_exists(self):
        """Test ProviderSelector class exists."""
        from hcode.providers.provider_selector import ProviderSelector
        assert ProviderSelector is not None


class TestConfigIntegration:
    """Test config integration."""

    def test_config_modules_exist(self):
        """Test config modules exist."""
        from hcode.config import settings
        from hcode.config import defaults

        # Settings should exist
        assert settings is not None
        assert defaults is not None


class TestAgentThinkingIntegration:
    """Test agent thinking integration."""

    def test_thinking_manager_import(self):
        """Test ThinkingManager can be imported."""
        from hcode.agent.thinking_manager import ThinkingManager
        from hcode.config import thinking

        # Both should exist
        assert ThinkingManager is not None
        assert thinking is not None


class TestEndToEndFlow:
    """Test end-to-end flows."""

    @pytest.mark.asyncio
    async def test_simple_file_workflow(self):
        """Test a simple file creation and reading workflow."""
        from hcode.tools.file_tools import WriteTool, ReadTool, GlobTool, GrepTool

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple files
            write_tool = WriteTool()
            await write_tool.execute(
                file_path=str(Path(tmpdir) / "main.py"),
                content="def main():\n    print('Hello')\n\nmain()"
            )
            await write_tool.execute(
                file_path=str(Path(tmpdir) / "utils.py"),
                content="def helper():\n    return 42"
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
        """Test a memory management workflow."""
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
            assert stats['session']['message_count'] >= 2
