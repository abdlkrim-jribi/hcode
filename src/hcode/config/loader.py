"""
Unified Configuration Loader for HCode.

This module provides a centralized configuration loading system that combines
settings from multiple sources with proper precedence.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from hcode.config.schema import (
    AgentBehaviorConfig,
    EnhancedHCodeSettings,
    FileOperationConfig,
    SafetyConfig,
)
from pydantic import ValidationError


class ConfigLoader:
    """
    Unified configuration loader with multi-source support.
    
    Configuration precedence (highest to lowest):
    1. Environment variables
    2. Project-local config (.hcode/config.yaml)
    3. User config (~/.hcode/config.yaml)
    4. External config files (agents.yaml, safety.yaml, etc.)
    5. Default values
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize configuration loader.
        
        Args:
            project_root: Project root directory (defaults to current directory)
        """
        self.project_root = project_root or Path.cwd()
        self.user_config_dir = Path.home() / ".hcode"
        self.project_config_dir = self.project_root / ".hcode"

        # Config file paths
        self.config_paths = self._get_config_paths()

    def _get_config_paths(self) -> Dict[str, list[Path]]:
        """Get all possible configuration file paths in order of precedence."""
        return {
            "main": [
                self.project_config_dir / "config.yaml",
                self.user_config_dir / "config.yaml",
            ],
            "agents": [
                self.project_config_dir / "agents.yaml",
                self.project_root / "config" / "agents.yaml",
                self.user_config_dir / "agents.yaml",
            ],
            "safety": [
                self.project_config_dir / "safety.yaml",
                self.project_root / "config" / "safety.yaml",
                self.user_config_dir / "safety.yaml",
            ],
            "file_operations": [
                self.project_config_dir / "file_operations.yaml",
                self.project_root / "config" / "file_operations.yaml",
                self.user_config_dir / "file_operations.yaml",
            ],
            "models": [
                self.project_config_dir / "models.yaml",
                self.project_root / "config" / "models.yaml",
                self.user_config_dir / "models.yaml",
            ],
            "prompts": [
                self.project_config_dir / "prompts.yaml",
                self.project_root / "config" / "prompts.yaml",
                self.user_config_dir / "prompts.yaml",
            ],
        }

    def _load_yaml_file(self, path: Path) -> Dict[str, Any]:
        """Load a YAML file and return its contents."""
        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data
        except Exception as e:
            print(f"Warning: Failed to load {path}: {e}")
            return {}

    def _find_first_existing(self, paths: list[Path]) -> Optional[Path]:
        """Find the first existing file from a list of paths."""
        for path in paths:
            if path.exists():
                return path
        return None

    def _merge_dicts(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries, with override taking precedence."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    def load_agent_behavior_config(self) -> AgentBehaviorConfig:
        """Load agent behavior configuration."""
        # Load from agents.yaml
        agents_path = self._find_first_existing(self.config_paths["agents"])
        if agents_path:
            data = self._load_yaml_file(agents_path)

            # Extract relevant fields for AgentBehaviorConfig
            config_data = {}

            if "temperature" in data:
                temp = data["temperature"]
                config_data["temperature_default"] = temp.get("default", 0.7)
                config_data["temperature_exploration"] = temp.get("exploration", 1.0)
                config_data["temperature_focused"] = temp.get("focused", 0.5)
                config_data["temperature_autonomous"] = temp.get("autonomous", 0.5)
                config_data["temperature_coding"] = temp.get("coding", 0.7)

            if "max_tokens" in data:
                tokens = data["max_tokens"]
                config_data["max_tokens_default"] = tokens.get("default", 4096)
                config_data["max_tokens_provider_max"] = tokens.get("provider_max", 16384)

                if "thinking" in tokens:
                    thinking = tokens["thinking"]
                    config_data["max_tokens_thinking_quick"] = thinking.get("quick", 1000)
                    config_data["max_tokens_thinking_medium"] = thinking.get("medium", 2500)
                    config_data["max_tokens_thinking_deep"] = thinking.get("deep", 4000)
                    config_data["max_tokens_thinking_focused"] = thinking.get("focused", 800)
                    config_data["max_tokens_thinking_comprehensive"] = thinking.get("comprehensive", 3000)

            if "max_iterations" in data:
                config_data["max_iterations"] = data["max_iterations"]

            return AgentBehaviorConfig(**config_data)

        return AgentBehaviorConfig()

    def load_safety_config(self) -> SafetyConfig:
        """Load safety configuration."""
        safety_path = self._find_first_existing(self.config_paths["safety"])
        if safety_path:
            data = self._load_yaml_file(safety_path)

            # Convert to SafetyConfig format
            config_data = {}

            if "enable_sandbox" in data:
                config_data["enable_sandbox"] = data["enable_sandbox"]

            if "dangerous_commands" in data:
                config_data["dangerous_commands"] = data["dangerous_commands"]

            if "confirmation_patterns" in data:
                config_data["confirmation_patterns"] = data["confirmation_patterns"]

            if "allowed_directories" in data:
                config_data["allowed_directories"] = data["allowed_directories"]

            if "blocked_directories" in data:
                config_data["blocked_directories"] = data["blocked_directories"]

            return SafetyConfig(**config_data)

        return SafetyConfig()

    def load_file_operations_config(self) -> FileOperationConfig:
        """Load file operations configuration."""
        file_ops_path = self._find_first_existing(self.config_paths["file_operations"])
        if file_ops_path:
            data = self._load_yaml_file(file_ops_path)

            # Convert to FileOperationConfig format
            config_data = {}

            if "limits" in data:
                limits = data["limits"]
                config_data["max_file_size_bytes"] = limits.get("max_file_size_bytes", 10485760)
                config_data["max_lines_per_read"] = limits.get("max_lines_per_read", 2000)
                config_data["max_files_per_operation"] = limits.get("max_files_per_operation", 100)

            if "encoding" in data:
                encoding = data["encoding"]
                config_data["default_encoding"] = encoding.get("default", "utf-8")
                config_data["fallback_encodings"] = encoding.get("fallbacks", ["latin-1", "cp1252", "iso-8859-1"])

            if "binary_extensions" in data:
                config_data["binary_extensions"] = data["binary_extensions"]

            if "ignored_patterns" in data:
                config_data["ignored_patterns"] = data["ignored_patterns"]

            return FileOperationConfig(**config_data)

        return FileOperationConfig()

    def load_all_configs(self) -> EnhancedHCodeSettings:
        """
        Load all configuration from multiple sources.
        
        Returns:
            EnhancedHCodeSettings with all configuration loaded
        """
        # Load individual config sections
        agent_behavior = self.load_agent_behavior_config()
        safety = self.load_safety_config()
        file_operations = self.load_file_operations_config()

        # Create settings object
        settings = EnhancedHCodeSettings(
            agent_behavior=agent_behavior,
            safety=safety,
            file_operations=file_operations,
        )

        # Load main config file if it exists
        main_path = self._find_first_existing(self.config_paths["main"])
        if main_path:
            main_data = self._load_yaml_file(main_path)

            # Override with main config values
            if main_data:
                try:
                    # Merge with existing settings
                    settings_dict = settings.to_dict()
                    merged = self._merge_dicts(settings_dict, main_data)
                    settings = EnhancedHCodeSettings.from_dict(merged)
                except ValidationError as e:
                    print(f"Warning: Invalid configuration in {main_path}: {e}")

        # Override with environment variables
        settings = self._apply_env_overrides(settings)

        return settings

    def _apply_env_overrides(self, settings: EnhancedHCodeSettings) -> EnhancedHCodeSettings:
        """Apply environment variable overrides to settings."""
        # This would check for environment variables and override settings
        # For now, we'll keep it simple and return settings as-is
        # The pydantic-settings integration will handle env vars
        return settings

    def validate_config(self, settings: EnhancedHCodeSettings) -> tuple[bool, list[str]]:
        """
        Validate configuration and return any errors.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # Validate agent behavior
        if settings.agent_behavior.temperature_default < 0 or settings.agent_behavior.temperature_default > 2:
            errors.append("temperature_default must be between 0 and 2")

        # Validate file operations
        if settings.file_operations.max_file_size_bytes < 1024:
            errors.append("max_file_size_bytes must be at least 1024 bytes")

        # Validate safety
        if not settings.safety.dangerous_commands:
            errors.append("Warning: No dangerous commands configured")

        return len(errors) == 0, errors


@lru_cache()
def get_config_loader(project_root: Optional[Path] = None) -> ConfigLoader:
    """Get cached configuration loader instance."""
    return ConfigLoader(project_root)


@lru_cache()
def load_enhanced_settings(project_root: Optional[Path] = None) -> EnhancedHCodeSettings:
    """Load enhanced settings with caching."""
    loader = get_config_loader(project_root)
    return loader.load_all_configs()


def clear_config_cache() -> None:
    """Clear configuration cache to force reload."""
    get_config_loader.cache_clear()
    load_enhanced_settings.cache_clear()
