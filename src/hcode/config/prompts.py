"""
Prompts and Model Configuration Loader for Hcode.

This module provides centralized access to all prompts and model parameters
from external YAML configuration files, making it easy to fine-tune
AI behavior without modifying code.
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
    max_tokens: int = 16384  # Maximum for most modern models
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

    max_context_tokens: int = 200000  # Claude 3.5 Sonnet max
    reserve_output_tokens: int = 16384  # Max output tokens
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
    Centralized prompts configuration loader.

    Loads prompts from config/prompts.yaml and provides
    easy access to all system prompts.
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
        # Check environment variable first
        env_path = os.getenv("HCODE_PROMPTS_CONFIG")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        # Search paths in order of priority
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
            # Use default prompts if no config file found
            self._prompts_data = self._get_default_prompts()

    def _get_default_prompts(self) -> Dict[str, Any]:
        """Return default prompts if no config file exists"""
        return {
            "system_prompts": {
                "coding_agent": self._default_coding_prompt(),
                "openai_coding": self._default_openai_prompt(),
                "agent": self._default_agent_prompt(),
                "sub_agent": self._default_sub_agent_prompt(),
            },
            "continuation_prompts": [
                "Continue from where you left off. Do not repeat what you've already written.",
                "Please continue. Pick up exactly where you stopped.",
                "Continue generating. Do not restart or repeat previous content.",
            ],
            "persona": {
                "name": "Hcode",
                "tone": "professional",
                "use_emojis": False,
                "verbosity": "balanced",
            },
        }

    def _default_coding_prompt(self) -> str:
        return """You are Hcode, an expert coding agent with access to a file system and development tools.

Your capabilities include:
- Reading and writing files across the project
- Running commands and tests
- Analyzing code for issues and improvements
- Implementing complete features
- Refactoring existing code
- Debugging and fixing errors

When working on tasks:
1. Always plan your approach before implementing
2. Test your changes thoroughly
3. Follow project conventions and best practices
4. Write clean, maintainable, well-documented code
5. Consider edge cases and error handling

You should be proactive, autonomous, and thorough. Break down complex tasks into manageable steps and execute them systematically."""

    def _default_openai_prompt(self) -> str:
        return """You are Hcode, an expert coding assistant with access to file system operations and command execution.

You can use the provided functions to:
- Read and write files
- Execute commands and tests
- Analyze code structure
- Implement features
- Refactor code
- Debug issues

Best practices:
1. Plan your approach before implementation
2. Write production-quality code with proper error handling
3. Follow existing code patterns and conventions
4. Include comprehensive testing
5. Document significant decisions

You are autonomous and thorough. Break down complex tasks systematically and validate your changes."""

    def _default_agent_prompt(self) -> str:
        return """You are Hcode, an advanced AI coding assistant with comprehensive tool access.

CORE CAPABILITIES:
- File Operations: Read, write, edit, and search files
- Code Execution: Run commands, tests, and scripts
- Web Access: Fetch documentation and search the web
- Task Management: Track and organize complex tasks
- Code Analysis: Understand and improve code quality

WORKING PRINCIPLES:
1. Understand First: Read and analyze existing code before making changes
2. Plan Carefully: Break complex tasks into manageable steps
3. Execute Precisely: Use the right tool for each operation
4. Verify Results: Test and validate all changes
5. Communicate Clearly: Explain your reasoning and actions

You are proactive, thorough, and quality-focused. Aim for production-ready solutions."""

    def _default_sub_agent_prompt(self) -> str:
        return """You are a specialized sub-agent of Hcode, focused on completing a specific delegated task.

Your role:
- Execute the assigned task efficiently
- Use available tools appropriately
- Report results clearly and concisely
- Escalate issues if you cannot complete the task

