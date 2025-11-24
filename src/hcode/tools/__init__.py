"""
Comprehensive tool system for Hcode.
Includes file operations, web tools, interactive features, and more.
"""

from .executor import ToolExecutor, ExecutionResult
from .base_tool import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ToolRegistry,
    ToolCategory
)
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
from .command_system import (
    SlashCommandTool,
    SkillTool,
    CommandRegistry,
    SlashCommand,
    Skill,
    HookSystem
)
from .tool_manager import ToolManager, ToolExecutionContext

__all__ = [
    # Core
    "ToolExecutor",
    "ExecutionResult",
    "BaseTool",
    "ToolResult",
    "ToolParameter",
    "ToolRegistry",
    "ToolCategory",

    # File Tools
    "ReadTool",
    "WriteTool",
    "EditTool",
    "MultiEditTool",
    "GlobTool",
    "GrepTool",

    # Bash/Execution Tools
    "BashTool",
    "BashOutputTool",
    "KillShellTool",
    "LSTool",

    # Agent Tools
    "TaskTool",
    "ExitPlanModeTool",
    "TodoReadTool",

    # Web Tools
    "WebFetchTool",
    "WebSearchTool",
    "WebScrapeTool",

    # Interactive Tools
    "AskUserQuestionTool",
    "TodoWriteTool",
    "ConfirmTool",
    "DisplayPanelTool",
    "ProgressTool",

    # Notebook Tools
    "NotebookEditTool",
    "NotebookReadTool",
    "NotebookExecuteTool",

    # Command System
    "SlashCommandTool",
    "SkillTool",
    "CommandRegistry",
    "SlashCommand",
    "Skill",
    "HookSystem",

    # Manager
    "ToolManager",
    "ToolExecutionContext",
]

