"""
Prompts and Model Configuration Loader for Hcode.

This module provides centralized access to prompts and model parameters.
Core prompts are now managed by CorePromptLoader in config/core_prompts/core/.
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Optional, List

import yaml


@dataclass
class GenerationParams:
    """Model generation parameters"""

    temperature: float = 0.3
    top_p: float = 1.0
    top_k: int = 0
    max_tokens: int = 16384
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls"""
        params = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.top_p < 1.0:
            params["top_p"] = self.top_p
        if self.top_k > 0:
            params["top_k"] = self.top_k
        if self.frequency_penalty != 0.0:
            params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty != 0.0:
            params["presence_penalty"] = self.presence_penalty
        if self.stop_sequences:
            params["stop"] = self.stop_sequences
        return params


@dataclass
class ContextConfig:
    """Context window configuration"""

    max_context_tokens: int = 200000
    reserve_output_tokens: int = 16384
    summarization_threshold: float = 0.85
    max_history_turns: int = 100


@dataclass
class ContinuationConfig:
    """Continuation settings for long outputs"""

    enabled: bool = True
    max_continuations: int = 20
    max_total_tokens: int = 200000
    truncation_patterns: List[str] = field(default_factory=list)


@dataclass
class ReliabilityConfig:
    """Retry and timeout settings"""

    timeout: float = 120.0
    connect_timeout: float = 30.0
    max_retries: int = 5
    retry_multiplier: float = 2.0
    retry_min: float = 2.0
    retry_max: float = 30.0


