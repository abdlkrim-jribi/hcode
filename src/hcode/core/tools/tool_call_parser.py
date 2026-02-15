"""
Tool Call Parser for Hcode Agent.

Simplified, intelligent tool parsing with 2 main strategies:
1. Native API tool calls (OpenAI/Anthropic)
2. JSON extraction from text
"""

import json
import re
from typing import Dict, List, Optional, Any, Set


# Valid tool names
VALID_TOOLS: Set[str] = {
    "ls", "lstool", "read", "readtool", "write", "writetool", 
    "edit", "edittool", "bash", "bashtool", "glob", "globtool",
    "grep", "greptool", "todowrite", "askuserquestion", "askuser",
    "notebookedit", "webfetch", "websearch", "task",
}


class ToolCallParser:
    """
    Parse tool calls from LLM responses.
    
    Design principles:
    - Single entry point for all parsing
    - Two simple strategies: native API or JSON extraction
    - No complex regex cascades
    """
    
    def __init__(
        self,
        valid_tools: Optional[Set[str]] = None,
        console: Any = None,
        debug_mode: bool = False,
    ):
        self.valid_tools = valid_tools or VALID_TOOLS
        self.console = console
        self.debug_mode = debug_mode
    
    def _debug(self, msg: str) -> None:
        if self.debug_mode and self.console:
            self.console.print(msg)
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def extract_tool_calls(
        self,
        raw_response: Any,
        response_text: str,
        provider_name: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Extract tool calls from response.
        
        Strategy:
        1. Try native API response (cleanest)
        2. Fall back to JSON extraction from text
        """
        # Strategy 1: Native API responses
        calls = self._from_native_api(raw_response)
        if calls:
            return calls
        
        # Strategy 2: JSON extraction from text
        return self._from_text(response_text)
    
    
    def normalize_arguments(self, tool_name: str, arguments: dict) -> dict:
        """
        Normalize tool arguments using intelligent parameter mapping.
        
        Instead of hardcoded mappings, use common patterns.
        """
        base = tool_name.lower().replace("tool", "")
        args = dict(arguments)
        
        # Path normalization
        for old_key in ("path", "file", "filename", "filepath"):
            if old_key in args and "file_path" not in args:
                if base in ("read", "write", "edit"):
                    args["file_path"] = args.pop(old_key)
        
        # Directory path normalization for ls
        if base == "ls":
            for old_key in ("path", "dir", "directory", "folder"):
                if old_key in args:
                    args["DirectoryPath"] = args.pop(old_key)
            if "DirectoryPath" not in args:
                args["DirectoryPath"] = "."
        
        # Content normalization
        for old_key in ("text", "data", "body"):
            if old_key in args and "content" not in args:
                args["content"] = args.pop(old_key)
        
        # Command normalization
        for old_key in ("cmd", "shell", "run", "exec"):
            if old_key in args and "command" not in args:
                args["command"] = args.pop(old_key)
        
        # Pattern normalization
        for old_key in ("query", "search", "regex"):
            if old_key in args and "pattern" not in args and base in ("grep", "glob"):
                args["pattern"] = args.pop(old_key)
        
        # Edit string normalization
        for old_key in ("old", "search", "find"):
            if old_key in args and "old_string" not in args:
                args["old_string"] = args.pop(old_key)
        for old_key in ("new", "replace", "replacement"):
            if old_key in args and "new_string" not in args:
                args["new_string"] = args.pop(old_key)
        
        # TodoWrite normalization
        if base == "todowrite":
            for old_key in ("items", "tasks", "list"):
                if old_key in args and "todos" not in args:
                    args["todos"] = args.pop(old_key)
        
        # AskUser normalization
        if base in ("askuserquestion", "askuser"):
            q = args.get("questions") or args.get("question") or args.get("prompt")
            if isinstance(q, str):
                args["questions"] = [{"question": q, "header": "Question", "type": "open"}]
        
        return args
    
    # =========================================================================
    # Strategy 1: Native API
    # =========================================================================
    
    def _from_native_api(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Extract from native API response."""
        if not raw_response:
            return []
        
        calls = []
        
        # OpenAI format
        if hasattr(raw_response, "choices"):
            choice = raw_response.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "tool_calls"):
                for tc in choice.message.tool_calls or []:
                    try:
                        calls.append({
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments)
                        })
                    except:
                        pass
        
        # Anthropic format
        elif hasattr(raw_response, "content"):
            for block in raw_response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    calls.append({
                        "name": block.name,
                        "arguments": block.input
                    })
        
        return calls
    
    # =========================================================================
    # Strategy 2: Text Extraction
    # =========================================================================
    
    def _from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract tool calls from text using unified JSON extraction."""
        if not text:
            return []
        
        calls = []
        
        # Method 1: JSON in code blocks
        for match in re.finditer(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text):
            call = self._parse_json_tool(match.group(1))
            if call:
                calls.append(call)
        
        if calls:
            return calls
        
        # Method 2: Inline JSON with "tool" key
        for match in re.finditer(r'\{\s*["\']tool["\']\s*:', text):
            json_str = self._extract_balanced_json(text[match.start():])
            if json_str:
                call = self._parse_json_tool(json_str)
                if call:
                    calls.append(call)
        
        if calls:
            return calls
        
        # Method 3: Any JSON object that looks like a tool call
        for match in re.finditer(r'\{[^{}]*(?:"file_path"|"command"|"pattern")[^{}]*\}', text):
            call = self._parse_json_tool(match.group(0))
            if call:
                calls.append(call)
        
        return calls
    
    def _parse_json_tool(self, json_str: str) -> Optional[Dict[str, Any]]:
        """Parse a JSON string into a tool call."""
        try:
            data = json.loads(json_str)
        except:
            return None
        
        if not isinstance(data, dict):
            return None
        
        # Extract tool name
        name = data.get("tool") or data.get("name") or data.get("function")
        
        # Extract arguments
        args = (
            data.get("parameters") or 
            data.get("arguments") or 
            data.get("params") or
            data.get("input") or
            {k: v for k, v in data.items() if k not in ("tool", "name", "function")}
        )
        
        # Infer tool from args if no explicit name
        if not name:
            if "file_path" in args and "content" in args:
                name = "Write"
            elif "file_path" in args:
                name = "Read"
            elif "command" in args:
                name = "Bash"
            elif "pattern" in args:
                name = "Grep"
            elif "todos" in args:
                name = "TodoWrite"
            else:
                return None
        
        # Validate
        if not self._is_valid(name):
            return None
        
        self._debug(f"[blue][+] Parsed {name}[/blue]")
        return {"name": name, "arguments": args}
    
    def _extract_balanced_json(self, text: str, max_len: int = 5000) -> Optional[str]:
        """Extract balanced JSON object starting at text[0]."""
        if not text or text[0] != "{":
            return None
        
        depth = 0
        in_str = False
        escape = False
        
        for i, c in enumerate(text[:max_len]):
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"' and not escape:
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[:i+1]
        
        return None
    
    def _is_valid(self, name: str) -> bool:
        """Check if tool name is valid."""
        if not name:
            return False
        return name.lower().replace("tool", "") in {t.replace("tool", "") for t in self.valid_tools}
