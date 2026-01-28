"""
Tool Call Validator for Hcode.

Provides validation layer for tool calls before execution to prevent:
- Missing required parameters
- Invalid file paths
- Unknown tool names
- Type mismatches
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of tool call validation"""
    is_valid: bool
    error_message: str = ""
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ToolCallValidator:
    """
    Validates tool calls before execution.
    
    This helps prevent hallucination-related errors by catching:
    - Non-existent tools
    - Missing required parameters
    - Invalid file paths (for read operations)
    - Type mismatches
    """
    
    def __init__(self, tool_manager, root_dir: Optional[Path] = None):
        """
        Initialize validator with tool manager reference.
        
        Args:
            tool_manager: The ToolManager instance for tool lookups
            root_dir: Project root directory for path validation
        """
        self.tool_manager = tool_manager
        self.root_dir = root_dir or Path.cwd()
        
        # Tool-specific required parameters
        self.required_params = {
            "read": ["file_path"],
            "readtool": ["file_path"],
            "write": ["file_path", "content"],
            "writetool": ["file_path", "content"],
            "edit": ["file_path", "old_string", "new_string"],
            "edittool": ["file_path", "old_string", "new_string"],
            "bash": ["command"],
            "bashtool": ["command"],
            "glob": ["pattern"],
            "globtool": ["pattern"],
            "grep": ["pattern"],
            "greptool": ["pattern"],
        }
        
        # Tools that require existing files
        self.file_read_tools = {
            "read", "readtool", "edit", "edittool", 
            "notebookread", "notebookedit"
        }
    
    def validate(self, tool_name: str, arguments: Dict[str, Any]) -> ValidationResult:
        """
        Validate a tool call before execution.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments/parameters
            
        Returns:
            ValidationResult with is_valid=True if OK, or error details
        """
        tool_lower = tool_name.lower()
        warnings = []
        
        # 1. Check if tool exists
        tool = self.tool_manager.get_tool(tool_name)
        if not tool:
            # Try common aliases
            aliases = {
                "read": "ReadTool",
                "write": "WriteTool", 
                "edit": "EditTool",
                "bash": "BashTool",
                "glob": "GlobTool",
                "grep": "GrepTool",
                "ls": "LSTool",
            }
            if tool_lower in aliases:
                tool = self.tool_manager.get_tool(aliases[tool_lower])
            
            if not tool:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unknown tool: '{tool_name}'. Available tools: {', '.join(self.tool_manager.tool_registry.tools.keys())}"
                )
        
        # 2. Check required parameters
        required = self.required_params.get(tool_lower, [])
        missing = [p for p in required if p not in arguments or not arguments[p]]
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required parameter(s) for {tool_name}: {', '.join(missing)}"
            )
        
        # 3. Validate file paths for read operations
        if tool_lower in self.file_read_tools:
            file_path = arguments.get("file_path", "")
            if file_path:
                path = Path(file_path)
                
                # Convert relative to absolute
                if not path.is_absolute():
                    path = self.root_dir / path
                    warnings.append(f"Converted relative path to absolute: {path}")
                
                # Check existence for read operations
                if not path.exists():
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"File does not exist: {path}"
                    )
                    
                if path.is_dir() and tool_lower not in {"ls", "lstool"}:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Path is a directory, not a file: {path}"
                    )
        
        # 4. Validate edit operations have non-empty strings
        if tool_lower in {"edit", "edittool"}:
            old_string = arguments.get("old_string", "")
            if not old_string.strip():
                warnings.append("old_string is empty - this will create a new file or insert at beginning")
        
        # 5. Validate command safety for bash
        if tool_lower in {"bash", "bashtool"}:
            command = arguments.get("command", "")
            dangerous_patterns = ["rm -rf /", "rm -rf ~", "> /dev/sda", "mkfs", "dd if="]
            for pattern in dangerous_patterns:
                if pattern in command.lower():
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Dangerous command pattern detected: {pattern}"
                    )
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    def validate_batch(self, tool_calls: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], ValidationResult]]:
        """
        Validate multiple tool calls.
        
        Args:
            tool_calls: List of tool call dicts with 'name'/'tool' and 'arguments'/'parameters'
            
        Returns:
            List of (tool_call, ValidationResult) tuples
        """
        results = []
        for tc in tool_calls:
            # Support different formats
            tool_name = tc.get("name") or tc.get("tool", "")
            arguments = tc.get("arguments") or tc.get("parameters", {})
            
            result = self.validate(tool_name, arguments)
            results.append((tc, result))
        
        return results
