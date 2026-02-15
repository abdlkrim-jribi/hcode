"""
Resilient Provider with Hot-Swapping and Automatic Fallback.

Provides:
- Automatic failover on API errors/rate limits
- Circuit breaker pattern to prevent cascading failures
- Health monitoring for all providers
- Seamless mid-conversation provider switching
- Exponential backoff retry logic
- Request queueing during provider issues
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
)

from hcode.providers.base import AIProvider, CompletionResponse, Message


class ProviderHealth(Enum):
    """Health status of a provider"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Slow responses or intermittent errors
    UNHEALTHY = "unhealthy"  # Consistent failures
    CIRCUIT_OPEN = "circuit_open"  # Circuit breaker tripped


class FailureType(Enum):
    """Types of provider failures"""

    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    CONTEXT_OVERFLOW = "context_overflow"
    INVALID_RESPONSE = "invalid_response"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass
class FailureRecord:
    """Record of a provider failure"""

    failure_type: FailureType
    timestamp: datetime
    error_message: str
    retry_after: Optional[float] = None  # Seconds to wait before retry


@dataclass
class ProviderStats:
    """Statistics for a provider"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency: float = 0.0
    recent_failures: Deque[FailureRecord] = field(default_factory=lambda: deque(maxlen=100))
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    circuit_opened_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def average_latency(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency / self.successful_requests

    @property
    def recent_failure_rate(self) -> float:
        """Failure rate in last 10 requests"""
        if len(self.recent_failures) == 0:
            return 0.0
        recent_window = datetime.now() - timedelta(minutes=5)
        recent = [f for f in self.recent_failures if f.timestamp > recent_window]
        return len(recent) / max(10, len(recent) + 5)  # Approximate denominator


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 3  # Successes before closing circuit
    open_timeout: float = 60.0  # Seconds circuit stays open
    half_open_max_calls: int = 3  # Max calls in half-open state


class CircuitBreaker:
    """
    Circuit breaker implementation.

    States:
    - CLOSED: Normal operation
    - OPEN: All calls fail fast
    - HALF_OPEN: Testing if provider recovered
    """

    class State(Enum):
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self._state = self.State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> State:
        # Auto-transition from OPEN to HALF_OPEN
        if self._state == self.State.OPEN:
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.open_timeout:
                    self._state = self.State.HALF_OPEN
                    self._half_open_calls = 0
        return self._state

    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        state = self.state
        if state == self.State.CLOSED:
            return True
        if state == self.State.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        return False

    def record_success(self):
        """Record successful execution"""
        if self._state == self.State.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = self.State.CLOSED
                self._failure_count = 0
                self._success_count = 0
        else:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        """Record failed execution"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == self.State.HALF_OPEN:
            # Any failure in half-open reopens circuit
            self._state = self.State.OPEN
            self._success_count = 0
        elif self._failure_count >= self.config.failure_threshold:
            self._state = self.State.OPEN

    def reset(self):
        """Reset circuit breaker"""
        self._state = self.State.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None


@dataclass
class RetryConfig:
    """Configuration for retry logic"""

    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: float = 0.1  # Random jitter factor


