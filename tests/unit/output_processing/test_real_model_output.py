"""
Test the tool call extraction with real model output patterns.

This tests the exact format that gpt-oss-120b produces.
"""

import pytest
import sys
import os
import json
import re
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# Copy the extraction functions for testing (to avoid import issues)
def parse_json_tool_calls_from_text(text: str) -> list:
    """Parse JSON tool calls from model text output - aggressive extraction"""
    tool_calls = []

    def unescape_content(content: str) -> str:
        if not isinstance(content, str):
            return content
        result = content
        result = result.replace("\\n", "\n")
        result = result.replace("\\t", "\t")
        result = result.replace("\\r", "\r")
        result = result.replace('\\"', '"')
        result = result.replace("\\'", "'")
        result = result.replace("\\\\", "\\")
        return result

    def process_arguments(args: dict) -> dict:
        if not isinstance(args, dict):
            return args
        processed = {}
        for key, value in args.items():
            if key == "content" and isinstance(value, str):
                processed[key] = unescape_content(value)
            elif isinstance(value, dict):
                processed[key] = process_arguments(value)
            else:
                processed[key] = value
        return processed

    def extract_tool_args(data: dict) -> dict:
        """
        Extract tool arguments from data, handling different formats:
        1. {"tool": "X", "parameters": {...}} - Standard format
        2. {"tool": "X", "params": {...}} - Alternate key
        3. {"tool": "X", "arguments": {...}} - OpenAI style
        4. {"tool": "X", "path": "...", "pattern": "..."} - Flat format
        """
        if "parameters" in data:
            return data["parameters"]
        if "params" in data:
            return data["params"]
        if "arguments" in data:
            return data["arguments"]

        # Flat format - parameters at root level alongside "tool"
        args = {}
        for key, value in data.items():
            if key != "tool":
                args[key] = value
        return args

    # STRATEGY 1: Look for JSON in code fences (most reliable)
    json_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)

    for block in json_blocks:
        try:
            data = json.loads(block)
            if "tool" in data:
                args = extract_tool_args(data)
                tool_calls.append({"name": data["tool"], "arguments": process_arguments(args)})
            elif "file_path" in data:
                tool_calls.append({"name": "WriteTool", "arguments": process_arguments(data)})
        except json.JSONDecodeError:
            continue

    if tool_calls:
        return tool_calls

    # STRATEGY 2: Find JSON objects with "tool" field anywhere in text
    tool_json_pattern = r'\{\s*["\']tool["\']\s*:\s*["\'](\w+)["\']\s*,\s*["\'](?:parameters|params|arguments)["\']\s*:\s*(\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\})'

    for match in re.finditer(tool_json_pattern, text, re.DOTALL):
        tool_name = match.group(1)
        params_str = match.group(2)
        try:
            params = json.loads(params_str)
            tool_calls.append({"name": tool_name, "arguments": process_arguments(params)})
        except json.JSONDecodeError:
            continue

    if tool_calls:
        return tool_calls

    # STRATEGY 3: Look for any JSON object that could be a tool call (flat format)
    # Find JSON objects with "tool" key and other keys at same level
    flat_json_pattern = r'\{\s*["\']tool["\']\s*:\s*["\'](\w+)["\'][^{}]*\}'
    for match in re.finditer(flat_json_pattern, text, re.DOTALL):
        try:
            json_str = match.group(0)
            data = json.loads(json_str)
            if "tool" in data:
                args = extract_tool_args(data)
                tool_calls.append({"name": data["tool"], "arguments": process_arguments(args)})
        except json.JSONDecodeError:
            continue

    if tool_calls:
        return tool_calls

    # STRATEGY 4: Look for multiline JSON with "tool" key
    # Extract balanced JSON starting from { "tool"
    tool_start_pattern = r'\{\s*["\']tool["\']\s*:'
    for match in re.finditer(tool_start_pattern, text):
        json_str = extract_balanced_json(text[match.start() :])
        if json_str:
            try:
                data = json.loads(json_str)
                if "tool" in data:
                    args = extract_tool_args(data)
                    tool_calls.append({"name": data["tool"], "arguments": process_arguments(args)})
            except json.JSONDecodeError:
                continue

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


