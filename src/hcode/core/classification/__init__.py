"""
Task classification system.

Replaces hardcoded word lists and regex patterns with configurable
classification strategies.
"""

from .task_classifier import TaskClassifier
from ...providers.provider_selector import TaskComplexity

__all__ = ["TaskClassifier", "TaskComplexity"]
