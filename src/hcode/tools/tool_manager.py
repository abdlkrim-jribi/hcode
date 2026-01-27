"""
Tool Manager for Hcode.
Initializes and manages all available tools.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from hcode.tools.agent_tools import TaskTool, ExitPlanModeTool
from hcode.tools.base_tool import ToolRegistry, BaseTool, ToolResult
from hcode.tools.bash_tools import BashTool, BashOutputTool, KillShellTool, LSTool, SearchOutputTool
from hcode.tools.command_system import SlashCommandTool, SkillTool, CommandRegistry
from hcode.tools.diff_tools import DiffPreviewTool, ApplyChangeTool, RejectChangeTool
from hcode.tools.file_tools import ReadTool, WriteTool, EditTool, MultiEditTool, GlobTool, GrepTool
from hcode.tools.git_tools import (
    GitStatusTool,
    GitDiffTool,
    GitAddTool,
    GitCommitTool,
    GitLogTool,
    GitCheckoutTool,
    GitBranchTool,
)
from hcode.tools.fuzzy_edit_tool import FuzzyEditTool
from hcode.tools.interactive_tools import (
    AskUserQuestionTool,
    ConfirmTool,
    DisplayPanelTool,
    ProgressTool,
)
from hcode.tools.notebook_tools import NotebookEditTool, NotebookReadTool, NotebookExecuteTool
from hcode.tools.web_tools import WebFetchTool, WebSearchTool, WebScrapeTool
from hcode.tools.hcode_tools import TaskBoundaryTool, NotifyUserTool
from hcode.tools.todo_write import TodoWriteTool
from hcode.tools.todo_read import TodoReadTool


class ToolManager:
    """
    Central manager for all tools in Hcode.
    Provides unified access to file operations, web tools, interactive features, etc.
    """

    def __init__(self, root_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize tool manager.

        Args:
            root_dir: Root directory for operations
            config: Configuration dictionary
        """
        self.root_dir = Path(root_dir or os.getcwd())
        self.config = config or {}

        # Initialize registries
        self.tool_registry = ToolRegistry()
        self.command_registry = CommandRegistry(root_dir=str(self.root_dir))

        # Initialize tools
        self._register_all_tools()

        # Track tool usage
        self.usage_stats: Dict[str, int] = {}

    def _register_all_tools(self):
        """Register all available tools"""

        # File operation tools
        self.tool_registry.register(ReadTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(WriteTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(EditTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(MultiEditTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(GlobTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(GrepTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(LSTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(FuzzyEditTool(root_dir=str(self.root_dir)))

        # Git tools
        self.tool_registry.register(GitStatusTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(GitDiffTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(GitAddTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(GitCommitTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(GitLogTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(GitCheckoutTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(GitBranchTool(root_dir=str(self.root_dir)))

        # Diff/Preview tools (for change preview before applying)
        self.diff_preview_tool = DiffPreviewTool(root_dir=str(self.root_dir))
        self.tool_registry.register(self.diff_preview_tool)
        self.tool_registry.register(ApplyChangeTool(self.diff_preview_tool))
        self.tool_registry.register(RejectChangeTool(self.diff_preview_tool))

        # Bash/Execution tools
        self.tool_registry.register(BashTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(BashOutputTool())
        self.tool_registry.register(KillShellTool())
        self.tool_registry.register(SearchOutputTool())

        # Web tools
        self.tool_registry.register(WebFetchTool())
        search_api_key = os.getenv("SEARCH_API_KEY")
        self.tool_registry.register(WebSearchTool(api_key=search_api_key))
        self.tool_registry.register(WebScrapeTool())

        # Interactive tools
        self.tool_registry.register(AskUserQuestionTool())

        self.tool_registry.register(ConfirmTool())
        self.tool_registry.register(DisplayPanelTool())
        self.tool_registry.register(ProgressTool())

        # Todo tools
        self.todo_write_tool = TodoWriteTool(root_dir=str(self.root_dir))
        self.tool_registry.register(self.todo_write_tool)
        self.todo_read_tool = TodoReadTool(root_dir=str(self.root_dir))
        self.tool_registry.register(self.todo_read_tool)

        # Agent tools
        self.task_tool = TaskTool()  # Will be initialized with agent_orchestrator later
        self.tool_registry.register(self.task_tool)
        self.tool_registry.register(ExitPlanModeTool())
        
        # Hcode Tools
        self.tool_registry.register(TaskBoundaryTool())
        self.tool_registry.register(NotifyUserTool())

        # Notebook tools
        self.tool_registry.register(NotebookEditTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(NotebookReadTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(NotebookExecuteTool(root_dir=str(self.root_dir)))

        self.tool_registry.register(SlashCommandTool(self.command_registry))
        self.tool_registry.register(SkillTool(self.command_registry))

        # Register Hcode Aliases
        # These aliases map the tool names used in the Hcode prompt to Hcode's actual tools
        if "greptool" in self.tool_registry.tools:
            self.tool_registry.tools["grep_search"] = self.tool_registry.tools["greptool"]
            self.tool_registry.tools["codebase_search"] = self.tool_registry.tools["greptool"]
        
        if "readtool" in self.tool_registry.tools:
            self.tool_registry.tools["view_file"] = self.tool_registry.tools["readtool"]
            
        if "globtool" in self.tool_registry.tools:
            self.tool_registry.tools["find_files"] = self.tool_registry.tools["globtool"]

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters

        Returns:
            ToolResult
        """
        # Track usage
        self.usage_stats[tool_name] = self.usage_stats.get(tool_name, 0) + 1

        # Execute tool
        result = await self.tool_registry.execute_tool(tool_name, **kwargs)

        return result

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tool_registry.get_tool(name)

    def list_tools(self, category: Optional[str] = None) -> List[BaseTool]:
        """List available tools"""
        from .base_tool import ToolCategory

        if category:
            cat_enum = ToolCategory[category.upper()]
            return self.tool_registry.list_tools(category=cat_enum)
        return self.tool_registry.list_tools()

    def get_tool_schemas_for_provider(self, provider: str) -> List[Dict[str, Any]]:
        """
        Get tool schemas for a specific AI provider.

        Args:
            provider: Provider name (anthropic or openai)

        Returns:
            List of tool schemas
        """
        if provider.lower() == "anthropic":
            return self.tool_registry.get_anthropic_schemas()
        elif provider.lower() == "openai":
            return self.tool_registry.get_function_schemas()
        else:
            return []

    def get_usage_stats(self) -> Dict[str, int]:
        """Get tool usage statistics"""
        return self.usage_stats.copy()

    def get_tool_documentation(self) -> str:
        """Get formatted documentation for all tools"""
        doc = "# Available Tools\n\n"

        tools_by_category = {}
        for tool in self.tool_registry.list_tools():
            category = tool.category.value
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool)

        for category, tools in sorted(tools_by_category.items()):
            doc += f"## {category.replace('_', ' ').title()}\n\n"

            for tool in sorted(tools, key=lambda t: t.name):
                doc += f"### {tool.name}\n\n"
                doc += f"{tool.get_description()}\n\n"

                doc += "**Parameters:**\n\n"
                for param in tool.get_parameters():
                    required = " (required)" if param.required else ""
                    doc += f"- `{param.name}` ({param.type}){required}: {param.description}\n"

                doc += "\n"

        return doc

    async def read_file(self, file_path: str, **kwargs) -> ToolResult:
        """Convenience method for reading files"""
        return await self.execute_tool("readtool", file_path=file_path, **kwargs)

    async def write_file(self, file_path: str, content: str) -> ToolResult:
        """Convenience method for writing files"""
        return await self.execute_tool("writetool", file_path=file_path, content=content)

    async def edit_file(
        self, file_path: str, old_string: str, new_string: str, **kwargs
    ) -> ToolResult:
        """Convenience method for editing files"""
        return await self.execute_tool(
            "edittool", file_path=file_path, old_string=old_string, new_string=new_string, **kwargs
        )

    async def search_files(self, pattern: str, **kwargs) -> ToolResult:
        """Convenience method for searching files"""
        return await self.execute_tool("greptool", pattern=pattern, **kwargs)

    async def find_files(self, pattern: str, **kwargs) -> ToolResult:
        """Convenience method for finding files"""
        return await self.execute_tool("globtool", pattern=pattern, **kwargs)

    async def ask_user(self, questions: List[Dict[str, Any]]) -> ToolResult:
        """Convenience method for asking user questions"""
        return await self.execute_tool("askuserquestiontool", questions=questions)



    def set_agent_orchestrator(self, agent_orchestrator):
        """Set the agent orchestrator for the Task tool"""
        if hasattr(self, "task_tool"):
            self.task_tool.agent_orchestrator = agent_orchestrator

    async def web_fetch(self, url: str, prompt: str) -> ToolResult:
        """Convenience method for fetching web content"""
        return await self.execute_tool("webfetchtool", url=url, prompt=prompt)

    async def web_search(self, query: str, **kwargs) -> ToolResult:
        """Convenience method for web search"""
        return await self.execute_tool("websearchtool", query=query, **kwargs)

    # =========================================================================
    # CHANGE PREVIEW METHODS (NEW)
    # =========================================================================

    async def preview_edit(
        self, file_path: str, old_string: str, new_string: str, replace_all: bool = False
    ) -> ToolResult:
        """Preview an edit without applying it"""
        return await self.execute_tool(
            "diffpreviewtool",
            file_path=file_path,
            old_string=old_string,
            new_string=new_string,
            replace_all=replace_all,
        )

    async def preview_write(self, file_path: str, new_content: str) -> ToolResult:
        """Preview a file write without applying it"""
        return await self.execute_tool(
            "diffpreviewtool", file_path=file_path, new_content=new_content
        )

    async def apply_change(self, proposal_id: str, force: bool = False) -> ToolResult:
        """Apply a previously previewed change"""
        return await self.execute_tool("applychangetool", proposal_id=proposal_id, force=force)

    async def reject_change(self, proposal_id: str, reason: str = None) -> ToolResult:
        """Reject a previously previewed change"""
        return await self.execute_tool("rejectchangetool", proposal_id=proposal_id, reason=reason)

    def get_pending_proposals(self) -> Dict[str, Any]:
        """Get all pending change proposals"""
        if hasattr(self, "diff_preview_tool"):
            return self.diff_preview_tool._pending_proposals
        return {}

    def set_preview_mode(self, enabled: bool = True):
        """Enable or disable preview mode for edit/write operations"""
        edit_tool = self.get_tool("edittool")
        write_tool = self.get_tool("writetool")

        if edit_tool:
            edit_tool.preview_mode = enabled
        if write_tool:
            write_tool.preview_mode = enabled


class ToolExecutionContext:
    """
    Context manager for tool execution with safety checks.
    """

    def __init__(
        self,
        tool_manager: ToolManager,
        safety_enabled: bool = True,
        require_confirmation: bool = False,
        console=None,
    ):
        """
        Initialize execution context.

        Args:
            tool_manager: Tool manager instance
            safety_enabled: Enable safety checks
            require_confirmation: Require user confirmation for write operations
            console: Rich console for user interaction
        """
        self.tool_manager = tool_manager
        self.safety_enabled = safety_enabled
        self.require_confirmation = require_confirmation
        self.console = console
        self.execution_log: List[Dict[str, Any]] = []
        self.pending_operations: List[Dict[str, Any]] = []

    def add_pending_operation(self, tool_name: str, **kwargs):
        """Add operation to pending queue for batch confirmation"""
        self.pending_operations.append({"tool": tool_name, "params": kwargs})

    async def confirm_and_execute_pending(self) -> List[ToolResult]:
        """Show pending operations to user, get confirmation, and execute"""
        if not self.pending_operations:
            return []

        # Display pending operations
        if self.console:
            from rich.panel import Panel
            from rich.text import Text

            ops_text = Text()
            ops_text.append("📋 Pending Operations:\n\n", style="bold yellow")

            for i, op in enumerate(self.pending_operations, 1):
                tool = op["tool"]
                params = op["params"]

                ops_text.append(f"  {i}. ", style="bold")
                ops_text.append(f"{tool}\n", style="bold cyan")

                if tool.lower() == "writetool":
                    file_path = params.get("file_path", "unknown")
                    content_preview = params.get("content", "")[:100]
                    ops_text.append(f"     File: {file_path}\n", style="dim")
                    ops_text.append(f"     Content preview: {content_preview}...\n", style="dim")
                elif tool.lower() == "edittool":
                    file_path = params.get("file_path", "unknown")
                    old_preview = params.get("old_string", "")[:50]
                    new_preview = params.get("new_string", "")[:50]
                    ops_text.append(f"     File: {file_path}\n", style="dim")
                    ops_text.append(f"     Replace: {old_preview}...\n", style="red dim")
                    ops_text.append(f"     With: {new_preview}...\n", style="green dim")
                else:
                    for k, v in params.items():
                        preview = str(v)[:50]
                        ops_text.append(f"     {k}: {preview}\n", style="dim")

                ops_text.append("\n")

            self.console.print(
                Panel(ops_text, title="[bold]Confirm Operations[/bold]", border_style="yellow")
            )

            # Ask for confirmation (default is Yes - press Enter to accept)
            self.console.print(
                "[bold yellow]Execute these operations?[/bold yellow] [[green]Ok[/green]/n]: ",
                end="",
            )
            try:
                response = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                response = "n"

            # Default to "yes" if user just presses Enter
            if response == "":
                response = "y"

            if response not in ["y", "yes", "ok"]:
                self.console.print("[bold red]❌ Operations cancelled by user[/bold red]")
                self.pending_operations = []
                return []

        # Execute all pending operations
        results = []
        for op in self.pending_operations:
            result = await self.execute(op["tool"], skip_confirmation=True, **op["params"])
            results.append(result)

        self.pending_operations = []
        return results

    async def execute(
        self, tool_name: str, skip_confirmation: bool = False, **kwargs
    ) -> ToolResult:
        """Execute tool with logging and optional confirmation"""
        import time

        start_time = time.time()

        # Safety checks and confirmation for write operations
        if self.safety_enabled and self.require_confirmation and not skip_confirmation:
            if tool_name.lower() in ["writetool", "edittool", "multiedittool"]:
                # Add to pending operations instead of executing immediately
                self.add_pending_operation(tool_name, **kwargs)
                return ToolResult(
                    success=True,
                    output=f"Operation queued for confirmation: {tool_name}",
                    metadata={"queued": True, "tool": tool_name},
                )

        # Execute tool
        result = await self.tool_manager.execute_tool(tool_name, **kwargs)

        # Log execution
        self.execution_log.append(
            {
                "tool": tool_name,
                "params": kwargs,
                "success": result.success,
                "duration": time.time() - start_time,
                "error": result.error,
            }
        )

        return result

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get execution log"""
        return self.execution_log.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        return {
            "total_executions": len(self.execution_log),
            "successful": sum(1 for log in self.execution_log if log["success"]),
            "failed": sum(1 for log in self.execution_log if not log["success"]),
            "total_duration": sum(log["duration"] for log in self.execution_log),
            "tools_used": list(set(log["tool"] for log in self.execution_log)),
            "pending_operations": len(self.pending_operations),
        }
