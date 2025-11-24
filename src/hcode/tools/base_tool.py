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

        # Check unknown parameters
        for provided_param in kwargs:
            if provided_param not in params:
                return False, f"Unknown parameter: {provided_param}"

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

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.name.lower()] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(name.lower())

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
