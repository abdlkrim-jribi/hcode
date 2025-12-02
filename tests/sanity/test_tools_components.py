"""
Sanity Check: Tools Components Tests.

Tests the basic functionality of tool components.
"""
import pytest
import tempfile
from pathlib import Path


class TestBaseToolComponent:
    """Test base tool component."""

    def test_base_tool_import(self):
        """Test base_tool module imports."""
        from hcode.tools.base_tool import BaseTool
        assert BaseTool is not None


class TestBashToolsComponent:
    """Test bash tools component."""

    def test_bash_tools_import(self):
        """Test bash_tools module imports."""
        from hcode.tools.bash_tools import BashTool
        assert BashTool is not None

    def test_bash_tool_instantiation(self):
        """Test BashTool can be instantiated."""
        from hcode.tools.bash_tools import BashTool
        tool = BashTool()
        assert tool is not None

    def test_bash_tool_has_execute(self):
        """Test BashTool has execute method."""
        from hcode.tools.bash_tools import BashTool
        tool = BashTool()
        assert hasattr(tool, 'execute')


class TestFileToolsComponent:
    """Test file tools component."""

    def test_file_tools_import(self):
        """Test file_tools module imports."""
        from hcode.tools.file_tools import ReadTool, WriteTool, EditTool, GlobTool, GrepTool
        assert ReadTool is not None
        assert WriteTool is not None
        assert EditTool is not None
        assert GlobTool is not None
        assert GrepTool is not None

    def test_read_tool_instantiation(self):
        """Test ReadTool can be instantiated."""
        from hcode.tools.file_tools import ReadTool
        tool = ReadTool()
        assert tool is not None

    def test_write_tool_instantiation(self):
        """Test WriteTool can be instantiated."""
        from hcode.tools.file_tools import WriteTool
        tool = WriteTool()
        assert tool is not None

    def test_edit_tool_instantiation(self):
        """Test EditTool can be instantiated."""
        from hcode.tools.file_tools import EditTool
        tool = EditTool()
        assert tool is not None

    def test_glob_tool_instantiation(self):
        """Test GlobTool can be instantiated."""
        from hcode.tools.file_tools import GlobTool
        tool = GlobTool()
        assert tool is not None

    def test_grep_tool_instantiation(self):
        """Test GrepTool can be instantiated."""
        from hcode.tools.file_tools import GrepTool
        tool = GrepTool()
        assert tool is not None


class TestWebToolsComponent:
    """Test web tools component."""

    def test_web_tools_import(self):
        """Test web_tools module imports."""
        from hcode.tools.web_tools import WebSearchTool, WebFetchTool
        assert WebSearchTool is not None
        assert WebFetchTool is not None

    def test_web_search_tool_instantiation(self):
        """Test WebSearchTool can be instantiated."""
        from hcode.tools.web_tools import WebSearchTool
        tool = WebSearchTool()
        assert tool is not None

    def test_web_fetch_tool_instantiation(self):
        """Test WebFetchTool can be instantiated."""
        from hcode.tools.web_tools import WebFetchTool
        tool = WebFetchTool()
        assert tool is not None


class TestNotebookToolsComponent:
    """Test notebook tools component."""

    def test_notebook_tools_import(self):
        """Test notebook_tools module imports."""
        from hcode.tools.notebook_tools import NotebookEditTool
        assert NotebookEditTool is not None

    def test_notebook_edit_tool_instantiation(self):
        """Test NotebookEditTool can be instantiated."""
        from hcode.tools.notebook_tools import NotebookEditTool
        tool = NotebookEditTool()
        assert tool is not None


class TestInteractiveToolsComponent:
    """Test interactive tools component."""

    def test_interactive_tools_import(self):
        """Test interactive_tools module imports."""
        from hcode.tools.interactive_tools import AskUserTool
        assert AskUserTool is not None

    def test_ask_user_tool_instantiation(self):
        """Test AskUserTool can be instantiated."""
        from hcode.tools.interactive_tools import AskUserTool
        tool = AskUserTool()
        assert tool is not None


class TestTodoWriteComponent:
    """Test todo write component."""

    def test_todo_write_import(self):
        """Test todo_write module imports."""
        from hcode.tools.todo_write import TodoWriteTool
        assert TodoWriteTool is not None

    def test_todo_write_tool_instantiation(self):
        """Test TodoWriteTool can be instantiated."""
        from hcode.tools.todo_write import TodoWriteTool
        tool = TodoWriteTool()
        assert tool is not None


class TestAgentToolsComponent:
    """Test agent tools component."""

    def test_agent_tools_import(self):
        """Test agent_tools module imports."""
        from hcode.tools.agent_tools import TaskTool
        assert TaskTool is not None

    def test_task_tool_instantiation(self):
        """Test TaskTool can be instantiated."""
        from hcode.tools.agent_tools import TaskTool
        tool = TaskTool()
        assert tool is not None


class TestToolManagerComponent:
    """Test tool manager component."""

    def test_tool_manager_import(self):
        """Test tool_manager module imports."""
        from hcode.tools.tool_manager import ToolManager
        assert ToolManager is not None

    def test_tool_manager_instantiation(self):
        """Test ToolManager can be instantiated."""
        from hcode.tools.tool_manager import ToolManager
        manager = ToolManager()
        assert manager is not None

    def test_tool_manager_get_tools(self):
        """Test ToolManager can get tools."""
        from hcode.tools.tool_manager import ToolManager
        manager = ToolManager()
        tools = manager.get_tools()
        assert isinstance(tools, (list, dict))


class TestExecutorComponent:
    """Test executor component."""

    def test_executor_import(self):
        """Test executor module imports."""
        from hcode.tools.executor import ToolExecutor
        assert ToolExecutor is not None


class TestParallelExecutorComponent:
    """Test parallel executor component."""

    def test_parallel_executor_import(self):
        """Test parallel_executor module imports."""
        from hcode.tools.parallel_executor import ParallelExecutor
        assert ParallelExecutor is not None


class TestCommandSystemComponent:
    """Test command system component."""

    def test_command_system_import(self):
        """Test command_system module imports."""
        from hcode.tools.command_system import CommandSystem
        assert CommandSystem is not None

    def test_command_system_instantiation(self):
        """Test CommandSystem can be instantiated."""
        from hcode.tools.command_system import CommandSystem
        system = CommandSystem()
        assert system is not None
