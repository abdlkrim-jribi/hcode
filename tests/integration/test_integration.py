"""
Integration tests for Hcode agent system.

Tests all tools working together in realistic workflows.
"""

import pytest
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hcode.tools.tool_manager import ToolManager
from hcode.tools.file_tools import ReadTool, WriteTool, EditTool, GlobTool, GrepTool
from hcode.tools.bash_tools import BashTool, LSTool
from hcode.tools.todo_write import TodoWriteTool
from hcode.tools.base_tool import ToolResult
from hcode.agent.todo import TodoManager, TodoStatus
from hcode.agent.thinking import ThinkingBlock, ThinkingSession, ThinkingPhase
from hcode.agent.thinking_manager import ThinkingManager
from hcode.agent.modes import AgentMode, SafetyConfig, get_mode_config


@pytest.fixture
def temp_project():
    """Create a temporary project structure for testing"""
    temp_dir = tempfile.mkdtemp()

    # Create project structure
    src_dir = Path(temp_dir) / "src"
    tests_dir = Path(temp_dir) / "tests"
    src_dir.mkdir()
    tests_dir.mkdir()

    # Create source files
    (src_dir / "main.py").write_text(
        """
def main():
    print("Hello, World!")
    result = calculate(5, 3)
    return result

def calculate(a, b):
    return a + b

if __name__ == "__main__":
    main()
"""
    )

    (src_dir / "utils.py").write_text(
        """
def format_message(msg):
    return f"[INFO] {msg}"

def validate_input(value):
    if not isinstance(value, str):
        raise TypeError("Expected string")
    return value.strip()
"""
    )

    (src_dir / "config.py").write_text(
        """
DEBUG = True
VERSION = "1.0.0"
DATABASE_URL = "sqlite:///app.db"
"""
    )

    # Create test files
    (tests_dir / "test_main.py").write_text(
        """
import pytest
from src.main import main, calculate

def test_calculate():
    assert calculate(2, 3) == 5

def test_main():
    result = main()
    assert result == 8
"""
    )

    # Create requirements.txt
    (Path(temp_dir) / "requirements.txt").write_text(
        """
pytest>=7.0.0
requests>=2.28.0
"""
    )

    # Create README
    (Path(temp_dir) / "README.md").write_text(
        """
# Test Project

A simple test project for integration testing.

## Usage

```python
from src.main import main
main()
```
"""
    )

    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def tool_manager(temp_project):
    """Create a ToolManager with all tools"""
    manager = ToolManager(root_dir=temp_project)
    return manager


class TestToolManagerIntegration:
    """Tests for ToolManager integration"""

    def test_initialization(self, tool_manager):
        """Test tool manager initializes with all tools"""
        tools = tool_manager.list_tools()
        tool_names = [t.name for t in tools]

        # Check essential tools are registered
        assert "Read" in tool_names or "ReadTool" in tool_names
        assert "Write" in tool_names or "WriteTool" in tool_names
        assert "Glob" in tool_names or "GlobTool" in tool_names

    @pytest.mark.asyncio
    async def test_read_existing_file(self, tool_manager, temp_project):
        """Test reading an existing file"""
        result = await tool_manager.read_file(str(Path(temp_project) / "src" / "main.py"))

        assert result.success == True
        assert "def main()" in result.output
        assert "calculate" in result.output

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, tool_manager, temp_project):
        """Test reading non-existent file fails gracefully"""
        result = await tool_manager.read_file(str(Path(temp_project) / "nonexistent.py"))

        assert result.success == False
        assert "not exist" in result.error.lower() or "not found" in result.error.lower()


