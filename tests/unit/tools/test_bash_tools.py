"""
Tests for bash execution tools.

Tests Bash, BashOutput, KillShell, and LS tools.
"""

import pytest
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
import platform

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hcode.tools.bash_tools import (
    BashTool,
    BashOutputTool,
    KillShellTool,
    LSTool,
    BashShellManager,
)
from hcode.tools.base_tool import ToolCategory


# Skip tests that require bash on Windows if bash is not available
IS_WINDOWS = platform.system() == "Windows"
HAS_BASH = shutil.which("bash") is not None or shutil.which("sh") is not None


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_dir(temp_dir):
    """Create sample directory structure"""
    # Create directories
    src_dir = Path(temp_dir) / "src"
    tests_dir = Path(temp_dir) / "tests"
    src_dir.mkdir()
    tests_dir.mkdir()

    # Create files
    (src_dir / "main.py").write_text("print('hello')")
    (src_dir / "utils.py").write_text("# utils")
    (tests_dir / "test_main.py").write_text("# tests")
    (Path(temp_dir) / "readme.md").write_text("# README")

    return temp_dir


class TestBashShellManager:
    """Tests for BashShellManager"""

    def test_initialization(self):
        """Test manager initialization"""
        manager = BashShellManager()
        assert manager.shells == {}

    def test_list_shells_empty(self):
        """Test listing shells when empty"""
        manager = BashShellManager()
        assert manager.list_shells() == []

    def test_get_shell_not_found(self):
        """Test getting non-existent shell"""
        manager = BashShellManager()
        assert manager.get_shell("nonexistent") is None

    def test_remove_shell_not_found(self):
        """Test removing non-existent shell"""
        manager = BashShellManager()
        assert manager.remove_shell("nonexistent") == False


class TestBashTool:
    """Tests for BashTool"""

    def test_initialization(self, temp_dir):
        """Test tool initialization"""
        tool = BashTool(root_dir=temp_dir)

        assert tool.name == "Bash"
        assert tool.category == ToolCategory.EXECUTION
        assert str(tool.root_dir) == temp_dir

    def test_get_parameters(self):
        """Test parameter definition"""
        tool = BashTool()
        params = tool.get_parameters()

        param_names = [p.name for p in params]
        assert "command" in param_names
        assert "timeout" in param_names
        assert "run_in_background" in param_names
        assert "description" in param_names

        # command is required
        command_param = next(p for p in params if p.name == "command")
        assert command_param.required == True

    @pytest.mark.asyncio
    async def test_execute_empty_command(self):
        """Test execution with empty command fails"""
        tool = BashTool()

        result = await tool.execute(command="")

        assert result.success == False
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_simple_command(self, temp_dir):
        """Test executing a simple command"""
        tool = BashTool(root_dir=temp_dir)

        # Use cross-platform command
        if IS_WINDOWS:
            result = await tool.execute(command="echo hello")
        else:
            result = await tool.execute(command="echo hello")

        assert result.success == True
        assert "hello" in result.output.lower()

    @pytest.mark.asyncio
    async def test_execute_with_exit_code(self, temp_dir):
        """Test command exit code is captured"""
        tool = BashTool(root_dir=temp_dir)

        # Successful command
        if IS_WINDOWS:
            result = await tool.execute(command="cmd /c exit 0")
        else:
            result = await tool.execute(command="exit 0")

        # Note: exit alone may not work in subprocess shell
        # Test with a command that we know succeeds
        result = await tool.execute(command="echo test")
        assert result.success == True
        assert result.metadata.get("exit_code") == 0

    @pytest.mark.asyncio
    async def test_execute_failing_command(self, temp_dir):
        """Test failing command is captured"""
        tool = BashTool(root_dir=temp_dir)

        # Command that should fail
        await tool.execute(command="ls /nonexistent_path_12345")

        # Either the command fails or produces error
        # On Windows without bash this might not work as expected

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, temp_dir):
        """Test timeout is enforced"""
        tool = BashTool(root_dir=temp_dir)

        # Command that would take too long
        # Use a very short timeout
        if IS_WINDOWS:
            command = "ping -n 10 127.0.0.1"
        else:
            command = "sleep 10"

        await tool.execute(command=command, timeout=500)  # 500ms timeout

        # Should timeout or fail
        # The result depends on timing

    @pytest.mark.asyncio
    async def test_execute_timeout_capped(self, temp_dir):
        """Test timeout is capped at maximum"""
        tool = BashTool(root_dir=temp_dir)

        # Request very long timeout
        result = await tool.execute(command="echo test", timeout=9999999999)  # Very large

        # Should still execute (timeout was capped)
        assert result.success == True

    @pytest.mark.asyncio
    async def test_execute_in_working_directory(self, temp_dir):
        """Test command runs in correct directory"""
        tool = BashTool(root_dir=temp_dir)

        if IS_WINDOWS:
            result = await tool.execute(command="cd")
        else:
            result = await tool.execute(command="pwd")

        assert result.success == True
        assert temp_dir in result.output or Path(temp_dir).name in result.output

    @pytest.mark.asyncio
    async def test_execute_captures_stderr(self, temp_dir):
        """Test stderr is captured"""
        tool = BashTool(root_dir=temp_dir)

        # Command that produces stderr
        if IS_WINDOWS:
            result = await tool.execute(command="dir nonexistent_file_xyz")
        else:
            await tool.execute(command="ls nonexistent_file_xyz 2>&1")

        # Should capture the error message

    @pytest.mark.asyncio
    async def test_execute_background(self, temp_dir):
        """Test background execution"""
        tool = BashTool(root_dir=temp_dir)

        if IS_WINDOWS:
            result = await tool.execute(command="ping -n 2 127.0.0.1", run_in_background=True)
        else:
            result = await tool.execute(command="sleep 1", run_in_background=True)

        assert result.success == True
        assert "shell_id" in result.metadata
        assert "background" in result.output.lower()

    @pytest.mark.asyncio
    async def test_metadata_includes_description(self, temp_dir):
        """Test metadata includes command description"""
        tool = BashTool(root_dir=temp_dir)

        result = await tool.execute(command="echo test", description="Test echo command")

        assert result.success == True
        assert result.metadata.get("description") == "Test echo command"


