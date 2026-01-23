"""
HCode Default Configurations.

This module defines the default configuration values and constants used throughout the HCode
framework, including version information, model settings, pricing, context windows, and
various operational defaults. These defaults can be overridden by user‑provided
configuration files.
"""

from __future__ import annotations

from typing import Final


# Version information
VERSION: Final[str] = "1.0.0"
APP_NAME: Final[str] = "hcode"
APP_DESCRIPTION: Final[str] = "HCode - An intelligent AI coding agent for your terminal"

# Default model configurations
DEFAULT_MODELS: Final[dict[str, dict[str, str]]] = {
    "anthropic": {
        "small": "claude-3-haiku-20240307",
        "mid": "claude-3-5-sonnet-20241022",
        "big": "claude-3-opus-20240229",
        "default": "claude-3-5-sonnet-20241022",
    },
    "openai": {
        "small": "gpt-4o-mini",
        "mid": "gpt-4o",
        "big": "gpt-4-turbo",
        "default": "gpt-4o",
    },
    "ollama": {
        "small": "llama3.2:3b",
        "mid": "llama3.2:7b",
        "big": "llama3.2:70b",
        "default": "llama3.2:7b",
    },
}

# Model pricing per million tokens (input, output)
MODEL_PRICING: Final[dict[str, tuple[float, float]]] = {
    # Anthropic models
    "claude-3-opus-20240229": (15.00, 75.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-sonnet-20240229": (3.00, 15.00),
    "claude-3-haiku-20240307": (0.25, 1.25),
    # OpenAI models
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4o": (5.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
}

# Context window sizes
CONTEXT_WINDOWS: Final[dict[str, int]] = {
    # Anthropic models
    "claude-3-opus-20240229": 200000,
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-sonnet-20240229": 200000,
    "claude-3-haiku-20240307": 200000,
    # OpenAI models
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4": 8192,
    "gpt-3.5-turbo": 16385,
}

# Default generation parameters
DEFAULT_TEMPERATURE: Final[float] = 0.7
DEFAULT_MAX_TOKENS: Final[int] = 4096
DEFAULT_TOP_P: Final[float] = 1.0

# Context management
DEFAULT_MAX_CONTEXT_TOKENS: Final[int] = 100000
CONTEXT_BUFFER_TOKENS: Final[int] = 2000  # Reserved for response

# File operation defaults
MAX_FILE_SIZE_BYTES: Final[int] = 10 * 1024 * 1024  # 10MB
MAX_LINES_PER_READ: Final[int] = 2000
DEFAULT_ENCODING: Final[str] = "utf-8"

# UI defaults
DEFAULT_THEME: Final[str] = "auto"
TERMINAL_WIDTH_MIN: Final[int] = 40
TERMINAL_WIDTH_MAX: Final[int] = 200

# Logging defaults
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
LOG_FILE_MAX_BYTES: Final[int] = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT: Final[int] = 5

# Memory defaults
MEMORY_DB_NAME: Final[str] = "memory.db"
MAX_HISTORY_ENTRIES: Final[int] = 100
SESSION_EXPIRY_DAYS: Final[int] = 30

# Safety defaults
DANGEROUS_COMMANDS: Final[list[str]] = [
    "rm -rf /",
    "rm -rf ~",
    "rm -rf /*",
    ":(){:|:&};:",
    "mkfs",
    "dd if=/dev/zero",
    "chmod -R 777 /",
    "chown -R",
    "> /dev/sda",
    "mv /* /dev/null",
    "wget -O- | sh",
    "curl | sh",
]

CONFIRMATION_REQUIRED_PATTERNS: Final[list[str]] = [
    "rm ",
    "delete",
    "drop ",
    "truncate",
    "git push --force",
    "git push -f",
    "git reset --hard",
    "git clean -fd",
    "npm publish",
    "pip install --upgrade",
]

# Ignored file patterns (for search operations)
IGNORED_PATTERNS: Final[list[str]] = [
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    "*.egg-info",
    ".eggs",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
]

# Binary file extensions (skip reading)
BINARY_EXTENSIONS: Final[set[str]] = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".rar",
    ".7z",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".ico",
    ".webp",
    ".svg",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".aac",
    ".mp4",
    ".avi",
    ".mkv",
    ".mov",
    ".wmv",
    ".webm",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".obj",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".db",
    ".sqlite",
    ".sqlite3",
}

