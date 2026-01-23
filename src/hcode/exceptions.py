"""
exceptions.py
==============

Custom exception hierarchy for the **Hcode** tooling suite.

The original implementation contained minimal documentation, making it
hard for new contributors to understand the purpose of each exception
type.  This module now provides clear, concise docstrings for every
exception class, describing when it should be raised and what information
it carries.

All exceptions inherit from :class:`HcodeError`, which itself derives
from :class:`Exception`.  This design allows callers to catch either a
specific error (e.g., :class:`InvalidConfigurationError`) or any Hcode‑
related error by catching :class:`HcodeError`.

Typical usage:

```python
from hcode.exceptions import InvalidConfigurationError

def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise InvalidConfigurationError(f"Config file not found: {path}")
    # ... load logic ...

try:
    config = load_config("settings.yaml")
except HcodeError as exc:
    logger.error("Hcode failed: %s", exc)
    raise
```

The hierarchy is deliberately flat – each subclass represents a distinct
error condition that can be handled independently if needed.
"""

from __future__ import annotations

from typing import Any


class HCodeError(Exception):
    """
    Base exception for all HCode errors.

    All HCode-specific exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ):
        self.message = message
        self.code = code or "HCODE_ERROR"
        self.details = details or {}
        self.suggestion = suggestion
        super().__init__(message)

    def __str__(self) -> str:
        result = f"[{self.code}] {self.message}"
        if self.suggestion:
            result += f"\nSuggestion: {self.suggestion}"
        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
        }


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigError(HCodeError):
    """Base exception for configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message,
            code="CONFIG_ERROR",
            details={"config_key": config_key} if config_key else {},
            **kwargs,
        )
        self.config_key = config_key


class ConfigNotFoundError(ConfigError):
    """Raised when a configuration file is not found."""

    def __init__(self, path: str, **kwargs: Any):
        super().__init__(
            f"Configuration file not found: {path}",
            suggestion="Run 'hcode init' to create default configuration",
            **kwargs,
        )
        self.path = path


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        expected: str | None = None,
        actual: Any = None,
        **kwargs: Any,
    ):
        details = {"config_key": config_key} if config_key else {}
        if expected:
            details["expected"] = expected
        if actual is not None:
            details["actual"] = str(actual)

        super().__init__(message, config_key=config_key, **kwargs)
        self.details.update(details)
        self.expected = expected
        self.actual = actual


class MissingAPIKeyError(ConfigError):
    """Raised when a required API key is not configured."""

    def __init__(self, provider: str, **kwargs: Any):
        env_var = f"{provider.upper()}_API_KEY"
        super().__init__(
            f"API key not configured for {provider}",
            config_key=f"llm.{provider}_api_key",
            suggestion=f"Set {env_var} environment variable or add to config",
            **kwargs,
        )
        self.provider = provider


# =============================================================================
# LLM/Provider Errors
# =============================================================================


