"""
Comprehensive tool system for Hcode.
Includes file operations, web tools, interactive features, and more.
"""

from hcode.tools.system.agent_tools import TaskTool, ExitPlanModeTool
from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolRegistry, ToolCategory
from hcode.tools.terminal.bash_tools import BashTool, BashOutputTool, KillShellTool, LSTool, SearchOutputTool
from hcode.tools.system.command_system import (
    SlashCommandTool,
    SkillTool,
    CommandRegistry,
    SlashCommand,
    Skill,
    HookSystem,
)
from hcode.tools.files.diff_tools import (
    DiffPreviewTool,
    ApplyChangeTool,
    RejectChangeTool,
    ChangeProposal,
    ChangeOperation,
    ChangeStatus,
    DiffLine,
    DiffHunk,
    SafetyWarning,
    ChangeSet,
)
from hcode.tools.core.executor import ToolExecutor, ExecutionResult
from hcode.tools.files.file_tools import ReadTool, WriteTool, EditTool, MultiEditTool, GlobTool, GrepTool
from hcode.tools.notebook.interactive_tools import (
    AskUserQuestionTool,
    ConfirmTool,
    DisplayPanelTool,
    ProgressTool,
)
from hcode.tools.notebook.notebook_tools import NotebookEditTool, NotebookReadTool, NotebookExecuteTool
from hcode.tools.core.tool_callbacks import (
    ToolCallbackManager,
    ToolEvent,
    ToolEventType,
    ToolCallback,
    CallbackContext,
    get_callback_manager,
)
from hcode.tools.core.tool_manager import ToolManager, ToolExecutionContext
from hcode.tools.core.tool_selector import (
    ToolSelectionEngine,
    ToolSuccessTracker,
    ToolSelectionRules,
    ToolSelection,
    ToolContext,
    TaskCategory,
    get_tool_selector,
    select_tools_for_task,
)
from hcode.tools.web.web_tools import WebFetchTool, WebSearchTool, WebScrapeTool
from hcode.tools.core.validator import ToolCallValidator, ValidationResult

__all__ = [
    # Core
    "ToolExecutor",
    "ExecutionResult",
    "BaseTool",
    "ToolResult",
    "ToolParameter",
    "ToolRegistry",
    "ToolCategory",
    # Validation
    "ToolCallValidator",
    "ValidationResult",
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
    "SearchOutputTool",
    # Agent Tools
    "TaskTool",
    "ExitPlanModeTool",
    # Web Tools
    "WebFetchTool",
    "WebSearchTool",
    "WebScrapeTool",
    # Interactive Tools
    "AskUserQuestionTool",
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
    # Diff/Preview Tools
    "DiffPreviewTool",
    "ApplyChangeTool",
    "RejectChangeTool",
    "ChangeProposal",
    "ChangeOperation",
    "ChangeStatus",
    "DiffLine",
    "DiffHunk",
    "SafetyWarning",
    "ChangeSet",
    # Tool Selection
    "ToolSelectionEngine",
    "ToolSuccessTracker",
    "ToolSelectionRules",
    "ToolSelection",
    "ToolContext",
    "TaskCategory",
    "get_tool_selector",
    "select_tools_for_task",
    # Tool Callbacks (for real-time UI updates)
    "ToolCallbackManager",
    "ToolEvent",
    "ToolEventType",
    "ToolCallback",
    "CallbackContext",
    "get_callback_manager",
]