# Default system prompt for coding tasks
DEFAULT_SYSTEM_PROMPT: Final[
    str
] = """You are HCode, an intelligent AI coding assistant.
Your purpose is to help developers with software engineering tasks including:
- Writing, reviewing, and debugging code
- Explaining technical concepts
- Refactoring and optimizing code
- Creating tests and documentation
- Analyzing project structures

Guidelines:
1. Write clean, maintainable, and well-documented code
2. Follow best practices and design patterns
3. Consider security, performance, and edge cases
4. Provide clear explanations when needed
5. Ask clarifying questions when requirements are unclear
6. Use the appropriate tools when needed (file operations, command execution, etc.)

When modifying files:
- Always read files before editing them
- Make minimal, focused changes
- Preserve existing code style and conventions
- Test changes when possible
"""

# Interactive chat commands
CHAT_COMMANDS: Final[dict[str, str]] = {
    "/help": "Show available commands",
    "/exit": "Exit chat session",
    "/quit": "Exit chat session (alias)",
    "/clear": "Clear conversation history",
    "/stats": "Show session statistics",
    "/export": "Export conversation to file",
    "/model": "Show or switch current model",
    "/system": "Show or set system prompt",
    "/history": "Show conversation history",
    "/save": "Save current session",
    "/load": "Load a saved session",
    "/undo": "Undo last file change",
    "/diff": "Show recent file changes",
}

# Default config file template
DEFAULT_CONFIG_YAML: Final[
    str
] = """# HCode Configuration
# Documentation: https://github.com/hcode-dev/hcode

# LLM Provider Settings
llm:
  provider: auto  # anthropic, openai, ollama, or auto
  # anthropic_api_key: sk-ant-...  # Or set ANTHROPIC_API_KEY env var
  # openai_api_key: sk-...         # Or set OPENAI_API_KEY env var
  ollama_base_url: http://localhost:11434
  model: claude-sonnet-4-20250514
  max_tokens: 4096
  temperature: 0.7

# Agent Behavior
agent:
  max_context_tokens: 100000
  auto_confirm_commands: false
  streaming: true
  verbose: false
  use_sub_agents: false
  max_iterations: 50

# User Interface
ui:
  theme: auto  # dark, light, or auto
  show_tokens: false
  show_cost: true
  syntax_highlighting: true
  markdown_rendering: true
  emoji_enabled: true

# Logging
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file_enabled: true
  debug_requests: false

# Memory & Persistence
memory:
  enabled: true
  max_history: 100
  embeddings_enabled: false

# Safety & Security
safety:
  enable_sandbox: true
  allowed_directories: []
  blocked_commands:
    - "rm -rf /"
    - "rm -rf ~"
    - ":(){:|:&};:"
"""


def get_default_model(provider: str, size: str = "default") -> str:
    """Get default model for a provider and size."""
    provider_models = DEFAULT_MODELS.get(provider, DEFAULT_MODELS["anthropic"])
    return provider_models.get(size, provider_models["default"])


def get_model_pricing(model: str) -> tuple[float, float]:
    """Get pricing for a model (input, output per million tokens)."""
    return MODEL_PRICING.get(model, (0.0, 0.0))


def get_context_window(model: str) -> int:
    """Get context window size for a model."""
    return CONTEXT_WINDOWS.get(model, 100000)


def is_binary_file(path: str) -> bool:
    """Check if a file path indicates a binary file."""
    from pathlib import Path

    return Path(path).suffix.lower() in BINARY_EXTENSIONS


def should_ignore_path(path: str) -> bool:
    """Check if a path should be ignored in search operations."""
    from pathlib import Path

    path_obj = Path(path)
    return any(ignored in path_obj.parts or path_obj.match(ignored) for ignored in IGNORED_PATTERNS)


# ============================================================================
# Configuration-aware helper functions
# These functions load values from configuration files instead of hardcoded constants
# ============================================================================

def get_agent_temperature(agent_type: str = "default") -> float:
    """
    Get temperature setting for a specific agent type.
    
    Args:
        agent_type: Agent type (default, exploration, focused, autonomous, coding)
    
    Returns:
        Temperature value from configuration
    """
    try:
        from hcode.config.loader import load_enhanced_settings
        settings = load_enhanced_settings()
        
        temp_map = {
            "default": settings.agent_behavior.temperature_default,
            "exploration": settings.agent_behavior.temperature_exploration,
            "focused": settings.agent_behavior.temperature_focused,
            "autonomous": settings.agent_behavior.temperature_autonomous,
            "coding": settings.agent_behavior.temperature_coding,
        }
        
        return temp_map.get(agent_type, settings.agent_behavior.temperature_default)
    except Exception:
        # Fallback to hardcoded default if config loading fails
        return DEFAULT_TEMPERATURE


