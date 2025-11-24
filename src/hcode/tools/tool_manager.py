"""
Tool Manager for Hcode.
Initializes and manages all available tools.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from .base_tool import ToolRegistry, BaseTool, ToolResult
from .file_tools import ReadTool, WriteTool, EditTool, MultiEditTool, GlobTool, GrepTool
from .bash_tools import BashTool, BashOutputTool, KillShellTool, LSTool
from .agent_tools import TaskTool, ExitPlanModeTool, TodoReadTool
from .web_tools import WebFetchTool, WebSearchTool, WebScrapeTool
from .interactive_tools import (
    AskUserQuestionTool,
    TodoWriteTool,
    ConfirmTool,
    DisplayPanelTool,
    ProgressTool
)
from .notebook_tools import NotebookEditTool, NotebookReadTool, NotebookExecuteTool
from .command_system import SlashCommandTool, SkillTool, CommandRegistry
from .executor import ToolExecutor


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

        # Bash/Execution tools
        self.tool_registry.register(BashTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(BashOutputTool())
        self.tool_registry.register(KillShellTool())

        # Web tools
        self.tool_registry.register(WebFetchTool())
        search_api_key = os.getenv("SEARCH_API_KEY")
        self.tool_registry.register(WebSearchTool(api_key=search_api_key))
        self.tool_registry.register(WebScrapeTool())

        # Interactive tools
        self.tool_registry.register(AskUserQuestionTool())
        self.todo_write_tool = TodoWriteTool()
        self.tool_registry.register(self.todo_write_tool)
        self.todo_read_tool = TodoReadTool()
        self.tool_registry.register(self.todo_read_tool)
        self.tool_registry.register(ConfirmTool())
        self.tool_registry.register(DisplayPanelTool())
        self.tool_registry.register(ProgressTool())

        # Agent tools
        self.task_tool = TaskTool()  # Will be initialized with agent_orchestrator later
        self.tool_registry.register(self.task_tool)
        self.tool_registry.register(ExitPlanModeTool())

        # Notebook tools
        self.tool_registry.register(NotebookEditTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(NotebookReadTool(root_dir=str(self.root_dir)))
        self.tool_registry.register(NotebookExecuteTool(root_dir=str(self.root_dir)))

        # Command system tools
        self.tool_registry.register(SlashCommandTool(self.command_registry))
        self.tool_registry.register(SkillTool(self.command_registry))

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

    async def edit_file(self, file_path: str, old_string: str, new_string: str, **kwargs) -> ToolResult:
        """Convenience method for editing files"""
        return await self.execute_tool(
            "edittool",
            file_path=file_path,
            old_string=old_string,
            new_string=new_string,
            **kwargs
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

    async def update_todos(self, todos: List[Dict[str, str]]) -> ToolResult:
        """Convenience method for updating todos"""
        result = await self.execute_tool("todowritetool", todos=todos)
        # Sync todos to TodoRead tool
        if hasattr(self, 'todo_read_tool'):
            self.todo_read_tool.set_todos(todos)
        return result

    async def read_todos(self) -> ToolResult:
        """Convenience method for reading todos"""
        return await self.execute_tool("todoreadtool")

    def set_agent_orchestrator(self, agent_orchestrator):
        """Set the agent orchestrator for the Task tool"""
        if hasattr(self, 'task_tool'):
            self.task_tool.agent_orchestrator = agent_orchestrator

    async def web_fetch(self, url: str, prompt: str) -> ToolResult:
        """Convenience method for fetching web content"""
        return await self.execute_tool("webfetchtool", url=url, prompt=prompt)

    async def web_search(self, query: str, **kwargs) -> ToolResult:
        """Convenience method for web search"""
        return await self.execute_tool("websearchtool", query=query, **kwargs)


class ToolExecutionContext:
    """
    Context manager for tool execution with safety checks.
    """

    def __init__(self, tool_manager: ToolManager, safety_enabled: bool = True):
        """
        Initialize execution context.

        Args:
            tool_manager: Tool manager instance
            safety_enabled: Enable safety checks
        """
        self.tool_manager = tool_manager
        self.safety_enabled = safety_enabled
        self.execution_log: List[Dict[str, Any]] = []

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute tool with logging"""
        import time

        start_time = time.time()

        # Safety checks
        if self.safety_enabled:
            # Check for destructive operations
            if tool_name.lower() in ["writetool", "edittool"]:
                # Could add confirmation here
                pass

        # Execute tool
        result = await self.tool_manager.execute_tool(tool_name, **kwargs)

        # Log execution
        self.execution_log.append({
            "tool": tool_name,
            "params": kwargs,
            "success": result.success,
            "duration": time.time() - start_time,
            "error": result.error
        })

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
            "tools_used": list(set(log["tool"] for log in self.execution_log))
        }