class PromptsConfig:
    """
    Prompts configuration loader.

    System prompts are loaded from CorePromptLoader (config/core_prompts/core/).
    This class provides backward compatibility and additional configuration.
    """

    _instance: Optional["PromptsConfig"] = None
    _prompts_data: Dict[str, Any] = {}
    _config_path: Optional[Path] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_prompts()
        return cls._instance

    def _find_config_path(self) -> Optional[Path]:
        """Find the prompts configuration file"""
        env_path = os.getenv("HCODE_PROMPTS_CONFIG")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        search_paths = [
            Path.cwd() / "config" / "prompts.yaml",
            Path.cwd() / "prompts.yaml",
            Path(__file__).parent.parent.parent.parent / "config" / "prompts.yaml",
            Path.home() / ".hcode" / "prompts.yaml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _load_prompts(self):
        """Load prompts from YAML file"""
        self._config_path = self._find_config_path()

        if self._config_path and self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._prompts_data = yaml.safe_load(f) or {}
        else:
            self._prompts_data = self._get_default_prompts()

    def _get_default_prompts(self) -> Dict[str, Any]:
        """Return default prompts configuration"""
        return {
            "system_prompts": {
                "coding_agent": self._default_coding_prompt(),
                "openai_coding": self._default_coding_prompt(),
                "agent": self._default_agent_prompt(),
                "sub_agent": self._default_sub_agent_prompt(),
            },
            "continuation_prompts": [
                "Continue from where you left off. Do not repeat what you've already written.",
                "Please continue. Pick up exactly where you stopped.",
            ],
            "tool_prompts": {
                "continuation_readonly": "Continue exploring. Use read-only tools to gather more information.",
                "continuation_general": "Continue with the task. Use appropriate tools to make progress.",
            },
            "persona": {
                "name": "Hcode",
                "tone": "professional",
                "use_emojis": False,
                "verbosity": "balanced",
            },
        }

    def _default_coding_prompt(self) -> str:
        """Get the default coding system prompt from CorePromptLoader."""
        try:
            from hcode.config.core_prompts.core import get_prompt_loader
            loader = get_prompt_loader()
            return loader.get_system_prompt("default")
        except Exception:
            # Fallback if CorePromptLoader not available
            return self._fallback_system_prompt()

    def _fallback_system_prompt(self) -> str:
        """Minimal fallback system prompt."""
        return """You are Hcode, an AI coding assistant.

Your capabilities:
- Read, write, and edit files
- Execute commands
- Search and analyze code
- Help with software development tasks

Guidelines:
1. Read files before modifying them
2. Use appropriate tools for each task
3. Verify changes work correctly
4. Communicate clearly about your actions"""

    def _default_agent_prompt(self) -> str:
        """Get the agent system prompt from CorePromptLoader."""
        try:
            from hcode.config.core_prompts.core import get_prompt_loader
            loader = get_prompt_loader()
            return loader.get_system_prompt("default")
        except Exception:
            return self._fallback_system_prompt()

    def _default_sub_agent_prompt(self) -> str:
        """Placeholder for sub-agent prompt - configured externally."""
        return "[SUB_AGENT_PROMPT_PLACEHOLDER]"

    def reload(self):
        """Reload prompts from file"""
        self._load_prompts()

    @property
    def config_path(self) -> Optional[Path]:
        """Get the path to the loaded config file"""
        return self._config_path

    def get_system_prompt(self, prompt_type: str = "coding_agent") -> str:
        """
        Get a system prompt by type.

        Args:
            prompt_type: Type of prompt (coding_agent, openai_coding, agent, sub_agent)

        Returns:
            The system prompt string
        """
        prompts = self._prompts_data.get("system_prompts", {})
        prompt = prompts.get(prompt_type)

        if not prompt:
            prompt = self._default_coding_prompt()

        # For OpenAI, prepend memory file content if available
        if prompt_type == "openai_coding":
            try:
                mem_cfg = self.get_memory_config()
                mem_file_name = mem_cfg.get("memory_file", "CLAUDE.md")
                mem_path = Path.cwd() / mem_file_name
                if mem_path.is_file():
                    mem_content = mem_path.read_text()
                    prompt = f"{mem_content}\n\n{prompt}"
            except Exception:
                pass

        return prompt

    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory configuration"""
        return self._prompts_data.get("memory", {"memory_file": "CLAUDE.md", "enabled": True})

    def get_continuation_prompts(self) -> List[str]:
        """Get list of continuation prompts"""
        return self._prompts_data.get(
            "continuation_prompts",
            ["Continue from where you left off. Do not repeat what you've already written."],
        )

    def get_continuation_prompt(self, index: int = 0) -> str:
        """Get a specific continuation prompt by index (rotates)"""
        prompts = self.get_continuation_prompts()
        return prompts[index % len(prompts)]

    def get_tool_prompt(self, prompt_name: str) -> str:
        """Get a tool-specific prompt"""
        tool_prompts = self._prompts_data.get("tool_prompts", {})
        default_prompts = {
            "continuation_readonly": "Continue exploring. Use read-only tools to gather more information.",
            "continuation_general": "Continue with the task. Use appropriate tools to make progress.",
        }
        return tool_prompts.get(prompt_name, default_prompts.get(prompt_name, ""))


class ModelsConfig:
    """
    Model configuration loader.

    Loads model parameters from config/models.yaml.
    """

    _instance: Optional["ModelsConfig"] = None
    _models_data: Dict[str, Any] = {}
    _config_path: Optional[Path] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_models()
        return cls._instance

    def _find_config_path(self) -> Optional[Path]:
        """Find the models configuration file"""
        env_path = os.getenv("HCODE_MODELS_CONFIG")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        search_paths = [
            Path.cwd() / "config" / "models.yaml",
            Path.cwd() / "models.yaml",
            Path(__file__).parent.parent.parent.parent / "config" / "models.yaml",
            Path.home() / ".hcode" / "models.yaml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    def _load_models(self):
        """Load model config from YAML file"""
        self._config_path = self._find_config_path()

        if self._config_path and self._config_path.exists():
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._models_data = yaml.safe_load(f) or {}
        else:
            self._models_data = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default model configuration"""
        return {
            "generation": {
                "temperature": 0.3,
                "top_p": 1.0,
                "top_k": 0,
                "max_tokens": 4096,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "stop_sequences": [],
            },
            "task_overrides": {},
            "context": {
                "max_context_tokens": 128000,
                "reserve_output_tokens": 8192,
                "summarization_threshold": 0.8,
                "max_history_turns": 50,
            },
            "continuation": {
                "enabled": True,
                "max_continuations": 10,
                "max_total_tokens": 100000,
            },
            "reliability": {
                "timeout": 120,
                "connect_timeout": 30,
                "max_retries": 5,
            },
        }

    def reload(self):
        """Reload configuration from file"""
        self._load_models()

    @property
    def config_path(self) -> Optional[Path]:
        """Get the path to the loaded config file"""
        return self._config_path

    def get_generation_params(self, task_type: Optional[str] = None) -> GenerationParams:
        """Get generation parameters, optionally for a specific task type."""
        gen_config = self._models_data.get("generation", {})

        params = GenerationParams(
            temperature=gen_config.get("temperature", 0.3),
            top_p=gen_config.get("top_p", 1.0),
            top_k=gen_config.get("top_k", 0),
            max_tokens=gen_config.get("max_tokens", 16384),
            frequency_penalty=gen_config.get("frequency_penalty", 0.0),
            presence_penalty=gen_config.get("presence_penalty", 0.0),
            stop_sequences=gen_config.get("stop_sequences", []),
        )

        if task_type:
            overrides = self._models_data.get("task_overrides", {}).get(task_type, {})
            if overrides:
                for key in ["temperature", "top_p", "top_k", "max_tokens", "frequency_penalty", "presence_penalty"]:
                    if key in overrides:
                        setattr(params, key, overrides[key])

        return params

    def get_temperature(self, task_type: Optional[str] = None) -> float:
        """Get temperature setting"""
        return self.get_generation_params(task_type).temperature

    def get_max_tokens(self, task_type: Optional[str] = None) -> int:
        """Get max tokens setting"""
        return self.get_generation_params(task_type).max_tokens

    def get_context_config(self) -> ContextConfig:
        """Get context window configuration"""
        ctx_data = self._models_data.get("context", {})
        return ContextConfig(
            max_context_tokens=ctx_data.get("max_context_tokens", 200000),
            reserve_output_tokens=ctx_data.get("reserve_output_tokens", 16384),
            summarization_threshold=ctx_data.get("summarization_threshold", 0.85),
            max_history_turns=ctx_data.get("max_history_turns", 100),
        )

    def get_continuation_config(self) -> ContinuationConfig:
        """Get continuation settings"""
        cont_data = self._models_data.get("continuation", {})
        return ContinuationConfig(
            enabled=cont_data.get("enabled", True),
            max_continuations=cont_data.get("max_continuations", 20),
            max_total_tokens=cont_data.get("max_total_tokens", 200000),
            truncation_patterns=cont_data.get("truncation_patterns", []),
        )

    def get_reliability_config(self) -> ReliabilityConfig:
        """Get reliability settings"""
        rel_data = self._models_data.get("reliability", {})
        return ReliabilityConfig(
            timeout=rel_data.get("timeout", 120.0),
            connect_timeout=rel_data.get("connect_timeout", 30.0),
            max_retries=rel_data.get("max_retries", 5),
        )


# Convenience functions
@lru_cache(maxsize=1)
def get_prompts_config() -> PromptsConfig:
    """Get the prompts configuration singleton"""
    return PromptsConfig()


@lru_cache(maxsize=1)
def get_models_config() -> ModelsConfig:
    """Get the models configuration singleton"""
    return ModelsConfig()


def get_system_prompt(prompt_type: str = "coding_agent") -> str:
    """Convenience function to get a system prompt"""
    return get_prompts_config().get_system_prompt(prompt_type)


def get_generation_params(task_type: Optional[str] = None) -> GenerationParams:
    """Convenience function to get generation parameters"""
    return get_models_config().get_generation_params(task_type)


def get_temperature(task_type: Optional[str] = None) -> float:
    """Convenience function to get temperature"""
    return get_models_config().get_temperature(task_type)


def get_max_tokens(task_type: Optional[str] = None) -> int:
    """Convenience function to get max tokens"""
    return get_models_config().get_max_tokens(task_type)


def reload_configs():
    """Reload all configuration files"""
    get_prompts_config().reload()
    get_models_config().reload()
    get_prompts_config.cache_clear()
    get_models_config.cache_clear()
