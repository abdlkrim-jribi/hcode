"""
MCP Server Quick-Start Template
================================
A minimal, production-ready MCP server template.

Usage:
    python quickstart_server.py

Test with MCP Inspector:
    npx @modelcontextprotocol/inspector python quickstart_server.py
"""
import json
import logging
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create server
mcp = FastMCP(
    name="quickstart",
    version="1.0.0",
)


# --- Tools ---

@mcp.tool()
def echo(message: str) -> str:
    """Echo a message back.

    Args:
        message: The message to echo.
    """
    logger.info(f"echo called with: {message}")
    return message


@mcp.tool()
def list_directory(
    path: str = ".",
    pattern: str = "*",
    max_results: int = 50,
) -> str:
    """List files in a directory.

    Args:
        path: Directory path to list.
        pattern: Glob pattern to filter files.
        max_results: Maximum number of results.
    """
    root = Path(path).resolve()

    if not root.exists():
        return json.dumps({"error": f"Path not found: {path}"})
    if not root.is_dir():
        return json.dumps({"error": f"Not a directory: {path}"})

    entries = []
    for entry in sorted(root.glob(pattern))[:max_results]:
        entries.append({
            "name": entry.name,
            "type": "directory" if entry.is_dir() else "file",
            "size": entry.stat().st_size if entry.is_file() else None,
        })

    return json.dumps({"path": str(root), "entries": entries})


@mcp.tool()
def read_file(file_path: str, max_chars: int = 10000) -> str:
    """Read the contents of a text file.

    Args:
        file_path: Path to the file to read.
        max_chars: Maximum characters to return.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        return json.dumps({"error": f"File not found: {file_path}"})
    if not path.is_file():
        return json.dumps({"error": f"Not a file: {file_path}"})

    try:
        content = path.read_text(encoding="utf-8")
        truncated = len(content) > max_chars
        return json.dumps({
            "path": str(path),
            "content": content[:max_chars],
            "truncated": truncated,
            "total_chars": len(content),
        })
    except UnicodeDecodeError:
        return json.dumps({"error": "Cannot read binary file as text"})


# --- Resources ---

@mcp.resource("info://server")
def server_info() -> str:
    """Return server metadata."""
    return json.dumps({
        "name": "quickstart",
        "version": "1.0.0",
        "tools": ["echo", "list_directory", "read_file"],
    })


# --- Entry Point ---

def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
