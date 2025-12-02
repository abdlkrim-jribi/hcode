"""
Configuration module for Hcode.

Includes thinking configuration, prompts, model settings, tools, and other configurations.
"""

from .thinking import ThinkingConfig, ThinkingMode, ThinkingVisibility
from .prompts import (
    PromptsConfig,
    ModelsConfig,
    GenerationParams,
    ContextConfig,
    ContinuationConfig,
    ReliabilityConfig,
    get_prompts_config,
    get_models_config,
    get_system_prompt,
    get_generation_params,
    get_temperature,
    get_max_tokens,
    reload_configs,
)
from .tools import (
    ToolsConfig,
    ToolDefinition,
    ToolParameter,
    get_tools_config,
    get_tool_schemas_for_openai,
    get_tool_schemas_for_anthropic,
)

__all__ = [
    # Thinking config
    'ThinkingConfig',
    'ThinkingMode',
    'ThinkingVisibility',
    # Prompts and models config
    'PromptsConfig',
    'ModelsConfig',
    'GenerationParams',
    'ContextConfig',
    'ContinuationConfig',
    'ReliabilityConfig',
    # Tools config
    'ToolsConfig',
    'ToolDefinition',
    'ToolParameter',
    # Convenience functions
    'get_prompts_config',
    'get_models_config',
    'get_system_prompt',
    'get_generation_params',
    'get_temperature',
    'get_max_tokens',
    'reload_configs',
    'get_tools_config',
    'get_tool_schemas_for_openai',
    'get_tool_schemas_for_anthropic',
]