Stay focused on your assigned task and avoid scope creep."""

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
            prompt_type: Type of prompt (coding_agent, openai_coding, agent, sub_agent, planning, code_review)

        Returns:
            The system prompt string, with optional memory file content prepended for OpenAI coding prompts.
        """
        prompts = self._prompts_data.get("system_prompts", {})
        prompt = prompts.get(prompt_type, self._default_coding_prompt())

        # If this is the OpenAI coding prompt, prepend the memory file content (e.g., CLAUDE.md)
        if prompt_type == "openai_coding":
            try:
                # Retrieve memory configuration (defaults to CLAUDE.md)
                mem_cfg = self.get_memory_config()
                mem_file_name = mem_cfg.get("memory_file", "CLAUDE.md")
                mem_path = Path.cwd() / mem_file_name
                if mem_path.is_file():
                    mem_content = mem_path.read_text()
                    # Ensure there is a clear separation between memory content and the prompt
                    prompt = f"{mem_content}\n\n{prompt}"
            except Exception:
                # If any issue occurs (e.g., file not found), fall back to the original prompt
                pass

        return prompt

    def get_continuation_prompts(self) -> List[str]:
        """Get list of continuation prompts"""
        return self._prompts_data.get(
            "continuation_prompts",
            [
                "Continue from where you left off. Do not repeat what you've already written.",
            ],
        )

    def get_continuation_prompt(self, index: int = 0) -> str:
        """Get a specific continuation prompt by index (rotates)"""
        prompts = self.get_continuation_prompts()
        return prompts[index % len(prompts)]

    def get_tool_prompt(self, prompt_name: str) -> str:
        """Get a tool-specific prompt"""
        tool_prompts = self._prompts_data.get("tool_prompts", {})
        return tool_prompts.get(prompt_name, "")

    def get_git_prompt(self, prompt_name: str) -> str:
        """Get a git-related prompt (commit_analysis, pr_analysis, etc.)"""
        git_prompts = self._prompts_data.get("git_prompts", {})
        return git_prompts.get(prompt_name, "")

    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration (banned commands, confirm commands)"""
        return self._prompts_data.get(
            "security",
            {
                "banned_commands": [],
                "confirm_commands": [],
            },
        )

    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory/CLAUDE.md configuration"""
        return self._prompts_data.get(
            "memory",
            {
                "memory_file": "CLAUDE.md",
                "memory_prompt": "",
            },
        )

    def get_persona(self) -> Dict[str, Any]:
        """Get persona configuration"""
        return self._prompts_data.get(
            "persona",
            {
                "name": "Hcode",
                "tone": "professional",
                "use_emojis": False,
                "verbosity": "balanced",
            },
        )

    def get_formatting(self) -> Dict[str, Any]:
        """Get formatting configuration"""
        return self._prompts_data.get(
            "formatting",
            {
                "code_block_style": "fenced",
                "default_language": "python",
                "show_line_numbers": True,
                "max_output_lines": 100,
            },
        )

    def get_claude_prompt(self) -> str:
        """
        Get the Claude Code style system prompt.

        Returns:
            Claude-style system prompt
        """
        return self.get_system_prompt("claude_code_style")

    def get_claude_reasoning_phase(self, phase_name: str) -> str:
        """
        Get a specific Claude reasoning phase template.

        Args:
            phase_name: Phase name (perception, comprehension, analysis, etc.)

        Returns:
            Reasoning phase template
        """
        phases = self._prompts_data.get("claude_reasoning_phases", {})
        return phases.get(phase_name, "")

    def get_claude_example(self, example_name: str) -> str:
        """
        Get a Claude-style interaction example.

        Args:
            example_name: Example identifier (simple_fix, complex_feature)

        Returns:
            Example interaction text
        """
        examples = self._prompts_data.get("claude_examples", {})
        return examples.get(example_name, "")

    def list_claude_reasoning_phases(self) -> List[str]:
        """
        List all available Claude reasoning phases.

        Returns:
            List of phase names
        """
        phases = self._prompts_data.get("claude_reasoning_phases", {})
        return list(phases.keys())

    def list_claude_examples(self) -> List[str]:
        """
        List all available Claude examples.

        Returns:
            List of example names
        """
        examples = self._prompts_data.get("claude_examples", {})
        return list(examples.keys())

    def get_reasoning_system_prompt(self) -> str:
        """
        Get the core reasoning system prompt.

        Returns:
            Reasoning system prompt string
        """
        return self._prompts_data.get("reasoning_prompts", {}).get("system", "")

    def get_reasoning_template(self, depth: str) -> str:
        """
        Get a thinking template for a specific depth (quick, standard, deep).

        Args:
            depth: depth name

        Returns:
            Thinking template string
        """
        return self._prompts_data.get("reasoning_prompts", {}).get("templates", {}).get(depth, "")

    def get_reasoning_enhancement(self, name: str) -> str:
        """
        Get an enhancement prompt (self_critique, uncertainty_handling, etc).

        Args:
            name: enhancement name

        Returns:
            Enhancement prompt string
        """
        return self._prompts_data.get("reasoning_prompts", {}).get("enhancements", {}).get(name, "")

    def get_reasoning_task_specific(self, task_name: str) -> str:
        """
        Get a task-specific reasoning protocol.

        Args:
            task_name: Task name (debugging, refactoring, etc)

        Returns:
            Task specific protocol string
        """
        return self._prompts_data.get("reasoning_prompts", {}).get("task_specific", {}).get(task_name, "")

    def get_phase_instruction(self, phase_name: str) -> str:
        """
        Get instruction for a specific reasoning phase.

        Args:
            phase_name: Name of the phase

        Returns:
            Instruction string
        """
        instructions = self._prompts_data.get("reasoning_prompts", {}).get("phase_instructions", {})
        return instructions.get(phase_name, "Think about this aspect of the problem.")