class LLMError(HCodeError):
    """Base exception for LLM-related errors."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ):
        details = {}
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model

        super().__init__(
            message,
            code="LLM_ERROR",
            details=details,
            **kwargs,
        )
        self.provider = provider
        self.model = model


class ProviderNotAvailableError(LLMError):
    """Raised when the requested provider is not available."""

    def __init__(self, provider: str, reason: str | None = None, **kwargs: Any):
        message = f"Provider not available: {provider}"
        if reason:
            message += f" ({reason})"
        super().__init__(
            message,
            provider=provider,
            suggestion="Check API key configuration or try a different provider",
            **kwargs,
        )


class ModelNotFoundError(LLMError):
    """Raised when the requested model is not found."""

    def __init__(
        self,
        model: str,
        provider: str | None = None,
        available_models: list[str] | None = None,
        **kwargs: Any,
    ):
        message = f"Model not found: {model}"
        suggestion = None
        if available_models:
            suggestion = f"Available models: {', '.join(available_models[:5])}"

        super().__init__(
            message,
            provider=provider,
            model=model,
            suggestion=suggestion,
            **kwargs,
        )
        self.available_models = available_models


class RateLimitError(LLMError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        provider: str,
        retry_after: float | None = None,
        **kwargs: Any,
    ):
        message = f"Rate limit exceeded for {provider}"
        if retry_after:
            message += f" (retry after {retry_after}s)"

        super().__init__(
            message,
            provider=provider,
            code="RATE_LIMIT",
            suggestion="Wait before retrying or reduce request frequency",
            **kwargs,
        )
        self.retry_after = retry_after


class TokenLimitError(LLMError):
    """Raised when token limit is exceeded."""

    def __init__(
        self,
        requested: int,
        limit: int,
        provider: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            f"Token limit exceeded: {requested:,} requested, {limit:,} max",
            provider=provider,
            model=model,
            code="TOKEN_LIMIT",
            suggestion="Reduce input size or increase max_tokens setting",
            **kwargs,
        )
        self.requested = requested
        self.limit = limit


class APIError(LLMError):
    """Raised for general API errors from providers."""

    def __init__(
        self,
        message: str,
        provider: str,
        status_code: int | None = None,
        response_body: str | None = None,
        **kwargs: Any,
    ):
        details = {"provider": provider}
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body[:500]  # Truncate

        super().__init__(
            message,
            provider=provider,
            code="API_ERROR",
            **kwargs,
        )
        self.details.update(details)
        self.status_code = status_code
        self.response_body = response_body


# =============================================================================
# Tool Errors
# =============================================================================


class ToolError(HCodeError):
    """Base exception for tool-related errors."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message,
            code="TOOL_ERROR",
            details={"tool": tool_name} if tool_name else {},
            **kwargs,
        )
        self.tool_name = tool_name


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found."""

    def __init__(self, tool_name: str, **kwargs: Any):
        super().__init__(
            f"Tool not found: {tool_name}",
            tool_name=tool_name,
            **kwargs,
        )


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
        original_error: Exception | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, tool_name=tool_name, **kwargs)
        if parameters:
            self.details["parameters"] = parameters
        if original_error:
            self.details["original_error"] = str(original_error)
        self.parameters = parameters
        self.original_error = original_error


class ToolPermissionError(ToolError):
    """Raised when tool operation is not permitted."""

    def __init__(
        self,
        message: str,
        tool_name: str,
        operation: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message,
            tool_name=tool_name,
            suggestion="Check permissions or enable auto_confirm_commands",
            **kwargs,
        )
        if operation:
            self.details["operation"] = operation
        self.operation = operation


# =============================================================================
# File System Errors
# =============================================================================


class FileSystemError(HCodeError):
    """Base exception for file system errors."""

    def __init__(
        self,
        message: str,
        path: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message,
            code="FILE_ERROR",
            details={"path": path} if path else {},
            **kwargs,
        )
        self.path = path


class FileNotFoundError_(FileSystemError):
    """Raised when a file is not found (custom to avoid shadowing builtin)."""

    def __init__(self, path: str, **kwargs: Any):
        super().__init__(
            f"File not found: {path}",
            path=path,
            **kwargs,
        )


class DirectoryNotFoundError(FileSystemError):
    """Raised when a directory is not found."""

    def __init__(self, path: str, **kwargs: Any):
        super().__init__(
            f"Directory not found: {path}",
            path=path,
            **kwargs,
        )


class FileReadError(FileSystemError):
    """Raised when file read fails."""

    def __init__(
        self,
        path: str,
        reason: str | None = None,
        **kwargs: Any,
    ):
        message = f"Failed to read file: {path}"
        if reason:
            message += f" ({reason})"
        super().__init__(message, path=path, **kwargs)


class FileWriteError(FileSystemError):
    """Raised when file write fails."""

    def __init__(
        self,
        path: str,
        reason: str | None = None,
        **kwargs: Any,
    ):
        message = f"Failed to write file: {path}"
        if reason:
            message += f" ({reason})"
        super().__init__(message, path=path, **kwargs)


class PathSecurityError(FileSystemError):
    """Raised when a path operation is blocked for security reasons."""

    def __init__(
        self,
        path: str,
        reason: str = "Path access denied",
        **kwargs: Any,
    ):
        super().__init__(
            f"Security: {reason} - {path}",
            path=path,
            code="SECURITY_ERROR",
            suggestion="Check if path is within allowed directories",
            **kwargs,
        )


# =============================================================================
# Agent Errors
# =============================================================================


class AgentError(HCodeError):
    """Base exception for agent-related errors."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message,
            code="AGENT_ERROR",
            details={"session_id": session_id} if session_id else {},
            **kwargs,
        )
        self.session_id = session_id


