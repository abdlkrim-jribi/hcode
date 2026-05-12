"""
HCode - Universal AI Coding Assistant

Supports both Anthropic Claude and OpenAI GPT models for autonomous coding tasks.
A production-ready AI coding agent for your terminal.
"""

import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass
except Exception as e:
    logger.error(f"[hcode] failed to load .env file: {e}")

__version__ = "1.0.0"
__author__ = "HCode Team"
__email__ = "contact@hcode.dev"

from hcode.core import (
    HcodeAgent,
    SafetyGuard,
    ContextManager,
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
