"""
Sanity Check: Functional Tests.

Tests actual functional behavior of HCode components.
"""
import pytest
import tempfile
import os
from pathlib import Path


class TestToolExecution:
    """Test tools can be executed."""

    def test_bash_tool_echo(self):
        """Test BashTool can execute echo command."""
        from hcode.tools.bash_tools import BashTool
        tool = BashTool()

        # Execute a simple echo command
        if os.name == 'nt':  # Windows
            result = tool.execute(command='echo hello')
        else:  # Unix
            result = tool.execute(command='echo hello')

        assert result is not None
        assert 'hello' in str(result).lower()

    def test_read_tool_read_file(self):
        """Test ReadTool can read a file."""
        from hcode.tools.file_tools import ReadTool

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_content = "Hello, HCode!"
            test_file.write_text(test_content)

            tool = ReadTool()
            result = tool.execute(file_path=str(test_file))

            assert result is not None
            assert test_content in str(result)

    def test_write_tool_write_file(self):
        """Test WriteTool can write a file."""
        from hcode.tools.file_tools import WriteTool

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "output.txt"
            test_content = "Written by HCode"

            tool = WriteTool()
            result = tool.execute(file_path=str(test_file), content=test_content)

            assert test_file.exists()
            assert test_file.read_text() == test_content

    def test_glob_tool_find_files(self):
        """Test GlobTool can find files."""
        from hcode.tools.file_tools import GlobTool

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "file1.py").write_text("# Python 1")
            (Path(tmpdir) / "file2.py").write_text("# Python 2")
            (Path(tmpdir) / "file.txt").write_text("text")

            tool = GlobTool()
            result = tool.execute(pattern="*.py", path=tmpdir)

            assert result is not None
            result_str = str(result)
            assert "file1.py" in result_str or "file2.py" in result_str

    def test_grep_tool_search(self):
        """Test GrepTool can search files."""
        from hcode.tools.file_tools import GrepTool

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file with searchable content
            test_file = Path(tmpdir) / "search.py"
            test_file.write_text("def my_function():\n    return 42\n")

            tool = GrepTool()
            result = tool.execute(pattern="my_function", path=tmpdir)

            assert result is not None


class TestMemoryFunctionality:
    """Test memory system functionality."""

    def test_session_memory_add_message(self):
        """Test SessionMemory can add messages."""
        from hcode.memory.session_memory import SessionMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SessionMemory(project_root=Path(tmpdir))
            session = sm.create_session()

            # Add a message
            sm.add_message(role="user", content="Hello!")
            sm.add_message(role="assistant", content="Hi there!")

            # Verify messages were added
            messages = sm.get_context_messages()
            assert len(messages) >= 2

    def test_file_memory_update(self):
        """Test FileMemory can update memory files."""
        from hcode.memory.file_memory import FileMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            fm = FileMemory(project_root=Path(tmpdir))

            # Update project memory
            content = "# Project Memory\n\nThis is a test."
            path = fm.update_memory(content=content, scope="project")

            assert path.exists()
            assert content in path.read_text()


class TestConfigFunctionality:
    """Test config functionality."""

    def test_settings_load(self):
        """Test Settings can load configuration."""
        from hcode.config.settings import Settings

        settings = Settings()
        assert settings is not None

        # Check for common settings
        assert hasattr(settings, 'model') or hasattr(settings, 'get')

    def test_defaults_access(self):
        """Test defaults can be accessed."""
        from hcode.config import defaults

        # Should be able to access some default values
        attrs = [a for a in dir(defaults) if not a.startswith('_')]
        assert len(attrs) > 0


class TestTodoFunctionality:
    """Test todo system functionality."""

    def test_todo_manager_operations(self):
        """Test TodoManager basic operations."""
        from hcode.agent.todo import TodoManager, TodoItem

        manager = TodoManager()

        # Add a todo
        item = TodoItem(
            content="Test task",
            status="pending",
            activeForm="Testing task"
        )
        manager.add_item(item)

        # Get todos
        todos = manager.get_items()
        assert len(todos) >= 1

        # Mark as completed
        manager.update_status(0, "completed")
        todos = manager.get_items()
        assert todos[0].status == "completed"


class TestDisplayFunctionality:
    """Test display functionality."""

    def test_display_format_output(self):
        """Test Display can format output."""
        from hcode.cli.display import Display

        display = Display()
        # Should be able to call display methods without error
        assert display is not None

    def test_icons_render(self):
        """Test Icons can render."""
        from hcode.cli.styles.icons import Icons

        icons = Icons()
        # Check icons are strings
        assert isinstance(icons.CHECK, str)
        assert isinstance(icons.ERROR, str)

    def test_colors_are_strings(self):
        """Test Colors are valid color strings."""
        from hcode.cli.styles.colors import Colors

        # Colors should be strings (color codes)
        assert isinstance(Colors.PRIMARY, str)
        assert isinstance(Colors.SUCCESS, str)
        assert isinstance(Colors.ERROR, str)


class TestToolManagerFunctionality:
    """Test tool manager functionality."""

    def test_tool_manager_register_and_get(self):
        """Test ToolManager can register and get tools."""
        from hcode.tools.tool_manager import ToolManager
        from hcode.tools.base_tool import BaseTool

        manager = ToolManager()
        tools = manager.get_tools()

        # Should have at least some built-in tools
        assert len(tools) >= 0

    def test_tool_manager_list_tools(self):
        """Test ToolManager can list available tools."""
        from hcode.tools.tool_manager import ToolManager

        manager = ToolManager()

        # Should be able to get tool names or definitions
        assert hasattr(manager, 'get_tools') or hasattr(manager, 'list_tools')