class RetryHandler:
    """Handles retry logic with exponential backoff"""

    def __init__(self, config: RetryConfig):
        self.config = config

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        should_retry: Optional[Callable[[Exception], bool]] = None,
        **kwargs,
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            should_retry: Optional function to determine if exception is retryable
            *args, **kwargs: Arguments for func

        Returns:
            Result of func
        """
        last_exception = None
        delay = self.config.initial_delay

        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if we should retry
                if should_retry and not should_retry(e):
                    raise

                # Last attempt, don't retry
                if attempt >= self.config.max_retries:
                    raise

                # Calculate delay with jitter
                import random

                jitter = random.uniform(-self.config.jitter * delay, self.config.jitter * delay)
                actual_delay = min(delay + jitter, self.config.max_delay)

                await asyncio.sleep(actual_delay)

                # Exponential backoff
                delay = min(delay * self.config.exponential_base, self.config.max_delay)

        raise last_exception


class ResilientProvider:
    """
    Resilient provider wrapper with automatic failover.

    Wraps multiple providers and handles:
    - Automatic failover on errors
    - Circuit breaker for failing providers
    - Health monitoring
    - Hot-swapping during execution
    """

    def __init__(
        self,
        providers: Dict[str, AIProvider],
        primary_provider: Optional[str] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """
        Initialize resilient provider.

        Args:
            providers: Dict of provider name -> provider instance
            primary_provider: Name of primary provider
            circuit_config: Circuit breaker configuration
            retry_config: Retry configuration
        """
        if not providers:
            raise ValueError("At least one provider required")

        self.providers = providers
        self._primary_name = primary_provider or list(providers.keys())[0]
        self._current_name = self._primary_name

        # Initialize per-provider components
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._stats: Dict[str, ProviderStats] = {}

        circuit_config = circuit_config or CircuitBreakerConfig()
        for name in providers:
            self._circuit_breakers[name] = CircuitBreaker(circuit_config)
            self._stats[name] = ProviderStats()

        self._retry_handler = RetryHandler(retry_config or RetryConfig())

        # Callbacks for provider events
        self._on_failover: Optional[Callable[[str, str, Exception], None]] = None
        self._on_recovery: Optional[Callable[[str], None]] = None

    @property
    def current_provider(self) -> AIProvider:
        """Get current active provider"""
        return self.providers[self._current_name]

    @property
    def current_provider_name(self) -> str:
        """Get current provider name"""
        return self._current_name

    def set_failover_callback(self, callback: Callable[[str, str, Exception], None]):
        """Set callback for failover events (from_provider, to_provider, exception)"""
        self._on_failover = callback

    def set_recovery_callback(self, callback: Callable[[str], None]):
        """Set callback for recovery events (provider_name)"""
        self._on_recovery = callback

    def get_health(self, provider_name: str) -> ProviderHealth:
        """Get health status of a provider"""
        if provider_name not in self.providers:
            return ProviderHealth.UNHEALTHY

        circuit = self._circuit_breakers[provider_name]
        stats = self._stats[provider_name]

        if circuit.state == CircuitBreaker.State.OPEN:
            return ProviderHealth.CIRCUIT_OPEN

        if stats.recent_failure_rate > 0.5:
            return ProviderHealth.UNHEALTHY

        if stats.recent_failure_rate > 0.2 or stats.average_latency > 10.0:
            return ProviderHealth.DEGRADED

        return ProviderHealth.HEALTHY


    def get_stats(self, provider_name: str) -> Optional[ProviderStats]:
        """Get statistics for a provider"""
        return self._stats.get(provider_name)

    def _classify_error(self, error: Exception) -> FailureType:
        """Classify an error into failure type"""
        error_str = str(error).lower()

        if "rate" in error_str or "limit" in error_str or "429" in error_str:
            return FailureType.RATE_LIMIT
        if "auth" in error_str or "api key" in error_str or "401" in error_str:
            return FailureType.AUTHENTICATION
        if "timeout" in error_str or "timed out" in error_str:
            return FailureType.TIMEOUT
        if "context" in error_str or "token" in error_str or "too long" in error_str:
            return FailureType.CONTEXT_OVERFLOW
        if "connection" in error_str or "network" in error_str:
            return FailureType.NETWORK_ERROR
        if "500" in error_str or "502" in error_str or "503" in error_str:
            return FailureType.API_ERROR

        return FailureType.UNKNOWN

    def _is_retryable(self, error: Exception) -> bool:
        """Check if error is retryable"""
        failure_type = self._classify_error(error)
        return failure_type in {
            FailureType.RATE_LIMIT,
            FailureType.TIMEOUT,
            FailureType.NETWORK_ERROR,
            FailureType.API_ERROR,
        }

    def _select_fallback(self, exclude: str) -> Optional[str]:
        """Select best fallback provider"""
        candidates = []

        for name in self.providers:
            if name == exclude:
                continue

            health = self.get_health(name)
            if health in {ProviderHealth.HEALTHY, ProviderHealth.DEGRADED}:
                stats = self._stats[name]
                # Score based on success rate and latency
                score = stats.success_rate * 100 - stats.average_latency
                candidates.append((name, score))

        if not candidates:
            # Try even unhealthy providers as last resort
            for name in self.providers:
                if name != exclude:
                    circuit = self._circuit_breakers[name]
                    if circuit.state != CircuitBreaker.State.OPEN:
                        return name
            return None

        # Return highest scoring candidate
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _record_success(self, provider_name: str, latency: float):
        """Record successful request"""
        stats = self._stats[provider_name]
        stats.total_requests += 1
        stats.successful_requests += 1
        stats.total_latency += latency
        stats.last_success = datetime.now()

        circuit = self._circuit_breakers[provider_name]
        circuit.record_success()

        # Check for recovery
        if provider_name == self._primary_name and provider_name != self._current_name:
            if self.get_health(provider_name) == ProviderHealth.HEALTHY:
                # Primary recovered, switch back
                self._current_name = self._primary_name
                if self._on_recovery:
                    self._on_recovery(provider_name)

    def _record_failure(self, provider_name: str, error: Exception):
        """Record failed request"""
        failure_type = self._classify_error(error)

        stats = self._stats[provider_name]
        stats.total_requests += 1
        stats.failed_requests += 1
        stats.last_failure = datetime.now()
        stats.recent_failures.append(
            FailureRecord(
                failure_type=failure_type, timestamp=datetime.now(), error_message=str(error)
            )
        )

        circuit = self._circuit_breakers[provider_name]
        circuit.record_failure()

    async def generate_completion(
        self, messages: List[Message], stream: bool = False, **kwargs
    ) -> CompletionResponse | AsyncIterator[str]:
        """
        Generate completion with automatic failover.

        Args:
            messages: List of messages
            stream: Whether to stream response
            **kwargs: Additional parameters

        Returns:
            CompletionResponse or AsyncIterator for streaming
        """
        tried_providers = set()
        last_error = None

        while len(tried_providers) < len(self.providers):
            provider_name = self._current_name

            # Skip if already tried
            if provider_name in tried_providers:
                provider_name = self._select_fallback(provider_name)
                if not provider_name:
                    break

            tried_providers.add(provider_name)
            provider = self.providers[provider_name]
            circuit = self._circuit_breakers[provider_name]

            # Check circuit breaker
            if not circuit.can_execute():
                fallback = self._select_fallback(provider_name)
                if fallback:
                    provider_name = fallback
                    provider = self.providers[fallback]
                else:
                    # All circuits open, wait and retry
                    await asyncio.sleep(1.0)
                    continue

            try:
                start_time = time.time()

                # Execute with retry
                result = await self._retry_handler.execute_with_retry(
                    provider.generate_completion,
                    messages,
                    stream=stream,
                    should_retry=self._is_retryable,
                    **kwargs,
                )

                latency = time.time() - start_time
                self._record_success(provider_name, latency)

                return result

            except Exception as e:
                last_error = e
                self._record_failure(provider_name, e)

                # Try failover
                fallback = self._select_fallback(provider_name)
                if fallback:
                    old_provider = self._current_name
                    self._current_name = fallback
                    if self._on_failover:
                        self._on_failover(old_provider, fallback, e)

        # All providers failed
        raise last_error or RuntimeError("All providers failed")



    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all providers"""
        return {
            "current_provider": self._current_name,
            "primary_provider": self._primary_name,
            "providers": {
                name: {
                    "health": self.get_health(name).value,
                    "success_rate": self._stats[name].success_rate,
                    "avg_latency": self._stats[name].average_latency,
                    "total_requests": self._stats[name].total_requests,
                    "circuit_state": self._circuit_breakers[name].state.value,
                }
                for name in self.providers
            },
        }


