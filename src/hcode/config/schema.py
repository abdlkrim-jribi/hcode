"""
Enhanced Configuration Schema for HCode.

This module provides comprehensive configuration models for all aspects of HCode,
enabling complete externalization of hardcoded values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal

from pydantic import BaseModel, Field


class AgentBehaviorConfig(BaseModel):
    """Agent-specific behavior configuration."""

    # Temperature settings for different agent modes
    temperature_default: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for general agent operations"
    )
    temperature_exploration: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Higher temperature for creative exploration"
    )
    temperature_focused: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Lower temperature for focused, deterministic tasks"
    )
    temperature_autonomous: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Temperature for autonomous agent decisions"
    )
    temperature_coding: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for code generation tasks"
    )

    # Token limits for different thinking modes
    max_tokens_default: int = Field(
        default=4096,
        ge=1,
        le=100000,
        description="Default maximum tokens for responses"
    )
    max_tokens_thinking_quick: int = Field(
        default=1000,
        ge=1,
        le=100000,
        description="Token limit for quick thinking mode"
    )
    max_tokens_thinking_medium: int = Field(
        default=2500,
        ge=1,
        le=100000,
        description="Token limit for medium thinking mode"
    )
    max_tokens_thinking_deep: int = Field(
        default=4000,
        ge=1,
        le=100000,
        description="Token limit for deep thinking mode"
    )
    max_tokens_thinking_focused: int = Field(
        default=800,
        ge=1,
        le=100000,
        description="Token limit for focused analysis"
    )
    max_tokens_thinking_comprehensive: int = Field(
        default=3000,
        ge=1,
        le=100000,
        description="Token limit for comprehensive analysis"
    )
    max_tokens_provider_max: int = Field(
        default=16384,
        ge=1,
        le=100000,
        description="Maximum output tokens for providers (e.g., GPT-4o)"
    )

    # Agent iteration limits
    max_iterations: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum agent iterations per task"
    )


class FileOperationConfig(BaseModel):
    """File operation limits and settings."""

    # Size and read limits
    max_file_size_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1024,
        description="Maximum file size in bytes"
    )
    max_lines_per_read: int = Field(
        default=2000,
        ge=1,
        description="Maximum lines to read at once"
    )
    max_files_per_operation: int = Field(
        default=100,
        ge=1,
        description="Maximum files to process in one operation"
    )

    # Encoding settings
    default_encoding: str = Field(
        default="utf-8",
        description="Default file encoding"
    )
    fallback_encodings: List[str] = Field(
        default_factory=lambda: ["latin-1", "cp1252", "iso-8859-1"],
        description="Fallback encodings to try if default fails"
    )

    # Binary file extensions (organized by category)
    binary_extensions: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "executables": [".exe", ".dll", ".so", ".dylib"],
            "archives": [".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z"],
            "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".webp", ".svg"],
            "audio": [".mp3", ".wav", ".ogg", ".flac", ".aac"],
            "video": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".webm"],
            "documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"],
            "compiled": [".pyc", ".pyo", ".class", ".o", ".obj"],
            "fonts": [".woff", ".woff2", ".ttf", ".otf", ".eot"],
            "databases": [".db", ".sqlite", ".sqlite3"],
        },
        description="Binary file extensions by category"
    )

    # Ignored patterns (organized by category)
    ignored_patterns: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "version_control": [".git", ".svn", ".hg"],
            "dependencies": ["node_modules", ".venv", "venv", "env"],
            "python_cache": ["__pycache__", ".pytest_cache", ".mypy_cache", ".tox", "*.pyc", "*.pyo"],
            "build_artifacts": ["dist", "build", "*.egg-info", ".eggs"],
            "system": [".DS_Store", "Thumbs.db"],
            "env_files": [".env"],
        },
        description="File patterns to ignore by category"
    )

    def get_all_binary_extensions(self) -> List[str]:
        """Get flattened list of all binary extensions."""
        extensions = []
        for category_exts in self.binary_extensions.values():
            extensions.extend(category_exts)
        return extensions

    def get_all_ignored_patterns(self) -> List[str]:
        """Get flattened list of all ignored patterns."""
        patterns = []
        for category_patterns in self.ignored_patterns.values():
            patterns.extend(category_patterns)
        return patterns


class SafetyConfig(BaseModel):
    """Safety and security configuration."""

    # Enable/disable sandbox
    enable_sandbox: bool = Field(
        default=True,
        description="Enable sandboxed command execution"
    )

    # Dangerous commands (organized by category)
    dangerous_commands: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "filesystem": [
                "rm -rf /",
                "rm -rf ~",
                "rm -rf /*",
                "mv /* /dev/null",
            ],
            "system": [
                ":(){:|:&};:",  # Fork bomb
                "mkfs",
                "dd if=/dev/zero",
                "chmod -R 777 /",
                "chown -R",
                "> /dev/sda",
            ],
            "remote_execution": [
                "wget -O- | sh",
                "curl | sh",
            ],
        },
        description="Dangerous commands that should be blocked"
    )

    # Commands requiring confirmation (organized by category)
    confirmation_patterns: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "destructive": ["rm ", "delete", "drop ", "truncate"],
            "version_control": [
                "git push --force",
                "git push -f",
                "git reset --hard",
                "git clean -fd",
            ],
            "package_management": [
                "npm publish",
                "pip install --upgrade",
            ],
        },
        description="Command patterns requiring user confirmation"
    )

    # Directory restrictions
    allowed_directories: List[str] = Field(
        default_factory=list,
        description="Allowed directories for file operations (empty = all allowed)"
    )
    blocked_directories: List[str] = Field(
        default_factory=lambda: ["/", "/etc", "/sys", "/proc", "/dev"],
        description="Blocked directories for file operations"
    )

    def get_all_dangerous_commands(self) -> List[str]:
        """Get flattened list of all dangerous commands."""
        commands = []
        for category_cmds in self.dangerous_commands.values():
            commands.extend(category_cmds)
        return commands

    def get_all_confirmation_patterns(self) -> List[str]:
        """Get flattened list of all confirmation patterns."""
        patterns = []
        for category_patterns in self.confirmation_patterns.values():
            patterns.extend(category_patterns)
        return patterns


class UIConfig(BaseModel):
    """Extended UI configuration."""

    # Terminal settings
    terminal_width_min: int = Field(
        default=40,
        ge=20,
        le=1000,
        description="Minimum terminal width"
    )
    terminal_width_max: int = Field(
        default=200,
        ge=40,
        le=1000,
        description="Maximum terminal width"
    )

    # Theme and display
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
        description="Show verbose debug output"
    )
    show_thinking: bool = Field(
        default=False,
        description="Show model thinking/reasoning steps"
    )
    minimal_output: bool = Field(
        default=True,
        description="Use minimal output style"
    )

    # Chat commands
    chat_commands: Dict[str, str] = Field(
        default_factory=lambda: {
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
        },
        description="Available chat commands"
    )


class LoggingConfig(BaseModel):
    """Extended logging configuration."""

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

    # Log formatting
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Date format for log messages"
    )


class MemoryConfig(BaseModel):
    """Extended memory configuration."""

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
    session_expiry_days: int = Field(
        default=30,
        ge=1,
        description="Number of days before sessions expire"
    )


class ContextConfig(BaseModel):
    """Context window configuration."""

    max_context_tokens: int = Field(
        default=100000,
        ge=1000,
        description="Maximum context window tokens"
    )
    buffer_tokens: int = Field(
        default=2000,
        ge=100,
        description="Reserved tokens for response buffer"
    )
    summarization_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Trigger summarization at this percentage of context usage"
    )
    max_history_turns: int = Field(
        default=100,
        ge=1,
        description="Maximum conversation history turns to keep"
    )


class EnhancedHCodeSettings(BaseModel):
    """
    Enhanced HCode settings with all externalized configuration.
    
    This extends the base settings with additional configuration groups
    for complete externalization of hardcoded values.
    """

    # New configuration groups
    agent_behavior: AgentBehaviorConfig = Field(
        default_factory=AgentBehaviorConfig,
        description="Agent behavior and model parameters"
    )
    file_operations: FileOperationConfig = Field(
        default_factory=FileOperationConfig,
        description="File operation limits and patterns"
    )
    safety: SafetyConfig = Field(
        default_factory=SafetyConfig,
        description="Safety and security settings"
    )
    ui: UIConfig = Field(
        default_factory=UIConfig,
        description="User interface configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="Memory and persistence settings"
    )
    context: ContextConfig = Field(
        default_factory=ContextConfig,
        description="Context window configuration"
    )

    def to_dict(self) -> dict:
        """Export settings to dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> "EnhancedHCodeSettings":
        """Create settings from dictionary."""
        return cls(**data)

    def save_to_yaml(self, path: Path) -> None:
        """Save settings to YAML file."""
        import yaml

        data = self.to_dict()

        # Convert Path objects to strings
        def convert_paths(obj):
            if isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            elif isinstance(obj, Path):
                return str(obj)
            return obj

        data = convert_paths(data)

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load_from_yaml(cls, path: Path) -> "EnhancedHCodeSettings":
        """Load settings from YAML file."""
        import yaml

        if not path.exists():
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)
