"""
Anthropic Claude API provider implementation.
Supports all Claude models with streaming and vision capabilities.
"""

import os
from typing import List, AsyncIterator, Dict, Any, Optional
import anthropic
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import AIProvider, Message, Usage, CompletionResponse


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider"""

    # Model pricing per million tokens (input, output)
    MODEL_PRICING = {
        "claude-3-opus-20240229": (15.00, 75.00),
        "claude-3-5-sonnet-20241022": (3.00, 15.00),
        "claude-3-sonnet-20240229": (3.00, 15.00),
        "claude-3-haiku-20240307": (0.25, 1.25),
    }

    # Context windows for different models
    CONTEXT_WINDOWS = {
        "claude-3-opus-20240229": 200000,
        "claude-3-5-sonnet-20241022": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000,
    }

    # Vision-capable models
    VISION_MODELS = [
        "claude-3-opus-20240229",
        "claude-3-5-sonnet-20241022",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4000,
        temperature: float = 0.3
    ):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
        """
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key not provided and ANTHROPIC_API_KEY not set")

        super().__init__(api_key, model, max_tokens, temperature)
        self.client = AsyncAnthropic(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_completion(
        self,
        messages: List[Message],
        stream: bool = False,
        system: Optional[str] = None,
        **kwargs
    ) -> CompletionResponse | AsyncIterator[str]:
        """
        Generate completion using Claude API.

        Args:
            messages: Conversation messages
            stream: Enable streaming
            system: System prompt (separate from messages in Claude API)
            **kwargs: Additional parameters

        Returns:
            CompletionResponse or streaming iterator
        """
        # Separate system messages from conversation
        system_message = system
        conversation_messages = []

        for msg in messages:
            if msg.role == "system" and not system_message:
                system_message = msg.content
            else:
                conversation_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        request_params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": conversation_messages,
            **kwargs
        }

        if system_message:
            request_params["system"] = system_message

        if stream:
            return self._stream_completion(request_params)
        else:
            return await self._complete(request_params)

    async def _complete(self, params: Dict[str, Any]) -> CompletionResponse:
        """Non-streaming completion"""
        response = await self.client.messages.create(**params)

        usage = Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens
        )

        self._update_usage(usage)

        return CompletionResponse(
            content=response.content[0].text,
            usage=usage,
            model=response.model,
            finish_reason=response.stop_reason or "stop",
            raw_response=response
        )

    async def _stream_completion(self, params: Dict[str, Any]) -> AsyncIterator[str]:
        """Streaming completion"""
        input_tokens = 0
        output_tokens = 0

        async with self.client.messages.stream(**params) as stream:
            async for event in stream:
                if hasattr(event, 'type'):
                    if event.type == "message_start":
                        input_tokens = event.message.usage.input_tokens
                    elif event.type == "content_block_delta":
                        if hasattr(event.delta, 'text'):
                            yield event.delta.text
                    elif event.type == "message_delta":
                        output_tokens = event.usage.output_tokens

        # Update usage after streaming completes
        usage = Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )
        self._update_usage(usage)

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using Anthropic's token counting.
        Approximates 3.5 characters per token for Claude.

        Args:
            text: Text to count

        Returns:
            Approximate token count
        """
        # Anthropic doesn't provide a direct tokenizer, so we approximate
        # Claude uses roughly 3.5 characters per token on average
        return int(len(text) / 3.5)

    def get_cost(self, usage: Usage) -> float:
        """
        Calculate cost for token usage.

        Args:
            usage: Token usage

        Returns:
            Cost in USD
        """
        if self.model not in self.MODEL_PRICING:
            # Default to Sonnet pricing for unknown models
            input_price, output_price = self.MODEL_PRICING["claude-3-5-sonnet-20241022"]
        else:
            input_price, output_price = self.MODEL_PRICING[self.model]

        input_cost = (usage.input_tokens / 1_000_000) * input_price
        output_cost = (usage.output_tokens / 1_000_000) * output_price

        return input_cost + output_cost

    def get_context_window(self) -> int:
        """Get context window size"""
        return self.CONTEXT_WINDOWS.get(self.model, 200000)

    def supports_vision(self) -> bool:
        """Check if model supports vision"""
        return self.model in self.VISION_MODELS

    def supports_function_calling(self) -> bool:
        """
        Check if model supports function calling.
        Claude uses tool use instead of function calling.
        """
        return True  # All Claude 3 models support tool use

    def get_system_prompt_for_coding(self) -> str:
        """Get optimized system prompt for coding tasks from external config"""
        from ..config.prompts import get_system_prompt
        return get_system_prompt("coding_agent")
