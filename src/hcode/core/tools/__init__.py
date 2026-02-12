"""
Hcode Core Tools Module.

Provides tool call parsing and processing for the Hcode agent.
"""

from .tool_call_parser import ToolCallParser, VALID_TOOLS

# Alias for compatibility
DEFAULT_VALID_TOOLS = VALID_TOOLS

__all__ = [
    "ToolCallParser",
    "VALID_TOOLS",
    "DEFAULT_VALID_TOOLS",
]
