"""
HCode Settings - Pydantic-based configuration management.

This module provides a centralized configuration system using pydantic-settings.
Configuration can be loaded from environment variables, .env files, or config files.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(
        env_prefix="HCODE_LLM_",
        extra="ignore",
    )

    provider: Literal["anthropic", "openai", "ollama", "auto"] = Field(
        default="auto",
        description="Default LLM provider"
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key"
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key"
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama base URL"
    )
    model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Default model name"
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=100000,
        description="Maximum tokens in response"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )

    @field_validator("anthropic_api_key", "openai_api_key", mode="before")
    @classmethod
    def get_from_env(cls, v: str | None, info) -> str | None:
        """Try to get API key from environment if not set."""
        if v is not None:
            return v
        field_name = info.field_name
        if field_name == "anthropic_api_key":
            return os.getenv("ANTHROPIC_API_KEY")
        elif field_name == "openai_api_key":
            return os.getenv("OPENAI_API_KEY")
        return v


class AgentSettings(BaseSettings):
    """Agent behavior settings."""

    model_config = SettingsConfigDict(
        env_prefix="HCODE_AGENT_",
        extra="ignore",
    )

    max_context_tokens: int = Field(
        default=100000,
        ge=1000,
        description="Maximum context window tokens"
    )
    auto_confirm_commands: bool = Field(
        default=False,
        description="Auto-confirm shell commands without prompting"
    )
    streaming: bool = Field(
        default=True,
        description="Enable streaming responses"
    )
    verbose: bool = Field(
        default=False,
        description="Verbose output mode"
    )
    use_sub_agents: bool = Field(
        default=False,
        description="Use specialized sub-agents for tasks"
    )
    max_iterations: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum agent iterations per task"
    )


class UISettings(BaseSettings):
    """User interface settings."""

    model_config = SettingsConfigDict(
        env_prefix="HCODE_UI_",
        extra="ignore",
    )

    theme: Literal["dark", "light", "auto"] = Field(
        default="auto",
        description="Color theme"
    )
    show_tokens: bool = Field(
        default=False,
        description="Show token usage in output"
    )
    show_cost: bool = Field(
        default=True,
        description="Show cost estimation in output"
    )
    syntax_highlighting: bool = Field(
        default=True,
        description="Enable syntax highlighting for code"
    )
    markdown_rendering: bool = Field(
        default=True,
        description="Enable markdown rendering"
    )
    emoji_enabled: bool = Field(
        default=True,
        description="Enable emoji in output"
    )
    debug_mode: bool = Field(
        default=False,
        description="Show verbose debug output (thinking panels, detailed messages)"
    )
    show_thinking: bool = Field(
        default=False,
        description="Show model thinking/reasoning steps (debug mode enables this)"
    )
    minimal_output: bool = Field(
        default=True,
        description="Use Claude Code-style minimal output"
    )


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="HCODE_LOG_",
        extra="ignore",
    )

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    file_enabled: bool = Field(
        default=True,
        description="Enable file logging"
    )
    log_dir: Path = Field(
        default=Path.home() / ".hcode" / "logs",
        description="Log files directory"
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum log file size in bytes"
    )
    backup_count: int = Field(
        default=5,
        description="Number of backup log files to keep"
    )
    debug_requests: bool = Field(
        default=False,
        description="Log full API requests/responses"
    )


class MemorySettings(BaseSettings):
    """Memory and persistence settings."""

    model_config = SettingsConfigDict(
        env_prefix="HCODE_MEMORY_",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        description="Enable conversation memory"
    )
    db_path: Path = Field(
        default=Path.home() / ".hcode" / "memory.db",
        description="SQLite database path for memory"
    )
    max_history: int = Field(
        default=100,
        description="Maximum conversation history entries"
    )
    embeddings_enabled: bool = Field(
        default=False,
        description="Enable semantic memory with embeddings"
    )


class SafetySettings(BaseSettings):
    """Safety and security settings."""

    model_config = SettingsConfigDict(
        env_prefix="HCODE_SAFETY_",
        extra="ignore",
    )

    enable_sandbox: bool = Field(
        default=True,
        description="Enable sandboxed command execution"
    )
    allowed_directories: list[str] = Field(
        default_factory=list,
        description="Allowed directories for file operations"
    )
    blocked_commands: list[str] = Field(
        default_factory=lambda: [
            "rm -rf /",
            "rm -rf ~",
            "format",
            ":(){:|:&};:",
            "mkfs",
            "dd if=/dev/zero",
        ],
        description="Blocked dangerous commands"
    )
    require_confirmation_patterns: list[str] = Field(
        default_factory=lambda: [
            "rm",
            "delete",
            "drop",
            "truncate",
            "git push --force",
            "git reset --hard",
        ],
        description="Patterns requiring user confirmation"
    )


class PromptsSettings(BaseSettings):
    """Prompts directory and loading settings."""

    model_config = SettingsConfigDict(
        env_prefix="HCODE_PROMPTS_",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        description="Enable custom prompts loading"
    )
    directory: Path = Field(
        default=Path.home() / ".hcode" / "prompts",
        description="Directory containing .prompt files"
    )
    project_directory: Path | None = Field(
        default=None,
        description="Project-local prompts directory (e.g., .hcode/prompts)"
    )
    auto_reload: bool = Field(
        default=False,
        description="Automatically reload prompts when files change"
    )
    extension: str = Field(
        default=".prompt",
        description="File extension for prompt files"
    )


class HCodeSettings(BaseSettings):
    """
    Main HCode settings container.

    Combines all settings groups and handles configuration file loading.
    Configuration priority (highest to lowest):
    1. Environment variables
    2. .env file
    3. ~/.hcode/config.yaml
    4. .hcode/config.yaml (project-local)
    5. Default values
    """

    model_config = SettingsConfigDict(
        env_prefix="HCODE_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Version info
    version: str = Field(default="1.0.0", description="HCode version")

    # Nested settings groups
    llm: LLMSettings = Field(default_factory=LLMSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    ui: UISettings = Field(default_factory=UISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    prompts: PromptsSettings = Field(default_factory=PromptsSettings)

    # Project-specific settings
    project_root: Path = Field(
        default_factory=Path.cwd,
        description="Project root directory"
    )
    config_dir: Path = Field(
        default=Path.home() / ".hcode",
        description="Global config directory"
    )

    @model_validator(mode="after")
    def ensure_directories(self) -> "HCodeSettings":
        """Ensure configuration directories exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logging.log_dir.mkdir(parents=True, exist_ok=True)
        self.memory.db_path.parent.mkdir(parents=True, exist_ok=True)
        return self

    def has_api_key(self) -> bool:
        """Check if any API key is configured."""
        return bool(self.llm.anthropic_api_key or self.llm.openai_api_key)

    def get_effective_provider(self) -> str:
        """Get the effective provider based on configuration and availability."""
        if self.llm.provider != "auto":
            return self.llm.provider

        if self.llm.anthropic_api_key:
            return "anthropic"
        elif self.llm.openai_api_key:
            return "openai"
        else:
            return "ollama"

    def to_dict(self) -> dict[str, Any]:
        """Export settings to dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HCodeSettings":
        """Create settings from dictionary."""
        return cls(**data)

    def save_to_file(self, path: Path | None = None) -> None:
        """Save settings to YAML file."""
        import yaml

        file_path = path or (self.config_dir / "config.yaml")
        data = self.to_dict()

        # Convert Path objects to strings for YAML
        def convert_paths(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            elif isinstance(obj, Path):
                return str(obj)
            return obj

        data = convert_paths(data)

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load_from_file(cls, path: Path) -> "HCodeSettings":
        """Load settings from YAML file."""
        import yaml

        if not path.exists():
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)


@lru_cache()
def get_settings() -> HCodeSettings:
    """
    Get cached HCode settings instance.

    This function returns a singleton settings instance.
    Call clear_settings_cache() to reload settings.
    """
    return HCodeSettings()


def clear_settings_cache() -> None:
    """Clear the settings cache to force reload."""
    get_settings.cache_clear()


def get_llm_settings() -> LLMSettings:
    """Get LLM settings."""
    return get_settings().llm


def get_agent_settings() -> AgentSettings:
    """Get agent settings."""
    return get_settings().agent


def get_ui_settings() -> UISettings:
    """Get UI settings."""
    return get_settings().ui


def get_logging_settings() -> LoggingSettings:
    """Get logging settings."""
    return get_settings().logging


def get_memory_settings() -> MemorySettings:
    """Get memory settings."""
    return get_settings().memory


def get_safety_settings() -> SafetySettings:
    """Get safety settings."""
    return get_settings().safety


def get_prompts_settings() -> PromptsSettings:
    """Get prompts settings."""
    return get_settings().prompts


def is_debug_mode() -> bool:
    """
    Check if debug mode is enabled.

    Returns True if any of these are true:
    - ui.debug_mode is True
    - ui.show_thinking is True
    - Environment variable HCODE_DEBUG is set
    """
    import os
    settings = get_settings()
    return (
        settings.ui.debug_mode or
        settings.ui.show_thinking or
        os.getenv('HCODE_DEBUG', '').lower() in ('1', 'true', 'yes')
    )
