"""
Response cleaning for Hcode agent.

This module handles cleaning LLM responses before displaying to users,
removing internal reasoning, tool calls, and formatting artifacts.
"""

import re
from typing import List


class ResponseCleaner:
    """
    Clean LLM responses for user display.
    
    Removes:
    - <thinking> blocks (internal reasoning)
    - Raw JSON tool calls that weren't executed
    - Duplicate content
    - Internal prompts and continuations
    """

    # Patterns for internal reasoning markers
    INTERNAL_PHRASE_PATTERNS = [
        r"\[UNDERSTAND\].*?(?=\n\n|\[|$)",
        r"\[CONTEXT\].*?(?=\n\n|\[|$)",
        r"\[ASSUMPTIONS?\].*?(?=\n\n|\[|$)",
        r"\[OPTIONS?\].*?(?=\n\n|\[|$)",
        r"\[DECISION\].*?(?=\n\n|\[|$)",
        r"\[RISK\].*?(?=\n\n|\[|$)",
        r"\[PLAN\].*?(?=\n\n|\[|$)",
        r"UNDERSTAND:.*?(?=\n\n|CONTEXT:|ASSUMPTIONS:|OPTIONS:|DECISION:|$)",
        r"CONTEXT:.*?(?=\n\n|ASSUMPTIONS:|OPTIONS:|DECISION:|RISK:|$)",
    ]

    def __init__(self):
        """Initialize the response cleaner."""
        pass

    def clean(self, response: str) -> str:
        """
        Clean the final response before showing to user.
        
        Args:
            response: The raw accumulated response
            
        Returns:
            Cleaned response for user display
        """
        if not response:
            return response

        cleaned = response

        # 1. Remove all <thinking>...</thinking> blocks
        cleaned = self._remove_thinking_blocks(cleaned)

        # 2. Remove raw JSON tool calls (already executed, shown in tool display)
        cleaned = self._remove_json_tool_calls(cleaned)

        # 3. Remove incomplete/fragment JSON that looks like tool calls
        cleaned = self._remove_json_fragments(cleaned)

        # 4. Remove internal continuation prompts
        cleaned = self._remove_internal_phrases(cleaned)

        # 5. Clean up multiple consecutive newlines
        cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)

        # 6. Clean up whitespace at start/end
        cleaned = cleaned.strip()

        # 7. If cleaning removed everything meaningful, try to extract useful content
        if not cleaned or len(cleaned) < 10:
            cleaned = self._extract_useful_content(response)

        return cleaned

    def _remove_thinking_blocks(self, text: str) -> str:
        """Remove all <thinking>...</thinking> blocks."""
        return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE)

    def _remove_json_tool_calls(self, text: str) -> str:
        """Remove raw JSON tool calls."""
        # Pattern: {"tool": "...", "parameters": {...}}
        return re.sub(
            r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^}]*\}\s*\}',
            "",
            text,
            flags=re.DOTALL,
        )

    def _remove_json_fragments(self, text: str) -> str:
        """Remove incomplete/fragment JSON that looks like tool calls."""
        return re.sub(
            r'\{\s*"(?:tool|path|file_path|command)"\s*:\s*"[^"]*"\s*(?:,\s*"[^"]+"\s*:\s*[^}]*)?\}?',
            "",
            text,
            flags=re.DOTALL,
        )

    def _remove_internal_phrases(self, text: str) -> str:
        """Remove internal continuation prompts and reasoning markers."""
        cleaned = text
        for pattern in self.INTERNAL_PHRASE_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        return cleaned

    def _extract_useful_content(self, response: str) -> str:
        """
        Extract useful content from a response that was mostly cleaned away.
        
        Args:
            response: Original response before cleaning
            
        Returns:
            Extracted useful lines
        """
        lines = response.split("\n")
        useful_lines: List[str] = []

        for line in lines:
            line = line.strip()
            # Skip internal reasoning markers
            if line.startswith("[") and "]" in line[:50]:
                continue
            if line.startswith("<thinking") or line.startswith("</thinking"):
                continue
            if line.startswith('{"tool"'):
                continue
            if line:
                useful_lines.append(line)

        if useful_lines:
            return "\n".join(useful_lines[-5:])  # Take last 5 useful lines

        return ""

    def strip_tool_calls_for_display(self, text: str) -> str:
        """
        Strip out tool call JSON from text for display purposes.
        
        This is used when displaying non-streaming responses where we want
        to show content but not raw tool JSON.
        
        Args:
            text: Response text that may contain tool calls
            
        Returns:
            Text with tool call JSON removed
        """
        display_text = text

        # Remove JSON blocks inside code fences (```json ... ```)
        display_text = re.sub(r"```json\s*\{[\s\S]*?\}\s*```", "", display_text)

        # Remove multiline JSON tool calls with nested content
        display_text = re.sub(
            r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[\s\S]*?\}\s*\}',
            "",
            display_text,
            flags=re.DOTALL,
        )

        # Remove TodoWrite JSON specifically (handles arrays in todos)
        display_text = re.sub(
            r'\{\s*"tool"\s*:\s*"TodoWrite"\s*,\s*"parameters"\s*:\s*\{[\s\S]*?"todos"\s*:\s*\[[\s\S]*?\]\s*\}\s*\}',
            "",
            display_text,
            flags=re.DOTALL,
        )

        # Remove simple tool JSON
        display_text = re.sub(
            r'\{\s*"tool"\s*:\s*"[^"]+"\s*\}', "", display_text, flags=re.DOTALL
        )

        # Remove any remaining JSON objects that look like tool calls
        display_text = re.sub(
            r'\{[^{}]*"tool"[^{}]*\}', "", display_text, flags=re.DOTALL
        )

        # Clean up excess whitespace
        display_text = re.sub(r"\n\s*\n\s*\n+", "\n\n", display_text)
        display_text = display_text.strip()

        return display_text

    def is_thinking_metadata_only(self, text: str) -> bool:
        """
        Check if text is only thinking metadata patterns (not substantive content).
        
        Args:
            text: Text to check
            
        Returns:
            True if text is just internal markers
        """
        return bool(re.match(
            r"^\s*\[(?:UNDERSTAND|CONTEXT|OPTIONS|DECISION|RISK|ASSUMPTIONS|OK|!)\]",
            text,
        ))
