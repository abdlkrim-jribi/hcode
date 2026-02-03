"""
Tool Executor for Hcode Agent.

This module handles executing tool calls with retry logic, validation,
confirmation prompts, and result display.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None


# Transient error patterns that warrant a retry
TRANSIENT_ERRORS = ["timeout", "temporary", "retry", "busy", "unavailable", "connection"]


class ToolExecutor:
    """
    Execute tool calls with retry logic and result display.
    
    Features:
    - Retry logic for transient failures
    - Tool name validation and auto-correction
    - Confirmation prompts for write operations
    - Standardized result display
    """
    
    def __init__(
        self,
        tool_manager: Any,
        console: Any,
        debug_mode: bool = False,
        palette: Any = None,
        icons: Any = None,
    ):
        """
        Initialize the tool executor.
        
        Args:
            tool_manager: ToolManager instance for executing tools
            console: Rich console for output
            debug_mode: Whether to print debug messages
            palette: Color palette for display
            icons: Icon set for display
        """
        self.tool_manager = tool_manager
        self.console = console
        self.debug_mode = debug_mode
        self.palette = palette
        self.icons = icons
        self.failed_commands: Dict[str, int] = {}
    
    def _debug_print(self, message: str) -> None:
        """Print message only if debug mode is enabled."""
        if self.debug_mode and self.console:
            self.console.print(message)
    
    def _is_transient_error(self, error_msg: str) -> bool:
        """Check if error is likely transient and worth retrying."""
        if not error_msg:
            return False
        error_lower = error_msg.lower()
        return any(pattern in error_lower for pattern in TRANSIENT_ERRORS)
    
    def _validate_and_suggest_tool(self, tool_name: str) -> Tuple[bool, str, str]:
        """
        Validate tool name and suggest corrections if invalid.
        
        Returns:
            Tuple of (is_valid, corrected_name, suggestion_message)
        """
        # Check if tool exists
        tool = self.tool_manager.get_tool(tool_name)
        if tool:
            return True, tool_name, ""
        
        # Tool doesn't exist - try to suggest corrections
        available_tools = [t.name.lower() for t in self.tool_manager.list_tools()]
        
        # Common mistakes and their corrections
        common_mistakes = {
            "fileread": "readtool",
            "file_read": "readtool",
            "readfile": "readtool",
            "writefile": "writetool",
            "file_write": "writetool",
            "writetofile": "writetool",
            "editfile": "edittool",
            "file_edit": "edittool",
            "modifyfile": "edittool",
            "findfiles": "globtool",
            "searchfiles": "greptool",
            "search": "greptool",
        }
        
        # Check common mistakes
        if tool_name in common_mistakes:
            suggested = common_mistakes[tool_name]
            return False, suggested, f"⚠️ Tool '{tool_name}' doesn't exist. Did you mean '{suggested}'?"
        
        # Check for close matches using simple string distance
        from difflib import get_close_matches
        close_matches = get_close_matches(tool_name, available_tools, n=3, cutoff=0.6)
        
        if close_matches:
            suggested = close_matches[0]
            others = ", ".join(close_matches[1:]) if len(close_matches) > 1 else ""
            msg = f"⚠️ Tool '{tool_name}' doesn't exist. Did you mean '{suggested}'?"
            if others:
                msg += f" (or: {others})"
            return False, suggested, msg
        
        return False, "", f"❌ Tool '{tool_name}' doesn't exist. Available tools: {', '.join(available_tools[:10])}"
    
    async def _execute_with_retry(
        self,
        tool_name: str,
        arguments: dict,
        max_retries: int = 2,
    ) -> ToolResult:
        """Execute a tool with retry logic for transient failures."""
        last_error = None
        
        # Validate tool name first
        is_valid, corrected_name, suggestion_msg = self._validate_and_suggest_tool(tool_name)
        
        if not is_valid:
            if corrected_name:
                self.console.print(f"[yellow]{suggestion_msg}[/yellow]")
                self.console.print(f"[dim]Auto-correcting: {tool_name} → {corrected_name}[/dim]")
                tool_name = corrected_name
            else:
                self.console.print(f"[red]{suggestion_msg}[/red]")
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid tool name: {tool_name}. {suggestion_msg}"
                )
        
        for attempt in range(max_retries + 1):
            try:
                result = await self.tool_manager.execute_tool(tool_name, **arguments)
                
                # Check for transient errors that might succeed on retry
                if not result.success and attempt < max_retries:
                    if self._is_transient_error(result.error):
                        self.console.print(
                            f"[dim][R] Retrying {tool_name} (attempt {attempt + 2}/{max_retries + 1})...[/dim]"
                        )
                        await asyncio.sleep(1)
                        continue
                
                return result
                
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    self.console.print(f"[dim][R] Tool error, retrying {tool_name}: {e}[/dim]")
                    await asyncio.sleep(1)
                    continue
                
                # All retries exhausted
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed after {max_retries + 1} attempts: {str(last_error)}",
                )
        
        return ToolResult(
            success=False,
            output="",
            error=f"Unexpected error after {max_retries + 1} attempts"
        )
    
    async def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        normalize_fn: Optional[Any] = None,
        require_confirmation: bool = False,
        max_retries: int = 2,
    ) -> List[Tuple[str, Any, dict]]:
        """
        Execute a list of tool calls and return results.
        
        Args:
            tool_calls: List of tool call dicts with 'name' and 'arguments'
            normalize_fn: Optional function to normalize tool arguments
            require_confirmation: Whether to ask user confirmation for writes
            max_retries: Maximum number of retries
            
        Returns:
            List of (tool_name, result, arguments) tuples
        """
        from hcode.tools.base.base_tool import ToolResult as BaseToolResult
        
        results = []
        write_operations = []
        other_operations = []
        
        # Separate write operations from others
        write_tool_names = ["writetool", "edittool", "multiedittool", "write", "edit", "multiedit"]
        
        for tc in tool_calls:
            tool_name = tc["name"].lower()
            if tool_name in write_tool_names:
                write_operations.append(tc)
            else:
                other_operations.append(tc)
        
        # Execute non-write operations immediately
        for tc in other_operations:
            tool_name = tc["name"].lower()
            arguments = tc["arguments"]
            if normalize_fn:
                arguments = normalize_fn(tool_name, arguments)
            
            self._debug_print(f"[bold yellow][>] Calling tool: {tool_name}[/bold yellow]")
            
            result = await self._execute_with_retry(tool_name, arguments, max_retries)
            results.append((tool_name, result, arguments))
        
        # Handle write operations with confirmation
        if write_operations:
            if require_confirmation:
                self.display_pending_writes(write_operations)
                
                self.console.print(
                    "[bold yellow]Execute these file operations?[/bold yellow] [[green]Ok[/green]/n]: ",
                    end="",
                )
                try:
                    response = input().strip().lower()
                except (EOFError, KeyboardInterrupt):
                    response = "n"
                
                if response == "":
                    response = "y"
                
                if response not in ["y", "yes", "ok"]:
                    self.console.print("[bold red][X] File operations cancelled by user[/bold red]")
                    for tc in write_operations:
                        arguments = tc["arguments"]
                        if normalize_fn:
                            arguments = normalize_fn(tc["name"].lower(), arguments)
                        results.append((
                            tc["name"],
                            BaseToolResult(success=False, output="", error="Operation cancelled by user"),
                            arguments,
                        ))
                    return results
            
            # Execute write operations
            for tc in write_operations:
                tool_name = tc["name"].lower()
                arguments = tc["arguments"]
                if normalize_fn:
                    arguments = normalize_fn(tool_name, arguments)
                
                self._debug_print(f"[bold green][W] Writing: {tool_name}[/bold green]")
                
                result = await self._execute_with_retry(tool_name, arguments, max_retries)
                results.append((tool_name, result, arguments))
        
        return results
    
    def display_pending_writes(self, write_operations: List[Dict[str, Any]]) -> None:
        """
        Display pending write operations for user review.
        
        Shows actual file diffs with syntax highlighting.
        """
        for tc in write_operations:
            tool_name = tc["name"].lower()
            args = tc["arguments"]
            
            if tool_name in ["writetool", "write"]:
                self._display_write_diff(args)
            elif tool_name in ["edittool", "edit"]:
                self._display_edit_diff(args)
            elif tool_name in ["multiedittool", "multiedit"]:
                self._display_multiedit_diff(args)
        
        self.console.print("")
    
    def _display_write_diff(self, args: dict) -> None:
        """Display write operation diff."""
        file_path = args.get("file_path", "unknown")
        content = args.get("content", "")
        
        file_exists = Path(file_path).exists()
        diff_lines = []
        
        if file_exists:
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    old_content = f.read()
                for line in old_content.split("\n")[:20]:
                    diff_lines.append(("remove", line))
                if old_content.count("\n") > 20:
                    diff_lines.append(("info", f"... ({old_content.count(chr(10)) - 20} more lines removed)"))
            except:
                pass
        
        new_lines = content.split("\n")
        for line in new_lines[:30]:
            diff_lines.append(("add", line))
        if len(new_lines) > 30:
            diff_lines.append(("info", f"... ({len(new_lines) - 30} more lines)"))
        
        action = "Edit" if file_exists else "Write"
        icon = getattr(self.icons, "FILE", "📄") if self.icons else "📄"
        color = getattr(self.palette, "warning", "yellow") if self.palette else "yellow"
        
        self.console.print(f"\n[bold {color}]{icon} {action}: {file_path}[/bold {color}]")
        
        for line_type, line in diff_lines:
            if line_type == "remove":
                self.console.print(f"[red]- {line}[/red]")
            elif line_type == "add":
                self.console.print(f"[green]+ {line}[/green]")
            else:
                self.console.print(f"[dim]{line}[/dim]")
    
    def _display_edit_diff(self, args: dict) -> None:
        """Display edit operation diff."""
        file_path = args.get("file_path", "unknown")
        old_str = args.get("old_string", "")
        new_str = args.get("new_string", "")
        
        icon = getattr(self.icons, "EDIT", "✏️") if self.icons else "✏️"
        color = getattr(self.palette, "warning", "yellow") if self.palette else "yellow"
        
        self.console.print(f"\n[bold {color}]{icon} Edit: {file_path}[/bold {color}]")
        
        old_lines = old_str.split("\n")
        for line in old_lines[:15]:
            self.console.print(f"[red]- {line}[/red]")
        if len(old_lines) > 15:
            self.console.print(f"[dim]... ({len(old_lines) - 15} more lines removed)[/dim]")
        
        new_lines = new_str.split("\n")
        for line in new_lines[:15]:
            self.console.print(f"[green]+ {line}[/green]")
        if len(new_lines) > 15:
            self.console.print(f"[dim]... ({len(new_lines) - 15} more lines added)[/dim]")
    
    def _display_multiedit_diff(self, args: dict) -> None:
        """Display multiedit operation diff."""
        file_path = args.get("file_path", "unknown")
        edits = args.get("edits", [])
        
        icon = getattr(self.icons, "EDIT", "✏️") if self.icons else "✏️"
        color = getattr(self.palette, "warning", "yellow") if self.palette else "yellow"
        
        self.console.print(f"\n[bold {color}]{icon} MultiEdit: {file_path}[/bold {color}]")
        self.console.print(f"[dim]{len(edits)} edit(s) to apply[/dim]")
        
        for i, edit in enumerate(edits[:3], 1):
            old_str = edit.get("old_string", "")[:50]
            new_str = edit.get("new_string", "")[:50]
            self.console.print(
                f"[dim]  {i}. [red]-[/red] {old_str}{'...' if len(edit.get('old_string', '')) > 50 else ''}[/dim]"
            )
            self.console.print(
                f"[dim]     [green]+[/green] {new_str}{'...' if len(edit.get('new_string', '')) > 50 else ''}[/dim]"
            )
        
        if len(edits) > 3:
            self.console.print(f"[dim]  ... and {len(edits) - 3} more edits[/dim]")
    
    def display_tool_result(
        self,
        tool_name: str,
        result: Any,
        arguments: dict,
    ) -> None:
        """
        Display tool execution result.
        
        Uses HcodeToolDisplay for consistent formatting.
        """
        from hcode.cli.tool_display import HcodeToolDisplay
        
        # Special handling for TodoWrite - skip display
        if tool_name.lower() == "todowrite":
            if self.debug_mode:
                todos = arguments.get("todos", [])
                if todos:
                    total = len(todos)
                    completed = sum(1 for t in todos if t.get("status") == "completed")
                    icon = getattr(self.icons, "GEAR", "⚙️") if self.icons else "⚙️"
                    color = getattr(self.palette, "info", "blue") if self.palette else "blue"
                    status_text = f"[{color}]{icon} Tasks updated: {completed}/{total} completed[/]"
                    self.console.print(status_text)
            return
        
        # Use Hcode-style tool display for other tools
        display = HcodeToolDisplay(self.console)
        display.display_tool_call(tool_name, arguments, result)
