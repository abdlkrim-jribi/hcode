"""
OpenAI GPT API provider implementation.
Supports GPT-4, GPT-4-Turbo, and GPT-3.5 models with function calling.
"""

import os
from typing import List, AsyncIterator, Dict, Any, Optional
from openai import AsyncOpenAI
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import AIProvider, Message, Usage, CompletionResponse


class OpenAIProvider(AIProvider):
    """OpenAI GPT API provider"""

    # Model pricing per million tokens (input, output)
    MODEL_PRICING = {
        "gpt-4-turbo-preview": (10.00, 30.00),
        "gpt-4-turbo": (10.00, 30.00),
        "gpt-4-turbo-2024-04-09": (10.00, 30.00),
        "gpt-4-0125-preview": (10.00, 30.00),
        "gpt-4": (30.00, 60.00),
        "gpt-4-32k": (60.00, 120.00),
        "gpt-3.5-turbo": (0.50, 1.50),
        "gpt-3.5-turbo-0125": (0.50, 1.50),
        "gpt-4o": (5.00, 15.00),
        "gpt-4o-mini": (0.15, 0.60),
    }

    # Context windows for different models
    CONTEXT_WINDOWS = {
        "gpt-4-turbo-preview": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4-turbo-2024-04-09": 128000,
        "gpt-4-0125-preview": 128000,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-3.5-turbo": 16385,
        "gpt-3.5-turbo-0125": 16385,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
    }

    # Vision-capable models
    VISION_MODELS = [
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "gpt-4-turbo-2024-04-09",
        "gpt-4o",
    ]

    # Function calling capable models
    FUNCTION_CALLING_MODELS = [
        "gpt-4-turbo-preview",
        "gpt-4-turbo",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-0125-preview",
        "gpt-4",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0125",
        "gpt-4o",
        "gpt-4o-mini",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
        max_tokens: int = 4000,
        temperature: float = 0.3,
        base_url: Optional[str] = None
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: GPT model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            base_url: Custom API base URL (defaults to OPENAI_BASE_URL env var)
                     Useful for Azure OpenAI, proxies, or OpenAI-compatible APIs
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY not set")

        # Get base URL from parameter or environment variable
        base_url = base_url or os.getenv("OPENAI_BASE_URL")

        super().__init__(api_key, model, max_tokens, temperature)

        # Initialize client with optional base_url
        if base_url:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            self.base_url = base_url
        else:
            self.client = AsyncOpenAI(api_key=api_key)
            self.base_url = None

        # Initialize tokenizer for this model
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Default to cl100k_base for unknown models
            self.encoding = tiktoken.get_encoding("cl100k_base")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_completion(
        self,
        messages: List[Message],
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> CompletionResponse | AsyncIterator[str]:
        """
        Generate completion using OpenAI API.

        Args:
            messages: Conversation messages
            stream: Enable streaming
            functions: Function definitions for function calling
            **kwargs: Additional parameters

        Returns:
            CompletionResponse or streaming iterator
        """
        # Convert messages to OpenAI format
        openai_messages = [msg.to_dict() for msg in messages]

        request_params = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            **kwargs
        }

        # Add functions if provided and model supports them
        if functions and self.supports_function_calling():
            request_params["tools"] = [
                {"type": "function", "function": func} for func in functions
            ]

        if stream:
            return self._stream_completion(request_params)
        else:
            return await self._complete(request_params)

    async def _complete(self, params: Dict[str, Any]) -> CompletionResponse:
        """Non-streaming completion"""
        response = await self.client.chat.completions.create(**params)

        usage = Usage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens
        )

        self._update_usage(usage)

        content = response.choices[0].message.content or ""

        # Handle function calls if present
        if response.choices[0].message.tool_calls:
            # Include function call information in the response
            tool_calls = response.choices[0].message.tool_calls
            content += f"\n[Function calls: {len(tool_calls)}]"

        return CompletionResponse(
            content=content,
            usage=usage,
            model=response.model,
            finish_reason=response.choices[0].finish_reason or "stop",
            raw_response=response
        )

    async def _stream_completion(self, params: Dict[str, Any]) -> AsyncIterator[str]:
        """Streaming completion"""
        params["stream"] = True

        total_tokens = 0
        content_tokens = []

        stream = await self.client.chat.completions.create(**params)

        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    content_tokens.append(delta.content)
                    yield delta.content

        # Estimate usage for streaming (OpenAI doesn't always provide it)
        full_content = "".join(content_tokens)
        output_tokens = len(self.encoding.encode(full_content))

        # Estimate input tokens from messages in params
        input_text = " ".join([msg["content"] for msg in params["messages"]])
        input_tokens = len(self.encoding.encode(input_text))

        usage = Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )
        self._update_usage(usage)

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken.

        Args:
            text: Text to count

        Returns:
            Exact token count
        """
        return len(self.encoding.encode(text))

    def get_cost(self, usage: Usage) -> float:
        """
        Calculate cost for token usage.

        Args:
            usage: Token usage

        Returns:
            Cost in USD
        """
        if self.model not in self.MODEL_PRICING:
            # Default to GPT-4-Turbo pricing for unknown models
            input_price, output_price = self.MODEL_PRICING["gpt-4-turbo"]
        else:
            input_price, output_price = self.MODEL_PRICING[self.model]

        input_cost = (usage.input_tokens / 1_000_000) * input_price
        output_cost = (usage.output_tokens / 1_000_000) * output_price

        return input_cost + output_cost

    def get_context_window(self) -> int:
        """Get context window size"""
        return self.CONTEXT_WINDOWS.get(self.model, 8192)

    def supports_vision(self) -> bool:
        """Check if model supports vision"""
        return self.model in self.VISION_MODELS

    def supports_function_calling(self) -> bool:
        """Check if model supports function calling"""
        return self.model in self.FUNCTION_CALLING_MODELS

    async def use_function_calling(
        self,
        messages: List[Message],
        functions: List[Dict[str, Any]]
    ) -> CompletionResponse:
        """
        Use function calling with OpenAI models.

        Args:
            messages: Conversation messages
            functions: Function definitions

        Returns:
            CompletionResponse with function call information
        """
        return await self.generate_completion(messages, stream=False, functions=functions)

    def get_system_prompt_for_coding(self) -> str:
        """Get optimized system prompt for coding tasks"""
        return """You are Hcode, an expert coding assistant with access to file system operations and command execution.

You can use the provided functions to:
- Read and write files
- Execute commands and tests
- Analyze code structure
- Implement features
- Refactor code
- Debug issues

Best practices:
1. Plan your approach before implementation
2. Write production-quality code with proper error handling
3. Follow existing code patterns and conventions
4. Include comprehensive testing
5. Document significant decisions

You are autonomous and thorough. Break down complex tasks systematically and validate your changes."""
