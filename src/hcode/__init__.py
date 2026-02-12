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

from hcode.core import (
    HcodeAgent,
    FileSystemManager,
    SafetyGuard,
    ContextManager,
)
from hcode.exceptions import (
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
from hcode.providers import (
    AIProvider,
    AnthropicProvider,
    OpenAIProvider,
    ProviderSelector,
    ProviderPreferences,
    TaskComplexity,
    TaskType,
)
from hcode.tools import (
    ToolExecutor,
    ExecutionResult,
)

from hcode.utils import (
    load_config,
    save_config,
    create_default_config,
)

# Export high‑level convenience modules
# Note: These modules are temporarily commented out during refactoring
# from .hcode_chat import HcodeChat  # noqa: F401
# from .cli_enhanced import cli_enhanced  # noqa: F401
# Export core submodules
from .core import *  # noqa: F401,F403
# Export tools submodule
from .tools import *  # noqa: F401,F403

# Export high‑level convenience modules
# Note: These modules are temporarily commented out during refactoring
# from .hcode_chat import HcodeChat  # noqa: F401
# from .cli_enhanced import cli_enhanced  # noqa: F401
# Export core submodules
from .core import *  # noqa: F401,F403
# Export tools submodule
from .tools import *  # noqa: F401,F403

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
