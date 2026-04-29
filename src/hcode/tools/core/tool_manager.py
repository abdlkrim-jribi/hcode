"""
Tool Manager for Hcode.
Initializes and manages all available tools.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from hcode.tools.analysis.outline_tool import ViewFileOutlineTool
from hcode.tools.base.base_tool import ToolRegistry, BaseTool, ToolResult
from hcode.tools.files.diff_tools import DiffPreviewTool, ApplyChangeTool, RejectChangeTool
from hcode.tools.files.file_tools import ReadTool, WriteTool, EditTool, MultiEditTool, GrepTool
from hcode.tools.files.fuzzy_edit_tool import FuzzyEditTool
from hcode.tools.files.smart_glob_tool import SmartGlobTool
from hcode.tools.git.git_tools import (
    GitStatusTool,
    GitDiffTool,
    GitAddTool,
    GitCommitTool,
    GitLogTool,
    GitCheckoutTool,
    GitBranchTool,
)
from hcode.tools.notebook.interactive_tools import (
    AskUserQuestionTool,
    ConfirmTool,
    DisplayPanelTool,
    ProgressTool,
)
from hcode.tools.notebook.notebook_tools import NotebookEditTool, NotebookReadTool, NotebookExecuteTool
from hcode.tools.system.agent_tools import TaskTool, ExitPlanModeTool
from hcode.tools.system.command_system import SlashCommandTool, SkillTool, CommandRegistry, WorkflowTool
from hcode.tools.system.hcode_tools import TaskBoundaryTool, NotifyUserTool
from hcode.tools.terminal.bash_tools import BashTool, BashOutputTool, KillShellTool, LSTool, SearchOutputTool
from hcode.tools.todo.todo_read import TodoReadTool
from hcode.tools.todo.todo_write import TodoWriteTool
from hcode.tools.web.web_tools import WebFetchTool, WebSearchTool, WebScrapeTool
from hcode.core.mcp import MCPClientManager, MCPToolRegistry, MCPConfigManager


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
        self.mcp_config_manager = MCPConfigManager(root_dir=str(self.root_dir))
        self.mcp_client_manager = MCPClientManager(self.mcp_config_manager)
        self.mcp_tool_registry = MCPToolRegistry(self.mcp_client_manager, self)

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
        # Use SmartGlobTool with context protection (Claude Code approach)
        self.tool_registry.register(SmartGlobTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(GrepTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(LSTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(FuzzyEditTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(ViewFileOutlineTool(root_dir=str(self.root_dir)))

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
        self.tool_registry.register(WorkflowTool(self.command_registry))

        # Register Hcode Aliases
        # These aliases map the tool names used in the Hcode prompt to Hcode's actual tools
        if "greptool" in self.tool_registry.tools:
            self.tool_registry.tools["grep_search"] = self.tool_registry.tools["greptool"]
            self.tool_registry.tools["codebase_search"] = self.tool_registry.tools["greptool"]

        if "readtool" in self.tool_registry.tools:
            self.tool_registry.tools["view_file"] = self.tool_registry.tools["readtool"]

        if "writetool" in self.tool_registry.tools:
            self.tool_registry.tools["write_to_file"] = self.tool_registry.tools["writetool"]

        if "edittool" in self.tool_registry.tools:
            self.tool_registry.tools["replace_file_content"] = self.tool_registry.tools["edittool"]

        if "globtool" in self.tool_registry.tools:
            self.tool_registry.tools["find_files"] = self.tool_registry.tools["globtool"]
            self.tool_registry.tools["find_by_name"] = self.tool_registry.tools["globtool"]

        if "bash" in self.tool_registry.tools:
            self.tool_registry.tools["run_command"] = self.tool_registry.tools["bash"]

        if "viewfileoutlinetool" in self.tool_registry.tools:
            self.tool_registry.tools["view_file_outline"] = self.tool_registry.tools["viewfileoutlinetool"]

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
        from hcode.tools.base.base_tool import ToolCategory

        if category:
            cat_enum = ToolCategory[category.upper()]
            return self.tool_registry.list_tools(category=cat_enum)
        return self.tool_registry.list_tools()

    def get_tool_documentation(self) -> str:
        """
        Generate documentation for all registered tools in a format suitable for the system prompt.
        
        Returns:
            String containing formatted tool documentation with JSON usage examples.
        """
        doc_parts = []

        # Get all registered tools
        # We access the internal dictionary to get aliases properly
        tools_map = self.tool_registry.tools

        # Sort by name for consistency
        sorted_names = sorted(tools_map.keys())

        for name in sorted_names:
            tool = tools_map[name]
            schema = tool.to_function_schema()

            # Construct JSON example
            params = {}
            for param_name, param_info in schema.get("parameters", {}).get("properties", {}).items():
                # specific example values based on param type or name
                val = "value"
                if "directory" in param_name.lower():
                    val = "absolute/path/to/dir"
                elif "path" in param_name.lower() or "file" in param_name.lower():
                    val = "absolute/path/to/file"
                elif "line" in param_name.lower():
                    val = 10
                elif param_info.get("type") == "boolean":
                    val = False
                elif param_info.get("type") == "integer":
                    val = 1

                params[param_name] = val

            example_json = {
                "tool": name,
                "parameters": params
            }

            import json
            json_str = json.dumps(example_json)

            doc_parts.append(f"**{name}** ({tool.__class__.__name__}) - {schema.get('description', '')}:")
            doc_parts.append(f"```json\n{json_str}\n```\n")

        return "\n".join(doc_parts)

    def get_usage_stats(self) -> Dict[str, int]:
        """Get tool usage statistics"""
        return self.usage_stats.copy()

    def set_agent_orchestrator(self, agent_orchestrator):
        """Set the agent orchestrator for tools that need it"""
        if hasattr(self, "task_tool"):
            self.task_tool.agent_orchestrator = agent_orchestrator

        # Also set for SkillTool
        skill_tool = self.get_tool("skilltool")
        if skill_tool:
            skill_tool.agent_orchestrator = agent_orchestrator

    async def connect_mcp_servers(self):
        """Connect all configured MCP servers and register their tools."""
        await self.mcp_client_manager.connect_all()
        await self.mcp_tool_registry.register_all_mcp_tools()

    def get_mcp_status(self) -> dict:
        """Return MCP connection status."""
        return {
            "connected_servers": self.mcp_client_manager.get_connected_servers(),
            "mcp_tools": self.mcp_tool_registry.get_mcp_tool_names(),
        }

    # =========================================================================
    # CHANGE PREVIEW METHODS (NEW)
    # =========================================================================
