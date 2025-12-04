"""
HCode - Universal AI Coding Assistant

Supports both Anthropic Claude and OpenAI GPT models for autonomous coding tasks.
A production-ready AI coding agent for your terminal.
"""

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

__version__ = "1.0.0"
__author__ = "HCode Team"
__email__ = "contact@hcode.dev"

from .core import (
    HcodeAgent,
    FileSystemManager,
    SafetyGuard,
    ContextManager,
)

from .providers import (
    AIProvider,
    AnthropicProvider,
    OpenAIProvider,
    ProviderSelector,
    ProviderPreferences,
    TaskComplexity,
    TaskType,
)

from .tools import (
    ToolExecutor,
    ExecutionResult,
)

from .utils import (
    load_config,
    save_config,
    create_default_config,
)

from .exceptions import (
    HCodeError,
    ConfigError,
    ConfigNotFoundError,
    ConfigValidationError,
    MissingAPIKeyError,
    LLMError,
    ProviderNotAvailableError,
    ModelNotFoundError,
    RateLimitError,
    TokenLimitError,
    APIError,
    ToolError,
    ToolNotFoundError,
    ToolExecutionError,
    ToolPermissionError,
    FileSystemError,
    FileReadError,
    FileWriteError,
    PathSecurityError,
    AgentError,
    AgentTimeoutError,
    AgentIterationLimitError,
    InputError,
    InvalidArgumentError,
    MissingArgumentError,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Core
    "HcodeAgent",
    "FileSystemManager",
    "SafetyGuard",
    "ContextManager",
    # Providers
    "AIProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "ProviderSelector",
    "ProviderPreferences",
    "TaskComplexity",
    "TaskType",
    # Tools
    "ToolExecutor",
    "ExecutionResult",
    # Utils
    "load_config",
    "save_config",
    "create_default_config",
    # Exceptions
    "HCodeError",
    "ConfigError",
    "ConfigNotFoundError",
    "ConfigValidationError",
    "MissingAPIKeyError",
    "LLMError",
    "ProviderNotAvailableError",
    "ModelNotFoundError",
    "RateLimitError",
    "TokenLimitError",
    "APIError",
    "ToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolPermissionError",
    "FileSystemError",
    "FileReadError",
    "FileWriteError",
    "PathSecurityError",
    "AgentError",
    "AgentTimeoutError",
    "AgentIterationLimitError",
    "InputError",
    "InvalidArgumentError",
    "MissingArgumentError",
]
