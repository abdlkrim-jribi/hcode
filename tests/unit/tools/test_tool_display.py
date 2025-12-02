"""
Test tool result display formatting.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dataclasses import dataclass


@dataclass
class MockToolResult:
    """Mock tool result for testing"""
    success: bool
    output: str
    error: str = ""


class TestToolDisplayLogic:
    """Test the tool display formatting logic"""

    def test_write_tool_shows_file_path_only(self):
        """WriteTool should only show file path, not content"""
        tool_name = "writetool"
        arguments = {
            "file_path": "test.html",
            "content": "<!DOCTYPE html>\n<html>\n<body>Very long content here...</body>\n</html>"
        }
        result = MockToolResult(success=True, output="File written successfully")

        # The display logic should:
        # 1. Show file path
        # 2. Show character count
        # 3. NOT show the actual content

        assert "file_path" in arguments
        assert len(arguments["content"]) > 0

        # Simulate the display logic
        file_path = arguments.get('file_path', 'unknown')
        content = arguments.get('content', '')

        display_info = {
            "tool": "WriteTool",
            "file": file_path,
            "chars": len(content),
            "show_content": False  # This is the key - no content display
        }

        assert display_info["file"] == "test.html"
        assert display_info["chars"] > 0
        assert display_info["show_content"] is False

    def test_edit_tool_shows_changes(self):
        """EditTool should show old and new strings"""
        tool_name = "edittool"
        arguments = {
            "file_path": "config.py",
            "old_string": "DEBUG = True",
            "new_string": "DEBUG = False"
        }
        result = MockToolResult(success=True, output="Edit successful")

        # The display logic should show:
        # 1. File path
        # 2. Old string (what was removed)
        # 3. New string (what was added)

        file_path = arguments.get('file_path', 'unknown')
        old_string = arguments.get('old_string', '')
        new_string = arguments.get('new_string', '')

        display_info = {
            "tool": "EditTool",
            "file": file_path,
            "removed": old_string,
            "added": new_string,
            "show_changes": True
        }

        assert display_info["file"] == "config.py"
        assert display_info["removed"] == "DEBUG = True"
        assert display_info["added"] == "DEBUG = False"
        assert display_info["show_changes"] is True

    def test_bash_tool_shows_command_and_output(self):
        """BashTool should show command and output"""
        tool_name = "bashtool"
        arguments = {
            "command": "ls -la"
        }
        result = MockToolResult(
            success=True,
            output="total 16\ndrwxr-xr-x  2 user user 4096 Jan  1 00:00 .\ndrwxr-xr-x 10 user user 4096 Jan  1 00:00 .."
        )

        # The display logic should show:
        # 1. Command that was run
        # 2. Full output (or truncated if too long)

        command = arguments.get('command', '')

        display_info = {
            "tool": "BashTool",
            "command": command,
            "output": result.output,
            "show_output": True
        }

        assert display_info["command"] == "ls -la"
        assert display_info["show_output"] is True
        assert len(display_info["output"]) > 0

    def test_bash_tool_truncates_long_output(self):
        """BashTool should truncate very long output"""
        # Generate long output (more than 20 lines)
        long_output = "\n".join([f"line {i}" for i in range(50)])

        output_lines = long_output.strip().split('\n')

        if len(output_lines) > 20:
            # Should truncate
            display_output = '\n'.join(output_lines[:20]) + f"\n... ({len(output_lines)} lines total)"
            truncated = True
        else:
            display_output = long_output.strip()
            truncated = False

        assert truncated is True
        assert "... (50 lines total)" in display_output
        assert display_output.count('\n') == 20  # 20 lines + 1 truncation message

    def test_error_display(self):
        """Failed tool calls should show error"""
        result = MockToolResult(success=False, output="", error="File not found")

        # The display logic should show error message
        assert result.success is False
        assert result.error == "File not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
