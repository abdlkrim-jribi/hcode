"""
Tool Configuration Loader for Hcode.

Loads tool definitions from external YAML configuration (config/tools.yaml)
to match Hcode tool specifications exactly.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List

import yaml


@dataclass
class ToolParameter:
    """Tool parameter definition"""

    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None


@dataclass
class ToolDefinition:
    """Tool definition matching Hcode format"""

    name: str
    description: str
    parameters: List[ToolParameter]

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema"""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {"type": param.type, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description.strip(),
                "parameters": {"type": "object", "properties": properties, "required": required},
            },
        }

    def to_anthropic_schema(self) -> Dict[str, Any]:
        """Convert to Anthropic tool schema"""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {"type": param.type, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description.strip(),
            "input_schema": {"type": "object", "properties": properties, "required": required},
        }


class ToolsConfig:
    """
    Centralized tool configuration loader.

    Loads tool definitions from config/tools.yaml and provides
    schemas for different AI providers.
    """

    _instance: Optional["ToolsConfig"] = None
    _tools_data: Dict[str, Any] = {}
    _config_path: Optional[Path] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_tools()
        return cls._instance

    def _find_config_path(self) -> Optional[Path]:
        """Find the tools configuration file"""
        env_path = os.getenv("HCODE_TOOLS_CONFIG")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        search_paths = [
            Path.cwd() / "config" / "tools.yaml",
            Path.cwd() / "tools.yaml",
            Path(__file__).parent.parent.parent.parent / "config" / "tools.yaml",
            Path.home() / ".hcode" / "tools.yaml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _load_tools(self):
        """Load tools from YAML file"""
        self._config_path = self._find_config_path()

        if self._config_path and self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._tools_data = yaml.safe_load(f) or {}
        else:
            self._tools_data = self._get_default_tools()

    def _get_default_tools(self) -> Dict[str, Any]:
        """Return default tool definitions if no config file exists"""
        return {
            "tools": {
                "Read": {
                    "name": "Read",
                    "description": "Reads a file from the local filesystem.",
                    "parameters": {
                        "file_path": {
                            "type": "string",
                            "description": "The absolute path to the file to read",
                            "required": True,
                        }
                    },
                },
                "Write": {
                    "name": "Write",
                    "description": "Write a file to the local filesystem.",
                    "parameters": {
                        "file_path": {
                            "type": "string",
                            "description": "The absolute path to the file to write",
                            "required": True,
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write",
                            "required": True,
                        },
                    },
                },
            }
        }

    def reload(self):
        """Reload tools from file"""
        self._load_tools()

    @property
    def config_path(self) -> Optional[Path]:
        """Get the path to the loaded config file"""
        return self._config_path

    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get a tool definition by name"""
        tools = self._tools_data.get("tools", {})
        tool_data = tools.get(tool_name)

        if not tool_data:
            return None

        parameters = []
        for param_name, param_data in tool_data.get("parameters", {}).items():
            parameters.append(
                ToolParameter(
                    name=param_name,
                    type=param_data.get("type", "string"),
                    description=param_data.get("description", ""),
                    required=param_data.get("required", True),
                    enum=param_data.get("enum"),
                )
            )

        return ToolDefinition(
            name=tool_data.get("name", tool_name),
            description=tool_data.get("description", ""),
            parameters=parameters,
        )

    def get_all_tool_definitions(self) -> List[ToolDefinition]:
        """Get all tool definitions"""
        tools = self._tools_data.get("tools", {})
        definitions = []

        for tool_name in tools:
            defn = self.get_tool_definition(tool_name)
            if defn:
                definitions.append(defn)

        return definitions

    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return list(self._tools_data.get("tools", {}).keys())

    def get_openai_schemas(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get OpenAI function calling schemas for specified tools (or all)"""
        schemas = []
        definitions = self.get_all_tool_definitions()

        for defn in definitions:
            if tool_names is None or defn.name in tool_names:
                schemas.append(defn.to_openai_schema())

        return schemas

    def get_anthropic_schemas(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get Anthropic tool schemas for specified tools (or all)"""
        schemas = []
        definitions = self.get_all_tool_definitions()

        for defn in definitions:
            if tool_names is None or defn.name in tool_names:
                schemas.append(defn.to_anthropic_schema())

        return schemas

    def get_tool_documentation(self) -> str:
        """Get formatted tool documentation for system prompt"""
        tools = self._tools_data.get("tools", {})
        docs = ["## Available Tools\n"]

        for tool_name, tool_data in tools.items():
            docs.append(f"### {tool_name}\n")
            docs.append(tool_data.get("description", "").strip())
            docs.append("\n")

        return "\n".join(docs)

    def get_banned_commands(self) -> List[str]:
        """Get list of banned bash commands"""
        policy = self._tools_data.get("policy", {})
        return policy.get("banned_commands", [])

    def get_prefer_tools_over_bash(self) -> Dict[str, str]:
        """Get mapping of bash commands that should use tools instead"""
        policy = self._tools_data.get("policy", {})
        return policy.get("prefer_tools_over_bash", {})


# Convenience functions
def get_tools_config() -> ToolsConfig:
    """Get the tools configuration singleton"""
    return ToolsConfig()


def get_tool_schemas_for_openai(tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Get OpenAI schemas for tools"""
    return get_tools_config().get_openai_schemas(tool_names)


def get_tool_schemas_for_anthropic(tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Get Anthropic schemas for tools"""
    return get_tools_config().get_anthropic_schemas(tool_names)
