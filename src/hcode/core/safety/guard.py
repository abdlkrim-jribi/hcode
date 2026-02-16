"""
SafetyGuard for Hcode.
Provides backup, rollback, and safety checks for file operations.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class SafetyGuard:
    """Manages safe file operations with backup and rollback"""

    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize SafetyGuard.

        Args:
            root_dir: Root directory (defaults to current directory)
        """
        self.root_dir = Path(root_dir or os.getcwd())
        self.backup_dir = self.root_dir / ".hcode" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.current_transaction: Optional[str] = None
        self.transaction_history: Dict[str, Dict] = {}
        self._load_history()

    def _load_history(self):
        """Load transaction history from disk"""
        history_file = self.backup_dir / "history.json"

        if history_file.exists():
            with open(history_file, "r") as f:
                self.transaction_history = json.load(f)

    def _save_history(self):
        """Save transaction history to disk"""
        history_file = self.backup_dir / "history.json"

        with open(history_file, "w") as f:
            json.dump(self.transaction_history, f, indent=2)

    def start_transaction(self, description: str = "") -> str:
        """
        Start a new safety transaction.

        Args:
            description: Description of the transaction

        Returns:
            Transaction ID
        """
        transaction_id = f"tx_{int(time.time() * 1000)}"

        self.current_transaction = transaction_id
        self.transaction_history[transaction_id] = {
            "id": transaction_id,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "files_backed_up": [],
            "files_created": [],
            "status": "in_progress",
        }

        self._save_history()
        return transaction_id

    def commit_transaction(self) -> bool:
        """
        Commit the current transaction.

        Returns:
            True if successful
        """
        if not self.current_transaction:
            return False

        self.transaction_history[self.current_transaction]["status"] = "committed"
        self._save_history()

        self.current_transaction = None
        return True

    def rollback_transaction(self, transaction_id: Optional[str] = None) -> bool:
        """
        Rollback a transaction.

        Args:
            transaction_id: Transaction to rollback (defaults to current)

        Returns:
            True if successful
        """
        tx_id = transaction_id or self.current_transaction

        if not tx_id or tx_id not in self.transaction_history:
            return False

        transaction = self.transaction_history[tx_id]

        # Delete created files
        for file_path in transaction["files_created"]:
            path = Path(file_path)
            if path.exists():
                path.unlink()

        # Mark transaction as rolled back
        transaction["status"] = "rolled_back"
        transaction["rollback_time"] = datetime.now().isoformat()

        self._save_history()

        if tx_id == self.current_transaction:
            self.current_transaction = None

        return True