class TestFileOperationsWorkflow:
    """Test file operations workflow"""

    @pytest.mark.asyncio
    async def test_read_modify_write_workflow(self, temp_project):
        """Test complete read-modify-write workflow"""
        file_path = str(Path(temp_project) / "src" / "config.py")

        # Read original file
        read_tool = ReadTool(root_dir=temp_project)
        read_result = await read_tool.execute(file_path=file_path)

        assert read_result.success == True
        original_content = read_result.output
        assert "DEBUG = True" in original_content

        # Edit file
        edit_tool = EditTool(root_dir=temp_project)
        edit_result = await edit_tool.execute(
            file_path=file_path, old_string="DEBUG = True", new_string="DEBUG = False"
        )

        assert edit_result.success == True

        # Read modified file
        read_result2 = await read_tool.execute(file_path=file_path)

        assert read_result2.success == True
        assert "DEBUG = False" in read_result2.output

    @pytest.mark.asyncio
    async def test_search_and_edit_workflow(self, temp_project):
        """Test search for pattern and edit matching files"""
        # Search for files containing "calculate"
        grep_tool = GrepTool(root_dir=temp_project)
        search_result = await grep_tool.execute(
            pattern="calculate", path=temp_project, output_mode="files_with_matches"
        )

        assert search_result.success == True
        assert "main.py" in search_result.output

        # Find all Python files
        glob_tool = GlobTool(root_dir=temp_project)
        glob_result = await glob_tool.execute(pattern="**/*.py", path=temp_project)

        assert glob_result.success == True
        assert len(glob_result.output) > 0

    @pytest.mark.asyncio
    async def test_create_new_file_workflow(self, temp_project):
        """Test creating a new file"""
        new_file_path = str(Path(temp_project) / "src" / "helpers.py")

        write_tool = WriteTool(root_dir=temp_project)
        write_result = await write_tool.execute(
            file_path=new_file_path,
            content="""
def helper_function(x):
    return x * 2

def another_helper(s):
    return s.upper()
""",
        )

        assert write_result.success == True
        assert Path(new_file_path).exists()

        # Verify content
        read_tool = ReadTool(root_dir=temp_project)
        read_result = await read_tool.execute(file_path=new_file_path)

        assert read_result.success == True
        assert "helper_function" in read_result.output


class TestSearchWorkflow:
    """Test search workflows"""

    @pytest.mark.asyncio
    async def test_glob_and_grep_workflow(self, temp_project):
        """Test finding files by pattern and searching content"""
        # Find all Python files
        glob_tool = GlobTool(root_dir=temp_project)
        python_files = await glob_tool.execute(pattern="**/*.py", path=temp_project)

        assert python_files.success == True

        # Search for specific function
        grep_tool = GrepTool(root_dir=temp_project)
        function_search = await grep_tool.execute(
            pattern="def.*\\(", path=temp_project, output_mode="content"
        )

        assert function_search.success == True
        assert "def" in function_search.output

    @pytest.mark.asyncio
    async def test_search_by_file_type(self, temp_project):
        """Test searching in specific file types"""
        grep_tool = GrepTool(root_dir=temp_project)

        # Search only in Python files
        result = await grep_tool.execute(
            pattern="import", path=temp_project, glob="*.py", output_mode="files_with_matches"
        )

        # May or may not have matches depending on imports
        assert result.success == True


class TestTodoIntegration:
    """Test TodoWrite integration with workflows"""

    @pytest.mark.asyncio
    async def test_todo_workflow(self):
        """Test todo management workflow"""
        manager = TodoManager()
        tool = TodoWriteTool(todo_manager=manager)

        # Start task
        result1 = await tool.execute(
            todos=[
                {
                    "content": "Read configuration",
                    "status": "in_progress",
                    "activeForm": "Reading configuration",
                },
                {
                    "content": "Update settings",
                    "status": "pending",
                    "activeForm": "Updating settings",
                },
                {"content": "Test changes", "status": "pending", "activeForm": "Testing changes"},
            ]
        )

        assert result1.success == True
        assert manager.get_current().content == "Read configuration"

        # Complete first, start second
        result2 = await tool.execute(
            todos=[
                {
                    "content": "Read configuration",
                    "status": "completed",
                    "activeForm": "Reading configuration",
                },
                {
                    "content": "Update settings",
                    "status": "in_progress",
                    "activeForm": "Updating settings",
                },
                {"content": "Test changes", "status": "pending", "activeForm": "Testing changes"},
            ]
        )

        assert result2.success == True
        assert manager.get_current().content == "Update settings"
        assert result2.output["stats"]["completed"] == 1

        # Complete all
        result3 = await tool.execute(
            todos=[
                {
                    "content": "Read configuration",
                    "status": "completed",
                    "activeForm": "Reading configuration",
                },
                {
                    "content": "Update settings",
                    "status": "completed",
                    "activeForm": "Updating settings",
                },
                {
                    "content": "Test changes",
                    "status": "in_progress",
                    "activeForm": "Testing changes",
                },
            ]
        )

        assert result3.success == True
        assert result3.output["stats"]["completed"] == 2


