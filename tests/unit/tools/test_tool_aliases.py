"""
Tests for tool name aliasing.

Tests that tool names like "LSTool", "ReadTool", etc. correctly resolve to
their registered names ("ls", "read", etc.) through the alias system.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hcode.tools.base.base_tool import ToolRegistry, BaseTool, ToolResult, ToolCategory  # noqa: E402


class DummyTool(BaseTool):
    """A simple tool for testing"""

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.category = ToolCategory.CUSTOM

    def get_parameters(self):
        return []

    async def execute(self, **kwargs):
        return ToolResult(success=True, output=f"Executed {self.name}")


class TestToolAliases:
    """Test tool name alias resolution"""

    def test_direct_lookup(self):
        """Direct lookup should work"""
        registry = ToolRegistry()
        registry.register(DummyTool("Read"))

        tool = registry.get_tool("read")
        assert tool is not None
        assert tool.name == "Read"

    def test_alias_lookup_lstool(self):
        """LSTool should resolve to ls"""
        registry = ToolRegistry()
        registry.register(DummyTool("LS"))

        # Direct lookup
        tool = registry.get_tool("ls")
        assert tool is not None
        assert tool.name == "LS"

        # Alias lookup
        tool = registry.get_tool("LSTool")
        assert tool is not None
        assert tool.name == "LS"

        tool = registry.get_tool("lstool")
        assert tool is not None
        assert tool.name == "LS"

    def test_alias_lookup_readtool(self):
        """ReadTool should resolve to read"""
        registry = ToolRegistry()
        registry.register(DummyTool("Read"))

        tool = registry.get_tool("ReadTool")
        assert tool is not None
        assert tool.name == "Read"

        tool = registry.get_tool("readtool")
        assert tool is not None
        assert tool.name == "Read"

    def test_alias_lookup_writetool(self):
        """WriteTool should resolve to write"""
        registry = ToolRegistry()
        registry.register(DummyTool("Write"))

        tool = registry.get_tool("WriteTool")
        assert tool is not None
        assert tool.name == "Write"

    def test_alias_lookup_edittool(self):
        """EditTool should resolve to edit"""
        registry = ToolRegistry()
        registry.register(DummyTool("Edit"))

        tool = registry.get_tool("EditTool")
        assert tool is not None
        assert tool.name == "Edit"

    def test_alias_lookup_globtool(self):
        """GlobTool should resolve to glob"""
        registry = ToolRegistry()
        registry.register(DummyTool("Glob"))

        tool = registry.get_tool("GlobTool")
        assert tool is not None
        assert tool.name == "Glob"

    def test_alias_lookup_greptool(self):
        """GrepTool should resolve to grep"""
        registry = ToolRegistry()
        registry.register(DummyTool("Grep"))

        tool = registry.get_tool("GrepTool")
        assert tool is not None
        assert tool.name == "Grep"

    def test_alias_lookup_bashtool(self):
        """BashTool should resolve to bash"""
        registry = ToolRegistry()
        registry.register(DummyTool("Bash"))

        tool = registry.get_tool("BashTool")
        assert tool is not None
        assert tool.name == "Bash"

    def test_tool_suffix_stripping(self):
        """Names ending in 'tool' should have suffix stripped"""
        registry = ToolRegistry()
        registry.register(DummyTool("Custom"))

        # Should find by stripping 'tool' suffix
        tool = registry.get_tool("CustomTool")
        assert tool is not None
        assert tool.name == "Custom"

    def test_case_insensitive(self):
        """Tool lookup should be case insensitive"""
        registry = ToolRegistry()
        registry.register(DummyTool("MyTool"))

        tool = registry.get_tool("mytool")
        assert tool is not None

        tool = registry.get_tool("MYTOOL")
        assert tool is not None

        tool = registry.get_tool("MyTool")
        assert tool is not None

    def test_nonexistent_tool(self):
        """Nonexistent tools should return None"""
        registry = ToolRegistry()
        registry.register(DummyTool("Existing"))

        tool = registry.get_tool("NonExistent")
        assert tool is None

    def test_multiple_tools_with_aliases(self):
        """Multiple tools should all be resolvable via aliases"""
        registry = ToolRegistry()
        registry.register(DummyTool("LS"))
        registry.register(DummyTool("Read"))
        registry.register(DummyTool("Write"))
        registry.register(DummyTool("Edit"))
        registry.register(DummyTool("Glob"))
        registry.register(DummyTool("Grep"))
        registry.register(DummyTool("Bash"))

        # All should be findable via alias
        assert registry.get_tool("LSTool") is not None
        assert registry.get_tool("ReadTool") is not None
        assert registry.get_tool("WriteTool") is not None
        assert registry.get_tool("EditTool") is not None
        assert registry.get_tool("GlobTool") is not None
        assert registry.get_tool("GrepTool") is not None
        assert registry.get_tool("BashTool") is not None


class TestToolRegistryWithRealTools:
    """Test tool registry with actual tool implementations"""

    def test_file_tools_aliases(self):
        """File tools should be resolvable via aliases"""
        from hcode.tools.files.file_tools import ReadTool, WriteTool, EditTool, GlobTool, GrepTool

        registry = ToolRegistry()
        registry.register(ReadTool())
        registry.register(WriteTool())
        registry.register(EditTool())
        registry.register(GlobTool())
        registry.register(GrepTool())

        # Direct names work (class names become lowercase)
        assert registry.get_tool("readtool") is not None
        assert registry.get_tool("writetool") is not None
        assert registry.get_tool("edittool") is not None
        assert registry.get_tool("globtool") is not None
        assert registry.get_tool("greptool") is not None

        # Mixed case should also work
        assert registry.get_tool("ReadTool") is not None
        assert registry.get_tool("WriteTool") is not None

    def test_bash_tools_aliases(self):
        """Bash tools should be resolvable via aliases"""
        from hcode.tools.bash_tools import BashTool, LSTool

        registry = ToolRegistry()
        registry.register(BashTool())
        registry.register(LSTool())

        # LSTool registers as "LS"
        assert registry.get_tool("ls") is not None
        assert registry.get_tool("LSTool") is not None
        assert registry.get_tool("lstool") is not None

        # BashTool registers as "Bash"
        assert registry.get_tool("bash") is not None
        assert registry.get_tool("BashTool") is not None
        assert registry.get_tool("bashtool") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