def get_agent_max_tokens(mode: str = "default") -> int:
    """
    Get max tokens setting for a specific mode.
    
    Args:
        mode: Mode (default, quick, medium, deep, focused, comprehensive, provider_max)
    
    Returns:
        Max tokens value from configuration
    """
    try:
        from hcode.config.loader import load_enhanced_settings
        settings = load_enhanced_settings()
        
        token_map = {
            "default": settings.agent_behavior.max_tokens_default,
            "quick": settings.agent_behavior.max_tokens_thinking_quick,
            "medium": settings.agent_behavior.max_tokens_thinking_medium,
            "deep": settings.agent_behavior.max_tokens_thinking_deep,
            "focused": settings.agent_behavior.max_tokens_thinking_focused,
            "comprehensive": settings.agent_behavior.max_tokens_thinking_comprehensive,
            "provider_max": settings.agent_behavior.max_tokens_provider_max,
        }
        
        return token_map.get(mode, settings.agent_behavior.max_tokens_default)
    except Exception:
        # Fallback to hardcoded default if config loading fails
        return DEFAULT_MAX_TOKENS


def get_dangerous_commands() -> list[str]:
    """
    Get list of dangerous commands from configuration.
    
    Returns:
        List of dangerous command patterns
    """
    try:
        from hcode.config.loader import load_enhanced_settings
        settings = load_enhanced_settings()
        return settings.safety.get_all_dangerous_commands()
    except Exception:
        # Fallback to hardcoded list if config loading fails
        return DANGEROUS_COMMANDS


def get_confirmation_patterns() -> list[str]:
    """
    Get list of confirmation required patterns from configuration.
    
    Returns:
        List of command patterns requiring confirmation
    """
    try:
        from hcode.config.loader import load_enhanced_settings
        settings = load_enhanced_settings()
        return settings.safety.get_all_confirmation_patterns()
    except Exception:
        # Fallback to hardcoded list if config loading fails
        return CONFIRMATION_REQUIRED_PATTERNS


def get_ignored_patterns() -> list[str]:
    """
    Get list of ignored file patterns from configuration.
    
    Returns:
        List of file patterns to ignore
    """
    try:
        from hcode.config.loader import load_enhanced_settings
        settings = load_enhanced_settings()
        return settings.file_operations.get_all_ignored_patterns()
    except Exception:
        # Fallback to hardcoded list if config loading fails
        return IGNORED_PATTERNS


def get_binary_extensions() -> list[str]:
    """
    Get list of binary file extensions from configuration.
    
    Returns:
        List of binary file extensions
    """
    try:
        from hcode.config.loader import load_enhanced_settings
        settings = load_enhanced_settings()
        return settings.file_operations.get_all_binary_extensions()
    except Exception:
        # Fallback to hardcoded set if config loading fails
        return list(BINARY_EXTENSIONS)


def get_max_file_size() -> int:
    """
    Get maximum file size from configuration.
    
    Returns:
        Maximum file size in bytes
    """
    try:
        from hcode.config.loader import load_enhanced_settings
        settings = load_enhanced_settings()
        return settings.file_operations.max_file_size_bytes
    except Exception:
        return MAX_FILE_SIZE_BYTES


def get_max_lines_per_read() -> int:
    """
    Get maximum lines per read from configuration.
    
    Returns:
        Maximum lines to read at once
    """
    try:
        from hcode.config.loader import load_enhanced_settings
        settings = load_enhanced_settings()
        return settings.file_operations.max_lines_per_read
    except Exception:
        return MAX_LINES_PER_READ


def get_context_buffer_tokens() -> int:
    """
    Get context buffer tokens from configuration.
    
    Returns:
        Number of tokens to reserve for response buffer
    """
    try:
        from hcode.config.loader import load_enhanced_settings
        settings = load_enhanced_settings()
        return settings.context.buffer_tokens
    except Exception:
        return CONTEXT_BUFFER_TOKENS