# =============================================================================
# STREAMING WRAPPER
# =============================================================================


class ResilientStreamWrapper:
    """
    Wrapper for resilient streaming that handles mid-stream failures.
    """

    def __init__(self, resilient_provider: ResilientProvider, messages: List[Message], **kwargs):
        self.resilient_provider = resilient_provider
        self.messages = messages
        self.kwargs = kwargs
        self._buffer: List[str] = []
        self._current_stream: Optional[AsyncIterator[str]] = None
        self._completed = False

    async def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if self._completed:
            raise StopAsyncIteration

        try:
            if self._current_stream is None:
                # Start new stream
                self._current_stream = await self.resilient_provider.generate_completion(
                    self.messages, stream=True, **self.kwargs
                )

            chunk = await self._current_stream.__anext__()
            self._buffer.append(chunk)
            return chunk

        except StopAsyncIteration:
            self._completed = True
            raise

        except Exception:
            # Mid-stream failure, attempt recovery
            self._current_stream = None

            # Add partial response to messages for continuation
            if self._buffer:
                partial_response = "".join(self._buffer)
                self.messages = self.messages + [
                    Message(role="assistant", content=partial_response)
                ]
                self._buffer = []

            # Retry with failover
            try:
                self._current_stream = await self.resilient_provider.generate_completion(
                    self.messages, stream=True, **self.kwargs
                )
                chunk = await self._current_stream.__anext__()
                self._buffer.append(chunk)
                return chunk
            except Exception:
                self._completed = True
                raise


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def create_resilient_provider(
    anthropic_key: Optional[str] = None,
    openai_key: Optional[str] = None,
    primary: str = "anthropic",
    **kwargs,
) -> ResilientProvider:
    """
    Create a resilient provider from API keys.

    Args:
        anthropic_key: Anthropic API key
        openai_key: OpenAI API key
        primary: Primary provider name
        **kwargs: Additional configuration

    Returns:
        ResilientProvider instance
    """
    from .anthropic_provider import AnthropicProvider
    from .openai_provider import OpenAIProvider

    providers = {}

    if anthropic_key:
        providers["anthropic"] = AnthropicProvider(
            api_key=anthropic_key, model=kwargs.get("anthropic_model", "claude-3-5-sonnet-20241022")
        )

    if openai_key:
        providers["openai"] = OpenAIProvider(
            api_key=openai_key,
            model=kwargs.get("openai_model", "gpt-4o"),
            base_url=kwargs.get("openai_base_url"),
        )

    if not providers:
        raise ValueError("At least one API key required")

    return ResilientProvider(
        providers=providers,
        primary_provider=primary if primary in providers else None,
        circuit_config=kwargs.get("circuit_config"),
        retry_config=kwargs.get("retry_config"),
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ProviderHealth",
    "FailureType",
    "FailureRecord",
    "ProviderStats",
    "CircuitBreakerConfig",
    "CircuitBreaker",
    "RetryConfig",
    "RetryHandler",
    "ResilientProvider",
    "ResilientStreamWrapper",
    "create_resilient_provider",
]
