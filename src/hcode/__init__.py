"""
Hcode - Universal AI Coding Assistant

Supports both Anthropic Claude and OpenAI GPT models for autonomous coding tasks.
"""

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

__version__ = "0.1.0"

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

__all__ = [
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
]