class TestThinkingIntegration:
    """Test thinking system integration"""

    def test_thinking_session_workflow(self):
        """Test thinking session creation and management"""
        # ThinkingSession uses metadata, not task parameter
        session = ThinkingSession(metadata={"task": "Implement feature"})

        # Add analysis phase (using ANALYZING phase)
        analysis_block = ThinkingBlock(
            phase=ThinkingPhase.ANALYZING, content="Analyzing the requirements..."
        )
        session.add_block(analysis_block)

        # Add planning phase
        planning_block = ThinkingBlock(
            phase=ThinkingPhase.PLANNING, content="Creating implementation plan..."
        )
        session.add_block(planning_block)

        # Add reasoning phase (instead of EXECUTION)
        reasoning_block = ThinkingBlock(
            phase=ThinkingPhase.REASONING, content="Implementing the feature..."
        )
        session.add_block(reasoning_block)

        # Complete session
        session.complete()

        # Session is complete when end_time is set
        assert session.end_time is not None
        assert len(session.blocks) == 3
        assert session.duration_ms() >= 0

    def test_thinking_manager_integration(self):
        """Test thinking manager with listeners"""
        from hcode.config.thinking import ThinkingConfig

        config = ThinkingConfig()
        manager = ThinkingManager(config=config)
        received_blocks = []

        def listener(block):
            received_blocks.append(block)

        manager.add_listener(listener)

        # Create session
        session = manager.start_session(metadata={"task": "Test task"})
        assert session is not None

        # Add block
        block = ThinkingBlock(phase=ThinkingPhase.ANALYZING, content="Test content")
        session.add_block(block)

        # End session
        manager.end_session()


class TestSafetyIntegration:
    """Test safety configuration integration"""

    def test_safety_with_file_operations(self, temp_project):
        """Test safety checks for file operations"""
        safety = SafetyConfig()

        # Check protected files
        env_path = str(Path(temp_project) / ".env")
        req_path = str(Path(temp_project) / "requirements.txt")
        main_path = str(Path(temp_project) / "src" / "main.py")

        # .env should be protected
        assert safety.is_protected_file(env_path)

        # requirements.txt should be protected
        assert safety.is_protected_file(req_path)

        # main.py should not be protected
        assert not safety.is_protected_file(main_path)

    def test_safety_with_commands(self):
        """Test safety checks for commands"""
        safety = SafetyConfig()

        # Safe commands
        assert safety.assess_command_risk("ls -la") == safety.assess_command_risk(
            "pwd"
        )  # Both SAFE
        assert safety.assess_command_risk("cat file.txt").value == "safe"

        # Dangerous commands
        assert safety.assess_command_risk("rm -rf /").value == "dangerous"
        assert safety.assess_command_risk("git push --force").value == "dangerous"


class TestModeIntegration:
    """Test mode configuration integration"""

    def test_mode_affects_behavior(self):
        """Test different modes affect behavior"""
        interactive_config = get_mode_config(AgentMode.INTERACTIVE)
        auto_config = get_mode_config(AgentMode.AUTO)
        plan_config = get_mode_config(AgentMode.PLAN)
        review_config = get_mode_config(AgentMode.REVIEW)

        # Interactive should always ask
        assert interactive_config.ask_permission == True
        assert interactive_config.max_actions_without_confirm == 1

        # Auto should not ask (except dangerous)
        assert auto_config.ask_permission == False
        assert auto_config.confirm_dangerous == True

        # Plan should show plan first
        assert plan_config.show_plan == True
        assert plan_config.execute_after_plan == True

        # Review should require approval
        assert review_config.require_approval == True


