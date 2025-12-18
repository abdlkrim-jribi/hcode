

import os
import json
from typing import Any, Dict, List, Optional


def read_json(file_path: str) -> Optional[Dict[str, Any]]:
    """Read a JSON file and return its contents as a dictionary.

    Args:
        file_path (str): Path to the JSON file to read.

    Returns:
        Optional[Dict[str, Any]]: The parsed JSON data if the file exists and is valid,
        otherwise ``None``.
    """


    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def write_json(data: Dict[str, Any], file_path: str, *, indent: int = 4) -> bool:
    """Write a dictionary to a JSON file.

    Args:
        data (Dict[str, Any]): The data to serialize to JSON.
        file_path (str): Destination file path.
        indent (int, optional): Number of spaces for indentation. Defaults to 4.

    Returns:
        bool: ``True`` if the file was written successfully, ``False`` otherwise.
    """


    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
        return True
    except OSError:
        return False


def list_files(directory: str, extension: Optional[str] = None) -> List[str]:
    """List files in a directory optionally filtered by extension.

    Args:
        directory (str): Path to the directory to search.
        extension (Optional[str], optional): File extension to filter by (e.g., ``".json"``). If ``None``, all files are returned. Defaults to ``None``.

    Returns:
        List[str]: A list of file paths matching the criteria.
    """


    matched_files: List[str] = []
    for root, _, files in os.walk(directory):
        for name in files:
            if extension is None or name.lower().endswith(extension.lower()):
                matched_files.append(os.path.join(root, name))
    return matched_files