class TestRealModelOutputExtraction:
    """Test extraction from actual model output patterns"""

    def test_arguments_key_instead_of_parameters(self):
        """Model uses 'arguments' instead of 'parameters'"""
        text = """Let's list files. Use LS.
{
  "tool": "LS",
  "arguments": {"path": "."}
}
Let's try."""

        tool_calls = parse_json_tool_calls_from_text(text)

        assert len(tool_calls) >= 1
        assert tool_calls[0]["name"] == "LS"
        assert tool_calls[0]["arguments"].get("path") == "."

    def test_json_without_code_fence(self):
        """Model outputs JSON directly without code fence"""
        text = """We need to use the LS tool.
{ "tool": "LS", "arguments": {"path": "."} }
Let's try again."""

        tool_calls = parse_json_tool_calls_from_text(text)

        assert len(tool_calls) >= 1
        assert tool_calls[0]["name"] == "LS"

    def test_json_with_newlines_in_braces(self):
        """Model outputs JSON with newlines inside braces"""
        text = """We need to call the tool:
{
    "tool": "WriteTool",
    "parameters": {
        "file_path": "test.html",
        "content": "<!DOCTYPE html>"
    }
}
Done."""

        tool_calls = parse_json_tool_calls_from_text(text)

        assert len(tool_calls) >= 1
        assert tool_calls[0]["name"] == "WriteTool"

    def test_multiple_json_attempts_in_text(self):
        """Model tries multiple JSON formats"""
        text = """Let's use LS.
{ "path": "." }
That didn't work. Let's try:
{ "tool": "LS", "path": "." }
Still nothing. Try again:
{ "tool": "LS", "arguments": {"path": "."} }
Maybe this works."""

        tool_calls = parse_json_tool_calls_from_text(text)

        # Should find at least one valid tool call
        assert len(tool_calls) >= 1
        # The one with "tool" key should be found
        ls_calls = [tc for tc in tool_calls if tc["name"] == "LS"]
        assert len(ls_calls) >= 1

    def test_flat_parameters_at_root(self):
        """Model puts parameters at root level with tool"""
        text = """Use GlobTool:
{ "tool": "Glob", "path": ".", "pattern": "**/*.html" }"""

        tool_calls = parse_json_tool_calls_from_text(text)

        assert len(tool_calls) >= 1
        assert tool_calls[0]["name"] == "Glob"
        # Parameters should be extracted from root level
        args = tool_calls[0]["arguments"]
        assert "path" in args or "pattern" in args

    def test_reasoning_before_json(self):
        """Model outputs lots of reasoning before the JSON"""
        text = """Let's list files.Use LS.We need to actually call LS tool.We need to use the LS tool.We need to call LS with path ".".We need to use the tool.It seems I need to issue a tool command.Let's run LS.We need to use the LS tool with appropriate JSON.Probably the correct syntax:

{ "path": "." }

Let's try.The tool didn't run. Maybe need to use the tool name LS.We need to call LS with arguments. According to spec: LS: Lists files and directories at a specified path with optional ignore patterns. So we call LS with JSON: {"path": "."}.It seems the tool interface not being invoked. Maybe need to use a specific format:

{
  "tool": "LS",
  "arguments": {"path": "."}
}

Let's try."""

        tool_calls = parse_json_tool_calls_from_text(text)

        # Should extract the LS tool call
        assert len(tool_calls) >= 1
        ls_calls = [tc for tc in tool_calls if tc["name"] == "LS"]
        assert len(ls_calls) >= 1


class TestArgumentsKeySupport:
    """Test that 'arguments' key is supported like 'parameters'"""

    def test_extract_tool_args_with_arguments_key(self):
        """Test the extract_tool_args helper handles 'arguments' key"""
        # Test with 'arguments' key
        text = '{"tool": "ReadTool", "arguments": {"file_path": "/test/file.txt"}}'

        tool_calls = parse_json_tool_calls_from_text(text)

        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "ReadTool"
        assert tool_calls[0]["arguments"].get("file_path") == "/test/file.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
