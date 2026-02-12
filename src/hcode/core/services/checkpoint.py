"""
Checkpoint serialization for AgentContext resume-on-failure.

Provides:
- Save AgentContext to JSON checkpoint after each subtask
- Load AgentContext from checkpoint to resume failed tasks
- Checkpoint cleanup and management
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from hcode.core.protocols import AgentContext

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages checkpoint serialization and deserialization for AgentContext.

    Checkpoints are stored in `.hcode/checkpoints/` directory with format:
    `checkpoint_{session_id}_{iteration}_{timestamp}.json`

    This enables:
    - Resume from failure at exact point of crash
    - Rollback to previous iterations if needed
    - Audit trail of execution progression
    """

    def __init__(self, checkpoint_dir: str = ".hcode/checkpoints"):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory for storing checkpoints (relative to working_dir)
        """
        self.checkpoint_dir = checkpoint_dir

    def save_checkpoint(
        self,
        context: AgentContext,
        phase_name: Optional[str] = None,
    ) -> str:
        """
        Save AgentContext to checkpoint file.

        Args:
            context: Current agent context to serialize
            phase_name: Optional phase name to include in filename

        Returns:
            Path to saved checkpoint file
        """
        try:
            # Create checkpoint directory
            checkpoint_path = Path(context.working_dir) / self.checkpoint_dir
            checkpoint_path.mkdir(parents=True, exist_ok=True)

            # Build filename with phase if provided
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            phase_suffix = f"_{phase_name}" if phase_name else ""
            filename = f"checkpoint_{context.session_id}_iter{context.iteration}{phase_suffix}_{timestamp}.json"

            file_path = checkpoint_path / filename

            # Serialize context to JSON
            checkpoint_data = {
                "task": context.task,
                "session_id": context.session_id,
                "working_dir": context.working_dir,
                "iteration": context.iteration,
                "modified_files": context.modified_files,
                "completed_actions": context.completed_actions,
                "artifacts": context.artifacts,
                "metadata": context.metadata,
                "tokens_used": context.tokens_used,
                "token_budget": context.token_budget,
                "checkpoint_time": timestamp,
                "phase": phase_name,
            }

            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved checkpoint: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise

    def load_checkpoint(
        self,
        session_id: str,
        working_dir: str,
        iteration: Optional[int] = None,
    ) -> Optional[AgentContext]:
        """
        Load AgentContext from checkpoint file.

        Args:
            session_id: Session ID to load
            working_dir: Working directory where checkpoints are stored
            iteration: Specific iteration to load (None = latest)

        Returns:
            Restored AgentContext or None if checkpoint doesn't exist
        """
        try:
            checkpoint_path = Path(working_dir) / self.checkpoint_dir

            if not checkpoint_path.exists():
                logger.warning(f"Checkpoint directory does not exist: {checkpoint_path}")
                return None

            # Find matching checkpoint files
            pattern = f"checkpoint_{session_id}_*.json"
            checkpoint_files = list(checkpoint_path.glob(pattern))

            if not checkpoint_files:
                logger.warning(f"No checkpoints found for session {session_id}")
                return None

            # Filter by iteration if specified
            if iteration is not None:
                checkpoint_files = [
                    f for f in checkpoint_files
                    if f"_iter{iteration}_" in f.name or f"_iter{iteration}." in f.name
                ]

            if not checkpoint_files:
                logger.warning(f"No checkpoints found for iteration {iteration}")
                return None

            # Get most recent checkpoint
            latest_checkpoint = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

            # Load checkpoint data
            with open(latest_checkpoint, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Restore AgentContext
            context = AgentContext(
                task=data["task"],
                session_id=data["session_id"],
                working_dir=data["working_dir"],
                iteration=data["iteration"],
                modified_files=data.get("modified_files", []),
                completed_actions=data.get("completed_actions", []),
                artifacts=data.get("artifacts", {}),
                metadata=data.get("metadata", {}),
                tokens_used=data.get("tokens_used", {}),
                token_budget=data.get("token_budget", 500000),
            )

            logger.info(f"Loaded checkpoint from: {latest_checkpoint}")
            logger.info(f"  Session: {context.session_id}")
            logger.info(f"  Iteration: {context.iteration}")
            logger.info(f"  Phase: {data.get('phase', 'unknown')}")
            logger.info(f"  Modified files: {len(context.modified_files)}")
            logger.info(f"  Tokens used: {sum(context.tokens_used.values())}")

            return context

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def list_checkpoints(
        self,
        session_id: str,
        working_dir: str,
    ) -> List[Dict[str, Any]]:
        """
        List all checkpoints for a session.

        Args:
            session_id: Session ID to list checkpoints for
            working_dir: Working directory where checkpoints are stored

        Returns:
            List of checkpoint metadata dicts
        """
        try:
            checkpoint_path = Path(working_dir) / self.checkpoint_dir

            if not checkpoint_path.exists():
                return []

            # Find matching checkpoint files
            pattern = f"checkpoint_{session_id}_*.json"
            checkpoint_files = sorted(
                checkpoint_path.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            checkpoints = []
            for file_path in checkpoint_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    checkpoints.append({
                        "file": str(file_path),
                        "iteration": data.get("iteration", 0),
                        "phase": data.get("phase", "unknown"),
                        "timestamp": data.get("checkpoint_time", ""),
                        "tokens_used": sum(data.get("tokens_used", {}).values()),
                        "modified_files": len(data.get("modified_files", [])),
                    })
                except Exception as e:
                    logger.warning(f"Failed to read checkpoint {file_path}: {e}")
                    continue

            return checkpoints

        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []

    def cleanup_old_checkpoints(
        self,
        session_id: str,
        working_dir: str,
        keep_count: int = 5,
    ) -> int:
        """
        Remove old checkpoints, keeping only the most recent N.

        Args:
            session_id: Session ID to clean up
            working_dir: Working directory where checkpoints are stored
            keep_count: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints deleted
        """
        try:
            checkpoint_path = Path(working_dir) / self.checkpoint_dir

            if not checkpoint_path.exists():
                return 0

            # Find matching checkpoint files
            pattern = f"checkpoint_{session_id}_*.json"
            checkpoint_files = sorted(
                checkpoint_path.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if len(checkpoint_files) <= keep_count:
                return 0

            # Delete old checkpoints
            deleted_count = 0
            for file_path in checkpoint_files[keep_count:]:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old checkpoint: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete checkpoint {file_path}: {e}")

            logger.info(f"Cleaned up {deleted_count} old checkpoints for session {session_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup checkpoints: {e}")
            return 0


def get_checkpoint_manager(checkpoint_dir: str = ".hcode/checkpoints") -> CheckpointManager:
    """
    Get singleton checkpoint manager instance.

    Args:
        checkpoint_dir: Directory for storing checkpoints

    Returns:
        CheckpointManager instance
    """
    return CheckpointManager(checkpoint_dir=checkpoint_dir)
