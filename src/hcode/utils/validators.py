"""
Input Validation Utilities.

Provides validators for file paths, API keys, prompts, and other user inputs.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


class ValidationResult:
    """Result of a validation check."""

    def __init__(
        self,
        is_valid: bool,
        value: Any = None,
        error: str | None = None,
        warnings: list[str] | None = None,
    ):
        self.is_valid = is_valid
        self.value = value
        self.error = error
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        return self.is_valid

    @classmethod
    def success(cls, value: Any = None, warnings: list[str] | None = None) -> "ValidationResult":
        return cls(True, value=value, warnings=warnings)

    @classmethod
    def failure(cls, error: str) -> "ValidationResult":
        return cls(False, error=error)


def validate_file_path(
    path: str,
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_directory: bool = False,
    allowed_extensions: list[str] | None = None,
    max_size_bytes: int | None = None,
) -> ValidationResult:
    """
    Validate a file path.

    Args:
        path: File path to validate
        must_exist: Whether the path must exist
        must_be_file: Whether the path must be a file
        must_be_directory: Whether the path must be a directory
        allowed_extensions: List of allowed file extensions
        max_size_bytes: Maximum file size in bytes

    Returns:
        ValidationResult with validated path
    """
    if not path:
        return ValidationResult.failure("Path cannot be empty")

    # Normalize path
    try:
        normalized = Path(path).resolve()
    except Exception as e:
        return ValidationResult.failure(f"Invalid path: {e}")

    # Check existence
    if must_exist and not normalized.exists():
        return ValidationResult.failure(f"Path does not exist: {path}")

    # Check if file
    if must_be_file and normalized.exists() and not normalized.is_file():
        return ValidationResult.failure(f"Path is not a file: {path}")

    # Check if directory
    if must_be_directory and normalized.exists() and not normalized.is_dir():
        return ValidationResult.failure(f"Path is not a directory: {path}")

    # Check extension
    if allowed_extensions and normalized.suffix.lower() not in allowed_extensions:
        return ValidationResult.failure(
            f"File extension not allowed. Allowed: {', '.join(allowed_extensions)}"
        )

    # Check file size
    if max_size_bytes and normalized.exists() and normalized.is_file():
        size = normalized.stat().st_size
        if size > max_size_bytes:
            return ValidationResult.failure(
                f"File too large: {size:,} bytes (max: {max_size_bytes:,} bytes)"
            )

    warnings = []

    # Check for potentially dangerous paths
    dangerous_patterns = [
        r"^/etc/",
        r"^/usr/",
        r"^/bin/",
        r"^/sbin/",
        r"^C:\\Windows",
        r"^C:\\Program Files",
    ]
    for pattern in dangerous_patterns:
        if re.match(pattern, str(normalized), re.IGNORECASE):
            warnings.append(f"Path appears to be a system directory: {normalized}")
            break

    return ValidationResult.success(str(normalized), warnings=warnings)


def validate_api_key(
    key: str,
    provider: str = "anthropic",
) -> ValidationResult:
    """
    Validate an API key format.

    Args:
        key: API key to validate
        provider: Provider name (anthropic, openai)

    Returns:
        ValidationResult
    """
    if not key:
        return ValidationResult.failure("API key cannot be empty")

    key = key.strip()

    # Provider-specific validation
    patterns = {
        "anthropic": r"^sk-ant-[a-zA-Z0-9_-]{90,}$",
        "openai": r"^sk-[a-zA-Z0-9]{32,}$",
    }

    if provider in patterns:
        pattern = patterns[provider]
        if not re.match(pattern, key):
            return ValidationResult.failure(
                f"Invalid {provider} API key format"
            )

    # Mask the key for security
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"

    return ValidationResult.success(key, warnings=[f"Using key: {masked}"])


def validate_model_name(
    model: str,
    provider: str | None = None,
) -> ValidationResult:
    """
    Validate a model name.

    Args:
        model: Model name to validate
        provider: Optional provider for stricter validation

    Returns:
        ValidationResult
    """
    if not model:
        return ValidationResult.failure("Model name cannot be empty")

    model = model.strip()

    # Known valid models
    known_models = {
        "anthropic": [
            "claude-3-opus-20240229",
            "claude-3-5-sonnet-20241022",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-sonnet-4-20250514",
        ],
        "openai": [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
        ],
        "ollama": [
            "llama3.2",
            "llama3.2:3b",
            "llama3.2:7b",
            "llama3.2:70b",
            "mistral",
            "codellama",
        ],
    }

    warnings = []

    if provider and provider in known_models:
        if model not in known_models[provider]:
            warnings.append(
                f"Model '{model}' is not in the known list for {provider}. "
                "It may be valid but unrecognized."
            )

    # Basic format validation
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$", model):
        return ValidationResult.failure("Invalid model name format")

    return ValidationResult.success(model, warnings=warnings)


def validate_prompt(
    prompt: str,
    min_length: int = 1,
    max_length: int = 100000,
) -> ValidationResult:
    """
    Validate a user prompt.

    Args:
        prompt: Prompt text to validate
        min_length: Minimum length
        max_length: Maximum length

    Returns:
        ValidationResult
    """
    if not prompt:
        return ValidationResult.failure("Prompt cannot be empty")

    prompt = prompt.strip()

    if len(prompt) < min_length:
        return ValidationResult.failure(
            f"Prompt too short (min: {min_length} characters)"
        )

    if len(prompt) > max_length:
        return ValidationResult.failure(
            f"Prompt too long (max: {max_length:,} characters)"
        )

    warnings = []

    # Check for potential issues
    if len(prompt) > 10000:
        warnings.append("Very long prompt - consider breaking it down")

    if prompt.count("```") % 2 != 0:
        warnings.append("Unclosed code block detected")

    return ValidationResult.success(prompt, warnings=warnings)


def validate_temperature(value: float) -> ValidationResult:
    """
    Validate temperature parameter.

    Args:
        value: Temperature value

    Returns:
        ValidationResult
    """
    if not isinstance(value, (int, float)):
        return ValidationResult.failure("Temperature must be a number")

    if value < 0.0:
        return ValidationResult.failure("Temperature cannot be negative")

    if value > 2.0:
        return ValidationResult.failure("Temperature cannot exceed 2.0")

    warnings = []
    if value > 1.5:
        warnings.append("High temperature may produce unpredictable outputs")
    elif value < 0.1:
        warnings.append("Very low temperature may produce repetitive outputs")

    return ValidationResult.success(value, warnings=warnings)


def validate_max_tokens(value: int, context_limit: int = 200000) -> ValidationResult:
    """
    Validate max_tokens parameter.

    Args:
        value: Max tokens value
        context_limit: Model's context window limit

    Returns:
        ValidationResult
    """
    if not isinstance(value, int):
        return ValidationResult.failure("Max tokens must be an integer")

    if value < 1:
        return ValidationResult.failure("Max tokens must be at least 1")

    if value > context_limit:
        return ValidationResult.failure(
            f"Max tokens cannot exceed context limit ({context_limit:,})"
        )

    warnings = []
    if value > 8192:
        warnings.append("Large max_tokens may increase costs")

    return ValidationResult.success(value, warnings=warnings)


def validate_url(url: str) -> ValidationResult:
    """
    Validate a URL.

    Args:
        url: URL to validate

    Returns:
        ValidationResult
    """
    if not url:
        return ValidationResult.failure("URL cannot be empty")

    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return ValidationResult.failure("Invalid URL format")

        if result.scheme not in ("http", "https"):
            return ValidationResult.failure("URL must use http or https")

    except Exception as e:
        return ValidationResult.failure(f"Invalid URL: {e}")

    return ValidationResult.success(url)


def validate_session_id(session_id: str) -> ValidationResult:
    """
    Validate a session ID.

    Args:
        session_id: Session ID to validate

    Returns:
        ValidationResult
    """
    if not session_id:
        return ValidationResult.failure("Session ID cannot be empty")

    # Allow alphanumeric, hyphens, and underscores
    if not re.match(r"^[a-zA-Z0-9_-]{1,64}$", session_id):
        return ValidationResult.failure(
            "Session ID must be alphanumeric (with - and _) and max 64 characters"
        )

    return ValidationResult.success(session_id)


def validate_command(
    command: str,
    blocked_patterns: list[str] | None = None,
) -> ValidationResult:
    """
    Validate a shell command for safety.

    Args:
        command: Command to validate
        blocked_patterns: List of blocked command patterns

    Returns:
        ValidationResult
    """
    if not command:
        return ValidationResult.failure("Command cannot be empty")

    command = command.strip()

    # Default dangerous patterns
    default_blocked = [
        r"rm\s+-rf\s+/",
        r"rm\s+-rf\s+~",
        r"mkfs\.",
        r"dd\s+if=/dev/zero",
        r":\(\)\{:|:&\};:",
        r"chmod\s+-R\s+777\s+/",
        r">\s*/dev/sda",
        r"\|\s*sh\s*$",
        r"\|\s*bash\s*$",
    ]

    blocked = blocked_patterns or default_blocked
    warnings = []

    for pattern in blocked:
        if re.search(pattern, command, re.IGNORECASE):
            return ValidationResult.failure(
                f"Potentially dangerous command blocked: {pattern}"
            )

    # Warn about potentially risky commands
    risky_patterns = [
        (r"^sudo\s+", "Command uses sudo - requires elevated privileges"),
        (r"rm\s+", "Command removes files - verify targets"),
        (r"git\s+push", "Command pushes to remote - verify changes"),
        (r"git\s+reset\s+--hard", "Command resets git - may lose uncommitted changes"),
        (r"pip\s+install", "Command installs packages - verify source"),
        (r"npm\s+install", "Command installs packages - verify source"),
    ]

    for pattern, warning in risky_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            warnings.append(warning)

    return ValidationResult.success(command, warnings=warnings)


def validate_glob_pattern(pattern: str) -> ValidationResult:
    """
    Validate a glob pattern.

    Args:
        pattern: Glob pattern to validate

    Returns:
        ValidationResult
    """
    if not pattern:
        return ValidationResult.failure("Pattern cannot be empty")

    # Check for valid glob syntax
    try:
        # Basic validation - make sure it's not too broad
        if pattern in ("*", "**", "**/*"):
            return ValidationResult.success(
                pattern,
                warnings=["Very broad pattern - may match many files"]
            )

        # Check for invalid characters
        invalid_chars = ["<", ">", "|", '"', "\0"]
        for char in invalid_chars:
            if char in pattern:
                return ValidationResult.failure(f"Invalid character in pattern: {char}")

    except Exception as e:
        return ValidationResult.failure(f"Invalid pattern: {e}")

    return ValidationResult.success(pattern)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe use.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = os.path.basename(filename)

    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*\0'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing spaces and dots
    filename = filename.strip(". ")

    # Ensure not empty
    if not filename:
        filename = "unnamed"

    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[: max_length - len(ext)] + ext

    return filename


def is_safe_path(path: str, base_dir: str | None = None) -> bool:
    """
    Check if a path is safe (doesn't escape base directory).

    Args:
        path: Path to check
        base_dir: Base directory to contain path in

    Returns:
        True if safe, False otherwise
    """
    try:
        resolved = Path(path).resolve()

        if base_dir:
            base = Path(base_dir).resolve()
            # Check if path is within base
            try:
                resolved.relative_to(base)
                return True
            except ValueError:
                return False

        # Without base_dir, just check for path traversal attempts
        if ".." in str(path):
            return False

        return True

    except Exception:
        return False
