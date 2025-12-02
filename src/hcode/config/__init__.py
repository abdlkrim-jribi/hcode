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
from .settings import (
    HCodeSettings,
    LLMSettings,
    AgentSettings,
    UISettings,
    LoggingSettings,
    MemorySettings,
    SafetySettings,
    get_settings,
    clear_settings_cache,
    get_llm_settings,
    get_agent_settings,
    get_ui_settings,
    get_logging_settings,
    get_memory_settings,
    get_safety_settings,
)
from .defaults import (
    VERSION,
    APP_NAME,
    DEFAULT_MODELS,
    MODEL_PRICING,
    CONTEXT_WINDOWS,
    DEFAULT_SYSTEM_PROMPT,
    CHAT_COMMANDS,
    DEFAULT_CONFIG_YAML,
    get_default_model,
    get_model_pricing,
    get_context_window,
    is_binary_file,
    should_ignore_path,
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
    # Settings (pydantic)
    'HCodeSettings',
    'LLMSettings',
    'AgentSettings',
    'UISettings',
    'LoggingSettings',
    'MemorySettings',
    'SafetySettings',
    # Defaults
    'VERSION',
    'APP_NAME',
    'DEFAULT_MODELS',
    'MODEL_PRICING',
    'CONTEXT_WINDOWS',
    'DEFAULT_SYSTEM_PROMPT',
    'CHAT_COMMANDS',
    'DEFAULT_CONFIG_YAML',
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
    'get_settings',
    'clear_settings_cache',
    'get_llm_settings',
    'get_agent_settings',
    'get_ui_settings',
    'get_logging_settings',
    'get_memory_settings',
    'get_safety_settings',
    'get_default_model',
    'get_model_pricing',
    'get_context_window',
    'is_binary_file',
    'should_ignore_path',
]
