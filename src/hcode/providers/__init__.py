"""
AI Provider implementations for Hcode.
Supports Anthropic Claude and OpenAI GPT models.
"""

from hcode.providers.base import AIProvider, Message, Usage, CompletionResponse, ModelType
from hcode.providers.anthropic_provider import AnthropicProvider
from hcode.providers.openai_provider import OpenAIProvider, LLMConnectionError
from hcode.providers.provider_selector import ProviderSelector, ProviderPreferences, TaskComplexity, TaskType
from hcode.providers.resilient_provider import (
    ResilientProvider,
    ResilientStreamWrapper,
    ProviderHealth,
    FailureType,
    ProviderStats,
    CircuitBreaker,
    CircuitBreakerConfig,
    RetryConfig,
    RetryHandler,
    create_resilient_provider,
)

__all__ = [
    "AIProvider",
    "Message",
    "Usage",
    "CompletionResponse",
    "ModelType",
    "AnthropicProvider",
    "OpenAIProvider",
    "LLMConnectionError",
    "ProviderSelector",
    "ProviderPreferences",
    "TaskComplexity",
    "TaskType",
    # Resilient Provider
    "ResilientProvider",
    "ResilientStreamWrapper",
    "ProviderHealth",
    "FailureType",
    "ProviderStats",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "RetryConfig",
    "RetryHandler",
    "create_resilient_provider",
]
