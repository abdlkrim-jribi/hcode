"""
OpenAI GPT API provider implementation.
Supports GPT-4, GPT-4-Turbo, and GPT-3.5 models with function calling.
"""

import os
from typing import List, AsyncIterator, Dict, Any, Optional

import httpx
import tiktoken
from hcode.providers.base import AIProvider, Message, Usage, CompletionResponse
from openai import AsyncOpenAI, APIConnectionError, APITimeoutError, RateLimitError, APIStatusError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class LLMConnectionError(Exception):
    """Custom exception for LLM connection errors with detailed information"""

    def __init__(self, message: str, base_url: str = None, original_error: Exception = None):
        self.base_url = base_url
        self.original_error = original_error
        super().__init__(message)


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
        # GPT-OSS and custom models (OpenAI-compatible APIs)
        "gpt-oss-120b": (0.00, 0.00),  # Self-hosted, adjust if billing applies
        "gpt-oss-70b": (0.00, 0.00),
        "gpt-oss-13b": (0.00, 0.00),
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
        # GPT-OSS models - large context windows
        "gpt-oss-120b": 128000,
        "gpt-oss-70b": 128000,
        "gpt-oss-13b": 32768,
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
        # GPT-OSS models with function calling support
        "gpt-oss-120b",
        "gpt-oss-70b",
        "gpt-oss-13b",
    ]

    # Patterns for detecting large/capable models (for smart defaults)
    LARGE_MODEL_PATTERNS = [
        "120b",
        "70b",
        "65b",
        "gpt-4",
        "claude",
        "large",
        "turbo",
        "opus",
        "sonnet",
        "pro",
        "ultra",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
        max_tokens: int = 16384,  # GPT-4o max output tokens
        temperature: float = 0.3,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
        verify_ssl: Optional[bool] = None,
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
            timeout: Request timeout in seconds (default 120s)
            max_retries: Maximum number of retries for failed requests
            verify_ssl: Whether to verify SSL certificates (defaults to OPENAI_VERIFY_SSL env var or True)
                       Set to False for self-signed or internal CA certificates
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY not set")

        # Get base URL from parameter or environment variable
        base_url = base_url or os.getenv("OPENAI_BASE_URL")

        # Get SSL verification setting from parameter or environment variable
        if verify_ssl is None:
            verify_ssl_env = os.getenv("OPENAI_VERIFY_SSL", "true").lower()
            verify_ssl = verify_ssl_env not in ("false", "0", "no", "off")

        super().__init__(api_key, model, max_tokens, temperature)

        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl

        # Create custom httpx client with timeout and SSL configuration
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout, connect=30.0
            ),  # Connection timeout of 30s, total timeout configurable
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            verify=verify_ssl,  # SSL verification setting
        )

        # Initialize client with optional base_url and timeout
        if base_url:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
                http_client=http_client,
            )
            self.base_url = base_url
        else:
            self.client = AsyncOpenAI(
                api_key=api_key, timeout=timeout, max_retries=max_retries, http_client=http_client
            )
            self.base_url = None

        # Initialize tokenizer for this model
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Default to cl100k_base for unknown models
            self.encoding = tiktoken.get_encoding("cl100k_base")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError, RateLimitError)),
    )
    async def generate_completion(
        self,
        messages: List[Message],
        stream: bool = False,
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
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

        Raises:
            ConnectionError: When unable to connect to the API after retries
            APIStatusError: When the API returns an error status
        """
        try:
            # Convert messages to OpenAI format
            openai_messages = [msg.to_dict() for msg in messages]

            request_params = {
                "model": self.model,
                "messages": openai_messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                **kwargs,
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

        except APIConnectionError as e:
            error_msg = f"Connection error to LLM API"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            error_msg += f": {str(e)}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        except APITimeoutError as e:
            error_msg = f"Request timeout ({self.timeout}s) to LLM API"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        except RateLimitError as e:
            raise RuntimeError(f"Rate limit exceeded: {str(e)}") from e

        except APIStatusError as e:
            if e.status_code == 401:
                raise ValueError(f"Invalid API key or unauthorized access") from e
            elif e.status_code == 404:
                raise ValueError(f"Model '{self.model}' not found or endpoint not available") from e
            elif e.status_code >= 500:
                raise LLMConnectionError(
                    f"LLM server error ({e.status_code}): {str(e)}", self.base_url, e
                ) from e
            else:
                raise

        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to LLM API"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            error_msg += f": {str(e)}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        except httpx.TimeoutException as e:
            error_msg = f"Connection timeout to LLM API"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error from LLM API: {e.response.status_code}"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        except Exception as e:
            # Catch any other connection-related errors
            error_str = str(e).lower()
            if any(
                kw in error_str
                for kw in ["connect", "timeout", "network", "refused", "unreachable"]
            ):
                error_msg = f"Connection error to LLM API"
                if self.base_url:
                    error_msg += f" at {self.base_url}"
                error_msg += f": {str(e)}"
                raise LLMConnectionError(error_msg, self.base_url, e) from e
            raise

    def _handle_api_error(self, e: Exception):
        """
        Handle API errors and convert them to more descriptive exceptions.

        Args:
            e: The original exception

        Raises:
            LLMConnectionError: For connection-related errors
            ValueError: For configuration errors
            RuntimeError: For rate limiting
        """
        error_str = str(e).lower()

        if isinstance(e, APIConnectionError):
            error_msg = f"Connection error to LLM API"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            error_msg += f": {str(e)}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        elif isinstance(e, APITimeoutError):
            error_msg = f"Request timeout ({self.timeout}s) to LLM API"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        elif isinstance(e, RateLimitError):
            raise RuntimeError(f"Rate limit exceeded: {str(e)}") from e

        elif isinstance(e, APIStatusError):
            if e.status_code == 401:
                raise ValueError(f"Invalid API key or unauthorized access") from e
            elif e.status_code == 404:
                raise ValueError(f"Model '{self.model}' not found or endpoint not available") from e
            elif e.status_code >= 500:
                raise LLMConnectionError(
                    f"LLM server error ({e.status_code}): {str(e)}", self.base_url, e
                ) from e
            else:
                raise

        elif isinstance(e, httpx.ConnectError):
            error_msg = f"Failed to connect to LLM API"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            error_msg += f": {str(e)}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        elif isinstance(e, httpx.TimeoutException):
            error_msg = f"Connection timeout to LLM API"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        elif isinstance(e, httpx.HTTPStatusError):
            error_msg = f"HTTP error from LLM API: {e.response.status_code}"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        # Check for connection-related keywords in generic exceptions
        elif any(
            kw in error_str
            for kw in [
                "connect",
                "timeout",
                "network",
                "refused",
                "unreachable",
                "connection error",
            ]
        ):
            error_msg = f"Connection error to LLM API"
            if self.base_url:
                error_msg += f" at {self.base_url}"
            error_msg += f": {str(e)}"
            raise LLMConnectionError(error_msg, self.base_url, e) from e

        else:
            # Re-raise unknown exceptions
            raise

    async def _complete(self, params: Dict[str, Any]) -> CompletionResponse:
        """Non-streaming completion"""
        try:
            response = await self.client.chat.completions.create(**params)

            usage = Usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
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
                raw_response=response,
            )
        except Exception as e:
            # Re-raise with better error message for connection errors
            self._handle_api_error(e)

    async def _stream_completion(self, params: Dict[str, Any]) -> AsyncIterator[str]:
        """Streaming completion"""
        params["stream"] = True

        total_tokens = 0
        content_tokens = []

        try:
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
                total_tokens=input_tokens + output_tokens,
            )
            self._update_usage(usage)
        except Exception as e:
            # Re-raise with better error message for connection errors
            self._handle_api_error(e)

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

    def _is_large_model(self) -> bool:
        """Check if model appears to be a large/capable model based on name patterns."""
        model_lower = self.model.lower()
        return any(pattern in model_lower for pattern in self.LARGE_MODEL_PATTERNS)

    def get_context_window(self) -> int:
        """
        Get context window size with smart defaults for unknown models.

        For known models, returns the exact context window.
        For unknown models that appear to be large (120b, 70b, etc.), defaults to 128k.
        For other unknown models, defaults to 32k (safe middle ground).
        """
        if self.model in self.CONTEXT_WINDOWS:
            return self.CONTEXT_WINDOWS[self.model]

        # Smart default based on model name patterns
        if self._is_large_model():
            return 128000  # Large models typically have 128k context

        # Default to 32k for unknown models (better than 8k)
        return 32768

    def supports_vision(self) -> bool:
        """Check if model supports vision"""
        return self.model in self.VISION_MODELS

    def supports_function_calling(self) -> bool:
        """
        Check if model supports function calling.

        For known models, checks the explicit list.
        For unknown models that appear to be large, assumes support.
        """
        if self.model in self.FUNCTION_CALLING_MODELS:
            return True

        # Assume large OSS/custom models support function calling
        if self._is_large_model():
            return True

        return False

    async def use_function_calling(
        self, messages: List[Message], functions: List[Dict[str, Any]]
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

    async def test_connection(self) -> tuple[bool, str]:
        """
        Test the connection to the LLM API.

        Returns:
            Tuple of (success: bool, message: str)
        """
        endpoint_info = f" at {self.base_url}" if self.base_url else ""

        try:
            # Make a minimal API call to test connectivity
            response = await self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": "Hi"}], max_tokens=5
            )
            return True, f"Connected to {self.model}{endpoint_info}"

        except APIConnectionError as e:
            return False, f"Connection failed{endpoint_info}: {str(e)}"

        except APITimeoutError as e:
            return False, f"Connection timeout{endpoint_info}: {str(e)}"

        except APIStatusError as e:
            if e.status_code == 401:
                return False, f"Invalid API key{endpoint_info}"
            elif e.status_code == 404:
                return False, f"Model '{self.model}' not found{endpoint_info}"
            else:
                return False, f"API error ({e.status_code}){endpoint_info}: {str(e)}"

        except httpx.ConnectError as e:
            return False, f"Failed to connect{endpoint_info}: {str(e)}"

        except httpx.TimeoutException as e:
            return False, f"Connection timeout{endpoint_info}: {str(e)}"

        except Exception as e:
            error_str = str(e).lower()
            # Check for connection-related errors in generic exceptions
            if any(
                kw in error_str
                for kw in ["connect", "timeout", "network", "refused", "unreachable"]
            ):
                return False, f"Connection error{endpoint_info}: {str(e)}"
            return False, f"Unexpected error: {str(e)}"

    def get_system_prompt_for_coding(self) -> str:
        """Get optimized system prompt for coding tasks from external config"""
        from ..config.prompts import get_system_prompt

        return get_system_prompt("openai_coding")
