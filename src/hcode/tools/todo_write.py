"""
TodoWrite tool matching Claude Code exactly.

Handles batch todo updates with validation.
"""

from typing import Any, Dict, List, Optional
import json

from .base_tool import BaseTool, ToolParameter, ToolResult
from ..agent.todo import TodoManager, TodoStatus


class TodoWriteTool(BaseTool):
    """
    TodoWrite tool for managing task lists.

    Matches Claude Code's TodoWrite behavior exactly:
    - Batch updates (replace entire list)
    - Validates single in-progress rule
    - Generates active forms automatically
    - Notifies listeners of changes
    """

    name = "TodoWrite"
    description = """Use this tool to create and manage a structured task list for your current coding session.

IMPORTANT: Match Claude Code's exact behavior:
1. Always send the COMPLETE todo list (not just changes)
2. Exactly ONE todo must be in_progress at a time
3. Each todo must have: content (imperative), status, activeForm (present continuous)
4. Mark completed IMMEDIATELY after finishing (don't batch)
5. Active form examples: "Add tests" -> "Adding tests", "Fix bug" -> "Fixing bug"

When to use:
- Complex multi-step tasks (3+ steps)
- Non-trivial tasks requiring planning
- User provides multiple tasks
- After receiving new instructions
- When starting work (mark in_progress BEFORE)
- After completing (mark completed and move to next)

When NOT to use:
- Single straightforward task
- Trivial task (< 3 steps)
- Purely conversational tasks

Required format:
{
  "todos": [
    {
      "content": "Imperative form (e.g., 'Add tests')",
      "status": "pending|in_progress|completed|blocked|skipped",
      "activeForm": "Present continuous (e.g., 'Adding tests')"
    }
  ]
}

Status rules:
- pending: Not yet started
- in_progress: Currently working (ONLY ONE at a time)
- completed: Finished and verified
- blocked: Cannot proceed (create new task to unblock)
- skipped: Intentionally skipped

Completion rules:
- ONLY mark completed when FULLY accomplished
- If errors/blockers: keep in_progress, create new task
- Never mark completed if: tests failing, partial implementation, unresolved errors
"""

    parameters = {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "Complete list of todos (replace entire list)",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Todo description (imperative form)",
                            "minLength": 1
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "blocked", "skipped"],
                            "description": "Current status"
                        },
                        "activeForm": {
                            "type": "string",
                            "description": "Present continuous form",
                            "minLength": 1
                        }
                    },
                    "required": ["content", "status", "activeForm"]
                }
            }
        },
        "required": ["todos"]
    }

    def __init__(self, todo_manager: Optional[TodoManager] = None):
        """
        Initialize TodoWrite tool.

        Args:
            todo_manager: Optional TodoManager instance
        """
        super().__init__()
        self.name = "TodoWrite"  # Override default name
        self.todo_manager = todo_manager or TodoManager()

    @property
    def todos(self) -> List[Dict[str, Any]]:
        """
        Get todos as a list of dicts (compatibility property).

        Returns:
            List of todo dictionaries
        """
        return self.todo_manager.to_dict_list()

    def get_parameters(self) -> List[ToolParameter]:
        """Get tool parameters"""
        return [
            ToolParameter(
                name="todos",
                type="array",
                description="Complete list of todos (replace entire list)",
                required=True
            )
        ]

    async def execute(self, todos: List[Dict[str, Any]], **kwargs) -> ToolResult:
        """
        Execute todo batch update.

        Args:
            todos: List of todo dictionaries
            **kwargs: Additional parameters

        Returns:
            Execution result
        """
        try:
            # Validate todos format
            validation_result = self._validate_todos(todos)
            if not validation_result["valid"]:
                return ToolResult(
                    success=False,
                    output=None,
                    error=validation_result["error"]
                )

            # Perform batch update
            self.todo_manager.batch_update(todos)

            # Get progress stats
            stats = self.todo_manager.get_progress()

            # Get the updated todo list
            updated_todos = self.todo_manager.to_dict_list()

            # Emit todo update event for real-time UI updates
            try:
                from .tool_callbacks import get_callback_manager, ToolEventType, ToolEvent
                callback_manager = get_callback_manager()
                callback_manager.emit(ToolEvent(
                    event_type=ToolEventType.TODO_UPDATE,
                    tool_name="TodoWrite",
                    arguments={"todos": todos},
                    todos=updated_todos,
                    metadata={"stats": stats}
                ))
            except ImportError:
                pass  # Callbacks not available, continue without

            return ToolResult(
                success=True,
                output={
                    "message": "Todos have been modified successfully. Ensure that you continue to use the todo list to track your progress. Please proceed with the current tasks if applicable",
                    "stats": stats,
                    "todos": updated_todos
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to update todos: {str(e)}"
            )

    def _validate_todos(self, todos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate todos list.

        Checks:
        - Required fields present
        - Valid status values
        - Single in-progress rule
        - Active form provided

        Args:
            todos: List of todo dictionaries

        Returns:
            Validation result with "valid" and optional "error"
        """
        if not isinstance(todos, list):
            return {
                "valid": False,
                "error": "Todos must be a list"
            }

        # Count in-progress todos
        in_progress_count = 0

        for i, todo in enumerate(todos):
            # Check required fields
            if not isinstance(todo, dict):
                return {
                    "valid": False,
                    "error": f"Todo at index {i} is not a dictionary"
                }

            for field in ["content", "status", "activeForm"]:
                if field not in todo:
                    return {
                        "valid": False,
                        "error": f"Todo at index {i} missing required field: {field}"
                    }

            # Validate status
            try:
                status = TodoStatus(todo["status"])
                if status == TodoStatus.IN_PROGRESS:
                    in_progress_count += 1
            except ValueError:
                return {
                    "valid": False,
                    "error": f"Todo at index {i} has invalid status: {todo['status']}"
                }

            # Validate content not empty
            if not todo["content"].strip():
                return {
                    "valid": False,
                    "error": f"Todo at index {i} has empty content"
                }

            # Validate activeForm not empty
            if not todo["activeForm"].strip():
                return {
                    "valid": False,
                    "error": f"Todo at index {i} has empty activeForm"
                }

        # Validate single in-progress rule
        if in_progress_count == 0:
            return {
                "valid": False,
                "error": "Must have exactly ONE todo in_progress (found 0). Mark a todo as in_progress before starting work."
            }

        if in_progress_count > 1:
            return {
                "valid": False,
                "error": f"Must have exactly ONE todo in_progress (found {in_progress_count}). Only one task should be active at a time."
            }

        return {"valid": True}

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
