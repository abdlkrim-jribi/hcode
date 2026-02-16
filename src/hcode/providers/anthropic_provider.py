"""
Anthropic Claude API provider implementation.
Supports all Claude models with streaming and vision capabilities.
"""

import os
from typing import List, AsyncIterator, Dict, Any, Optional

from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from hcode.memory import Message
from hcode.providers.base import AIProvider, ToolCall, CompletionResponse, Usage


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
            max_tokens: int = 16384,  # Increased for complex reasoning outputs
            temperature: float = 0.2,  # Lower for more deterministic/consistent results
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_completion(
            self, messages: List[Message], stream: bool = False, system: Optional[str] = None, **kwargs
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
                conversation_messages.append({"role": msg.role, "content": msg.content})

        request_params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": conversation_messages,
            **kwargs,
        }

        if system_message:
            request_params["system"] = system_message

        if stream:
            return self._stream_completion(request_params)
        else:
            return await self._complete(request_params)

    async def _complete(self, params: Dict[str, Any]) -> CompletionResponse:
        """Non-streaming completion with native tool_use parsing"""
        response = await self.client.messages.create(**params)

        usage = Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )

        # Parse content blocks - may include text and tool_use blocks
        text_content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                # Native tool call from Claude
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {}
                ))

        # Calculate cost
        input_price, output_price = self.MODEL_PRICING.get(response.model, (0.0, 0.0))
        cost = (usage.input_tokens * input_price / 1_000_000) + (usage.output_tokens * output_price / 1_000_000)
        self.total_cost += cost

        return CompletionResponse(
            content=text_content,
            usage=usage,
            model=response.model,
            finish_reason=response.stop_reason or "stop",
            raw_response=response,
            tool_calls=tool_calls if tool_calls else None
        )

    async def _stream_completion(self, params: Dict[str, Any]) -> AsyncIterator[str]:
        """Streaming completion"""
        async with self.client.messages.stream(**params) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield event.delta.text

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
