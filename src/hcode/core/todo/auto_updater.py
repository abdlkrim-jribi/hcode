"""
Todo Auto-Updater for Hcode Agent.

Simplified, intelligent todo management using semantic word matching
instead of hardcoded keyword dictionaries.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple


class TodoAutoUpdater:
    """
    Intelligent todo auto-updater using semantic matching.
    
    Design principles:
    - No hardcoded keyword dictionaries
    - Simple word overlap for matching
    - Minimal logic, maximum clarity
    """

    def __init__(
            self,
            tool_manager: Any,
            console: Any = None,
            icons: Any = None,
    ):
        self.tool_manager = tool_manager
        self.console = console
        self.icons = icons

    def _get_todos(self) -> Optional[list]:
        """Get the current todo list."""
        try:
            tool = self.tool_manager.get_tool("TodoWrite")
            if tool and hasattr(tool, "todos"):
                return tool.todos
        except:
            pass
        return None

    def _get_info(self, todo) -> Tuple[str, str]:
        """Extract content and status from a todo."""
        if hasattr(todo, "content"):
            return todo.content.lower(), getattr(todo, "status", "pending")
        if isinstance(todo, dict):
            return todo.get("content", "").lower(), todo.get("status", "pending")
        return "", "pending"

    def _set_status(self, todos: list, idx: int, status: str) -> None:
        """Set status of a todo."""
        if hasattr(todos[idx], "status"):
            todos[idx].status = status
        elif isinstance(todos[idx], dict):
            todos[idx]["status"] = status

    # =========================================================================
    # Public API
    # =========================================================================

    def get_completion_state(self) -> Dict[str, int]:
        """Get counts of total and completed todos."""
        todos = self._get_todos()
        if not todos:
            return {"total": 0, "completed": 0}

        completed = sum(1 for t in todos if self._get_info(t)[1] == "completed")
        return {"total": len(todos), "completed": completed}

    def has_pending_todos(self) -> bool:
        """Check if there are incomplete todos."""
        todos = self._get_todos()
        if not todos:
            return False
        return any(self._get_info(t)[1] in ["pending", "in_progress"] for t in todos)

    def auto_update(self, action: Dict[str, Any]) -> bool:
        """
        Update todos based on a completed action.
        
        Uses intelligent word matching instead of hardcoded keywords.
        """
        if not action.get("success"):
            return False

        tool_name = action.get("tool", "").lower()
        if tool_name in ("todowrite", "todo_write", "todo"):
            return False

        todos = self._get_todos()
        if not todos:
            return False

        try:
            # Build action description from tool + args
            action_words = self._extract_action_words(tool_name, action.get("args", {}))

            # Find best matching todo
            best_idx = self._match_to_todo(todos, action_words)

            if best_idx is not None:
                self._set_status(todos, best_idx, "completed")
                self._advance_next(todos, best_idx)
                self._show_progress(todos, best_idx)
                return True

            return False

        except Exception as e:
            if self.console:
                self.console.print(f"[dim red]Todo update error: {e}[/dim red]")
            return False

    def _extract_action_words(self, tool_name: str, args: dict) -> set:
        """Extract meaningful words from tool action."""
        words = set()

        # Add tool name parts
        words.update(tool_name.replace("_", " ").split())

        # Add file path parts
        for key in ("file_path", "path", "file", "directory"):
            if key in args and args[key]:
                path = Path(str(args[key]))
                words.add(path.name.lower())
                words.update(p.lower() for p in path.parts if len(p) > 2)

        # Add other string args
        for key, val in args.items():
            if isinstance(val, str) and len(val) < 100:
                words.update(val.lower().split()[:5])

        return words

    def _match_to_todo(self, todos: list, action_words: set) -> Optional[int]:
        """Find best matching todo using word overlap."""
        best_idx = None
        best_score = 0

        for i, todo in enumerate(todos):
            content, status = self._get_info(todo)
            if status == "completed":
                continue

            # Calculate word overlap
            todo_words = set(content.split())
            overlap = len(action_words & todo_words)

            # Bonus for in_progress
            if status == "in_progress":
                overlap += 1

            if overlap > best_score:
                best_score = overlap
                best_idx = i

        # Require at least 1 word match
        return best_idx if best_score >= 1 else None

    def _advance_next(self, todos: list, completed_idx: int) -> None:
        """Advance next pending todo to in_progress."""
        for i in range(completed_idx + 1, len(todos)):
            if self._get_info(todos[i])[1] == "pending":
                self._set_status(todos, i, "in_progress")
                break

    def _show_progress(self, todos: list, idx: int) -> None:
        """Display progress update."""
        if not self.console:
            return

        completed = sum(1 for t in todos if self._get_info(t)[1] == "completed")
        total = len(todos)
        icon = getattr(self.icons, "SUCCESS", "✓") if self.icons else "✓"
        self.console.print(
            f"[dim cyan][{icon}] Todo {idx + 1}/{total}: completed ({completed}/{total})[/dim cyan]"
        )
