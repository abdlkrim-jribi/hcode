"""
Property-based tests for tool call extraction.

Task #18: Add property-based tests for tool call extraction

Uses hypothesis to generate edge cases and validate that the tool call
extraction parser handles malformed JSON, nested objects, and various
formats gracefully without crashing.
"""

import pytest
import json
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hcode.core.phases.base_handler import BasePhaseHandler


class TestToolCallExtraction:
    """Property-based tests for _extract_tool_calls method."""

    @pytest.fixture
    def handler(self):
        """Create a minimal base handler for testing."""
        handler = BasePhaseHandler(
            artifact_manager=None,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )
        handler.phase_name = "test"
        return handler

    def test_extract_valid_tool_call(self, handler):
        """Test extraction of a valid tool call."""
        response = '''
<thinking>I need to read a file</thinking>

```json
{"tool": "Read", "arguments": {"TargetFile": "test.py"}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Read"
        assert tool_calls[0]["arguments"]["TargetFile"] == "test.py"

    def test_extract_multiple_tool_calls(self, handler):
        """Test extraction of multiple tool calls in one response."""
        response = '''
<output>Creating files</output>

```json
{"tool": "Write", "arguments": {"TargetFile": "a.py", "Content": "pass"}}
```

```json
{"tool": "Write", "arguments": {"TargetFile": "b.py", "Content": "pass"}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 2
        assert tool_calls[0]["tool"] == "Write"
        assert tool_calls[1]["tool"] == "Write"
        assert tool_calls[0]["arguments"]["TargetFile"] == "a.py"
        assert tool_calls[1]["arguments"]["TargetFile"] == "b.py"

    def test_extract_tool_call_with_parameters_alias(self, handler):
        """Test extraction when using 'parameters' instead of 'arguments'."""
        response = '''
```json
{"tool": "Read", "parameters": {"TargetFile": "test.py"}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Read"
        # Should normalize 'parameters' to 'arguments'
        assert tool_calls[0]["arguments"]["TargetFile"] == "test.py"

    def test_extract_malformed_json_no_crash(self, handler):
        """Test that malformed JSON doesn't crash the parser."""
        malformed_responses = [
            '```json\n{"tool": "Read", "arguments": {invalid}}\n```',
            '```json\n{"tool": "Read",}\n```',  # Trailing comma
            '```json\n{"tool": }\n```',  # Incomplete
            '```json\n{tool: "Read"}\n```',  # No quotes
            '```json\n"tool": "Read"\n```',  # Missing braces
            '```json\n{"tool": "Read" "arguments": {}}\n```',  # Missing comma
        ]

        for response in malformed_responses:
            # Should not crash, just return empty list
            tool_calls = handler._extract_tool_calls(response)
            assert isinstance(tool_calls, list)
            # May or may not extract anything, but shouldn't crash

    def test_extract_missing_tool_field(self, handler):
        """Test extraction when 'tool' field is missing."""
        response = '''
```json
{"arguments": {"TargetFile": "test.py"}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        # Should return empty list when 'tool' field is missing
        assert len(tool_calls) == 0

    def test_extract_nested_json_in_arguments(self, handler):
        """Test extraction with nested JSON objects in arguments."""
        response = '''
```json
{
  "tool": "ComplexTool",
  "arguments": {
    "config": {
      "nested": {
        "value": 123
      }
    },
    "simple": "value"
  }
}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "ComplexTool"
        assert tool_calls[0]["arguments"]["config"]["nested"]["value"] == 123
        assert tool_calls[0]["arguments"]["simple"] == "value"

    def test_extract_without_code_block_markers(self, handler):
        """Test extraction of inline JSON without code blocks."""
        response = 'Here is the tool call: {"tool": "Read", "arguments": {"TargetFile": "test.py"}}'

        tool_calls = handler._extract_tool_calls(response)

        # Should fall back to inline extraction
        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Read"

    def test_extract_with_json_code_block_label(self, handler):
        """Test extraction with explicit 'json' code block label."""
        response = '''
```json
{"tool": "Read", "arguments": {"TargetFile": "test.py"}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Read"

    def test_extract_with_no_code_block_label(self, handler):
        """Test extraction with no code block label."""
        response = '''
```
{"tool": "Read", "arguments": {"TargetFile": "test.py"}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Read"

    def test_extract_ignores_non_json_code_blocks(self, handler):
        """Test that non-JSON code blocks are ignored."""
        response = '''
```python
def foo():
    pass
```

```json
{"tool": "Read", "arguments": {"TargetFile": "test.py"}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        # Should only extract the JSON block
        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Read"

    def test_extract_empty_response(self, handler):
        """Test extraction from empty response."""
        tool_calls = handler._extract_tool_calls("")
        assert tool_calls == []

    def test_extract_none_response(self, handler):
        """Test extraction from None response."""
        tool_calls = handler._extract_tool_calls(None)
        assert tool_calls == []

    @settings(
        max_examples=50,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        tool_name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        file_path=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.one_of(
                st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
                st.sampled_from(['/', '.', '_', '-'])
            )
        ),
    )
    def test_extract_property_valid_json(self, handler, tool_name, file_path):
        """Property-based test: Valid JSON should always be extracted correctly."""
        # Build a valid JSON tool call
        tool_call = {
            "tool": tool_name,
            "arguments": {
                "TargetFile": file_path
            }
        }

        # Wrap in code block
        response = f'```json\n{json.dumps(tool_call)}\n```'

        # Extract
        extracted = handler._extract_tool_calls(response)

        # Should extract exactly one tool call
        assert len(extracted) == 1
        assert extracted[0]["tool"] == tool_name
        assert extracted[0]["arguments"]["TargetFile"] == file_path

    @settings(
        max_examples=50,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        text_before=st.text(max_size=100),
        text_after=st.text(max_size=100),
        tool_name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
    )
    def test_extract_property_surrounded_by_text(self, handler, text_before, text_after, tool_name):
        """Property-based test: Tool calls surrounded by text should be extracted."""
        assume('```' not in text_before)
        assume('```' not in text_after)

        tool_call = {"tool": tool_name, "arguments": {}}
        response = f'{text_before}\n```json\n{json.dumps(tool_call)}\n```\n{text_after}'

        extracted = handler._extract_tool_calls(response)

        # Should extract the tool call regardless of surrounding text
        assert len(extracted) >= 1
        assert any(tc["tool"] == tool_name for tc in extracted)

    @settings(
        max_examples=30,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        content=st.text(max_size=200),
    )
    def test_extract_property_no_crash_on_arbitrary_input(self, handler, content):
        """Property-based test: Parser should never crash on arbitrary input."""
        # This test ensures robustness - should handle ANY input without crashing
        try:
            tool_calls = handler._extract_tool_calls(content)
            # Should always return a list (possibly empty)
            assert isinstance(tool_calls, list)
            # Each extracted tool call should have 'tool' and 'arguments' keys
            for tc in tool_calls:
                assert "tool" in tc
                assert "arguments" in tc
        except Exception as e:
            pytest.fail(f"Parser crashed on input: {repr(content[:100])}... Error: {e}")

    def test_extract_special_characters_in_arguments(self, handler):
        """Test extraction with special characters in argument values."""
        response = '''
```json
{"tool": "Write", "arguments": {"TargetFile": "test.py", "Content": "def foo():\\n    pass\\n\\n# Comment with 'quotes' and \\"escapes\\""}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Write"
        assert "def foo()" in tool_calls[0]["arguments"]["Content"]

    def test_extract_unicode_in_arguments(self, handler):
        """Test extraction with Unicode characters in arguments."""
        response = '''
```json
{"tool": "Write", "arguments": {"TargetFile": "测试.py", "Content": "# 中文注释\\nprint('Hello 世界')"}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Write"
        assert "测试.py" in tool_calls[0]["arguments"]["TargetFile"]

    def test_extract_array_in_arguments(self, handler):
        """Test extraction with array values in arguments."""
        response = '''
```json
{"tool": "MultiEdit", "arguments": {"files": ["a.py", "b.py", "c.py"]}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "MultiEdit"
        assert tool_calls[0]["arguments"]["files"] == ["a.py", "b.py", "c.py"]

    def test_extract_boolean_and_number_in_arguments(self, handler):
        """Test extraction with boolean and number values in arguments."""
        response = '''
```json
{"tool": "Config", "arguments": {"enabled": true, "count": 42, "ratio": 3.14}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["enabled"] is True
        assert tool_calls[0]["arguments"]["count"] == 42
        assert tool_calls[0]["arguments"]["ratio"] == 3.14

    def test_extract_null_in_arguments(self, handler):
        """Test extraction with null values in arguments."""
        response = '''
```json
{"tool": "Test", "arguments": {"optional": null}}
```
'''
        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["optional"] is None


class TestInlineJsonExtraction:
    """Tests for inline JSON extraction (fallback method)."""

    @pytest.fixture
    def handler(self):
        """Create a minimal base handler for testing."""
        handler = BasePhaseHandler(
            artifact_manager=None,
            provider=None,
            tool_executor=None,
            context_manager=None,
        )
        handler.phase_name = "test"
        return handler

    def test_inline_extraction_simple(self, handler):
        """Test inline JSON extraction without code blocks."""
        response = 'Use this tool: {"tool": "Read", "arguments": {"TargetFile": "test.py"}}'

        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Read"

    def test_inline_extraction_multiple(self, handler):
        """Test inline extraction of multiple tool calls."""
        response = '''
First call: {"tool": "Read", "arguments": {"TargetFile": "a.py"}}
Second call: {"tool": "Read", "arguments": {"TargetFile": "b.py"}}
'''
        tool_calls = handler._extract_tool_calls(response)

        # Should extract both
        assert len(tool_calls) >= 2
        tools = [tc["tool"] for tc in tool_calls]
        assert tools.count("Read") >= 2

    def test_inline_extraction_nested_braces(self, handler):
        """Test inline extraction with nested braces."""
        response = 'Tool: {"tool": "Config", "arguments": {"settings": {"nested": {"value": 1}}}}'

        tool_calls = handler._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["tool"] == "Config"
        assert tool_calls[0]["arguments"]["settings"]["nested"]["value"] == 1

    def test_inline_extraction_with_strings_containing_braces(self, handler):
        """Test inline extraction when string values contain braces."""
        response = '''Tool: {"tool": "Write", "arguments": {"Content": "function() { return {}; }"}}'''

        tool_calls = handler._extract_tool_calls(response)

        # Should handle braces inside strings correctly
        assert len(tool_calls) >= 1
        # At least one should be the Write tool
        assert any(tc["tool"] == "Write" for tc in tool_calls)
