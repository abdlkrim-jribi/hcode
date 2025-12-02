"""
Abstract base class for AI providers.
Defines the interface that all AI providers (Anthropic, OpenAI) must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional
from dataclasses import dataclass
from enum import Enum


class ModelType(Enum):
    """Types of models available across providers"""
    FLAGSHIP = "flagship"  # Most capable (Opus, GPT-4)
    BALANCED = "balanced"  # Good balance (Sonnet, GPT-4-Turbo)
    FAST = "fast"  # Quick and economical (Haiku, GPT-3.5-Turbo)


@dataclass
class Message:
    """Represents a chat message"""
    role: str  # "user", "assistant", "system"
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class Usage:
    """Token usage information"""
    input_tokens: int
    output_tokens: int
    total_tokens: int

    def __add__(self, other: 'Usage') -> 'Usage':
        """Allow adding usage objects together"""
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )


@dataclass
class CompletionResponse:
    """Response from an AI completion request"""
    content: str
    usage: Usage
    model: str
    finish_reason: str
    raw_response: Optional[Any] = None


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(self, api_key: str, model: str, max_tokens: int = 16384, temperature: float = 0.3):
        """
        Initialize the AI provider.

        Args:
            api_key: API key for the provider
            model: Model identifier
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._total_usage = Usage(0, 0, 0)

    @abstractmethod
    async def generate_completion(
        self,
        messages: List[Message],
        stream: bool = False,
        **kwargs
    ) -> CompletionResponse | AsyncIterator[str]:
        """
        Generate a completion from the AI model.

        Args:
            messages: List of conversation messages
            stream: Whether to stream the response
            **kwargs: Additional provider-specific parameters

        Returns:
            CompletionResponse if not streaming, AsyncIterator[str] if streaming
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    def get_cost(self, usage: Usage) -> float:
        """
        Calculate the cost for a given usage.

        Args:
            usage: Token usage information

        Returns:
            Cost in USD
        """
        pass

    @abstractmethod
    def get_context_window(self) -> int:
        """
        Get the maximum context window size for the current model.

        Returns:
            Maximum number of tokens in context window
        """
        pass

    @abstractmethod
    def supports_vision(self) -> bool:
        """
        Check if the current model supports vision capabilities.

        Returns:
            True if vision is supported
        """
        pass

    @abstractmethod
    def supports_function_calling(self) -> bool:
        """
        Check if the current model supports function calling.

        Returns:
            True if function calling is supported
        """
        pass

    @property
    def total_usage(self) -> Usage:
        """Get total usage across all requests"""
        return self._total_usage

    @property
    def total_cost(self) -> float:
        """Get total cost across all requests"""
        return self.get_cost(self._total_usage)

    def _update_usage(self, usage: Usage):
        """Update the total usage tracker"""
        self._total_usage = self._total_usage + usage

    def get_provider_name(self) -> str:
        """Get the name of this provider"""
        return self.__class__.__name__.replace("Provider", "")

    def __str__(self) -> str:
        return f"{self.get_provider_name()}({self.model})"