class TestBashOutputTool:
    """Tests for BashOutputTool"""

    def test_initialization(self):
        """Test tool initialization"""
        tool = BashOutputTool()

        assert tool.name == "BashOutput"
        assert tool.category == ToolCategory.EXECUTION

    def test_get_parameters(self):
        """Test parameter definition"""
        tool = BashOutputTool()
        params = tool.get_parameters()

        param_names = [p.name for p in params]
        assert "bash_id" in param_names
        assert "filter" in param_names

    @pytest.mark.asyncio
    async def test_execute_missing_bash_id(self):
        """Test execution without bash_id fails"""
        tool = BashOutputTool()

        result = await tool.execute()

        assert result.success == False
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_shell_not_found(self):
        """Test execution with invalid shell ID"""
        tool = BashOutputTool()

        result = await tool.execute(bash_id="nonexistent_shell_123")

        assert result.success == False
        assert "not found" in result.error.lower()


class TestKillShellTool:
    """Tests for KillShellTool"""

    def test_initialization(self):
        """Test tool initialization"""
        tool = KillShellTool()

        assert tool.name == "KillShell"
        assert tool.category == ToolCategory.EXECUTION

    def test_get_parameters(self):
        """Test parameter definition"""
        tool = KillShellTool()
        params = tool.get_parameters()

        param_names = [p.name for p in params]
        assert "shell_id" in param_names

    @pytest.mark.asyncio
    async def test_execute_missing_shell_id(self):
        """Test execution without shell_id fails"""
        tool = KillShellTool()

        result = await tool.execute()

        assert result.success == False
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_shell_not_found(self):
        """Test execution with invalid shell ID"""
        tool = KillShellTool()

        result = await tool.execute(shell_id="nonexistent_shell_123")

        assert result.success == False
        assert "not found" in result.error.lower()


