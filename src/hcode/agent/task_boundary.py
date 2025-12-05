"""
Task Boundary System for HCode Agent.

Provides structured workflow tracking with Claude Code-style phase management.
Enables Planning → Execution → Verification workflow with clear boundaries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class AgentMode(Enum):
    """Agent workflow modes"""
    
    PLANNING = "planning"
    EXECUTION = "execution"
    VERIFICATION = "verification"


@dataclass
class TaskBoundary:
    """
    Represents the current task context and phase.
    
    Similar to Claude Code's task boundary system, this tracks:
    - Current task name (e.g., "Planning Authentication System")
    - Current mode (Planning/Execution/Verification)
    - Task status (what the agent is doing right now)
    - Task summary (what has been accomplished so far)
    - Predicted size (estimated tool calls remaining)
    
    Example:
        boundary = TaskBoundary(
            task_name="Planning User Authentication",
            mode=AgentMode.PLANNING,
            task_status="Analyzing existing auth implementation",
            task_summary="Reviewed codebase structure",
            predicted_size=8
        )
    """
    
    task_name: str
    mode: AgentMode
    task_status: str
    task_summary: str
    predicted_size: int
    
    # Metadata
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    
    # History of status updates
    status_history: List[str] = field(default_factory=list)
    
    def update_status(self, new_status: str):
        """Update task status and record in history"""
        self.status_history.append(self.task_status)
        self.task_status = new_status
        self.last_update = datetime.now()
    
    def update_summary(self, new_summary: str):
        """Update task summary (what has been done)"""
        self.task_summary = new_summary
        self.last_update = datetime.now()
    
    def transition_to(
        self, 
        mode: AgentMode, 
        task_name: Optional[str] = None,
        task_status: Optional[str] = None
    ):
        """
        Transition to a new mode (e.g., Planning → Execution).
        
        Args:
            mode: New agent mode
            task_name: Optional new task name
            task_status: Optional new status
        """
        self.mode = mode
        if task_name:
            self.task_name = task_name
        if task_status:
            self.update_status(task_status)
    
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds since task start"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_name": self.task_name,
            "mode": self.mode.value,
            "task_status": self.task_status,
            "task_summary": self.task_summary,
            "predicted_size": self.predicted_size,
            "start_time": self.start_time.isoformat(),
            "elapsed_seconds": self.elapsed_time(),
        }


class TaskBoundaryManager:
    """
    Manages task boundaries throughout agent execution.
    
    Provides a singleton-like interface for tracking the current task context.
    """
    
    def __init__(self):
        self._current_boundary: Optional[TaskBoundary] = None
        self._boundary_history: List[TaskBoundary] = []
    
    def set_task_boundary(
        self,
        task_name: str,
        mode: AgentMode,
        task_status: str,
        task_summary: str,
        predicted_size: int
    ) -> TaskBoundary:
        """
        Set a new task boundary.
        
        Args:
            task_name: Name of the task (e.g., "Planning Authentication")
            mode: Agent mode (Planning/Execution/Verification)
            task_status: Current status (what agent is doing)
            task_summary: Summary of what's been done
            predicted_size: Estimated tool calls remaining
            
        Returns:
            The created TaskBoundary
        """
        # Archive current boundary if exists
        if self._current_boundary:
            self._boundary_history.append(self._current_boundary)
        
        # Create new boundary
        self._current_boundary = TaskBoundary(
            task_name=task_name,
            mode=mode,
            task_status=task_status,
            task_summary=task_summary,
            predicted_size=predicted_size
        )
        
        return self._current_boundary
    
    def get_current_boundary(self) -> Optional[TaskBoundary]:
        """Get the current active task boundary"""
        return self._current_boundary
    
    def update_current_status(self, new_status: str):
        """Update the current boundary's status"""
        if self._current_boundary:
            self._current_boundary.update_status(new_status)
    
    def update_current_summary(self, new_summary: str):
        """Update the current boundary's summary"""
        if self._current_boundary:
            self._current_boundary.update_summary(new_summary)
    
    def transition_to_mode(
        self,
        mode: AgentMode,
        task_name: Optional[str] = None,
        task_status: Optional[str] = None
    ):
        """
        Transition current boundary to new mode.
        
        Args:
            mode: New mode to transition to
            task_name: Optional new task name
            task_status: Optional new status
        """
        if self._current_boundary:
            self._current_boundary.transition_to(mode, task_name, task_status)
    
    def clear_current_boundary(self):
        """Clear the current boundary (task completed)"""
        if self._current_boundary:
            self._boundary_history.append(self._current_boundary)
            self._current_boundary = None
    
    def get_history(self) -> List[TaskBoundary]:
        """Get history of previous boundaries"""
        return self._boundary_history.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about boundary usage"""
        return {
            "total_boundaries": len(self._boundary_history) + (1 if self._current_boundary else 0),
            "current_active": self._current_boundary is not None,
            "current_mode": self._current_boundary.mode.value if self._current_boundary else None,
            "mode_distribution": self._get_mode_distribution(),
        }
    
    def _get_mode_distribution(self) -> Dict[str, int]:
        """Get distribution of modes used"""
        distribution = {mode.value: 0 for mode in AgentMode}
        
        for boundary in self._boundary_history:
            distribution[boundary.mode.value] += 1
        
        if self._current_boundary:
            distribution[self._current_boundary.mode.value] += 1
        
        return distribution


# Global instance for easy access
_global_boundary_manager: Optional[TaskBoundaryManager] = None


def get_task_boundary_manager() -> TaskBoundaryManager:
    """Get the global task boundary manager instance"""
    global _global_boundary_manager
    if _global_boundary_manager is None:
        _global_boundary_manager = TaskBoundaryManager()
    return _global_boundary_manager


def set_task_boundary(
    task_name: str,
    mode: AgentMode,
    task_status: str,
    task_summary: str,
    predicted_size: int
) -> TaskBoundary:
    """Convenience function to set task boundary using global manager"""
    manager = get_task_boundary_manager()
    return manager.set_task_boundary(
        task_name=task_name,
        mode=mode,
        task_status=task_status,
        task_summary=task_summary,
        predicted_size=predicted_size
    )


def get_current_boundary() -> Optional[TaskBoundary]:
    """Convenience function to get current boundary"""
    manager = get_task_boundary_manager()
    return manager.get_current_boundary()


def transition_to_mode(
    mode: AgentMode,
    task_name: Optional[str] = None,
    task_status: Optional[str] = None
):
    """Convenience function to transition mode"""
    manager = get_task_boundary_manager()
    manager.transition_to_mode(mode, task_name, task_status)


__all__ = [
    "AgentMode",
    "TaskBoundary",
    "TaskBoundaryManager",
    "get_task_boundary_manager",
    "set_task_boundary",
    "get_current_boundary",
    "transition_to_mode",
]
