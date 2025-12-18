
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def find_config_file(start_path: str = ".") -> Optional[Path]:

    """Find the configuration file.

    Args:
        start_path (str): Starting directory to search.

    Returns:
        Optional[Path]: Path to the config file if found, otherwise None.
    """
    
    current = Path(start_path).resolve()
    for parent in [current] + list(current.parents):
        candidate = parent / "hcode_config.json"
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:

    """Load configuration from a JSON file.

    Args:
        path (Optional[Path]): Path to the config file. If None, the function searches for
            ``hcode_config.json`` starting from the current directory.

    Returns:
        Dict[str, Any]: Parsed configuration dictionary, or an empty dict if no file is found.
    """
    
    if path is None:
        path = find_config_file()
        if path is None:
            return {}

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:

    """Recursively merge two dictionaries.

    Args:
        base (Dict[str, Any]): The original dictionary.
        overrides (Dict[str, Any]): Dictionary with overriding values.

    Returns:
        Dict[str, Any]: The merged dictionary.
    """
    
    result = base.copy()
    for key, value in overrides.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_model_for_size(size: str) -> str:

    """Map a size label to an OpenAI model name.

    Args:
        size (str): One of ``"small"``, ``"medium"`` or ``"large"``.

    Returns:
        str: The corresponding model identifier.
    """
    
    mapping = {"small": "gpt-3.5-turbo", "medium": "gpt-4", "large": "gpt-4-32k"}
    return mapping.get(size.lower(), "gpt-3.5-turbo")


def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:

    """Override configuration values with environment variables.

    Args:
        config (Dict[str, Any]): Original configuration dictionary.

    Returns:
        Dict[str, Any]: Configuration with any ``HCODE_<KEY>`` environment variables applied.
    """
    
    overridden = config.copy()
    for key in config:
        env_key = f"HCODE_{key.upper()}"
        if env_key in os.environ:
            overridden[key] = os.environ[env_key]
    return overridden


def save_config(config: Dict[str, Any], path: Path) -> None:

    """Save the configuration dictionary to a JSON file.

    Args:
        config (Dict[str, Any]): Configuration data to write.
        path (Path): Destination file path. Parent directories are created if needed.
    """
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, sort_keys=True)


def create_default_config() -> Dict[str, Any]:

    return {
        "api_key": "",
        "model": "gpt-3.5-turbo",
        "temperature": 0.7,
        "max_tokens": 1024,
    }


def get_project_instructions(project_path: str) -> str:

    """Retrieve project instructions from common README files.

    Args:
        project_path (str): Path to the project directory.

    Returns:
        str: Contents of the first found instruction file, or an empty string if none exist.
    """
    
    for filename in ("README.md", "INSTRUCTIONS.md"):
        candidate = Path(project_path) / filename
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return ""


def validate_config(config: Dict[str, Any]) -> bool:

    """Validate that required configuration keys are present.

    Args:
        config (Dict[str, Any]): Configuration dictionary to validate.

    Returns:
        bool: ``True`` if all required keys have non‑empty values, otherwise ``False``.
    """
    
    required_keys = ["api_key", "model"]
    for key in required_keys:
        if not config.get(key):
            return False
    return True