class ModelsConfig:
    """
    Centralized model configuration loader.

    Loads model parameters from config/models.yaml and provides
    easy access to generation settings.
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
        # Check environment variable first
        env_path = os.getenv("HCODE_MODELS_CONFIG")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        # Search paths in order of priority
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
            # Use default config if no file found
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
        """
        Get generation parameters, optionally for a specific task type.

        Args:
            task_type: Optional task type (code_generation, bug_fixing, etc.)

        Returns:
            GenerationParams instance
        """
        # Start with base generation params
        gen_config = self._models_data.get("generation", {})

        params = GenerationParams(
            temperature=gen_config.get("temperature", 0.3),
            top_p=gen_config.get("top_p", 1.0),
            top_k=gen_config.get("top_k", 0),
            max_tokens=gen_config.get("max_tokens", 16384),  # Maximum for most models
            frequency_penalty=gen_config.get("frequency_penalty", 0.0),
            presence_penalty=gen_config.get("presence_penalty", 0.0),
            stop_sequences=gen_config.get("stop_sequences", []),
        )

        # Apply task-specific overrides if specified
        if task_type:
            overrides = self._models_data.get("task_overrides", {}).get(task_type, {})
            if overrides:
                if "temperature" in overrides:
                    params.temperature = overrides["temperature"]
                if "top_p" in overrides:
                    params.top_p = overrides["top_p"]
                if "top_k" in overrides:
                    params.top_k = overrides["top_k"]
                if "max_tokens" in overrides:
                    params.max_tokens = overrides["max_tokens"]
                if "frequency_penalty" in overrides:
                    params.frequency_penalty = overrides["frequency_penalty"]
                if "presence_penalty" in overrides:
                    params.presence_penalty = overrides["presence_penalty"]

        return params

    def get_temperature(self, task_type: Optional[str] = None) -> float:
        """Get temperature setting"""
        return self.get_generation_params(task_type).temperature

    def get_top_p(self, task_type: Optional[str] = None) -> float:
        """Get top_p setting"""
        return self.get_generation_params(task_type).top_p

    def get_max_tokens(self, task_type: Optional[str] = None) -> int:
        """Get max_tokens setting"""
        return self.get_generation_params(task_type).max_tokens

    def get_context_config(self) -> ContextConfig:
        """Get context window configuration"""
        ctx = self._models_data.get("context", {})
        return ContextConfig(
            max_context_tokens=ctx.get("max_context_tokens", 128000),
            reserve_output_tokens=ctx.get("reserve_output_tokens", 8192),
            summarization_threshold=ctx.get("summarization_threshold", 0.8),
            max_history_turns=ctx.get("max_history_turns", 50),
        )

    def get_continuation_config(self) -> ContinuationConfig:
        """Get continuation configuration"""
        cont = self._models_data.get("continuation", {})
        return ContinuationConfig(
            enabled=cont.get("enabled", True),
            max_continuations=cont.get("max_continuations", 10),
            max_total_tokens=cont.get("max_total_tokens", 100000),
            truncation_patterns=cont.get("truncation_patterns", []),
        )

    def get_reliability_config(self) -> ReliabilityConfig:
        """Get reliability/retry configuration"""
        rel = self._models_data.get("reliability", {})
        return ReliabilityConfig(
            timeout=rel.get("timeout", 120.0),
            connect_timeout=rel.get("connect_timeout", 30.0),
            max_retries=rel.get("max_retries", 5),
            retry_multiplier=rel.get("retry_multiplier", 2.0),
            retry_min=rel.get("retry_min", 2.0),
            retry_max=rel.get("retry_max", 30.0),
        )

    def get_model_for_provider(self, provider: str, size: str = "medium") -> str:
        """
        Get model name for a provider and size.

        Args:
            provider: Provider name (anthropic, openai)
            size: Size alias (small, medium, large, fast, balanced, quality)

        Returns:
            Model name string
        """
        models = self._models_data.get("models", {})

        # Check aliases first
        aliases = models.get("aliases", {})
        if size in aliases and provider in aliases[size]:
            return aliases[size][provider]

        # Fall back to defaults
        defaults = models.get("defaults", {})
        return defaults.get(provider, "gpt-4o")

    def get_compatible_model(self, provider_hint: str, size: str = "medium") -> str:
        """
        Get model for OpenAI-compatible providers.

        Args:
            provider_hint: Provider name or base URL hint
            size: Size alias

        Returns:
            Model name string
        """
        models = self._models_data.get("models", {})
        compatible = models.get("compatible", {})

        # Try to match provider
        provider_lower = provider_hint.lower()
        for compat_name, sizes in compatible.items():
            if compat_name in provider_lower:
                return sizes.get(size, sizes.get("medium", ""))

        # Return empty if not found
        return ""


# Convenience functions for easy access
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
    # Clear caches
    get_prompts_config.cache_clear()
    get_models_config.cache_clear()


def get_claude_prompt() -> str:
    """Convenience function to get Claude Code style prompt"""
    return get_prompts_config().get_claude_prompt()



def get_claude_reasoning_phase(phase_name: str) -> str:
    """Convenience function to get a Claude reasoning phase"""
    return get_prompts_config().get_claude_reasoning_phase(phase_name)


def get_reasoning_system_prompt() -> str:
    """Convenience function to get reasoning system prompt"""
    return get_prompts_config().get_reasoning_system_prompt()


def get_phase_instruction(phase_name: str) -> str:
    """Convenience function to get phase instruction"""
    return get_prompts_config().get_phase_instruction(phase_name)

