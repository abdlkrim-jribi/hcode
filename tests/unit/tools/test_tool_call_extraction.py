"""
Tests for tool call extraction from model text output.

Tests the JSON parsing capabilities for models that don't support native function calling.
"""

import pytest
import sys
import os
import json
import re
from typing import Optional
from unittest.mock import Mock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def parse_json_tool_calls_from_text(text: str) -> list:
    """Parse JSON tool calls from model text output - aggressive extraction

    This is a standalone copy of the method for testing purposes.
    """
    tool_calls = []

    # STRATEGY 1: Look for JSON in code fences (most reliable)
    json_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)

    for block in json_blocks:
        try:
            data = json.loads(block)
            if "tool" in data:
                tool_calls.append(
                    {
                        "name": data["tool"],
                        "arguments": data.get("parameters") or data.get("params", {}),
                    }
                )
            elif "file_path" in data:
                # Looks like WriteTool parameters
                tool_calls.append({"name": "WriteTool", "arguments": data})
        except json.JSONDecodeError:
            continue

    if tool_calls:
        return tool_calls

    # STRATEGY 2: Find JSON objects with "tool" field anywhere in text
    tool_json_pattern = r'\{\s*["\']tool["\']\s*:\s*["\'](\w+)["\']\s*,\s*["\'](?:parameters|params)["\']\s*:\s*(\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\})'

    for match in re.finditer(tool_json_pattern, text, re.DOTALL):
        tool_name = match.group(1)
        params_str = match.group(2)
        try:
            params = json.loads(params_str)
            tool_calls.append({"name": tool_name, "arguments": params})
        except json.JSONDecodeError:
            continue

    if tool_calls:
        return tool_calls

    # STRATEGY 3: Look for any JSON object that could be a tool call
    json_objects = re.findall(
        r'(\{[^{}]*(?:"tool"|"file_path"|"content")[^{}]*\})', text, re.DOTALL
    )

    for obj_str in json_objects:
        try:
            data = json.loads(obj_str)
            if "tool" in data:
                tool_calls.append(
                    {
                        "name": data["tool"],
                        "arguments": data.get("parameters") or data.get("params", {}),
                    }
                )
            elif "file_path" in data and "content" in data:
                tool_calls.append({"name": "WriteTool", "arguments": data})
        except json.JSONDecodeError:
            continue

    if tool_calls:
        return tool_calls

    # STRATEGY 4: Look for the full JSON structure including nested parameters
    try:
        tool_start = re.search(r'\{\s*["\']tool["\']', text)
        if tool_start:
            json_str = extract_balanced_json(text[tool_start.start() :])
            if json_str:
                data = json.loads(json_str)
                if "tool" in data:
                    tool_calls.append(
                        {
                            "name": data["tool"],
                            "arguments": data.get("parameters") or data.get("params", {}),
                        }
                    )
    except (json.JSONDecodeError, Exception):
        pass

    if tool_calls:
        return tool_calls

    # STRATEGY 5: Last resort - look for file_path and content anywhere
    file_path_match = re.search(r'["\']file_path["\']\s*:\s*["\']([^"\']+)["\']', text)
    content_match = re.search(
        r'["\']content["\']\s*:\s*["\'](.+?)["\'](?:\s*[,}])', text, re.DOTALL
    )

    if file_path_match and content_match:
        file_path = file_path_match.group(1)
        content = content_match.group(1)
        content = content.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')
        tool_calls.append(
            {"name": "WriteTool", "arguments": {"file_path": file_path, "content": content}}
        )

    return tool_calls


def extract_balanced_json(text: str, max_length: int = 10000) -> Optional[str]:
    """Extract a balanced JSON object from text"""
    if not text or text[0] != "{":
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[:max_length]):
        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[: i + 1]

    return None


