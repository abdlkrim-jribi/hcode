"""
Artifact manager for PEV workflow.

Manages phase artifacts:
- task.md: Task understanding and subtasks
- implementation_plan.md: Implementation steps
- walkthrough.md: Implementation walkthrough with test results
"""

from pathlib import Path
from typing import Optional, Tuple

from ..protocols import ArtifactManagerProtocol, AgentContext


class ArtifactManager(ArtifactManagerProtocol):
    """
    Manages creation and validation of phase artifacts.

    Each PEV phase produces specific artifacts:
    - Planning: task.md, implementation_plan.md
    - Execution: Modified files tracked in context
    - Verification: walkthrough.md
    """

    def __init__(self, artifacts_dir: str = ".hcode"):
        """
        Initialize artifact manager.

        Args:
            artifacts_dir: Directory for artifacts (default: .hcode)
        """
        self.artifacts_dir = artifacts_dir

    def _get_artifact_path(self, artifact_name: str, context: AgentContext) -> Path:
        """
        Get full path for artifact.

        Args:
            artifact_name: Name of artifact (e.g., "task.md")
            context: Current agent context

        Returns:
            Full Path to artifact
        """
        base_dir = Path(context.working_dir) / self.artifacts_dir
        return base_dir / artifact_name

    def create_artifact(
            self,
            artifact_name: str,
            content: str,
            context: AgentContext,
    ) -> str:
        """
        Create a phase artifact file.

        Args:
            artifact_name: Name of artifact (e.g., "task.md")
            content: Content to write
            context: Current agent context

        Returns:
            Full path to created artifact
        """
        artifact_path = self._get_artifact_path(artifact_name, context)

        # Ensure directory exists
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        # Write artifact
        artifact_path.write_text(content, encoding='utf-8')

        # Track in context
        context.artifacts[artifact_name] = str(artifact_path)

        return str(artifact_path)

    def load_artifact(
            self,
            artifact_name: str,
            context: AgentContext,
    ) -> Optional[str]:
        """
        Load artifact content.

        Args:
            artifact_name: Name of artifact to load
            context: Current agent context

        Returns:
            Artifact content or None if doesn't exist
        """
        artifact_path = self._get_artifact_path(artifact_name, context)

        if not artifact_path.exists():
            return None

        try:
            return artifact_path.read_text(encoding='utf-8')
        except Exception:
            return None

    def artifact_exists(
            self,
            artifact_name: str,
            context: AgentContext,
    ) -> bool:
        """
        Check if artifact exists.

        Args:
            artifact_name: Name of artifact
            context: Current agent context

        Returns:
            True if artifact file exists
        """
        artifact_path = self._get_artifact_path(artifact_name, context)
        return artifact_path.exists()

    def validate_artifact_content(
            self,
            artifact_name: str,
            content: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate artifact has required content.

        Args:
            artifact_name: Name of artifact
            content: Artifact content to validate

        Returns:
            Tuple of (valid, error_message)
        """
        if not content or not content.strip():
            return False, f"{artifact_name} is empty"

        # Specific validation for each artifact type
        if artifact_name == "task.md":
            return self._validate_task_md(content)
        elif artifact_name == "implementation_plan.md":
            return self._validate_implementation_plan(content)
        elif artifact_name == "walkthrough.md":
            return self._validate_walkthrough(content)

        # Default: just check it's not empty
        return True, None

    def _validate_task_md(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate task.md has required sections.

        Required sections:
        - # Task (or similar heading)
        - Some understanding/context
        - Subtasks (optional but recommended)
        """
        content.lower()

        # Should have a heading
        if not any(marker in content for marker in ["# ", "## "]):
            return False, "task.md should have markdown headings"

        # Should have some content (at least 50 chars)
        if len(content.strip()) < 50:
            return False, "task.md content is too brief"

        return True, None

    def _validate_implementation_plan(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate implementation_plan.md has required sections.

        Required sections:
        - Approach or strategy
        - Steps or actions
        - Files to modify (for implementation tasks)
        """
        content_lower = content.lower()

        # Should have headings
        if not any(marker in content for marker in ["# ", "## "]):
            return False, "implementation_plan.md should have markdown headings"

        # Should mention steps or plan
        if not any(keyword in content_lower for keyword in ["step", "plan", "approach", "strategy"]):
            return False, "implementation_plan.md should describe steps or approach"

        # Should have reasonable length
        if len(content.strip()) < 100:
            return False, "implementation_plan.md is too brief"

        return True, None

    def _validate_walkthrough(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate walkthrough.md has required sections.

        Required sections:
        - What was implemented
        - Files modified (or verification steps)
        - Test results or verification
        """
        content_lower = content.lower()

        # Should have headings
        if not any(marker in content for marker in ["# ", "## "]):
            return False, "walkthrough.md should have markdown headings"

        # Should mention implementation or changes
        if not any(keyword in content_lower for keyword in [
            "implement", "change", "modif", "add", "creat", "updat"
        ]):
            return False, "walkthrough.md should describe what was implemented"

        # Should have reasonable length
        if len(content.strip()) < 100:
            return False, "walkthrough.md is too brief"

        return True, None
