"""
Todo management tool for Hcode.
Strictly aligns with Antigravity standards by syncing with task.md.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from hcode.core.todo import TodoManager, TodoStatus
from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class TodoWriteTool(BaseTool):
    """
    Update the task list (todos).
    This tool synchronizes the agent's internal task state with the physical task.md file.
    """

    def __init__(self, todo_manager: Optional[TodoManager] = None, root_dir: Optional[str] = None):
        super().__init__()
        self.name = "todowritetool"
        self.category = ToolCategory.PLANNING
        self.todo_manager = todo_manager or TodoManager()
        self.root_dir = Path(root_dir or os.getcwd())
        self.task_file = self.root_dir / ".hcode" / "task.md"
        self._last_mtime = 0.0

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                "todos",
                "array",
                "List of todo objects with 'content', 'status', and optionally 'activeForm'",
                required=True,
            ),
        ]

    async def execute(self, todos: List[Dict[str, Any]], **kwargs) -> ToolResult:
        """Update todos and sync to task.md"""
        try:
            # Update internal manager
            self.todo_manager.batch_update(todos)

            # Sync to task.md
            success = self._sync_to_file()

            if success:
                return ToolResult(
                    success=True,
                    output=f"Successfully updated {len(todos)} todo(s) and synced to {self.task_file.name}",
                    metadata={"count": len(todos), "file_synced": True}
                )
            else:
                return ToolResult(
                    success=True,
                    output=f"Updated {len(todos)} todo(s) in-memory, but failed to sync to file.",
                    metadata={"count": len(todos), "file_synced": False}
                )


        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _sync_to_file(self) -> bool:
        """Sync current todos to .hcode/task.md in Antigravity format"""
        try:
            # Ensure directory exists
            self.task_file.parent.mkdir(parents=True, exist_ok=True)

            content = "# Task Checklist\n\n"

            for todo in self.todo_manager.get_all():
                status_char = " "
                if todo.status == TodoStatus.COMPLETED:
                    status_char = "x"
                elif todo.status == TodoStatus.IN_PROGRESS:
                    status_char = "/"

                content += f"- [{status_char}] {todo.content}\n"

            with open(self.task_file, "w", encoding="utf-8") as f:
                f.write(content)

            # Update mtime after write to avoid unnecessary reload
            if self.task_file.exists():
                self._last_mtime = self.task_file.stat().st_mtime

            return True
        except Exception:
            return False

    def _refresh_from_file(self):
        """Reload todos from task.md if file has changed"""
        try:
            if not self.task_file.exists():
                return

            current_mtime = self.task_file.stat().st_mtime
            if current_mtime == self._last_mtime:
                return

            # File has changed, reload
            content = self.task_file.read_text(encoding="utf-8")

            # Simple parsing (duplicated from TodoReadTool to avoid circular deps/complexity)
            import re
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

            if todos:
                # Update manager without triggering sync back to file
                self.todo_manager.batch_update(todos)

            self._last_mtime = current_mtime

        except Exception:
            # If read fails, stick with current state
            pass

    @property
    def todos(self) -> List[Dict[str, Any]]:
        """Return todos as list of dicts (for compatibility)"""
        # Auto-refresh if file changed
        self._refresh_from_file()
        return self.todo_manager.to_dict_list()
