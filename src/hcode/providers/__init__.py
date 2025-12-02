"""
AI Provider implementations for Hcode.
Supports Anthropic Claude and OpenAI GPT models.
"""

from .base import AIProvider, Message, Usage, CompletionResponse, ModelType
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider, LLMConnectionError
from .provider_selector import (
    ProviderSelector,
    ProviderPreferences,
    TaskComplexity,
    TaskType
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
]
