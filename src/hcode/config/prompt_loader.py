"""
Prompt Loader for HCode.

Loads prompt files (.prompt) from a configurable directory.
Supports variable substitution, metadata parsing, and prompt chaining.

Prompt File Format:
---
name: my_prompt
description: Description of what this prompt does
author: Your Name
version: 1.0
variables:
  - name: task
    description: The task to perform
    required: true
  - name: context
    description: Additional context
    required: false
    default: ""
---
You are an expert at {{task}}.

{{#if context}}
Additional context: {{context}}
{{/if}}

Please help with the following...
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import yaml


@dataclass
class PromptVariable:
    """Definition of a variable in a prompt template."""

    name: str
    description: str = ""
    required: bool = False
    default: Any = None


@dataclass
class PromptMetadata:
    """Metadata for a prompt file."""

    name: str
    description: str = ""
    author: str = ""
    version: str = "1.0"
    variables: List[PromptVariable] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    category: str = "general"


@dataclass
class LoadedPrompt:
    """A loaded and parsed prompt."""

    file_path: Path
    metadata: PromptMetadata
    template: str
    raw_content: str

    def render(self, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Render the prompt template with variables.

        Args:
            variables: Dictionary of variable values

        Returns:
            Rendered prompt string
        """
        variables = variables or {}
        result = self.template

        # Apply defaults for missing variables
        for var in self.metadata.variables:
            if var.name not in variables and var.default is not None:
                variables[var.name] = var.default

        # Check required variables
        missing = []
        for var in self.metadata.variables:
            if var.required and var.name not in variables:
                missing.append(var.name)

        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")

        # Simple variable substitution: {{variable}}
        for name, value in variables.items():
            result = result.replace(f"{{{{{name}}}}}", str(value))

        # Handle conditionals: {{#if variable}}...{{/if}}
        result = self._process_conditionals(result, variables)

        # Handle loops: {{#each items}}...{{/each}}
        result = self._process_loops(result, variables)

        return result.strip()

    def _process_conditionals(self, template: str, variables: Dict[str, Any]) -> str:
        """Process {{#if variable}}...{{/if}} blocks."""
        pattern = r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}"

        def replace_conditional(match):
            var_name = match.group(1)
            content = match.group(2)
            if var_name in variables and variables[var_name]:
                return content
            return ""

        return re.sub(pattern, replace_conditional, template, flags=re.DOTALL)

    def _process_loops(self, template: str, variables: Dict[str, Any]) -> str:
        """Process {{#each items}}...{{/each}} blocks."""
        pattern = r"\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}"

        def replace_loop(match):
            var_name = match.group(1)
            content = match.group(2)
            if var_name in variables and isinstance(variables[var_name], (list, tuple)):
                results = []
                for i, item in enumerate(variables[var_name]):
                    item_content = content
                    if isinstance(item, dict):
                        for k, v in item.items():
                            item_content = item_content.replace(f"{{{{this.{k}}}}}", str(v))
                    else:
                        item_content = item_content.replace("{{this}}", str(item))
                    item_content = item_content.replace("{{@index}}", str(i))
                    results.append(item_content)
                return "".join(results)
            return ""

        return re.sub(pattern, replace_loop, template, flags=re.DOTALL)


