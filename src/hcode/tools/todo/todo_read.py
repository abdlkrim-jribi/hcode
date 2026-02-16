"""
Todo reading tool for Hcode.
Strictly aligns with Antigravity standards by reading from task.md.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class TodoReadTool(BaseTool):
    """
    Read the current task list (todos).
    This tool reads the physical task.md file to get the current state of tasks.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.name = "todoreadtool"
        self.category = ToolCategory.PLANNING
        self.root_dir = Path(root_dir or os.getcwd())
        self.task_file = self.root_dir / ".hcode" / "task.md"

    def get_parameters(self) -> List[ToolParameter]:
        return []  # No parameters needed

    async def execute(self, **kwargs) -> ToolResult:
        """Read todos from task.md"""
        try:
            if not self.task_file.exists():
                return ToolResult(
                    success=True,
                    output="No task list found (task.md does not exist).",
                    metadata={"todos": [], "exists": False}
                )

            content = self.task_file.read_text(encoding="utf-8")
            todos = self._parse_task_md(content)

            return ToolResult(
                success=True,
                output=f"Read {len(todos)} todo(s) from {self.task_file.name}",
                metadata={"todos": todos, "exists": True}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _parse_task_md(self, content: str) -> List[Dict[str, Any]]:
        """Parse task.md content into todo dictionaries"""
        todos = []
        for line in content.splitlines():
            match = re.match(r"^\s*-\s*\[([\s/xX])\]\s*(.*)$", line)
            if match:
                status_char = match.group(1).lower()
                todo_content = match.group(2).strip()

                status = "pending"
                if status_char == "x":
                    status = "completed"
                elif status_char == "/":
                    status = "in_progress"

                todos.append({
                    "content": todo_content,
                    "status": status
                })
        return todos
