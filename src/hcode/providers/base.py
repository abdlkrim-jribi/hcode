"""
Abstract base class for AI providers.
Defines the interface that all AI providers (Anthropic, OpenAI) must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator, Optional


@dataclass
class Message:
    """Represents a chat message"""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: Optional[List["ToolCall"]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {"role": self.role, "content": self.content}
        if self.tool_calls:
            data["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        return data


@dataclass
class Usage:
    """Token usage information"""

    input_tokens: int
    output_tokens: int
    total_tokens: int

    def __add__(self, other: "Usage") -> "Usage":
        """Allow adding usage objects together"""
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


@dataclass
class ToolCall:
    """Represents a tool call from the model (native function calling)"""

    id: str  # Unique identifier for this tool call
    name: str  # Tool name
    arguments: Dict[str, Any]  # Tool arguments as a dictionary

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "arguments": self.arguments}


@dataclass
class CompletionResponse:
    """Response from an AI completion request"""

    content: str
    usage: Usage
    model: str
    finish_reason: str
    raw_response: Optional[Any] = None
    tool_calls: Optional[List["ToolCall"]] = None  # Native tool calls from the model


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

    @abstractmethod
    async def generate_completion(
            self, messages: List[Message], stream: bool = False, **kwargs
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

    def get_provider_name(self) -> str:
        """Get the name of this provider"""
        return self.__class__.__name__.replace("Provider", "")

    def __str__(self) -> str:
        return f"{self.get_provider_name()}({self.model})"
