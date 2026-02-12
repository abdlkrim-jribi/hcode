"""
Task classification system.

Replaces hardcoded word lists and regex patterns with configurable
classification strategies.
"""

from .task_classifier import TaskClassifier

__all__ = ["TaskClassifier"]
