from __future__ import annotations
from enum import Enum
from rich.text import Text

class StatusType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

def get_icon(name: str) -> str:
    icons = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
    }
    return icons.get(name, "")

def format_status(message: str, status_type: StatusType) -> Text:
    """Return a ``rich.text.Text`` object styled according to *status_type*.
    """
    style_map = {
        StatusType.SUCCESS: "green",
        StatusType.ERROR: "red",
        StatusType.WARNING: "yellow",
        StatusType.INFO: "cyan",
        StatusType.DEBUG: "magenta",
    }
    style = style_map.get(status_type, "white")
    return Text(message, style=style)
