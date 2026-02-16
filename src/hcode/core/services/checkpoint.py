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



def get_checkpoint_manager(checkpoint_dir: str = ".hcode/checkpoints") -> CheckpointManager:
    """
    Get singleton checkpoint manager instance.

    Args:
        checkpoint_dir: Directory for storing checkpoints

    Returns:
        CheckpointManager instance
    """
    return CheckpointManager(checkpoint_dir=checkpoint_dir)
