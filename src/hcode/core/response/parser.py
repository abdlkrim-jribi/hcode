"""
Response parsing for Hcode agent.

This module handles parsing tool calls from LLM responses, supporting
both native API tool calls and text-based JSON tool calls.
"""

import json
import re
from typing import Dict, Any, List, Optional, Set

from ..protocols import ParsedToolCall


class ResponseParser:
    """
    Extract and validate tool calls from LLM output.
    
    Handles:
    - OpenAI-style native tool calls
    - Anthropic-style tool_use blocks
    - JSON tool calls embedded in text
    - Todo normalization
    """
    
    # Valid tool names (lowercase for comparison)
    VALID_TOOLS: Set[str] = {
        "ls", "lstool", "read", "readtool", "write", "writetool",
        "edit", "edittool", "bash", "bashtool", "glob", "globtool",
        "grep", "greptool", "todowrite", "askuserquestion", "askuser",
        "notebookedit", "webfetch", "websearch", "task", "todoread",
    }
    
    # Verb mappings for activeForm generation
    VERB_MAP = {
        "add": "Adding", "create": "Creating", "fix": "Fixing",
        "update": "Updating", "remove": "Removing", "delete": "Deleting",
        "implement": "Implementing", "write": "Writing", "read": "Reading",
        "test": "Testing", "run": "Running", "check": "Checking",
        "analyze": "Analyzing", "review": "Reviewing", "refactor": "Refactoring",
        "debug": "Debugging", "investigate": "Investigating", "explore": "Exploring",
        "search": "Searching", "find": "Finding", "look": "Looking",
        "build": "Building", "compile": "Compiling", "install": "Installing",
        "configure": "Configuring", "setup": "Setting up", "set": "Setting",
        "get": "Getting", "fetch": "Fetching", "load": "Loading",
        "save": "Saving", "export": "Exporting", "import": "Importing",
        "parse": "Parsing", "extract": "Extracting", "convert": "Converting",
        "validate": "Validating", "verify": "Verifying", "ensure": "Ensuring",
    }
    
    def __init__(self, tool_registry: Optional[Dict[str, Any]] = None, console=None, debug_mode: bool = False):
        """
        Initialize the response parser.
        
        Args:
            tool_registry: Optional dict mapping tool names to tool instances
            console: Optional Rich console for debug output
            debug_mode: Whether to print debug messages
        """
        self.tool_registry = tool_registry or {}
        self.console = console
        self.debug_mode = debug_mode
    
    def extract_tool_calls(
        self,
        raw_response: Any,
        response_text: str,
        provider_name: str,
    ) -> List[ParsedToolCall]:
        """
        Extract tool calls from LLM response.
        
        Handles both native API tool calls and text-based JSON tool calls.
        
        Args:
            raw_response: Raw response object from provider
            response_text: Text content of response
            provider_name: Name of the provider (e.g., "openai", "anthropic")
            
        Returns:
            List of parsed tool calls
        """
        tool_calls = []
        
        # Check OpenAI style tool calls
        if raw_response and hasattr(raw_response, "choices"):
            choice = raw_response.choices[0]
            if (
                hasattr(choice, "message")
                and hasattr(choice.message, "tool_calls")
                and choice.message.tool_calls
            ):
                for tc in choice.message.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append(ParsedToolCall(
                        name=tc.function.name,
                        arguments=args,
                        id=getattr(tc, "id", None),
                        source="native",
                    ))
                return tool_calls
        
        # Check Anthropic style tool calls
        if raw_response and hasattr(raw_response, "content"):
            for block in raw_response.content:
                if hasattr(block, "type") and block.type == "tool_use":
                    tool_calls.append(ParsedToolCall(
                        name=block.name,
                        arguments=block.input if hasattr(block, "input") else {},
                        id=getattr(block, "id", None),
                        source="native",
                    ))
            if tool_calls:
                return tool_calls
        
        # Fallback: Parse from text
        return self.parse_json_tool_calls(response_text)
    
    def parse_json_tool_calls(self, text: str) -> List[ParsedToolCall]:
        """
        Parse JSON tool calls from text content.
        
        Args:
            text: Text potentially containing JSON tool calls
            
        Returns:
            List of parsed tool calls
        """
        tool_calls = []
        
        # Strategy 0: Detect TodoWrite attempts
        todo_calls = self._extract_todo_calls(text)
        tool_calls.extend(todo_calls)
        
        # Strategy 1: Standard JSON tool call format
        standard_calls = self._extract_standard_tool_calls(text)
        tool_calls.extend(standard_calls)
        
        # Strategy 2: Code block JSON
        if not tool_calls:
            code_block_calls = self._extract_code_block_calls(text)
            tool_calls.extend(code_block_calls)
        
        # Strategy 3: Balanced JSON extraction
        if not tool_calls:
            balanced_calls = self._extract_balanced_json_calls(text)
            tool_calls.extend(balanced_calls)
        
        return tool_calls
    
    def extract_balanced_json(self, text: str, max_length: int = 10000) -> Optional[str]:
        """
        Extract a balanced JSON object from text.
        
        Args:
            text: Text containing JSON
            max_length: Maximum extraction length
            
        Returns:
            Extracted JSON string or None
        """
        start_idx = text.find("{")
        if start_idx == -1:
            return None
        
        depth = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text[start_idx:start_idx + max_length]):
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
                    return text[start_idx:start_idx + i + 1]
        
        return None
    
    def _extract_todo_calls(self, text: str) -> List[ParsedToolCall]:
        """Extract TodoWrite calls from various formats."""
        calls = []
        
        todowrite_patterns = [
            # Full TodoWrite tool call
            r'\{\s*["\']tool["\']\s*:\s*["\']TodoWrite["\']\s*,\s*["\'](?:parameters|params|arguments)["\']\s*:\s*\{\s*["\']todos["\']\s*:\s*(\[[\s\S]*?\])\s*\}\s*\}',
            # Just {"todos": [...]} format
            r'\{\s*["\']todos["\']\s*:\s*(\[[\s\S]*?\])\s*\}',
            # Task list markdown followed by JSON
            r'(?:task\s*list|todowrite|tasks?)[\s\S]{0,50}\{\s*["\']todos["\']\s*:\s*(\[[\s\S]*?\])',
        ]
        
        for pattern in todowrite_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                try:
                    todos_str = match.group(1).strip()
                    todos_raw = json.loads(todos_str)
                    normalized = self._normalize_todos_list(todos_raw)
                    if normalized:
                        self._debug_print(f"[+] Detected TodoWrite - normalizing {len(normalized)} items")
                        calls.append(ParsedToolCall(
                            name="TodoWrite",
                            arguments={"todos": normalized},
                            source="text",
                        ))
                        return calls  # Only one TodoWrite per response
                except (json.JSONDecodeError, IndexError):
                    continue
        
        return calls
    
    def _extract_standard_tool_calls(self, text: str) -> List[ParsedToolCall]:
        """Extract standard format tool calls: {"tool": "X", "parameters": {...}}"""
        calls = []
        
        # Pattern for standard tool call format
        pattern = r'\{\s*["\']tool["\']\s*:\s*["\']([^"\']+)["\']\s*,\s*["\'](?:parameters|params|arguments)["\']\s*:\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*\}'
        
        for match in re.finditer(pattern, text, re.DOTALL):
            tool_name = match.group(1)
            try:
                args_str = match.group(2)
                args = json.loads(args_str)
                
                if self._is_valid_tool_call(tool_name, args):
                    args = self._process_arguments(args)
                    calls.append(ParsedToolCall(
                        name=tool_name,
                        arguments=args,
                        source="text",
                    ))
            except json.JSONDecodeError:
                continue
        
        # Also try flat format: {"tool": "X", "path": "..."}
        flat_pattern = r'\{\s*["\']tool["\']\s*:\s*["\']([^"\']+)["\']\s*(?:,\s*["\'][^"\']+["\']\s*:\s*[^{}]+)+\s*\}'
        
        for match in re.finditer(flat_pattern, text, re.DOTALL):
            json_str = match.group(0)
            try:
                data = json.loads(json_str)
                tool_name = data.get("tool", "")
                args = self._extract_tool_args(data)
                
                if self._is_valid_tool_call(tool_name, args):
                    args = self._process_arguments(args)
                    # Check we haven't already added this
                    if not any(c.name == tool_name and c.arguments == args for c in calls):
                        calls.append(ParsedToolCall(
                            name=tool_name,
                            arguments=args,
                            source="text",
                        ))
            except json.JSONDecodeError:
                continue
        
        return calls
    
    def _extract_code_block_calls(self, text: str) -> List[ParsedToolCall]:
        """Extract tool calls from code blocks (```json ... ```)."""
        calls = []
        
        code_block_pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
        
        for match in re.finditer(code_block_pattern, text, re.DOTALL):
            try:
                data = json.loads(match.group(1))
                if "tool" in data:
                    tool_name = data["tool"]
                    args = self._extract_tool_args(data)
                    
                    if self._is_valid_tool_call(tool_name, args):
                        args = self._process_arguments(args)
                        calls.append(ParsedToolCall(
                            name=tool_name,
                            arguments=args,
                            source="text",
                        ))
            except json.JSONDecodeError:
                continue
        
        return calls
    
    def _extract_balanced_json_calls(self, text: str) -> List[ParsedToolCall]:
        """Extract tool calls using balanced JSON extraction."""
        calls = []
        remaining = text
        
        while '{"tool"' in remaining or "{'tool'" in remaining:
            # Find start of tool call
            start = remaining.find('{"tool"')
            if start == -1:
                start = remaining.find("{'tool'")
            if start == -1:
                break
            
            json_str = self.extract_balanced_json(remaining[start:])
            if not json_str:
                remaining = remaining[start + 1:]
                continue
            
            try:
                data = json.loads(json_str)
                tool_name = data.get("tool", "")
                args = self._extract_tool_args(data)
                
                if self._is_valid_tool_call(tool_name, args):
                    args = self._process_arguments(args)
                    calls.append(ParsedToolCall(
                        name=tool_name,
                        arguments=args,
                        source="text",
                    ))
            except json.JSONDecodeError:
                pass
            
            remaining = remaining[start + len(json_str):]
        
        return calls
    
    def _is_valid_tool_name(self, name: str) -> bool:
        """Check if tool name is valid."""
        if not name:
            return False
        return name.lower() in self.VALID_TOOLS
    
    def _is_valid_tool_call(self, tool_name: str, args: dict) -> bool:
        """Validate that tool call has reasonable arguments."""
        if not self._is_valid_tool_name(tool_name):
            return False
        
        tool_lower = tool_name.lower().replace("tool", "")
        
        # Validate based on tool type
        if tool_lower in ["ls", "list"]:
            # LS needs DirectoryPath
            path = args.get("DirectoryPath") or args.get("path", "")
            if path == "/" or path == "\\":
                # Fix root path to current directory
                args["DirectoryPath"] = "."
                if "path" in args:
                    del args["path"]
            elif not path:
                args["DirectoryPath"] = "."
                if "path" in args:
                    del args["path"]
            elif "path" in args and "DirectoryPath" not in args:
                args["DirectoryPath"] = args["path"]
                del args["path"]
            return True
        
        if tool_lower == "read":
            return "file_path" in args
        
        if tool_lower == "write":
            return "file_path" in args and "content" in args
        
        if tool_lower == "edit":
            return "file_path" in args and ("old_string" in args or "new_string" in args)
        
        if tool_lower == "bash":
            return "command" in args
        
        if tool_lower == "glob":
            return "pattern" in args
        
        if tool_lower == "grep":
            return "pattern" in args
        
        # Default: accept if it has at least one argument
        return bool(args)
    
    def _extract_tool_args(self, data: dict) -> dict:
        """
        Extract tool arguments from data, handling different formats.
        
        Formats:
        1. {"tool": "X", "parameters": {...}}
        2. {"tool": "X", "params": {...}}
        3. {"tool": "X", "path": "...", ...} - Flat format
        """
        if "parameters" in data:
            return data["parameters"]
        if "params" in data:
            return data["params"]
        if "arguments" in data:
            return data["arguments"]
        
        # Flat format - all keys except "tool"
        return {k: v for k, v in data.items() if k != "tool"}
    
    def _process_arguments(self, args: dict) -> dict:
        """Process arguments - unescape content when needed."""
        if not isinstance(args, dict):
            return args
        
        processed = {}
        for key, value in args.items():
            if key == "content" and isinstance(value, str):
                # Only unescape if double-escaped
                if "\n" not in value and "\\n" in value:
                    processed[key] = self._unescape_content(value)
                else:
                    processed[key] = value
            elif key in ("old_string", "new_string"):
                # Don't unescape edit strings
                processed[key] = value
            elif isinstance(value, dict):
                processed[key] = self._process_arguments(value)
            else:
                processed[key] = value
        
        return processed
    
    def _unescape_content(self, content: str) -> str:
        """Unescape double-escaped content."""
        if not isinstance(content, str):
            return content
        
        if "\n" in content:
            return content
        
        if "\\" not in content:
            return content
        
        result = content
        result = result.replace("\\n", "\n")
        result = result.replace("\\t", "\t")
        result = result.replace("\\r", "\r")
        
        return result
    
    def _normalize_todos_list(self, todos_raw) -> Optional[List[Dict[str, str]]]:
        """Normalize a list of todos to proper format."""
        if not isinstance(todos_raw, list) or not todos_raw:
            return None
        
        normalized = []
        has_in_progress = False
        
        for i, item in enumerate(todos_raw):
            todo = self._normalize_todo_item(item, i, not has_in_progress)
            if todo:
                if todo["status"] == "in_progress":
                    has_in_progress = True
                normalized.append(todo)
        
        return normalized if normalized else None
    
    def _normalize_todo_item(self, item, index: int = 0, first_in_progress: bool = True) -> Optional[Dict[str, str]]:
        """Normalize a todo item to proper format."""
        if isinstance(item, str):
            content = item.strip()
            status = "in_progress" if (index == 0 and first_in_progress) else "pending"
            active_form = self._generate_active_form(content)
            return {"content": content, "status": status, "activeForm": active_form}
        
        elif isinstance(item, dict):
            content = (
                item.get("content") or item.get("title") or item.get("task")
                or item.get("text") or item.get("description") or item.get("name") or ""
            )
            if not content:
                return None
            
            status = item.get("status", "pending")
            if status not in ["pending", "in_progress", "completed", "blocked", "skipped"]:
                status = "pending"
            
            active_form = (
                item.get("activeForm") or item.get("active_form")
                or item.get("activeform") or self._generate_active_form(content)
            )
            return {"content": content, "status": status, "activeForm": active_form}
        
        return None
    
    def _generate_active_form(self, content: str) -> str:
        """Generate present continuous form from imperative form."""
        if not content:
            return "Working..."
        
        words = content.strip().split()
        if not words:
            return "Working..."
        
        verb = words[0].lower()
        rest = " ".join(words[1:]) if len(words) > 1 else ""
        
        if verb in self.VERB_MAP:
            return f"{self.VERB_MAP[verb]} {rest}".strip()
        elif verb.endswith("e"):
            return f"{verb[:-1].capitalize()}ing {rest}".strip()
        else:
            return f"{verb.capitalize()}ing {rest}".strip()
    
    def _debug_print(self, message: str) -> None:
        """Print debug message if console available."""
        if self.console and self.debug_mode:
            self.console.print(f"[bold blue]{message}[/bold blue]")