class AgentTimeoutError(AgentError):
    """Raised when agent operation times out."""

    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        **kwargs: Any,
    ):
        super().__init__(
            f"Operation timed out after {timeout_seconds}s: {operation}",
            code="AGENT_TIMEOUT",
            **kwargs,
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class AgentIterationLimitError(AgentError):
    """Raised when agent exceeds maximum iterations."""

    def __init__(
        self,
        max_iterations: int,
        task: str | None = None,
        **kwargs: Any,
    ):
        message = f"Agent exceeded maximum iterations ({max_iterations})"
        if task:
            message += f" for task: {task}"

        super().__init__(
            message,
            code="ITERATION_LIMIT",
            suggestion="Break down the task or increase max_iterations",
            **kwargs,
        )
        self.max_iterations = max_iterations
        self.task = task


# =============================================================================
# Memory Errors
# =============================================================================


class MemoryError_(HCodeError):
    """Base exception for memory-related errors (custom to avoid shadowing builtin)."""

    def __init__(
        self,
        message: str,
        **kwargs: Any,
    ):
        super().__init__(
            message,
            code="MEMORY_ERROR",
            **kwargs,
        )


class SessionNotFoundError(MemoryError_):
    """Raised when a session is not found."""

    def __init__(self, session_id: str, **kwargs: Any):
        super().__init__(
            f"Session not found: {session_id}",
            **kwargs,
        )
        self.session_id = session_id


class DatabaseError(MemoryError_):
    """Raised for database-related errors."""

    def __init__(
        self,
        message: str,
        db_path: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        if db_path:
            self.details["db_path"] = db_path
        self.db_path = db_path


# =============================================================================
# User Input Errors
# =============================================================================


class InputError(HCodeError):
    """Base exception for user input errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            message,
            code="INPUT_ERROR",
            details={"field": field} if field else {},
            **kwargs,
        )
        self.field = field


class InvalidArgumentError(InputError):
    """Raised for invalid CLI arguments."""

    def __init__(
        self,
        argument: str,
        reason: str | None = None,
        **kwargs: Any,
    ):
        message = f"Invalid argument: {argument}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, field=argument, **kwargs)


class MissingArgumentError(InputError):
    """Raised for missing required arguments."""

    def __init__(self, argument: str, **kwargs: Any):
        super().__init__(
            f"Missing required argument: {argument}",
            field=argument,
            **kwargs,
        )


# =============================================================================
# Utility Functions
# =============================================================================


def format_exception_for_user(error: Exception) -> str:
    """
    Format an exception for user-friendly display.

    Args:
        error: Exception to format

    Returns:
        Formatted error message
    """
    if isinstance(error, HCodeError):
        return str(error)

    # Handle common Python exceptions
    error_messages = {
        ConnectionError: "Connection failed. Check your network connection.",
        TimeoutError: "Operation timed out. Please try again.",
        PermissionError: "Permission denied. Check file/directory permissions.",
        FileNotFoundError: "File or directory not found.",
        KeyboardInterrupt: "Operation cancelled by user.",
    }

    for error_type, message in error_messages.items():
        if isinstance(error, error_type):
            return message

    # Generic fallback
    return f"An error occurred: {str(error)}"


def is_retriable_error(error: Exception) -> bool:
    """
    Check if an error is retriable.

    Args:
        error: Exception to check

    Returns:
        True if the error is retriable
    """
    retriable_types = (
        RateLimitError,
        ConnectionError,
        TimeoutError,
        APIError,
    )
    return isinstance(error, retriable_types)
