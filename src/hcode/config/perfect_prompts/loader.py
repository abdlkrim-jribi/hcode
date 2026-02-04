"""
Perfect Prompt Loader.

Loads prompt templates from the perfect_prompts directory in project root.
These templates define the agent's behavior for planning, execution, and verification.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class PerfectPromptLoader:
    """
    Loader for perfect prompt templates.

    Templates are loaded from the `perfect_prompts/` directory in project root.
    Supports variable substitution using {{variable}} syntax.

    Available templates:
    - planning-mode.txt: System prompt for planning phase
    - task.md: Task list format and guidelines
    - implementation_plan.md: Implementation plan structure
    - walkthrough.md: Verification walkthrough format
    - tool_calling.md: Tool documentation and anti-hallucination rules
    - modes.md: Mode descriptions (PLANNING, EXECUTION, VERIFICATION)
    - workflows.md: Workflow definitions
    - identity.md: Agent identity and persona

    Usage:
        loader = PerfectPromptLoader()
        system_prompt = loader.get_planning_system_prompt(working_dir="/path/to/project")
        task_template = loader.get_task_md_template()
    """

    _instance: Optional["PerfectPromptLoader"] = None

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the loader."""
        if self._initialized:
            return

        self._templates: Dict[str, str] = {}
        self._prompts_dir = self._find_prompts_dir()
        self._load_all_templates()
        self._initialized = True

    def _find_prompts_dir(self) -> Path:
        """
        Find the perfect_prompts directory.

        Searches in order:
        1. Current working directory
        2. Project root (where .git or pyproject.toml exists)
        3. Relative to this file (navigate up to find project root)
        4. Package data directory (fallback)
        """
        # Try current working directory first
        cwd_prompts = Path.cwd() / "perfect_prompts"
        if cwd_prompts.exists():
            logger.debug(f"Found perfect_prompts in cwd: {cwd_prompts}")
            return cwd_prompts

        # Try relative to this file's location (go up to project root)
        current = Path(__file__).resolve()

        # Navigate up to find project root markers
        for _ in range(10):
            parent = current.parent

            # Check if we hit project root markers
            if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
                prompts_dir = parent / "perfect_prompts"
                if prompts_dir.exists():
                    logger.debug(f"Found perfect_prompts at project root: {prompts_dir}")
                    return prompts_dir

            # Also check directly in this parent
            prompts_dir = parent / "perfect_prompts"
            if prompts_dir.exists():
                logger.debug(f"Found perfect_prompts at: {prompts_dir}")
                return prompts_dir

            if parent == current:
                break

            current = parent

        # Fallback to package directory
        fallback = Path(__file__).parent / "templates"
        logger.warning(f"perfect_prompts not found, using fallback: {fallback}")
        return fallback

    def _load_all_templates(self) -> None:
        """Load all template files."""
        if not self._prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self._prompts_dir}")
            return

        template_files = [
            "planning-mode.txt",
            "task.md",
            "implementation_plan.md",
            "walkthrough.md",
            "tool_calling.md",
            "modes.md",
            "workflows.md",
            "identity.md",
            "artifact_formatting_guidelines.md",
            "knowledge_items.md",
            "notify_user_tool.md",
            "task_boundary_tool.md",
            "Fast Prompt.txt",
        ]

        for filename in template_files:
            file_path = self._prompts_dir / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    # Use filename without extension as key
                    key = filename.replace(".txt", "").replace(".md", "").replace(" ", "_").lower()
                    self._templates[key] = content
                    logger.debug(f"Loaded template: {filename} as {key}")
                except Exception as e:
                    logger.error(f"Failed to load template {filename}: {e}")

    def reload(self) -> None:
        """Reload all templates from disk."""
        self._templates.clear()
        self._load_all_templates()

    def get_raw(self, template_name: str) -> Optional[str]:
        """
        Get raw template content without substitution.

        Args:
            template_name: Template key (e.g., "planning-mode", "task", "implementation_plan")

        Returns:
            Template content or None if not found
        """
        # Normalize the key
        key = template_name.replace("-", "_").replace(".txt", "").replace(".md", "").lower()
        return self._templates.get(key)

    def get(self, template_name: str, **kwargs) -> str:
        """
        Get template with variable substitution.

        Args:
            template_name: Template key
            **kwargs: Variables to substitute (e.g., ArtifactDirectoryPath=".hcode")

        Returns:
            Template with variables substituted
        """
        content = self.get_raw(template_name)
        if content is None:
            logger.warning(f"Template not found: {template_name}")
            return ""

        return self._substitute(content, kwargs)

    def _substitute(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Substitute variables in template.

        Supports {{variable}} syntax.

        Args:
            template: Template string
            variables: Variables to substitute

        Returns:
            Template with variables substituted
        """
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_planning_system_prompt(
        self,
        working_dir: str = ".",
        artifacts_dir: str = ".hcode",
    ) -> str:
        """
        Build complete system prompt for planning phase.

        Combines:
        - planning-mode.txt (main system prompt)
        - tool_calling.md (tool documentation)

        Args:
            working_dir: Project working directory
            artifacts_dir: Directory for artifacts (default: .hcode)

        Returns:
            Complete system prompt
        """
        # Get base planning prompt
        base_prompt = self.get_raw("planning_mode") or ""

        # Get tool documentation
        tool_docs = self.get_raw("tool_calling") or ""

        # Substitute artifact path
        artifact_path = f"{working_dir}/{artifacts_dir}"
        base_prompt = base_prompt.replace("{{ArtifactDirectoryPath}}", artifact_path)

        # Combine
        full_prompt = base_prompt
        if tool_docs:
            full_prompt += f"\n\n<tool_documentation>\n{tool_docs}\n</tool_documentation>"

        return full_prompt

    def get_task_md_template(self, artifacts_dir: str = ".hcode") -> str:
        """
        Get task.md template with guidelines.

        Args:
            artifacts_dir: Directory for artifacts

        Returns:
            Task.md template
        """
        template = self.get_raw("task") or self._get_default_task_template()
        return template.replace("{{ArtifactDirectoryPath}}", artifacts_dir)

    def get_implementation_plan_template(self, artifacts_dir: str = ".hcode") -> str:
        """
        Get implementation_plan.md template.

        Args:
            artifacts_dir: Directory for artifacts

        Returns:
            Implementation plan template
        """
        template = self.get_raw("implementation_plan") or self._get_default_plan_template()
        return template.replace("{{ArtifactDirectoryPath}}", artifacts_dir)

    def get_walkthrough_template(self) -> str:
        """
        Get walkthrough.md template.

        Returns:
            Walkthrough template
        """
        return self.get_raw("walkthrough") or self._get_default_walkthrough_template()

    def get_tool_documentation(self) -> str:
        """
        Get tool calling documentation.

        Returns:
            Tool documentation
        """
        return self.get_raw("tool_calling") or ""

    def get_mode_descriptions(self) -> str:
        """
        Get mode descriptions (PLANNING, EXECUTION, VERIFICATION).

        Returns:
            Mode descriptions
        """
        return self.get_raw("modes") or self._get_default_modes()

    def get_identity(self) -> str:
        """
        Get agent identity/persona.

        Returns:
            Identity description
        """
        return self.get_raw("identity") or self._get_default_identity()

    # =========================================================================
    # Default Templates (Fallbacks)
    # =========================================================================

    def _get_default_task_template(self) -> str:
        """Default task.md template."""
        return """# Task Management

## Task
{{task}}

## Subtasks
- [ ] Analyze requirements <!-- id: 0 -->
- [ ] Research codebase <!-- id: 1 -->
- [ ] Create implementation plan <!-- id: 2 -->
- [ ] Implement changes <!-- id: 3 -->
- [ ] Verify implementation <!-- id: 4 -->

## Notes
(Add any notes or findings here)
"""

    def _get_default_plan_template(self) -> str:
        """Default implementation_plan.md template."""
        return """# Implementation Plan

## Goal
{{goal}}

## Proposed Changes

### Component 1
- Changes to be made

## Verification Plan

### Automated Tests
- Commands to run

### Manual Verification
- Steps to verify
"""

    def _get_default_walkthrough_template(self) -> str:
        """Default walkthrough.md template."""
        return """# Implementation Walkthrough

## Summary
Brief summary of what was implemented.

## Changes Made
- List of changes

## Verification Summary
- What was tested
- Results
"""

    def _get_default_modes(self) -> str:
        """Default mode descriptions."""
        return """## Modes

### PLANNING
Research the codebase, understand requirements, and design your approach.
Create implementation_plan.md to document proposed changes.

### EXECUTION
Write code, make changes, implement your design.
Return to PLANNING if you discover unexpected complexity.

### VERIFICATION
Test your changes, run verification steps, validate correctness.
Create walkthrough.md after completing verification.
"""

    def _get_default_identity(self) -> str:
        """Default agent identity."""
        return """You are Hcode, an AI coding assistant designed for agentic software development.
You help users with coding tasks through a structured Planning → Execution → Verification workflow.
"""

    def list_templates(self) -> list:
        """
        List all available template keys.

        Returns:
            List of template keys
        """
        return sorted(self._templates.keys())


# Global singleton
_loader: Optional[PerfectPromptLoader] = None


def get_perfect_prompt_loader() -> PerfectPromptLoader:
    """
    Get the global PerfectPromptLoader instance.

    Returns:
        The singleton PerfectPromptLoader instance
    """
    global _loader
    if _loader is None:
        _loader = PerfectPromptLoader()
    return _loader