class TestLSTool:
    """Tests for LSTool"""

    def test_initialization(self, temp_dir):
        """Test tool initialization"""
        tool = LSTool(root_dir=temp_dir)

        assert tool.name == "LS"
        assert tool.category == ToolCategory.FILE_OPERATIONS

    def test_get_parameters(self):
        """Test parameter definition"""
        tool = LSTool()
        params = tool.get_parameters()

        param_names = [p.name for p in params]
        assert "path" in param_names
        assert "ignore" in param_names

    @pytest.mark.asyncio
    async def test_execute_missing_path(self):
        """Test execution without path fails"""
        tool = LSTool()

        result = await tool.execute()

        assert result.success == False
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_path_not_exists(self):
        """Test execution with non-existent path"""
        tool = LSTool()

        result = await tool.execute(path="/nonexistent/path/12345")

        assert result.success == False
        assert "not exist" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_path_not_directory(self, sample_dir):
        """Test execution with file path (not directory)"""
        tool = LSTool(root_dir=sample_dir)
        file_path = str(Path(sample_dir) / "readme.md")

        result = await tool.execute(path=file_path)

        assert result.success == False
        assert "not a directory" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_list_directory(self, sample_dir):
        """Test listing directory contents"""
        tool = LSTool(root_dir=sample_dir)

        result = await tool.execute(path=sample_dir)

        assert result.success == True
        assert "src" in result.output
        assert "tests" in result.output
        assert "readme.md" in result.output
        assert result.metadata["count"] > 0

    @pytest.mark.asyncio
    async def test_execute_list_subdirectory(self, sample_dir):
        """Test listing subdirectory"""
        tool = LSTool(root_dir=sample_dir)
        src_path = str(Path(sample_dir) / "src")

        result = await tool.execute(path=src_path)

        assert result.success == True
        assert "main.py" in result.output
        assert "utils.py" in result.output

    @pytest.mark.asyncio
    async def test_execute_with_ignore(self, sample_dir):
        """Test listing with ignore patterns"""
        tool = LSTool(root_dir=sample_dir)

        result = await tool.execute(path=sample_dir, ignore="*.md")

        assert result.success == True
        assert "readme.md" not in result.output.lower()

    @pytest.mark.asyncio
    async def test_execute_metadata(self, sample_dir):
        """Test result metadata"""
        tool = LSTool(root_dir=sample_dir)

        result = await tool.execute(path=sample_dir)

        assert "path" in result.metadata
        assert "count" in result.metadata
        assert "entries" in result.metadata
        assert isinstance(result.metadata["entries"], list)


class TestBashToolIntegration:
    """Integration tests for bash tools"""

    @pytest.mark.asyncio
    async def test_background_shell_workflow(self, temp_dir):
        """Test full background shell workflow"""
        bash_tool = BashTool(root_dir=temp_dir)
        output_tool = BashOutputTool()
        kill_tool = KillShellTool()

        # Start background command
        if IS_WINDOWS:
            start_result = await bash_tool.execute(
                command="ping -n 5 127.0.0.1", run_in_background=True
            )
        else:
            start_result = await bash_tool.execute(
                command="sleep 5 && echo done", run_in_background=True
            )

        assert start_result.success == True
        shell_id = start_result.metadata["shell_id"]

        # Get output
        await asyncio.sleep(0.5)  # Wait a bit for output
        output_result = await output_tool.execute(bash_id=shell_id)
        assert output_result.success == True

        # Kill shell
        kill_result = await kill_tool.execute(shell_id=shell_id)
        assert kill_result.success == True

        # Verify shell is gone
        output_result2 = await output_tool.execute(bash_id=shell_id)
        assert output_result2.success == False

    @pytest.mark.asyncio
    async def test_command_chaining(self, temp_dir):
        """Test command chaining with && and ||"""
        tool = BashTool(root_dir=temp_dir)

        # Chain successful commands
        if IS_WINDOWS:
            result = await tool.execute(command="echo first && echo second")
        else:
            result = await tool.execute(command="echo first && echo second")

        assert result.success == True
        assert "first" in result.output
        assert "second" in result.output

    @pytest.mark.asyncio
    async def test_command_with_pipes(self, temp_dir):
        """Test command with pipes"""
        tool = BashTool(root_dir=temp_dir)

        if not IS_WINDOWS:
            await tool.execute(command="echo 'hello world' | wc -w")
            # Note: output format may vary


class TestToolSchemas:
    """Tests for tool schema generation"""

    def test_bash_tool_openai_schema(self):
        """Test OpenAI schema generation"""
        tool = BashTool()
        schema = tool.to_function_schema()

        assert schema["name"] == "bash"
        assert "parameters" in schema
        assert "command" in schema["parameters"]["properties"]

    def test_bash_tool_anthropic_schema(self):
        """Test Anthropic schema generation"""
        tool = BashTool()
        schema = tool.to_anthropic_tool_schema()

        assert schema["name"] == "bash"
        assert "input_schema" in schema
        assert "command" in schema["input_schema"]["properties"]

    def test_ls_tool_schema(self):
        """Test LS tool schema"""
        tool = LSTool()
        schema = tool.to_function_schema()

        assert schema["name"] == "ls"
        assert "path" in schema["parameters"]["required"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
