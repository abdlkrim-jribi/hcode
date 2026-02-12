import os
import json
from typing import Any, Dict, List, Optional


def read_json(file_path: str) -> Optional[Dict[str, Any]]:
    """Read a JSON file and return its contents as a dict.
    Returns ``None`` if the file does not exist or cannot be parsed.
    """
    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def write_json(data: Dict[str, Any], file_path: str, *, indent: int = 4) -> bool:
    """Write *data* to *file_path* as JSON.
    Returns ``True`` on success, ``False`` on any IOError.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
        return True
    except OSError:
        return False


def list_files(root_dir: str, extension: str) -> List[str]:
    """Recursively list files under *root_dir* that end with *extension*.
    Returns a list of absolute file paths as strings.
    """
    matches: List[str] = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.endswith(extension):
                matches.append(os.path.abspath(os.path.join(dirpath, fname)))
    return matches
