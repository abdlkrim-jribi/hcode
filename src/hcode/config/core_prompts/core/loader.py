"""
Core Prompt Loader.

Loads and provides access to all core prompts from YAML configuration files.
Supports template substitution with context variables.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

import yaml

logger = logging.getLogger(__name__)


class CorePromptLoader:
    """
    Centralized loader for all core prompts.

    Loads prompts from YAML files in the config/core_prompts/core directory
    and provides easy access with template substitution support.

    Usage:
        loader = CorePromptLoader()

        # Get a simple prompt
        prompt = loader.get("system.default")

        # Get a prompt with variable substitution
        prompt = loader.get("phases.planning.instruction", task="Fix the bug")

        # Get all prompts in a category
        phase_prompts = loader.get_category("phases")
    """

    # Singleton instance
    _instance: Optional["CorePromptLoader"] = None

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the loader."""
        if self._initialized:
            return

        self._prompts: Dict[str, Any] = {}
        self._prompts_dir = Path(__file__).parent
        self._load_all_prompts()
        self._initialized = True

    def _load_all_prompts(self) -> None:
        """Load all prompt YAML and markdown files."""
        # Load YAML files
        yaml_files = [
            "phases.yaml",
            "templates.yaml",
            "system.yaml",
            "reasoning.yaml",
        ]

        for yaml_file in yaml_files:
            file_path = self._prompts_dir / yaml_file
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = yaml.safe_load(f)
                        if content:
                            # Use filename without extension as category
                            category = yaml_file.replace(".yaml", "")
                            self._prompts[category] = content
                            logger.debug(f"Loaded prompts from {yaml_file}")
                except Exception as e:
                    logger.error(f"Failed to load prompts from {yaml_file}: {e}")

        # Load markdown files as raw text
        md_files = [
            "identity.md",
            "tool_format.md",
            "planning_mode.md",
            "execution_mode.md",
        ]

        for md_file in md_files:
            file_path = self._prompts_dir / md_file
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content:
                            # Use filename without extension as key
                            key = md_file.replace(".md", "")
                            self._prompts[key] = content
                            logger.debug(f"Loaded markdown prompt: {md_file}")
                except Exception as e:
                    logger.error(f"Failed to load prompt {md_file}: {e}")

    def reload(self) -> None:
        """Reload all prompts from files."""
        self._prompts.clear()
        self._load_all_prompts()
        # Clear cached results
        self.get.cache_clear()

    @lru_cache(maxsize=256)
    def get(self, path: str, **kwargs) -> str:
        """
        Get a prompt by dot-notation path with optional variable substitution.

        Args:
            path: Dot-notation path to the prompt (e.g., "phases.planning.instruction")
            **kwargs: Variables to substitute in the prompt template

        Returns:
            The prompt string with variables substituted

        Raises:
            KeyError: If the prompt path is not found

        Example:
            # Get system default prompt
            prompt = loader.get("system.system.default")

            # Get planning instruction with task variable
            prompt = loader.get("phases.planning.instruction", task="Fix authentication")
        """
        # Navigate to the prompt using dot notation
        parts = path.split(".")
        current = self._prompts

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Prompt not found: {path}")

        if not isinstance(current, str):
            raise KeyError(f"Path does not point to a prompt string: {path}")

        # Clear cache and return with substitution if kwargs provided
        if kwargs:
            # Can't cache with kwargs, so we return directly
            self.get.cache_clear()
            return self._substitute(current, kwargs)

        return current

    def get_raw(self, path: str) -> str:
        """
        Get a raw prompt without any substitution.

        Args:
            path: Dot-notation path to the prompt

        Returns:
            The raw prompt string without substitution
        """
        parts = path.split(".")
        current = self._prompts

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Prompt not found: {path}")

        if not isinstance(current, str):
            raise KeyError(f"Path does not point to a prompt string: {path}")

        return current

    def get_category(self, category: str) -> Dict[str, Any]:
        """
        Get all prompts in a category.

        Args:
            category: Category name (e.g., "phases", "system", "templates")

        Returns:
            Dictionary of prompts in the category
        """
        if category not in self._prompts:
            raise KeyError(f"Category not found: {category}")
        return self._prompts[category].copy()

    def _substitute(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Substitute variables in a prompt template.

        Supports both {variable} and {{variable}} syntax.

        Args:
            template: The prompt template string
            variables: Dictionary of variables to substitute

        Returns:
            The template with variables substituted
        """
        result = template

        for key, value in variables.items():
            # Handle both {key} and {{key}} patterns
            result = result.replace(f"{{{key}}}", str(value))
            result = result.replace(f"{{{{{key}}}}}", str(value))

        return result

    def format_prompt(self, path: str, **kwargs) -> str:
        """
        Alias for get() with kwargs - format a prompt with variables.

        Args:
            path: Dot-notation path to the prompt
            **kwargs: Variables to substitute

        Returns:
            Formatted prompt string
        """
        return self.get(path, **kwargs)

    def list_prompts(self, category: Optional[str] = None) -> list:
        """
        List all available prompt paths.

        Args:
            category: Optional category to filter by

        Returns:
            List of prompt paths
        """
        paths = []

        def _collect_paths(obj: Any, prefix: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_prefix = f"{prefix}.{key}" if prefix else key
                    _collect_paths(value, new_prefix)
            elif isinstance(obj, str):
                paths.append(prefix)

        if category:
            if category in self._prompts:
                _collect_paths(self._prompts[category], category)
        else:
            _collect_paths(self._prompts)

        return sorted(paths)

    # =========================================================================
    # Markdown Prompt Access
    # =========================================================================

    def get_identity(self) -> str:
        """Get the Hcode identity prompt."""
        return self._prompts.get("identity", "You are Hcode, an AI coding assistant.")

    def get_tool_format(self) -> str:
        """Get the tool format documentation."""
        return self._prompts.get("tool_format", "")

    def get_planning_mode(self) -> str:
        """Get the planning mode prompt."""
        return self._prompts.get("planning_mode", "")

    def get_execution_mode(self) -> str:
        """Get the execution mode prompt."""
        return self._prompts.get("execution_mode", "")

    # =========================================================================
    # Convenience Methods for Common Prompts
    # =========================================================================

    def get_phase_prompt(self, phase: str, prompt_type: str = "instruction") -> str:
        """
        Get a phase-specific prompt.

        Args:
            phase: Phase name (planning, execution, verification)
            prompt_type: Type of prompt (instruction, workflow)

        Returns:
            The phase prompt
        """
        return self.get_raw(f"phases.{phase}.{prompt_type}")

    def get_template(self, template_name: str) -> str:
        """
        Get an artifact template.

        Args:
            template_name: Template name (task_md, implementation_plan_md, walkthrough_md)

        Returns:
            The template string
        """
        return self.get_raw(f"templates.{template_name}.template")

    def get_system_prompt(self, prompt_type: str = "default") -> str:
        """
        Get a system prompt.

        Args:
            prompt_type: Type of system prompt (default, autonomous_mode, interactive_mode)

        Returns:
            The system prompt
        """
        return self.get_raw(f"system.system.{prompt_type}")

    def get_continuation_prompt(self, prompt_type: str = "default") -> str:
        """
        Get a continuation prompt.

        Args:
            prompt_type: Type of continuation (default, with_task, with_reason, etc.)

        Returns:
            The continuation prompt
        """
        return self.get_raw(f"system.continuation.{prompt_type}")

    def get_thinking_template(self, depth: str = "standard") -> str:
        """
        Get a thinking template.

        Args:
            depth: Thinking depth (quick, standard, deep)

        Returns:
            The thinking template
        """
        return self.get_raw(f"reasoning.thinking_templates.{depth}")

    def get_output_format(self, format_type: str = "default") -> str:
        """
        Get output format instructions.

        Args:
            format_type: Format type (default, concise, verbose)

        Returns:
            The output format instructions
        """
        return self.get_raw(f"system.output_format.{format_type}")

    # =========================================================================
    # Phase Prompt Builders (with variable substitution)
    # =========================================================================

    def build_planning_prompt(self, task: str) -> str:
        """
        Build the planning phase prompt with task.

        Args:
            task: The user's task

        Returns:
            Complete planning prompt
        """
        template = self.get_raw("phases.planning.instruction")
        return self._substitute(template, {"task": task})

    def build_execution_prompt(
        self,
        plan_content: str,
        modified_files_count: int,
        completed_actions_count: int,
        iteration: int,
    ) -> str:
        """
        Build the execution phase prompt with context.

        Args:
            plan_content: Content of implementation_plan.md
            modified_files_count: Number of modified files
            completed_actions_count: Number of completed actions
            iteration: Current iteration number

        Returns:
            Complete execution prompt
        """
        template = self.get_raw("phases.execution.instruction")
        return self._substitute(template, {
            "plan_content": plan_content,
            "modified_files_count": modified_files_count,
            "completed_actions_count": completed_actions_count,
            "iteration": iteration,
        })

    def build_task_md(self, task: str) -> str:
        """
        Build task.md content from template.

        Args:
            task: The user's task

        Returns:
            task.md content
        """
        template = self.get_raw("templates.task_md.template")
        return self._substitute(template, {"task": task})

    def build_implementation_plan_md(self) -> str:
        """
        Build implementation_plan.md content from template.

        Returns:
            implementation_plan.md content
        """
        return self.get_raw("templates.implementation_plan_md.template")

    def build_walkthrough_md(
        self,
        task: str,
        modified_files_section: str,
        changes_details: str,
        test_section: str,
    ) -> str:
        """
        Build walkthrough.md content from template.

        Args:
            task: The user's task
            modified_files_section: Formatted list of modified files
            changes_details: Details of changes made
            test_section: Test results section

        Returns:
            walkthrough.md content
        """
        template = self.get_raw("templates.walkthrough_md.template")
        return self._substitute(template, {
            "task": task,
            "modified_files_section": modified_files_section,
            "changes_details": changes_details,
            "test_section": test_section,
        })

    def build_user_context(self, os_name: str, root_dir: str) -> str:
        """
        Build user context information.

        Args:
            os_name: Operating system name
            root_dir: Root directory path

        Returns:
            User context string
        """
        template = self.get_raw("system.user_context.user_info")
        return self._substitute(template, {
            "os_name": os_name,
            "root_dir": root_dir,
        })

    def build_refinement_prompt(
        self,
        original_reasoning: str,
        feedback: str,
        outcome: str,
    ) -> str:
        """
        Build refinement prompt for iterating on reasoning.

        Args:
            original_reasoning: The original reasoning that led to unexpected outcome
            feedback: Feedback received
            outcome: The actual outcome

        Returns:
            Refinement prompt
        """
        template = self.get_raw("reasoning.refinement.template")
        return self._substitute(template, {
            "original_reasoning": original_reasoning,
            "feedback": feedback,
            "outcome": outcome,
        })


# Global singleton instance for easy access
_loader: Optional[CorePromptLoader] = None


def get_prompt_loader() -> CorePromptLoader:
    """
    Get the global CorePromptLoader instance.

    Returns:
        The singleton CorePromptLoader instance
    """
    global _loader
    if _loader is None:
        _loader = CorePromptLoader()
    return _loader
