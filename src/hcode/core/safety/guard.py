"""
SafetyGuard for Hcode.
Provides backup, rollback, and safety checks for file operations.
"""

import hashlib
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


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

        # Dangerous patterns to watch for
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",  # Recursive delete from root
            r"DROP\s+DATABASE",  # Database drop
            r"DELETE\s+FROM.*WHERE\s+1\s*=\s*1",  # Delete all rows
            r"\.env",  # Environment files
            r"credentials",  # Credential files
            r"secrets",  # Secret files
        ]

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
            "files_deleted": [],
            "status": "in_progress",
        }

        self._save_history()
        return transaction_id

    def backup_file(self, file_path: str) -> str:
        """
        Create backup of a file.

        Args:
            file_path: Path to file to backup

        Returns:
            Backup path

        Raises:
            ValueError: If no transaction is active
        """
        if not self.current_transaction:
            raise ValueError("No active transaction. Call start_transaction() first.")

        source_path = Path(file_path)

        if not source_path.exists():
            return ""  # Nothing to backup

        # Create backup directory structure
        rel_path = (
            source_path.relative_to(self.root_dir)
            if source_path.is_relative_to(self.root_dir)
            else source_path
        )
        backup_path = self.backup_dir / self.current_transaction / rel_path

        # Create parent directories
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(source_path, backup_path)

        # Record in transaction
        self.transaction_history[self.current_transaction]["files_backed_up"].append(
            {
                "original": str(file_path),
                "backup": str(backup_path),
                "hash": self._hash_file(source_path),
            }
        )

        self._save_history()
        return str(backup_path)

    def record_creation(self, file_path: str):
        """
        Record that a file was created in this transaction.

        Args:
            file_path: Path to created file
        """
        if not self.current_transaction:
            raise ValueError("No active transaction")

        self.transaction_history[self.current_transaction]["files_created"].append(str(file_path))
        self._save_history()

    def record_deletion(self, file_path: str):
        """
        Record that a file was deleted in this transaction.

        Args:
            file_path: Path to deleted file
        """
        if not self.current_transaction:
            raise ValueError("No active transaction")

        # Backup before deletion
        if Path(file_path).exists():
            self.backup_file(file_path)

        self.transaction_history[self.current_transaction]["files_deleted"].append(str(file_path))
        self._save_history()

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

        # Restore backed up files
        for backup_info in transaction["files_backed_up"]:
            backup_path = Path(backup_info["backup"])
            original_path = Path(backup_info["original"])

            if backup_path.exists():
                # Restore original file
                shutil.copy2(backup_path, original_path)

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

    def validate_operation(
        self, operation: str, file_path: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Validate if an operation is safe.

        Args:
            operation: Operation description or command
            file_path: File path involved in operation

        Returns:
            Tuple of (is_safe, reason)
        """
        import re

        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, operation, re.IGNORECASE):
                return False, f"Operation matches dangerous pattern: {pattern}"

        # Check for sensitive files
        if file_path:
            path_lower = file_path.lower()
            sensitive_files = [".env", "credentials", "secrets", "password", "token", "api_key"]

            for sensitive in sensitive_files:
                if sensitive in path_lower:
                    return False, f"Operation involves sensitive file: {file_path}"

        # Check if file is in system directories
        if file_path:
            path = Path(file_path)
            system_dirs = ["/usr", "/bin", "/sbin", "/etc", "C:\\Windows", "C:\\Program Files"]

            for sys_dir in system_dirs:
                if str(path).startswith(sys_dir):
                    return False, f"Operation in system directory: {sys_dir}"

        return True, "Operation appears safe"

    def create_checkpoint(self, name: str, files: List[str]) -> str:
        """
        Create a named checkpoint of specific files.

        Args:
            name: Checkpoint name
            files: List of files to checkpoint

        Returns:
            Checkpoint ID
        """
        checkpoint_id = f"cp_{name}_{int(time.time())}"
        checkpoint_dir = self.backup_dir / "checkpoints" / checkpoint_id

        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_info = {
            "id": checkpoint_id,
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "files": [],
        }

        for file_path in files:
            source = Path(file_path)
            if source.exists():
                rel_path = (
                    source.relative_to(self.root_dir)
                    if source.is_relative_to(self.root_dir)
                    else source
                )
                dest = checkpoint_dir / rel_path

                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)

                checkpoint_info["files"].append(
                    {"path": str(file_path), "hash": self._hash_file(source)}
                )

        # Save checkpoint info
        with open(checkpoint_dir / "info.json", "w") as f:
            json.dump(checkpoint_info, f, indent=2)

        return checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Restore from a checkpoint.

        Args:
            checkpoint_id: Checkpoint to restore

        Returns:
            True if successful
        """
        checkpoint_dir = self.backup_dir / "checkpoints" / checkpoint_id

        if not checkpoint_dir.exists():
            return False

        info_file = checkpoint_dir / "info.json"
        if not info_file.exists():
            return False

        with open(info_file, "r") as f:
            checkpoint_info = json.load(f)

        # Restore each file
        for file_info in checkpoint_info["files"]:
            original_path = Path(file_info["path"])
            rel_path = (
                original_path.relative_to(self.root_dir)
                if original_path.is_relative_to(self.root_dir)
                else original_path
            )
            backup_path = checkpoint_dir / rel_path

            if backup_path.exists():
                original_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, original_path)

        return True

    def list_checkpoints(self) -> List[Dict]:
        """
        List all available checkpoints.

        Returns:
            List of checkpoint information
        """
        checkpoint_base = self.backup_dir / "checkpoints"

        if not checkpoint_base.exists():
            return []

        checkpoints = []

        for checkpoint_dir in checkpoint_base.iterdir():
            if checkpoint_dir.is_dir():
                info_file = checkpoint_dir / "info.json"
                if info_file.exists():
                    with open(info_file, "r") as f:
                        checkpoints.append(json.load(f))

        return sorted(checkpoints, key=lambda x: x["timestamp"], reverse=True)

    def list_transactions(self, status: Optional[str] = None) -> List[Dict]:
        """
        List transactions.

        Args:
            status: Filter by status (in_progress, committed, rolled_back)

        Returns:
            List of transactions
        """
        transactions = list(self.transaction_history.values())

        if status:
            transactions = [t for t in transactions if t["status"] == status]

        return sorted(transactions, key=lambda x: x["timestamp"], reverse=True)

    def cleanup_old_backups(self, days: int = 7):
        """
        Clean up backups older than specified days.

        Args:
            days: Number of days to keep backups
        """
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        for tx_id, transaction in list(self.transaction_history.items()):
            tx_time = datetime.fromisoformat(transaction["timestamp"]).timestamp()

            if tx_time < cutoff_time and transaction["status"] == "committed":
                # Remove backup files
                backup_path = self.backup_dir / tx_id
                if backup_path.exists():
                    shutil.rmtree(backup_path)

                # Remove from history
                del self.transaction_history[tx_id]

        self._save_history()

    def _hash_file(self, file_path: Path) -> str:
        """
        Calculate hash of file contents.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def dry_run_mode(self) -> "DryRunContext":
        """
        Enter dry run mode (preview changes without applying).

        Returns:
            Context manager for dry run mode
        """
        return DryRunContext(self)


class DryRunContext:
    """Context manager for dry run mode"""

    def __init__(self, safety_guard: SafetyGuard):
        self.safety_guard = safety_guard
        self.operations: List[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def record_operation(self, operation: str):
        """Record an operation that would be performed"""
        self.operations.append(operation)

    def get_operations(self) -> List[str]:
        """Get list of operations that would be performed"""
        return self.operations
