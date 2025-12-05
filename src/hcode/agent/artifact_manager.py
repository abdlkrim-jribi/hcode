"""
Artifact Manager for HCode Agent.

Manages task artifacts including:
- implementation_plan.md: Planning phase output
- task.md: Task checklist
- walkthrough.md: Verification phase output
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class ArtifactManager:
    """
    Manages creation and updates of task artifacts.
    
    Artifacts are structured markdown documents that communicate
    the agent's work to users in a Claude Code-style format.
    """
    
    def __init__(self, artifact_dir: Optional[Path] = None):
        """
        Initialize artifact manager.
        
        Args:
            artifact_dir: Directory to store artifacts (default: .hcode/artifacts)
        """
        if artifact_dir is None:
            # Use conversation-specific directory
            self.artifact_dir = Path.cwd() / ".hcode" / "artifacts"
        else:
            self.artifact_dir = Path(artifact_dir)
        
        # Create directory if it doesn't exist
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
    
    def create_implementation_plan(
        self,
        goal_description: str,
        proposed_changes: List[Dict[str, Any]],
        verification_plan: Dict[str, Any],
        user_review_required: Optional[List[str]] = None,
        confidence_score: float = 0.8,
        reasoning_summary: Optional[str] = None
    ) -> Path:
        """
        Create implementation_plan.md artifact.
        
        Args:
            goal_description: What this plan accomplishes
            proposed_changes: List of changes grouped by component
            verification_plan: How changes will be verified
            user_review_required: Items requiring user review
            confidence_score: Agent's confidence in the plan
            reasoning_summary: Summary of reasoning process
            
        Returns:
            Path to created artifact
        """
        plan_path = self.artifact_dir / "implementation_plan.md"
        
        content = f"# {goal_description}\n\n"
        
        # User review section
        if user_review_required:
            content += "## User Review Required\n\n"
            for item in user_review_required:
                content += f"> [!WARNING]\n> {item}\n\n"
        
        # Proposed changes
        content += "## Proposed Changes\n\n"
        
        current_component = None
        for change in proposed_changes:
            component = change.get("component", "General")
            
            # Component header
            if component != current_component:
                content += f"### {component}\n\n"
                current_component = component
            
            # File changes
            action = change.get("action", "MODIFY")  # MODIFY, NEW, DELETE
            filepath = change.get("file", "")
            description = change.get("description", "")
            
            if filepath:
                # Make file links clickable
                file_link = f"[{Path(filepath).name}](file:///{filepath.replace(os.sep, '/')})"
                content += f"#### [{action}] {file_link}\n"
            
            if description:
                content += f"{description}\n\n"
        
        # Verification plan
        content += "## Verification Plan\n\n"
        
        if verification_plan.get("automated_tests"):
            content += "### Automated Tests\n"
            for test in verification_plan["automated_tests"]:
                content += f"- {test}\n"
            content += "\n"
        
        if verification_plan.get("manual_verification"):
            content += "### Manual Verification\n"
            for item in verification_plan["manual_verification"]:
                content += f"- {item}\n"
            content += "\n"
        
        # Metadata footer
        content += "---\n\n"
        content += f"*Confidence: {confidence_score:.0%}*\n"
        content += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        # Write file
        plan_path.write_text(content, encoding="utf-8")
        return plan_path
    
    def create_task_md(
        self,
        task_name: str,
        action_items: List[str]
    ) -> Path:
        """
        Create task.md checklist artifact.
        
        Args:
            task_name: Name of the task
            action_items: List of tasks to complete
            
        Returns:
            Path to created artifact
        """
        task_path = self.artifact_dir / "task.md"
        
        content = f"# {task_name}\n\n"
        content += "## Tasks\n"
        
        for item in action_items:
            content += f"- [ ] {item}\n"
        
        task_path.write_text(content, encoding="utf-8")
        return task_path
    
    def update_task_progress(
        self,
        task_index: int,
        status: str
    ) -> Path:
        """
        Update task status in task.md.
        
        Args:
            task_index: Index of task to update (0-based)
            status: New status ("pending", "in_progress", "completed")
            
        Returns:
            Path to updated task.md
        """
        task_path = self.artifact_dir / "task.md"
        
        if not task_path.exists():
            raise FileNotFoundError(f"task.md not found at {task_path}")
        
        content = task_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        # Find task lines (start with "- [ ]" or "- [x]" or "- [/]")
        task_lines = [
            i for i, line in enumerate(lines)
            if line.strip().startswith("- [")
        ]
        
        if task_index >= len(task_lines):
            raise IndexError(f"Task index {task_index} out of range (max: {len(task_lines) - 1})")
        
        # Update the status marker
        line_idx = task_lines[task_index]
        line = lines[line_idx]
        
        # Replace status marker
        status_markers = {
            "pending": "[ ]",
            "in_progress": "[/]",
            "completed": "[x]"
        }
        
        marker = status_markers.get(status, "[ ]")
        
        # Replace the marker in the line
        import re
        updated_line = re.sub(r"\[.\]", marker, line, count=1)
        lines[line_idx] = updated_line
        
        # Write back
        task_path.write_text("\n".join(lines), encoding="utf-8")
        return task_path
    
    def create_walkthrough(
        self,
        task_name: str,
        changes_made: List[Dict[str, Any]],
        tests_run: List[str],
        validation_results: Dict[str, Any]
    ) -> Path:
        """
        Create walkthrough.md artifact after verification.
        
        Args:
            task_name: Name of completed task
            changes_made: List of changes that were made
            tests_run: List of tests that were executed
            validation_results: Results of validation
            
        Returns:
            Path to created artifact
        """
        walkthrough_path = self.artifact_dir / "walkthrough.md"
        
        content = f"# {task_name} - Walkthrough\n\n"
        
        # Changes made section
        content += "## Changes Made\n\n"
        
        current_component = None
        for change in changes_made:
            component = change.get("component", "General")
            
            if component != current_component:
                content += f"### {component}\n\n"
                current_component = component
            
            filepath = change.get("file", "")
            description = change.get("description", "")
            
            if filepath:
                file_link = f"[{Path(filepath).name}](file:///{filepath.replace(os.sep, '/')})"
                content += f"- **{file_link}**: {description}\n"
            else:
                content += f"- {description}\n"
        
        content += "\n"
        
        # Testing section
        if tests_run:
            content += "## Testing\n\n"
            for test in tests_run:
                content += f"- {test}\n"
            content += "\n"
        
        # Validation section
        content += "## Validation Results\n\n"
        
        if validation_results.get("success"):
            content += "✅ **All validations passed**\n\n"
        else:
            content += "⚠️ **Some validations failed**\n\n"
        
        if validation_results.get("details"):
            for detail in validation_results["details"]:
                content += f"- {detail}\n"
        
        content += "\n---\n\n"
        content += f"*Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        walkthrough_path.write_text(content, encoding="utf-8")
        return walkthrough_path
    
    def get_artifact_path(self, artifact_type: str) -> Path:
        """
        Get path for a specific artifact type.
        
        Args:
            artifact_type: Type of artifact ("plan", "task", "walkthrough")
            
        Returns:
            Path to artifact
        """
        filenames = {
            "plan": "implementation_plan.md",
            "task": "task.md",
            "walkthrough": "walkthrough.md"
        }
        
        filename = filenames.get(artifact_type)
        if not filename:
            raise ValueError(f"Unknown artifact type: {artifact_type}")
        
        return self.artifact_dir / filename
    
    def artifact_exists(self, artifact_type: str) -> bool:
        """Check if an artifact exists"""
        path = self.get_artifact_path(artifact_type)
        return path.exists()


__all__ = [
    "ArtifactManager",
]
