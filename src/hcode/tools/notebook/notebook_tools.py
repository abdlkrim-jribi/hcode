"""
Jupyter Notebook tools for Hcode.
Support for editing and executing notebook cells.
"""

import json
from pathlib import Path
from typing import List, Optional

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class NotebookEditTool(BaseTool):
    """
    Edit Jupyter notebook cells.
    Supports replace, insert, and delete operations.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or Path.cwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("notebook_path", "string", "Absolute path to notebook", required=True),
            ToolParameter("cell_id", "string", "ID of cell to edit", default=None),
            ToolParameter("cell_type", "string", "Type of cell (code or markdown)", default="code"),
            ToolParameter("new_source", "string", "New source for the cell", required=True),
            ToolParameter(
                "edit_mode", "string", "Edit mode (replace, insert, delete)", default="replace"
            ),
        ]

    async def execute(
        self,
        notebook_path: str,
        new_source: str,
        cell_id: Optional[str] = None,
        cell_type: str = "code",
        edit_mode: str = "replace",
    ) -> ToolResult:
        """Edit notebook cell"""
        try:
            path = Path(notebook_path)

            if not path.exists():
                return ToolResult(
                    success=False, output=None, error=f"Notebook not found: {notebook_path}"
                )

            # Read notebook
            with open(path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            if "cells" not in notebook:
                return ToolResult(success=False, output=None, error="Invalid notebook format")

            # Find cell by ID or index
            cell_idx = None
            if cell_id:
                for idx, cell in enumerate(notebook["cells"]):
                    if cell.get("id") == cell_id:
                        cell_idx = idx
                        break

                if cell_idx is None:
                    return ToolResult(
                        success=False, output=None, error=f"Cell not found: {cell_id}"
                    )
            else:
                # Use first cell if no ID specified
                cell_idx = 0

            # Perform edit operation
            if edit_mode == "replace":
                # Replace cell content
                notebook["cells"][cell_idx]["source"] = new_source.splitlines(keepends=True)
                notebook["cells"][cell_idx]["cell_type"] = cell_type
                operation = "replaced"

            elif edit_mode == "insert":
                # Insert new cell after specified cell
                new_cell = {
                    "cell_type": cell_type,
                    "id": f"new_cell_{len(notebook['cells'])}",
                    "metadata": {},
                    "source": new_source.splitlines(keepends=True),
                }

                if cell_type == "code":
                    new_cell["execution_count"] = None
                    new_cell["outputs"] = []

                notebook["cells"].insert(cell_idx + 1, new_cell)
                operation = "inserted"

            elif edit_mode == "delete":
                # Delete cell
                notebook["cells"].pop(cell_idx)
                operation = "deleted"

            else:
                return ToolResult(
                    success=False, output=None, error=f"Invalid edit mode: {edit_mode}"
                )

            # Write notebook back
            with open(path, "w", encoding="utf-8") as f:
                json.dump(notebook, f, indent=1, ensure_ascii=False)

            return ToolResult(
                success=True,
                output=f"Cell {operation} successfully",
                metadata={
                    "notebook_path": str(path),
                    "cell_index": cell_idx,
                    "edit_mode": edit_mode,
                    "total_cells": len(notebook["cells"]),
                },
            )

        except json.JSONDecodeError:
            return ToolResult(success=False, output=None, error="Invalid JSON in notebook file")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class NotebookReadTool(BaseTool):
    """
    Read Jupyter notebook contents.
    Returns all cells with their outputs.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or Path.cwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("notebook_path", "string", "Absolute path to notebook", required=True),
            ToolParameter("include_outputs", "boolean", "Include cell outputs", default=True),
        ]

    async def execute(self, notebook_path: str, include_outputs: bool = True) -> ToolResult:
        """Read notebook contents"""
        try:
            path = Path(notebook_path)

            if not path.exists():
                return ToolResult(
                    success=False, output=None, error=f"Notebook not found: {notebook_path}"
                )

            # Read notebook
            with open(path, "r", encoding="utf-8") as f:
                notebook = json.load(f)

            if "cells" not in notebook:
                return ToolResult(success=False, output=None, error="Invalid notebook format")

            # Format output
            output = f"# Notebook: {path.name}\n\n"

            for idx, cell in enumerate(notebook["cells"], 1):
                cell_type = cell.get("cell_type", "unknown")
                source = "".join(cell.get("source", []))

                output += f"## Cell {idx} ({cell_type})\n\n"
                output += f"```{cell_type}\n{source}\n```\n\n"

                # Include outputs for code cells
                if include_outputs and cell_type == "code":
                    outputs = cell.get("outputs", [])
                    if outputs:
                        output += "**Output:**\n```\n"
                        for out in outputs:
                            if "text" in out:
                                output += "".join(out["text"])
                            elif "data" in out:
                                # Handle rich outputs
                                if "text/plain" in out["data"]:
                                    output += "".join(out["data"]["text/plain"])
                        output += "\n```\n\n"

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "notebook_path": str(path),
                    "total_cells": len(notebook["cells"]),
                    "code_cells": sum(1 for c in notebook["cells"] if c.get("cell_type") == "code"),
                    "markdown_cells": sum(
                        1 for c in notebook["cells"] if c.get("cell_type") == "markdown"
                    ),
                },
            )

        except json.JSONDecodeError:
            return ToolResult(success=False, output=None, error="Invalid JSON in notebook file")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class NotebookExecuteTool(BaseTool):
    """
    Execute Jupyter notebook cells.
    Requires jupyter/nbconvert to be installed.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.CODE_EXECUTION
        self.root_dir = Path(root_dir or Path.cwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("notebook_path", "string", "Absolute path to notebook", required=True),
            ToolParameter("timeout", "integer", "Execution timeout in seconds", default=600),
        ]

    async def execute(self, notebook_path: str, timeout: int = 600) -> ToolResult:
        """Execute notebook"""
        try:
            path = Path(notebook_path)

            if not path.exists():
                return ToolResult(
                    success=False, output=None, error=f"Notebook not found: {notebook_path}"
                )

            # Use nbconvert to execute
            import subprocess

            result = subprocess.run(
                ["jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace", str(path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output="Notebook executed successfully",
                    metadata={"notebook_path": str(path), "execution_time": timeout},
                )
            else:
                return ToolResult(
                    success=False, output=None, error=f"Execution failed: {result.stderr}"
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False, output=None, error=f"Execution timed out after {timeout} seconds"
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                output=None,
                error="Jupyter not installed. Run: pip install jupyter nbconvert",
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
