"""
TODO management system matching Claude Code exactly.

Implements todo tracking, active form generation, and batch updates.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum
import uuid
import re


class TodoStatus(Enum):
    """Todo status matching Claude Code"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


@dataclass
class TodoItem:
    """
    A single todo item.

    Matches Claude Code's todo structure exactly.
    """

    # Todo description (imperative form: "Add tests")
    content: str

    # Current status
    status: TodoStatus = TodoStatus.PENDING

    # Active form (present continuous: "Adding tests")
    active_form: Optional[str] = None

    # Unique identifier
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Creation timestamp
    created_at: datetime = field(default_factory=datetime.now)

    # Completion timestamp
    completed_at: Optional[datetime] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate active form if not provided"""
        if self.active_form is None:
            self.active_form = self.generate_active_form(self.content)

    @staticmethod
    def generate_active_form(content: str) -> str:
        """
        Generate active form from content.

        Converts imperative to present continuous:
        - "Add tests" -> "Adding tests"
        - "Fix bug" -> "Fixing bug"
        - "Run build" -> "Running build"

        Args:
            content: Todo content in imperative form

        Returns:
            Active form in present continuous
        """
        content = content.strip()

        # Common verb transformations
        transformations = {
            # Verbs ending in 'e' - drop 'e' and add 'ing' (process first!)
            r"^(Analyze|Configure|Create|Explore|Investigate|Merge|Optimize|"
            r"Organize|Prepare|Resolve|Write)(\s+.*)$": lambda m: f"{m.group(1).rstrip('e')}ing{m.group(2)}",
            # Regular verbs - add 'ing'
            r"^(Add|Build|Check|Clean|Debug|Deploy|Design|Document|"
            r"Download|Edit|Export|Extract|Format|Generate|Import|Install|"
            r"Load|Modify|Parse|Process|Refactor|Remove|Rename|Review|"
            r"Search|Test|Upload|Validate|Verify)(\s+.*)$": lambda m: f"{m.group(1)}ing{m.group(2)}",
            # Special case for Update (ends in 'e' but needs special handling)
            r"^(Update)(\s+.*)$": lambda m: f"Updating{m.group(2)}",
            # Verbs with consonant doubling
            r"^(Run|Fix|Get|Set|Put)(\s+.*)$": {
                "Run": "Running",
                "Fix": "Fixing",
                "Get": "Getting",
                "Set": "Setting",
                "Put": "Putting",
            },
            # Irregular verbs
            r"^(Make|Do|Go|Read|Write)(\s+.*)$": {
                "Make": "Making",
                "Do": "Doing",
                "Go": "Going",
                "Read": "Reading",
                "Write": "Writing",
            },
        }

        # Try transformations
        for pattern, replacement in transformations.items():
            match = re.match(pattern, content, re.IGNORECASE)
            if match:
                if callable(replacement):
                    return replacement(match)
                elif isinstance(replacement, dict):
                    verb = match.group(1)
                    rest = match.group(2)
                    return replacement[verb] + rest

        # Fallback: just add "ing" to first word
        words = content.split()
        if words:
            first_word = words[0]
            # Simple heuristic: if ends in consonant, double it
            if first_word and first_word[-1] in "bdfgklmnprst" and len(first_word) > 2:
                active_first = first_word + first_word[-1] + "ing"
            elif first_word.endswith("e"):
                active_first = first_word[:-1] + "ing"
            else:
                active_first = first_word + "ing"

            return active_first + " " + " ".join(words[1:])

        return content

    def mark_in_progress(self) -> None:
        """Mark todo as in progress"""
        self.status = TodoStatus.IN_PROGRESS

    def mark_completed(self) -> None:
        """Mark todo as completed"""
        self.status = TodoStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_blocked(self, reason: Optional[str] = None) -> None:
        """
        Mark todo as blocked.

        Args:
            reason: Optional reason for blocking
        """
        self.status = TodoStatus.BLOCKED
        if reason:
            self.metadata["blocked_reason"] = reason

    def mark_skipped(self, reason: Optional[str] = None) -> None:
        """
        Mark todo as skipped.

        Args:
            reason: Optional reason for skipping
        """
        self.status = TodoStatus.SKIPPED
        if reason:
            self.metadata["skipped_reason"] = reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status.value,
            "activeForm": self.active_form,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation"""
        status_emoji = {
            TodoStatus.PENDING: "○",
            TodoStatus.IN_PROGRESS: "◐",
            TodoStatus.COMPLETED: "●",
            TodoStatus.BLOCKED: "⊗",
            TodoStatus.SKIPPED: "⊘",
        }
        emoji = status_emoji.get(self.status, "○")
        return f"{emoji} {self.content}"


class TodoManager:
    """
    Manages todo list with batch updates.

    Matches Claude Code's todo management behavior exactly.
    """

    def __init__(self):
        """Initialize todo manager"""
        self.todos: List[TodoItem] = []
        self.listeners: List[Callable[[List[TodoItem]], None]] = []

    def add_listener(self, listener: Callable[[List[TodoItem]], None]) -> None:
        """
        Add a listener for todo updates.

        Args:
            listener: Callback function for todo updates
        """
        self.listeners.append(listener)

    def notify_listeners(self) -> None:
        """Notify all listeners of todo updates"""
        for listener in self.listeners:
            try:
                listener(self.todos)
            except Exception as e:
                print(f"Listener error: {e}")

    def batch_update(self, todos: List[Dict[str, Any]]) -> None:
        """
        Batch update todos (Claude Code pattern).

        Replaces entire todo list with new list.

        Args:
            todos: List of todo dictionaries with content, status, activeForm
        """
        # Clear existing todos
        self.todos.clear()

        # Add new todos
        for todo_data in todos:
            todo = TodoItem(
                content=todo_data["content"],
                status=TodoStatus(todo_data["status"]),
                active_form=todo_data.get("activeForm"),
            )
            self.todos.append(todo)

        # Verify single in-progress rule
        in_progress_count = sum(1 for todo in self.todos if todo.status == TodoStatus.IN_PROGRESS)

        if in_progress_count != 1:
            # This is a warning condition - Claude Code should have exactly one
            print(f"Warning: {in_progress_count} todos in progress (should be 1)")

        # Notify listeners
        self.notify_listeners()

    def get_all(self) -> List[TodoItem]:
        """Get all todos"""
        return self.todos.copy()

    def get_by_status(self, status: TodoStatus) -> List[TodoItem]:
        """
        Get todos by status.

        Args:
            status: Status to filter by

        Returns:
            List of todos with that status
        """
        return [todo for todo in self.todos if todo.status == status]

    def get_current(self) -> Optional[TodoItem]:
        """
        Get current in-progress todo.

        Returns:
            Current todo or None
        """
        in_progress = self.get_by_status(TodoStatus.IN_PROGRESS)
        return in_progress[0] if in_progress else None

    def get_progress(self) -> Dict[str, int]:
        """
        Get progress statistics.

        Returns:
            Dictionary with counts by status
        """
        stats = {
            "total": len(self.todos),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "blocked": 0,
            "skipped": 0,
        }

        for todo in self.todos:
            stats[todo.status.value] += 1

        # Calculate percentage
        if stats["total"] > 0:
            stats["percent_complete"] = int((stats["completed"] / stats["total"]) * 100)
        else:
            stats["percent_complete"] = 0

        return stats

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """
        Convert all todos to dictionary list.

        Returns:
            List of todo dictionaries
        """
        return [todo.to_dict() for todo in self.todos]

    def __str__(self) -> str:
        """String representation"""
        stats = self.get_progress()
        return f"TodoManager({stats['completed']}/{stats['total']} completed)"
