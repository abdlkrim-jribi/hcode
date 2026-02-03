"""
Core services for the Hcode agent.

Services are focused components that handle specific responsibilities:
- ArtifactManager: Manages phase artifacts (task.md, implementation_plan.md, etc.)
- ContextService: Facade over ContextManager for simplified context operations
- PromptBuilder: Builds system prompts with context injection
"""

from .artifact_manager import ArtifactManager

__all__ = ["ArtifactManager"]
