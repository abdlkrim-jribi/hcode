"""
Todo management tool for Hcode.
Strictly aligns with Antigravity standards by syncing with task.md.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import os

from hcode.tools.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory
from hcode.agent.todo import TodoManager, TodoStatus

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
            
            return True
        except Exception:
            return False

    @property
    def todos(self) -> List[Dict[str, Any]]:
        """Return todos as list of dicts (for compatibility)"""
        return self.todo_manager.to_dict_list()
