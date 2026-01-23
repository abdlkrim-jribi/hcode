"""
Comprehensive tool system for Hcode.
Includes file operations, web tools, interactive features, and more.
"""
# Python files in this directory:
# - hcode_tools.py
# - file_tools.py
# - fuzzy_edit_tool.py
# - command_system.py
# - git_tools.py
# - notebook_tools.py
# - todo_write.py
# - validator.py
# - tool_manager.py
# - bash_tools.py
# - interactive_tools.py
# - __init__.py
# - base_tool.py
# - web_tools.py
# - executor.py
# - diff_tools.py
# - tool_callbacks.py
# - parallel_executor.py
# - agent_tools.py
# - tool_selector.py

from hcode.tools.agent_tools import TaskTool, ExitPlanModeTool, TodoReadTool
from hcode.tools.base_tool import BaseTool, ToolResult, ToolParameter, ToolRegistry, ToolCategory
from hcode.tools.bash_tools import BashTool, BashOutputTool, KillShellTool, LSTool, SearchOutputTool
from hcode.tools.command_system import (
    SlashCommandTool,
    SkillTool,
    CommandRegistry,
    SlashCommand,
    Skill,
    HookSystem,
)
from hcode.tools.diff_tools import (
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
from hcode.tools.executor import ToolExecutor, ExecutionResult
from hcode.tools.file_tools import ReadTool, WriteTool, EditTool, MultiEditTool, GlobTool, GrepTool
from hcode.tools.interactive_tools import (
    AskUserQuestionTool,
    TodoWriteTool,
    ConfirmTool,
    DisplayPanelTool,
    ProgressTool,
)
from hcode.tools.notebook_tools import NotebookEditTool, NotebookReadTool, NotebookExecuteTool
from hcode.tools.tool_callbacks import (
    ToolCallbackManager,
    ToolEvent,
    ToolEventType,
    ToolCallback,
    CallbackContext,
    get_callback_manager,
)
from hcode.tools.tool_manager import ToolManager, ToolExecutionContext
from hcode.tools.tool_selector import (
    ToolSelectionEngine,
    ToolSuccessTracker,
    ToolSelectionRules,
    ToolSelection,
    ToolContext,
    TaskCategory,
    get_tool_selector,
    select_tools_for_task,
)
from hcode.tools.web_tools import WebFetchTool, WebSearchTool, WebScrapeTool
from hcode.tools.validator import ToolCallValidator, ValidationResult

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