class PromptLoader:
    """
    Loads and manages prompt files from a directory.

    Supports:
    - Loading .prompt files with YAML frontmatter
    - Variable substitution
    - Prompt caching
    - Hot reloading
    """

    PROMPT_EXTENSION = ".prompt"
    FRONTMATTER_DELIMITER = "---"

    def __init__(self, prompts_dir: Optional[Path] = None, auto_reload: bool = False):
        """
        Initialize the prompt loader.

        Args:
            prompts_dir: Directory containing .prompt files
            auto_reload: Automatically reload prompts when files change
        """
        self.prompts_dir = prompts_dir or self._get_default_prompts_dir()
        self.auto_reload = auto_reload
        self._prompts_cache: Dict[str, LoadedPrompt] = {}
        self._file_mtimes: Dict[str, float] = {}
        self._listeners: List[Callable[[str, LoadedPrompt], None]] = []

    def _get_default_prompts_dir(self) -> Path:
        """Get the default prompts directory."""
        # Check environment variable first
        env_dir = os.getenv("HCODE_PROMPTS_DIR")
        if env_dir:
            return Path(env_dir)

        # Check project-local .hcode/prompts
        local_dir = Path.cwd() / ".hcode" / "prompts"
        if local_dir.exists():
            return local_dir

        # Default to user config directory
        return Path.home() / ".hcode" / "prompts"

    def ensure_directory(self) -> None:
        """Ensure the prompts directory exists."""
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> Dict[str, LoadedPrompt]:
        """
        Load all prompts from the directory.

        Returns:
            Dictionary mapping prompt names to LoadedPrompt objects
        """
        self.ensure_directory()
        prompts = {}

        for prompt_file in self.prompts_dir.glob(f"*{self.PROMPT_EXTENSION}"):
            try:
                prompt = self.load_file(prompt_file)
                prompts[prompt.metadata.name] = prompt
                self._prompts_cache[prompt.metadata.name] = prompt
            except Exception as e:
                print(f"Warning: Failed to load prompt {prompt_file}: {e}")

        return prompts

    def load_file(self, file_path: Path) -> LoadedPrompt:
        """
        Load a single prompt file.

        Args:
            file_path: Path to the .prompt file

        Returns:
            LoadedPrompt object
        """
        content = file_path.read_text(encoding="utf-8")
        self._file_mtimes[str(file_path)] = file_path.stat().st_mtime

        # Parse frontmatter and template
        metadata, template = self._parse_prompt_file(content, file_path)

        return LoadedPrompt(
            file_path=file_path, metadata=metadata, template=template, raw_content=content
        )

    def _parse_prompt_file(self, content: str, file_path: Path) -> tuple:
        """
        Parse a prompt file into metadata and template.

        Args:
            content: Raw file content
            file_path: Path for error messages

        Returns:
            Tuple of (PromptMetadata, template_string)
        """
        lines = content.split("\n")

        # Check for frontmatter
        if lines[0].strip() == self.FRONTMATTER_DELIMITER:
            # Find closing delimiter
            try:
                end_idx = lines[1:].index(self.FRONTMATTER_DELIMITER) + 1
                frontmatter = "\n".join(lines[1:end_idx])
                template = "\n".join(lines[end_idx + 1 :])
            except ValueError:
                # No closing delimiter - treat as no frontmatter
                frontmatter = ""
                template = content
        else:
            frontmatter = ""
            template = content

        # Parse frontmatter as YAML
        metadata = self._parse_metadata(frontmatter, file_path)

        return metadata, template.strip()

    def _parse_metadata(self, frontmatter: str, file_path: Path) -> PromptMetadata:
        """
        Parse YAML frontmatter into PromptMetadata.

        Args:
            frontmatter: YAML string
            file_path: Path for default name

        Returns:
            PromptMetadata object
        """
        if not frontmatter.strip():
            # No frontmatter - use filename as name
            return PromptMetadata(name=file_path.stem)

        try:
            data = yaml.safe_load(frontmatter) or {}
        except yaml.YAMLError:
            data = {}

        # Parse variables
        variables = []
        for var_data in data.get("variables", []):
            if isinstance(var_data, dict):
                variables.append(
                    PromptVariable(
                        name=var_data.get("name", ""),
                        description=var_data.get("description", ""),
                        required=var_data.get("required", False),
                        default=var_data.get("default"),
                    )
                )
            elif isinstance(var_data, str):
                variables.append(PromptVariable(name=var_data))

        return PromptMetadata(
            name=data.get("name", file_path.stem),
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0"),
            variables=variables,
            tags=data.get("tags", []),
            category=data.get("category", "general"),
        )

    def get(self, name: str, reload: bool = False) -> Optional[LoadedPrompt]:
        """
        Get a prompt by name.

        Args:
            name: Prompt name
            reload: Force reload from file

        Returns:
            LoadedPrompt or None if not found
        """
        if reload or self.auto_reload:
            self._check_for_updates(name)

        if name in self._prompts_cache:
            return self._prompts_cache[name]

        # Try to load by name
        prompt_file = self.prompts_dir / f"{name}{self.PROMPT_EXTENSION}"
        if prompt_file.exists():
            prompt = self.load_file(prompt_file)
            self._prompts_cache[name] = prompt
            return prompt

        return None

    def render(self, name: str, variables: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """
        Get and render a prompt by name.

        Args:
            name: Prompt name
            variables: Variable values
            **kwargs: Additional variables

        Returns:
            Rendered prompt string

        Raises:
            ValueError: If prompt not found or missing required variables
        """
        prompt = self.get(name)
        if not prompt:
            raise ValueError(f"Prompt not found: {name}")

        # Merge variables and kwargs
        all_vars = dict(variables or {})
        all_vars.update(kwargs)

        return prompt.render(all_vars)

    def _check_for_updates(self, name: str) -> None:
        """Check if a prompt file has been updated and reload if necessary."""
        prompt_file = self.prompts_dir / f"{name}{self.PROMPT_EXTENSION}"
        if not prompt_file.exists():
            return

        current_mtime = prompt_file.stat().st_mtime
        cached_mtime = self._file_mtimes.get(str(prompt_file), 0)

        if current_mtime > cached_mtime:
            prompt = self.load_file(prompt_file)
            self._prompts_cache[name] = prompt
            self._notify_listeners(name, prompt)

    def _notify_listeners(self, name: str, prompt: LoadedPrompt) -> None:
        """Notify listeners of prompt changes."""
        for listener in self._listeners:
            try:
                listener(name, prompt)
            except Exception:
                pass

    def add_listener(self, callback: Callable[[str, LoadedPrompt], None]) -> None:
        """Add a listener for prompt changes."""
        self._listeners.append(callback)

    def list_prompts(self) -> List[Dict[str, Any]]:
        """
        List all available prompts with metadata.

        Returns:
            List of prompt info dictionaries
        """
        self.load_all()
        return [
            {
                "name": prompt.metadata.name,
                "description": prompt.metadata.description,
                "category": prompt.metadata.category,
                "tags": prompt.metadata.tags,
                "variables": [
                    {"name": v.name, "description": v.description, "required": v.required}
                    for v in prompt.metadata.variables
                ],
                "file": str(prompt.file_path),
            }
            for prompt in self._prompts_cache.values()
        ]

    def create_prompt(
        self,
        name: str,
        template: str,
        description: str = "",
        variables: Optional[List[Dict[str, Any]]] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
    ) -> Path:
        """
        Create a new prompt file.

        Args:
            name: Prompt name
            template: Prompt template content
            description: Prompt description
            variables: Variable definitions
            category: Prompt category
            tags: Prompt tags

        Returns:
            Path to created file
        """
        self.ensure_directory()

        # Build frontmatter
        metadata = {
            "name": name,
            "description": description,
            "version": "1.0",
            "category": category,
        }

        if tags:
            metadata["tags"] = tags

        if variables:
            metadata["variables"] = variables

        # Build file content
        frontmatter = yaml.dump(metadata, default_flow_style=False)
        content = f"---\n{frontmatter}---\n\n{template}"

        # Write file
        file_path = self.prompts_dir / f"{name}{self.PROMPT_EXTENSION}"
        file_path.write_text(content, encoding="utf-8")

        # Reload
        self.load_file(file_path)

        return file_path


# Global prompt loader instance
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get the global prompt loader instance."""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


def set_prompts_dir(directory: Path) -> None:
    """Set the prompts directory and reinitialize the loader."""
    global _prompt_loader
    _prompt_loader = PromptLoader(prompts_dir=directory)


def load_prompt(name: str, **variables) -> str:
    """
    Convenience function to load and render a prompt.

    Args:
        name: Prompt name
        **variables: Variable values

    Returns:
        Rendered prompt string
    """
    return get_prompt_loader().render(name, variables)


def list_prompts() -> List[Dict[str, Any]]:
    """
    Convenience function to list all prompts.

    Returns:
        List of prompt info dictionaries
    """
    return get_prompt_loader().list_prompts()
