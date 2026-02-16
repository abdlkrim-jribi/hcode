"""
Session Manager for Hcode.
Handles session-level permissions and state for tools.
"""

import json
import logging
import os
from pathlib import Path
from typing import Set, Tuple

logger = logging.getLogger(__name__)


class SessionConfirmationManager:
    """
    Manages session-level permissions for tools.
    Allows tools to be "Session-Accepted" so the user doesn't need to approve
    every single action for the same file/context within a session.
    
    Persists state to .hcode/session_permissions.json to survive process restarts.
    """

    def __init__(self):
        # Set of (tool_name, target_path) that are allowed for this session
        self._allowed_actions: Set[Tuple[str, str]] = set()

        # Files that are always allowed to be edited/written without confirmation
        self._auto_allow_files = {
            "implementation_plan.md",
            "hcode.md",
            "task.md",
            "memory.md",
            "walkthrough.md"
        }

        self._session_file = Path(os.getcwd()) / ".hcode" / "session_permissions.json"
        self._load_state()

    def _load_state(self) -> None:
        """Load permissions from file."""
        try:
            if self._session_file.exists():
                with open(self._session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert list of lists back to set of tuples
                    self._allowed_actions = set(tuple(item) for item in data)
                logger.debug(f"Loaded {len(self._allowed_actions)} permissions from {self._session_file}")
        except Exception as e:
            logger.warning(f"Failed to load session state: {e}")
            # Start fresh if load fails
            self._allowed_actions = set()

    def _save_state(self) -> None:
        """Save permissions to file."""
        try:
            # Create directory if needed
            self._session_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert set of tuples to list of lists for JSON
            data = [list(item) for item in self._allowed_actions]

            with open(self._session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved session state to {self._session_file}")
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")

    def grant_permission(self, tool_name: str, target_path: str) -> None:
        """
        Grant permission for a tool to operate on a specific path for the duration of the session.
        
        Args:
            tool_name: Name of the tool (e.g., "Edit", "Write")
            target_path: Absolute path to the file or directory
        """
        # Normalize path
        try:
            abs_path = str(Path(target_path).resolve())
        except Exception:
            abs_path = target_path

        logger.info(f"Granting session permission for {tool_name} on {abs_path}")
        self._allowed_actions.add((tool_name, abs_path))
        self._save_state()

    def check_permission(self, tool_name: str, target_path: str) -> bool:
        """
        Check if a tool has permission to operate on a specific path.
        
        Args:
            tool_name: Name of the tool
            target_path: Absolute path to the file
            
        Returns:
            True if permission is granted, False otherwise
        """
        try:
            abs_path = str(Path(target_path).resolve())
            filename = Path(target_path).name
        except Exception:
            abs_path = target_path
            filename = ""

        # Check whitelist first
        if filename in self._auto_allow_files:
            return True

        return (tool_name, abs_path) in self._allowed_actions


# Global instance
_session_confirmation_manager = SessionConfirmationManager()


def get_session_manager() -> SessionConfirmationManager:
    """Get the global session confirmation manager instance."""
    return _session_confirmation_manager