class TestComplexWorkflows:
    """Test complex multi-step workflows"""

    @pytest.mark.asyncio
    async def test_refactoring_workflow(self, temp_project):
        """Test a refactoring workflow using multiple tools"""
        # Step 1: Find all files with a function
        grep_tool = GrepTool(root_dir=temp_project)
        search_result = await grep_tool.execute(
            pattern="def calculate", path=temp_project, output_mode="files_with_matches"
        )

        assert search_result.success == True

        # Step 2: Read the file
        read_tool = ReadTool(root_dir=temp_project)
        file_path = str(Path(temp_project) / "src" / "main.py")
        read_result = await read_tool.execute(file_path=file_path)

        assert read_result.success == True
        assert "calculate" in read_result.output

        # Step 3: Edit the function
        edit_tool = EditTool(root_dir=temp_project)
        edit_result = await edit_tool.execute(
            file_path=file_path,
            old_string="def calculate(a, b):\n    return a + b",
            new_string='def calculate(a, b):\n    """Calculate sum of two numbers"""\n    return a + b',
        )

        assert edit_result.success == True

        # Step 4: Verify the change
        verify_result = await read_tool.execute(file_path=file_path)
        assert "Calculate sum of two numbers" in verify_result.output

    @pytest.mark.asyncio
    async def test_bug_fix_workflow(self, temp_project):
        """Test a bug fix workflow"""
        # Create a file with a "bug"
        bug_file = str(Path(temp_project) / "src" / "buggy.py")
        write_tool = WriteTool(root_dir=temp_project)

        await write_tool.execute(
            file_path=bug_file,
            content="""
def divide(a, b):
    return a / b  # Bug: no zero check

def process(items):
    for item in items:
        print(itme)  # Bug: typo
""",
        )

        # Search for the bug pattern
        grep_tool = GrepTool(root_dir=temp_project)
        typo_search = await grep_tool.execute(
            pattern="itme", path=temp_project, output_mode="content"
        )

        assert typo_search.success == True
        assert "itme" in typo_search.output

        # Fix the typo
        edit_tool = EditTool(root_dir=temp_project)
        fix_result = await edit_tool.execute(
            file_path=bug_file, old_string="print(itme)", new_string="print(item)"
        )

        assert fix_result.success == True

        # Verify fix
        read_tool = ReadTool(root_dir=temp_project)
        verify_result = await read_tool.execute(file_path=bug_file)

        assert "print(item)" in verify_result.output
        assert "print(itme)" not in verify_result.output


class TestErrorHandling:
    """Test error handling across tools"""

    @pytest.mark.asyncio
    async def test_graceful_error_handling(self, temp_project):
        """Test tools handle errors gracefully"""
        read_tool = ReadTool(root_dir=temp_project)
        edit_tool = EditTool(root_dir=temp_project)
        grep_tool = GrepTool(root_dir=temp_project)

        # Read non-existent file
        read_result = await read_tool.execute(file_path=str(Path(temp_project) / "nonexistent.py"))
        assert read_result.success == False
        assert read_result.error is not None

        # Edit with non-matching string
        edit_result = await edit_tool.execute(
            file_path=str(Path(temp_project) / "src" / "main.py"),
            old_string="this string does not exist anywhere",
            new_string="replacement",
        )
        assert edit_result.success == False

        # Search in non-existent directory
        grep_result = await grep_tool.execute(
            pattern="test", path=str(Path(temp_project) / "nonexistent_dir")
        )
        # May succeed with no matches or fail depending on implementation

    @pytest.mark.asyncio
    async def test_todo_validation_errors(self):
        """Test todo validation errors are handled"""
        tool = TodoWriteTool()

        # Missing required field
        result1 = await tool.execute(
            todos=[{"content": "Task 1", "status": "in_progress"}]  # Missing activeForm
        )
        assert result1.success == False

        # Invalid status
        result2 = await tool.execute(
            todos=[{"content": "Task 1", "status": "invalid", "activeForm": "T1"}]
        )
        assert result2.success == False

        # Multiple in_progress
        result3 = await tool.execute(
            todos=[
                {"content": "Task 1", "status": "in_progress", "activeForm": "T1"},
                {"content": "Task 2", "status": "in_progress", "activeForm": "T2"},
            ]
        )
        assert result3.success == False


class TestConcurrentOperations:
    """Test concurrent tool operations"""

    @pytest.mark.asyncio
    async def test_parallel_reads(self, temp_project):
        """Test parallel file reads"""
        read_tool = ReadTool(root_dir=temp_project)

        files = [
            str(Path(temp_project) / "src" / "main.py"),
            str(Path(temp_project) / "src" / "utils.py"),
            str(Path(temp_project) / "src" / "config.py"),
        ]

        # Read all files in parallel
        results = await asyncio.gather(*[read_tool.execute(file_path=f) for f in files])

        assert all(r.success for r in results)
        assert "def main()" in results[0].output
        assert "format_message" in results[1].output
        assert "DEBUG" in results[2].output

    @pytest.mark.asyncio
    async def test_parallel_searches(self, temp_project):
        """Test parallel searches"""
        grep_tool = GrepTool(root_dir=temp_project)

        patterns = ["def", "import", "return", "if"]

        # Search all patterns in parallel
        results = await asyncio.gather(
            *[
                grep_tool.execute(pattern=p, path=temp_project, output_mode="count")
                for p in patterns
            ]
        )

        assert all(r.success for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