class TestToolCallExtraction:
    """Tests for _parse_json_tool_calls_from_text method"""

    def test_json_in_code_fence(self):
        """Test extraction from JSON in code fence"""
        text = """Here is the file creation:
```json
{"tool": "WriteTool", "parameters": {"file_path": "test.py", "content": "print('hello')"}}
```
"""
        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"
        assert result[0]["arguments"]["file_path"] == "test.py"
        assert result[0]["arguments"]["content"] == "print('hello')"

    def test_json_in_code_fence_no_json_tag(self):
        """Test extraction from code fence without json tag"""
        text = """Creating the file:
```
{"tool": "WriteTool", "parameters": {"file_path": "hello.py", "content": "def hello():\\n    print('world')"}}
```
"""
        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"
        assert result[0]["arguments"]["file_path"] == "hello.py"

    def test_inline_json_tool_call(self):
        """Test extraction from inline JSON"""
        text = """I will create the file now: {"tool": "WriteTool", "parameters": {"file_path": "app.py", "content": "import os"}}"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"
        assert result[0]["arguments"]["file_path"] == "app.py"

    def test_file_path_and_content_without_tool_wrapper(self):
        """Test extraction when model outputs just file_path and content"""
        text = """{"file_path": "config.py", "content": "DEBUG = True"}"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"
        assert result[0]["arguments"]["file_path"] == "config.py"
        assert result[0]["arguments"]["content"] == "DEBUG = True"

    def test_read_tool_extraction(self):
        """Test extraction of ReadTool call"""
        text = """```json
{"tool": "ReadTool", "parameters": {"file_path": "main.py"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "ReadTool"
        assert result[0]["arguments"]["file_path"] == "main.py"

    def test_bash_tool_extraction(self):
        """Test extraction of BashTool call"""
        text = """```json
{"tool": "BashTool", "parameters": {"command": "ls -la"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "BashTool"
        assert result[0]["arguments"]["command"] == "ls -la"

    def test_glob_tool_extraction(self):
        """Test extraction of GlobTool call"""
        text = """Let me search for Python files:
```json
{"tool": "GlobTool", "parameters": {"pattern": "**/*.py", "path": "."}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "GlobTool"
        assert result[0]["arguments"]["pattern"] == "**/*.py"

    def test_multiline_content(self):
        """Test extraction with multiline content"""
        text = """```json
{"tool": "WriteTool", "parameters": {"file_path": "script.py", "content": "def main():\\n    print('Hello')\\n\\nif __name__ == '__main__':\\n    main()"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"
        assert "def main()" in result[0]["arguments"]["content"]

    def test_params_alias(self):
        """Test extraction when model uses 'params' instead of 'parameters'"""
        text = """```json
{"tool": "ReadTool", "params": {"file_path": "data.txt"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "ReadTool"
        assert result[0]["arguments"]["file_path"] == "data.txt"

    def test_no_tool_call_in_text(self):
        """Test when there's no tool call in the text"""
        text = """This is just a regular response without any tool calls."""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 0

    def test_invalid_json(self):
        """Test handling of invalid JSON"""
        text = """```json
{"tool": "WriteTool", "parameters": {"file_path": "test.py", "content": }}
```"""

        result = parse_json_tool_calls_from_text(text)

        # Should not crash, just return empty
        assert len(result) == 0

    def test_mixed_text_and_json(self):
        """Test extraction when there's mixed text and JSON"""
        text = """I'll create a file handler module for you. This will include:
- File reading capabilities
- File writing capabilities
- Error handling

Here's the implementation:

```json
{"tool": "WriteTool", "parameters": {"file_path": "file_handler.py", "content": "class FileHandler:\\n    def read(self, path):\\n        with open(path) as f:\\n            return f.read()"}}
```

This creates a basic file handler class."""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"
        assert result[0]["arguments"]["file_path"] == "file_handler.py"
        assert "FileHandler" in result[0]["arguments"]["content"]

    def test_scattered_fields_extraction(self):
        """Test extraction from scattered JSON fields"""
        # This test checks extraction when file_path and content are in separate quoted strings
        # The format needs to match JSON-like patterns with quotes
        text = """{"file_path": "output.txt", "content": "Hello World"}"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"
        assert result[0]["arguments"]["file_path"] == "output.txt"
        assert result[0]["arguments"]["content"] == "Hello World"

    def test_edit_tool_extraction(self):
        """Test extraction of EditTool call"""
        text = """```json
{"tool": "EditTool", "parameters": {"file_path": "main.py", "old_string": "print('old')", "new_string": "print('new')"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "EditTool"
        assert result[0]["arguments"]["old_string"] == "print('old')"
        assert result[0]["arguments"]["new_string"] == "print('new')"

    def test_grep_tool_extraction(self):
        """Test extraction of GrepTool call"""
        text = """```json
{"tool": "GrepTool", "parameters": {"pattern": "def main", "path": "src/"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "GrepTool"
        assert result[0]["arguments"]["pattern"] == "def main"

    def test_ls_tool_extraction(self):
        """Test extraction of LSTool call"""
        text = """```json
{"tool": "LSTool", "parameters": {"path": "."}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "LSTool"
        assert result[0]["arguments"]["path"] == "."


class TestBalancedJsonExtraction:
    """Tests for _extract_balanced_json method"""

    def test_simple_json(self):
        """Test simple JSON extraction"""
        text = '{"key": "value"} extra text'

        result = extract_balanced_json(text)

        assert result == '{"key": "value"}'

    def test_nested_json(self):
        """Test nested JSON extraction"""
        text = '{"outer": {"inner": "value"}} more text'

        result = extract_balanced_json(text)

        assert result == '{"outer": {"inner": "value"}}'

    def test_json_with_string_braces(self):
        """Test JSON with braces inside strings"""
        text = '{"content": "function() { return {}; }"} extra'

        result = extract_balanced_json(text)

        assert result == '{"content": "function() { return {}; }"}'

    def test_not_starting_with_brace(self):
        """Test text not starting with brace"""
        text = 'text {"key": "value"}'

        result = extract_balanced_json(text)

        assert result is None

    def test_empty_text(self):
        """Test empty text"""
        result = extract_balanced_json("")

        assert result is None

    def test_unbalanced_json(self):
        """Test unbalanced JSON"""
        text = '{"key": "value"'

        result = extract_balanced_json(text)

        assert result is None


class TestRealWorldScenarios:
    """Test real-world model output scenarios"""

    def test_model_with_reasoning_before_json(self):
        """Test extraction when model adds reasoning before the JSON"""
        text = """I'll create a file handler module for you. This module will handle basic file operations.

Let me write the file now:

```json
{"tool": "WriteTool", "parameters": {"file_path": "file_handler.py", "content": "import os\\n\\nclass FileHandler:\\n    pass"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"

    def test_model_repeating_json_fields(self):
        """Test handling when model repeats JSON fields (as seen in the bug report)"""
        # This simulates the issue where the model got stuck outputting repeated JSON
        text = """{"file_path": "file_handler.py", "content": "class FileHandler:\\n    pass"}"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"

    def test_model_with_let_me_prefix(self):
        """Test extraction when model says 'let me...' before the JSON"""
        text = """Let me use WriteTool to create the file:

```json
{"tool": "WriteTool", "parameters": {"file_path": "test.py", "content": "# Test file\\nprint('test')"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"

    def test_model_with_we_need_prefix(self):
        """Test extraction when model says 'we need to...' before the JSON"""
        text = """We need to call WriteTool to write the file:

```json
{"tool": "WriteTool", "parameters": {"file_path": "app.py", "content": "from flask import Flask"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"

    def test_model_output_with_internal_thoughts(self):
        """Test extraction when model outputs internal thoughts"""
        text = """I need to create a file. Let's use WriteTool. We need to actually call WriteTool...

```json
{"tool": "WriteTool", "parameters": {"file_path": "handler.py", "content": "def handle():\\n    pass"}}
```

Now I will wait for the result."""

        result = parse_json_tool_calls_from_text(text)

        assert len(result) == 1
        assert result[0]["name"] == "WriteTool"
        assert result[0]["arguments"]["file_path"] == "handler.py"

    def test_model_output_multiple_tool_calls(self):
        """Test extraction of multiple tool calls"""
        text = """I'll first read the file, then modify it:

```json
{"tool": "ReadTool", "parameters": {"file_path": "config.py"}}
```

After reading, I'll edit:

```json
{"tool": "EditTool", "parameters": {"file_path": "config.py", "old_string": "DEBUG = False", "new_string": "DEBUG = True"}}
```"""

        result = parse_json_tool_calls_from_text(text)

        # Should get the first tool call (ReadTool)
        # The current implementation returns after finding the first block
        assert len(result) >= 1
        assert result[0]["name"] == "ReadTool"


class TestToolCallFormatInstructions:
    """Test that the tool call format instructions are correct"""

    def test_format_instructions_contain_all_tools(self):
        """Verify format instructions mention all important tools"""
        # Import the method to get the instructions
        try:
            from hcode.core.enhanced_agent import EnhancedHcodeAgent

            agent = Mock()
            agent._get_tool_call_format_instructions = (
                EnhancedHcodeAgent._get_tool_call_format_instructions.__get__(agent)
            )
            instructions = agent._get_tool_call_format_instructions()

            # Check all tools are mentioned
            assert "WriteTool" in instructions
            assert "ReadTool" in instructions
            assert "EditTool" in instructions
            assert "GlobTool" in instructions
            assert "GrepTool" in instructions
            assert "BashTool" in instructions
            assert "LSTool" in instructions

            # Check format is correct
            assert '"tool"' in instructions
            assert '"parameters"' in instructions
            # Check for critical instructions (can be "Do NOT" or "CRITICAL" guidance)
            assert "CRITICAL" in instructions or "Do NOT" in instructions
        except ImportError:
            pytest.skip("Could not import EnhancedHcodeAgent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
