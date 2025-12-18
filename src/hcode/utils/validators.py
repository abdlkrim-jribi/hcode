# validators.py
"""Input Validation Utilities.

Provides validators for file paths, API keys, prompts, and other user inputs.

This module contains helper classes and functions for validating user input.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class ValidationError(Exception):
    """Raised when validation fails.

    Args:
        message (str): Human‑readable error message.
        field (str | None, optional): Name of the field that failed validation.
    """

    def __init__(self, message: str, field: str | None = None):
        """Initialize ValidationError.

        Args:
            message: Description of the validation error.
            field: Optional field name associated with the error.
        """
        self.message = message
        self.field = field
        super().__init__(message)


class ValidationResult:
    """Result of a validation check.

    Attributes:
        is_valid (bool): Indicates if validation succeeded.
        value (Any): The validated value, if any.
        error (str | None): Error message if validation failed.
        warnings (list[str]): List of warning messages.
    """

    def __init__(self, is_valid: bool, value: Any = None, error: str | None = None, warnings: list[str] | None = None):
        """Create a ValidationResult.

        Args:
            is_valid: Whether the validation succeeded.
            value: The validated value.
            error: Error message if validation failed.
            warnings: Optional list of warnings.
        """
        self.is_valid = is_valid
        self.value = value
        self.error = error
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        """Return truthiness based on ``is_valid``.

        Returns:
            bool: ``True`` if validation succeeded, otherwise ``False``.
        """
        return self.is_valid

    @classmethod
    def success(cls, value: Any = None, warnings: list[str] | None = None) -> "ValidationResult":
        """Factory for a successful validation.

        Args:
            value: The validated value.
            warnings: Optional warnings generated during validation.

        Returns:
            ValidationResult: An instance representing success.
        """
        return cls(True, value=value, warnings=warnings)

    @classmethod
    def failure(cls, error: str) -> "ValidationResult":
        """Factory for a failed validation.

        Args:
            error: Description of why validation failed.

        Returns:
            ValidationResult: An instance representing failure.
        """
        return cls(False, error=error)


def validate_file_path(
    path: str,
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_directory: bool = False,
    allowed_extensions: list[str] | None = None,
    max_size_bytes: int | None = None,
) -> ValidationResult:
    """Validate a filesystem path.

    Args:
        path (str): The path to validate.
        must_exist (bool, optional): If True, the path must exist. Defaults to False.
        must_be_file (bool, optional): If True, the path must be a file. Defaults to False.
        must_be_directory (bool, optional): If True, the path must be a directory. Defaults to False.
        allowed_extensions (list[str] | None, optional): Optional list of permitted file extensions (including the leading dot). Defaults to None.
        max_size_bytes (int | None, optional): Optional maximum file size in bytes. Defaults to None.

    Returns:
        ValidationResult: Success with the resolved path or failure with an error message.
    """
    if not path:
        return ValidationResult.failure('Path cannot be empty')
    try:
        normalized = Path(path).resolve()
    except Exception as e:
        return ValidationResult.failure(f'Invalid path: {e}')
    if must_exist and not normalized.exists():
        return ValidationResult.failure(f'Path does not exist: {path}')
    if must_be_file and normalized.exists() and not normalized.is_file():
        return ValidationResult.failure(f'Path is not a file: {path}')
    if must_be_directory and normalized.exists() and not normalized.is_dir():
        return ValidationResult.failure(f'Path is not a directory: {path}')
    if allowed_extensions and normalized.suffix.lower() not in allowed_extensions:
        return ValidationResult.failure(
            f"File extension not allowed. Allowed: {', '.join(allowed_extensions)}"
        )
    if max_size_bytes and normalized.exists() and normalized.is_file():
        size = normalized.stat().st_size
        if size > max_size_bytes:
            return ValidationResult.failure(
                f'File too large: {size:,} bytes (max: {max_size_bytes:,} bytes)'
            )
    warnings = []
    dangerous_patterns = [
        r'^/etc/',
        r'^/usr/',
        r'^/bin/',
        r'^/sbin/',
        r'^C:\\Windows',
        r'^C:\\Program Files',
    ]
    for pattern in dangerous_patterns:
        if re.match(pattern, str(normalized), re.IGNORECASE):
            warnings.append(f'Path appears to be a system directory: {normalized}')
            break
    return ValidationResult.success(str(normalized), warnings=warnings)


def validate_api_key(key: str, provider: str = 'anthropic') -> ValidationResult:
    """Validate an API key for a given provider.

    Args:
        key: The API key string.
        provider: The name of the provider (e.g., ``'anthropic'`` or ``'openai'``).

    Returns:
        ValidationResult: Success with the original key or failure with an error message.
    """
    if not key:
        return ValidationResult.failure('API key cannot be empty')
    key = key.strip()
    patterns = {
        'anthropic': r'^sk-ant-[a-zA-Z0-9_-]{90,}$',
        'openai': r'^sk-[a-zA-Z0-9]{32,}$',
    }
    if provider in patterns:
        pattern = patterns[provider]
        if not re.match(pattern, key):
            return ValidationResult.failure(f'Invalid {provider} API key format')
    masked = key[:8] + '...' + key[-4:] if len(key) > 12 else '***'
    return ValidationResult.success(key, warnings=[f'Using key: {masked}'])


def validate_model_name(model: str, provider: str | None = None) -> ValidationResult:
    """Validate a model name for a specific provider.

    Args:
        model: The model identifier.
        provider: Optional provider name to restrict validation against known models.

    Returns:
        ValidationResult: Success with the model name or failure with an error message.
    """
    if not model:
        return ValidationResult.failure('Model name cannot be empty')
    model = model.strip()
    known_models = {
        'anthropic': [
            'claude-3-opus-20240229',
            'claude-3-5-sonnet-20241022',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307',
            'claude-sonnet-4-20250514',
        ],
        'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'],
        'ollama': [
            'llama3.2',
            'llama3.2:3b',
            'llama3.2:7b',
            'llama3.2:70b',
            'mistral',
            'codellama',
        ],
    }
    warnings = []
    if provider and provider in known_models:
        if model not in known_models[provider]:
            warnings.append(
                f"Model '{model}' is not in the known list for {provider}. It may be valid but unrecognized."
            )
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._:-]*$', model):
        return ValidationResult.failure('Invalid model name format')
    return ValidationResult.success(model, warnings=warnings)


def validate_prompt(prompt: str, min_length: int = 1, max_length: int = 100_000) -> ValidationResult:
    """Validate a textual prompt.

    Args:
        prompt: The prompt string.
        min_length: Minimum allowed length.
        max_length: Maximum allowed length.

    Returns:
        ValidationResult: Success with the cleaned prompt or failure with an error message.
    """
    if not prompt:
        return ValidationResult.failure('Prompt cannot be empty')
    prompt = prompt.strip()
    if len(prompt) < min_length:
        return ValidationResult.failure(f'Prompt too short (min: {min_length} characters)')
    if len(prompt) > max_length:
        return ValidationResult.failure(f'Prompt too long (max: {max_length:,} characters)')
    warnings = []
    if len(prompt) > 10_000:
        warnings.append('Very long prompt - consider breaking it down')
    if prompt.count('```') % 2 != 0:
        warnings.append('Unclosed code block detected')
    return ValidationResult.success(prompt, warnings=warnings)


def validate_temperature(value: float) -> ValidationResult:
    """Validate a temperature value for model sampling.

    Args:
        value: Temperature between 0.0 and 2.0 (inclusive).

    Returns:
        ValidationResult: Success if within range, otherwise failure.
    """
    if not isinstance(value, (int, float)):
        return ValidationResult.failure('Temperature must be a number')
    if not 0.0 <= float(value) <= 2.0:
        return ValidationResult.failure('Temperature must be between 0.0 and 2.0')
    return ValidationResult.success(float(value))


def validate_max_tokens(value: int) -> ValidationResult:
    """Validate the maximum number of tokens.

    Args:
        value: The maximum number of tokens.

    Returns:
        ValidationResult: Success if valid, otherwise failure.
    """
    if not isinstance(value, int):
        return ValidationResult.failure('Max tokens must be an integer')
    if value <= 0:
        return ValidationResult.failure('Max tokens must be greater than 0')
    return ValidationResult.success(value)


def validate_url(url: str) -> ValidationResult:
    """Validate a URL string.

    Args:
        url: The URL to validate.

    Returns:
        ValidationResult: Success with the URL or failure with an error message.
    """
    if not url:
        return ValidationResult.failure('URL cannot be empty')
    url = url.strip()
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return ValidationResult.failure('Invalid URL format')
        if result.scheme not in ('http', 'https'):
            return ValidationResult.failure('URL must use http or https')
    except Exception as e:
        return ValidationResult.failure(f'Invalid URL: {e}')
    return ValidationResult.success(url)


def validate_session_id(session_id: str) -> ValidationResult:
    """Validate a session identifier.

    Args:
        session_id: The session ID string.

    Returns:
        ValidationResult: Success if the ID matches the required pattern.
    """
    if not session_id:
        return ValidationResult.failure('Session ID cannot be empty')
    if not re.match(r'^[a-zA-Z0-9_-]{1,64}$', session_id):
        return ValidationResult.failure(
            'Session ID must be alphanumeric (with - and _) and max 64 characters'
        )
    return ValidationResult.success(session_id)


def validate_command(command: str, blocked_patterns: list[str] | None = None) -> ValidationResult:
    """Validate a shell command against dangerous patterns.

    Args:
        command: The command string to validate.
        blocked_patterns: Optional custom list of regex patterns to block.

    Returns:
        ValidationResult: Success with the command or failure if a blocked pattern is found.
    """
    if not command:
        return ValidationResult.failure('Command cannot be empty')
    command = command.strip()
    default_blocked = [
        r'rm\s+-rf\s+/',
        r'rm\s+-rf\s+~',
        r'mkfs\.',
        r'dd\s+if=/dev/zero',
        r':\(\)\{:|:&\};:',
        r'chmod\s+-R\s+777\s+/',
        r'>\s*/dev/sda',
        r'\|\s*sh\s*$',
        r'\|\s*bash\s*$',
    ]
    blocked = blocked_patterns or default_blocked
    for pattern in blocked:
        if re.search(pattern, command, re.IGNORECASE):
            return ValidationResult.failure(f'Potentially dangerous command blocked: {pattern}')
    risky_patterns = [
        (r'^sudo\s+', 'Command uses sudo - requires elevated privileges'),
        (r'rm\s+', 'Command removes files - verify targets'),
        (r'git\s+push', 'Command pushes to remote - verify changes'),
        (r'git\s+reset\s+--hard', 'Command resets git - may lose uncommitted changes'),
        (r'pip\s+install', 'Command installs packages - verify source'),
        (r'npm\s+install', 'Command installs packages - verify source'),
    ]
    warnings = []
    for pattern, warning in risky_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            warnings.append(warning)
    return ValidationResult.success(command, warnings=warnings)


def validate_glob_pattern(pattern: str) -> ValidationResult:
    """Validate a glob pattern string.

    Args:
        pattern: The glob pattern to validate.

    Returns:
        ValidationResult: Success with the pattern or failure with an error message.
    """
    if not pattern:
        return ValidationResult.failure('Pattern cannot be empty')
    try:
        if pattern in ('*', '**', '**/*'):
            return ValidationResult.success(pattern, warnings=['Very broad pattern - may match many files'])
        invalid_chars = ['<', '>', '|', '"', '\x00']
        for char in invalid_chars:
            if char in pattern:
                return ValidationResult.failure(f'Invalid character in pattern: {char}')
    except Exception as e:
        return ValidationResult.failure(f'Invalid pattern: {e}')
    return ValidationResult.success(pattern)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to be safe for the filesystem.

    Args:
        filename: The original filename.

    Returns:
        str: A sanitized filename.
    """
    filename = os.path.basename(filename)
    invalid_chars = '<>:"/\\|?*\x00'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    filename = filename.strip('. ')
    if not filename:
        filename = 'unnamed'
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[: max_length - len(ext)] + ext
    return filename


def is_safe_path(path: str, base_dir: str | None = None) -> bool:
    """Determine whether a path is safe relative to an optional base directory.

    Args:
        path: The path to check.
        base_dir: Optional base directory to which ``path`` must be relative.

    Returns:
        bool: ``True`` if the path is safe, otherwise ``False``.
    """
    try:
        resolved = Path(path).resolve()
        if base_dir:
            base = Path(base_dir).resolve()
            try:
                resolved.relative_to(base)
                return True
            except ValueError:
                return False
        if '..' in str(path):
            return False
        return True
    except Exception:
        return False

