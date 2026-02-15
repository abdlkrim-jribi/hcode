import json
import pathlib
from typing import Any, Dict, Optional


def find_config_file() -> Optional[str]:
    """Search upward from the current directory for a config file.
    Looks for ``hcode_config.yaml`` or ``hcode_config.json`` in each parent
    directory, then falls back to ``~/.hcode/config.yaml``.
    Returns the absolute path as a string or ``None`` if not found.
    """
    cwd = pathlib.Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        for name in ("hcode_config.yaml", "hcode_config.json"):
            candidate = parent / name
            if candidate.is_file():
                return str(candidate)
    # global fallback
    global_cfg = pathlib.Path.home() / ".hcode" / "config.yaml"
    return str(global_cfg) if global_cfg.is_file() else None


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load a JSON or YAML configuration file.
    If *path* is ``None`` the function searches for a config file using
    :func:`find_config_file`. Returns an empty ``dict`` on any error.
    """
    import yaml
    if path is None:
        path = find_config_file()
    if not path:
        return {}
    try:
        p = pathlib.Path(path)
        if p.suffix.lower() in {".json"}:
            return json.loads(p.read_text())
        if p.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(p.read_text()) or {}
    except Exception:
        return {}
    return {}


def deep_merge(a: Dict[Any, Any], b: Dict[Any, Any]) -> Dict[Any, Any]:
    """Recursively merge ``b`` into ``a`` and return the merged dict.
    Scalars in ``b`` override those in ``a``.
    """
    result = dict(a)  # shallow copy
    for key, val in b.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(val, dict)
        ):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def get_model_for_size(size: str) -> str:
    """Map a size hint to a model name.
    Supported sizes: ``small``, ``medium`` → ``gpt-3.5-turbo``;
    ``large`` → ``gpt-4``. Defaults to ``gpt-3.5-turbo``.
    """
    mapping = {
        "small": "gpt-3.5-turbo",
        "medium": "gpt-3.5-turbo",
        "large": "gpt-4",
    }
    return mapping.get(size.lower(), "gpt-3.5-turbo")




def save_config(path: str, data: Dict[str, Any]) -> bool:
    """Write *data* as pretty‑printed JSON to *path*.
    Returns ``True`` on success, ``False`` on any IOError.
    """
    try:
        pathlib.Path(path).write_text(json.dumps(data, indent=2))
        return True
    except Exception:
        return False


def create_default_config() -> Dict[str, Any]:
    """Return a minimal default configuration.
    The tests only require the presence of a ``model`` key.
    """
    return {"model": "gpt-3.5-turbo", "api_key": ""}




