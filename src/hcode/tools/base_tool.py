"""
Base tool interface for Hcode tool system.
Inspired by Hcode's sophisticated tool architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ToolCategory(Enum):
    """Categories of tools"""
    FILE_OPERATION = "file_operation"
    FILE_OPERATIONS = "file_operations"  # Alias for compatibility
    CODE_EXECUTION = "code_execution"
    EXECUTION = "execution"  # Alias for compatibility
    SEARCH = "search"
    WEB = "web"
    INTERACTIVE = "interactive"
    ANALYSIS = "analysis"
    AGENT = "agent"
    PLANNING = "planning"
    CUSTOM = "custom"


@dataclass
class ToolParameter:
    """Tool parameter specification"""
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None


@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        if self.success:
            return f"Success: {self.output}"
        else:
            return f"Error: {self.error}"


class BaseTool(ABC):
    """Base class for all tools"""

    def __init__(self):
        self.name = self.__class__.__name__
        self.category = ToolCategory.CUSTOM

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.

        Returns:
            ToolResult with execution results
        """
        pass

    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """
        Get tool parameter specifications.

        Returns:
            List of parameter specifications
        """
        pass

    def get_description(self) -> str:
        """Get tool description"""
        return self.__doc__ or "No description available"

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate provided parameters.

        Returns:
            Tuple of (is_valid, error_message)
        """
        params = {p.name: p for p in self.get_parameters()}

        # Check required parameters
        for param_name, param_spec in params.items():
            if param_spec.required and param_name not in kwargs:
                return False, f"Missing required parameter: {param_name}"

        # NOTE: We intentionally don't fail on unknown parameters
        # to be more lenient with different model outputs.
        # Unknown parameters will simply be ignored by the tool.

        return True, None

    def to_function_schema(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling schema.

        Returns:
            Function schema dictionary
        """
        properties = {}
        required = []

        for param in self.get_parameters():
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                required.append(param.name)

        return {
            "name": self.name.lower(),
            "description": self.get_description(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

    def to_anthropic_tool_schema(self) -> Dict[str, Any]:
        """
        Convert tool to Anthropic tool use schema.

        Returns:
            Tool schema dictionary
        """
        input_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param in self.get_parameters():
            input_schema["properties"][param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                input_schema["required"].append(param.name)

        return {
            "name": self.name.lower(),
            "description": self.get_description(),
            "input_schema": input_schema
        }


class ToolRegistry:
    """Registry for managing available tools"""

    # Tool name aliases for common variations
    # Maps alternate names -> canonical registered name (lowercase class name)
    # Example: 'read' -> 'readtool' (because ReadTool is registered as 'readtool')
    TOOL_ALIASES = {
        # ===== FILE OPERATIONS =====
        # LSTool - registered as 'lstool'
        'ls': 'lstool',
        'list': 'lstool',
        'listdir': 'lstool',
        'list_directory': 'lstool',
        'directory_list': 'lstool',

        # ReadTool - registered as 'readtool'
        'read': 'readtool',
        'readfile': 'readtool',
        'read_file': 'readtool',
        'file_read': 'readtool',
        'get_file': 'readtool',
        'cat': 'readtool',

        # WriteTool - registered as 'writetool'
        'write': 'writetool',
        'writefile': 'writetool',
        'write_file': 'writetool',
        'file_write': 'writetool',
        'create_file': 'writetool',
        'save_file': 'writetool',

        # EditTool - registered as 'edittool'
        'edit': 'edittool',
        'editfile': 'edittool',
        'edit_file': 'edittool',
        'file_edit': 'edittool',
        'modify_file': 'edittool',
        'str_replace': 'edittool',
        'string_replace': 'edittool',

        # MultiEditTool - registered as 'multiedittool'
        'multiedit': 'multiedittool',
        'multi_edit': 'multiedittool',
        'multi_edit_tool': 'multiedittool',
        'batch_edit': 'multiedittool',

        # ===== SEARCH OPERATIONS =====
        # GlobTool - registered as 'globtool'
        'glob': 'globtool',
        'findfiles': 'globtool',
        'find_files': 'globtool',
        'file_glob': 'globtool',
        'pattern_search': 'globtool',

        # GrepTool - registered as 'greptool'
        'grep': 'greptool',
        'search': 'greptool',
        'searchfiles': 'greptool',
        'search_files': 'greptool',
        'content_search': 'greptool',
        'search_content': 'greptool',
        'ripgrep': 'greptool',
        'rg': 'greptool',

        # ===== EXECUTION =====
        # BashTool - registered as 'bashtool'
        'bash': 'bashtool',
        'shell': 'bashtool',
        'exec': 'bashtool',
        'execute': 'bashtool',
        'run_command': 'bashtool',
        'bash_execute': 'bashtool',
        'execute_bash': 'bashtool',
        'run_bash': 'bashtool',
        'terminal': 'bashtool',
        'cmd': 'bashtool',
        'command': 'bashtool',

        # BashOutputTool - registered as 'bashoutputtool'
        'bashoutput': 'bashoutputtool',
        'bash_output': 'bashoutputtool',
        'get_output': 'bashoutputtool',

        # KillShellTool - registered as 'killshelltool'
        'killshell': 'killshelltool',
        'kill_shell': 'killshelltool',
        'stop_shell': 'killshelltool',

        # ===== WEB OPERATIONS =====
        # WebFetchTool - registered as 'webfetchtool'
        'webfetch': 'webfetchtool',
        'fetch': 'webfetchtool',
        'web_fetch': 'webfetchtool',
        'fetch_url': 'webfetchtool',
        'get_url': 'webfetchtool',
        'http_get': 'webfetchtool',

        # WebSearchTool - registered as 'websearchtool'
        'websearch': 'websearchtool',
        'web_search': 'websearchtool',
        'search_web': 'websearchtool',
        'google': 'websearchtool',
        'internet_search': 'websearchtool',

        # WebScrapeTool - registered as 'webscrapetool'
        'webscrape': 'webscrapetool',
        'scrape': 'webscrapetool',
        'web_scrape': 'webscrapetool',

        # ===== TASK MANAGEMENT =====
        # TodoWriteTool - registered as 'todowritetool'
        'todowrite': 'todowritetool',
        'updatetodos': 'todowritetool',
        'update_todos': 'todowritetool',
        'todo_write': 'todowritetool',
        'write_todos': 'todowritetool',
        'set_todos': 'todowritetool',

        # TodoReadTool - registered as 'todoreadtool'
        'todoread': 'todoreadtool',
        'gettodos': 'todoreadtool',
        'get_todos': 'todoreadtool',
        'todo_read': 'todoreadtool',
        'read_todos': 'todoreadtool',

        # ===== INTERACTIVE =====
        # AskUserQuestionTool - registered as 'askuserquestiontool'
        'askuserquestion': 'askuserquestiontool',
        'askuser': 'askuserquestiontool',
        'ask': 'askuserquestiontool',
        'ask_user': 'askuserquestiontool',
        'ask_question': 'askuserquestiontool',
        'prompt_user': 'askuserquestiontool',
        'user_input': 'askuserquestiontool',

        # ===== AGENTS =====
        # TaskTool - registered as 'tasktool'
        'task': 'tasktool',
        'createtask': 'tasktool',
        'create_task': 'tasktool',
        'spawn_agent': 'tasktool',
        'delegate': 'tasktool',
        'subagent': 'tasktool',
        'sub_agent': 'tasktool',

        # ExitPlanModeTool - registered as 'exitplanmodetool'
        'exitplanmode': 'exitplanmodetool',
        'exit_plan_mode': 'exitplanmodetool',

        # ===== NOTEBOOKS =====
        # NotebookEditTool - registered as 'notebookedittool'
        'notebookedit': 'notebookedittool',
        'notebook_edit': 'notebookedittool',
        'edit_notebook': 'notebookedittool',
        'jupyter_edit': 'notebookedittool',

        # NotebookReadTool - registered as 'notebookreadtool'
        'notebookread': 'notebookreadtool',
        'notebook_read': 'notebookreadtool',
        'read_notebook': 'notebookreadtool',
        'jupyter_read': 'notebookreadtool',

        # NotebookExecuteTool - registered as 'notebookexecutetool'
        'notebookexecute': 'notebookexecutetool',
        'notebook_execute': 'notebookexecutetool',
        'run_notebook': 'notebookexecutetool',
        'jupyter_execute': 'notebookexecutetool',

        # ===== COMMAND SYSTEM =====
        # SlashCommandTool - registered as 'slashcommandtool'
        'slashcommand': 'slashcommandtool',
        'slash_command': 'slashcommandtool',

        # SkillTool - registered as 'skilltool'
        'skill': 'skilltool',

        # ===== OTHERS =====
        # ConfirmTool - registered as 'confirmtool'
        'confirm': 'confirmtool',

        # DisplayPanelTool - registered as 'displaypaneltool'
        'displaypanel': 'displaypaneltool',
        'display_panel': 'displaypaneltool',

        # ProgressTool - registered as 'progresstool'
        'progress': 'progresstool',
    }

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.name.lower()] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name, supporting extensive aliasing for model compatibility.

        Resolution order:
        1. Direct lookup (exact match)
        2. Alias lookup from TOOL_ALIASES
        3. Strip 'Tool' suffix (e.g., 'ReadTool' -> 'read')
        4. Snake_case to lowercase (e.g., 'file_read' -> 'fileread')
        5. CamelCase to lowercase (e.g., 'FileRead' -> 'fileread')
        6. Fuzzy matching for common patterns
        """
        if not name:
            return None

        name_lower = name.lower().strip()

        # 1. Direct lookup
        tool = self.tools.get(name_lower)
        if tool:
            return tool

        # 2. Alias lookup
        canonical_name = self.TOOL_ALIASES.get(name_lower)
        if canonical_name:
            tool = self.tools.get(canonical_name)
            if tool:
                return tool

        # 3. Strip 'tool' suffix if present
        if name_lower.endswith('tool'):
            base_name = name_lower[:-4]
            tool = self.tools.get(base_name)
            if tool:
                return tool
            # Also check alias for base name
            canonical_name = self.TOOL_ALIASES.get(base_name)
            if canonical_name:
                tool = self.tools.get(canonical_name)
                if tool:
                    return tool

        # 4. Try removing underscores (snake_case normalization)
        normalized = name_lower.replace('_', '')
        tool = self.tools.get(normalized)
        if tool:
            return tool

        # Also check alias for normalized name
        canonical_name = self.TOOL_ALIASES.get(normalized)
        if canonical_name:
            tool = self.tools.get(canonical_name)
            if tool:
                return tool

        # 5. Try CamelCase to lowercase conversion
        import re
        # Convert CamelCase to lowercase (e.g., FileRead -> fileread)
        camel_converted = re.sub(r'(?<!^)(?=[A-Z])', '', name).lower()
        tool = self.tools.get(camel_converted)
        if tool:
            return tool

        # 6. Fuzzy matching for common prefixes/suffixes
        # Try stripping common prefixes
        for prefix in ['run_', 'execute_', 'do_', 'perform_']:
            if name_lower.startswith(prefix):
                stripped = name_lower[len(prefix):]
                tool = self.tools.get(stripped)
                if tool:
                    return tool
                canonical_name = self.TOOL_ALIASES.get(stripped)
                if canonical_name:
                    tool = self.tools.get(canonical_name)
                    if tool:
                        return tool

        return None

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[BaseTool]:
        """List all tools, optionally filtered by category"""
        if category:
            return [t for t in self.tools.values() if t.category == category]
        return list(self.tools.values())

    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI function schemas for all tools"""
        return [tool.to_function_schema() for tool in self.tools.values()]

    def get_anthropic_schemas(self) -> List[Dict[str, Any]]:
        """Get Anthropic tool schemas for all tools"""
        return [tool.to_anthropic_tool_schema() for tool in self.tools.values()]

    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get_tool(name)

        if not tool:
            return ToolResult(
                success=False,
                output=None,
                error=f"Tool not found: {name}"
            )

        # Validate parameters
        is_valid, error = tool.validate_parameters(**kwargs)
        if not is_valid:
            return ToolResult(
                success=False,
                output=None,
                error=error
            )

        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
