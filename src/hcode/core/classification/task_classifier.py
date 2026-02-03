"""
Task classifier that uses configurable patterns instead of hardcoded logic.

Replaces the hardcoded word lists and regex patterns in agent.py with
a YAML-based configuration system.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from ..protocols import TaskClassifierProtocol


class TaskClassifier(TaskClassifierProtocol):
    """
    Classify tasks using configurable patterns from YAML.

    Replaces hardcoded logic like:
    - Lines 1124-1182: is_read_only() word lists
    - Lines 1258-1279: exploration task detection
    - Lines 1285-1300: action command detection
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize classifier with configuration.

        Args:
            config_path: Path to task_classification.yaml
        """
        if config_path is None:
            # Default to config/task_classification.yaml
            config_path = Path(__file__).parent.parent.parent / "config" / "task_classification.yaml"

        self.config_path = config_path
        self.config = self._load_config()
        self.last_confidence = 0.0
        self.last_scores: Dict[str, float] = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load classification configuration from YAML."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            # Fallback to default configuration
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get minimal default configuration if file load fails."""
        return {
            "task_types": {
                "exploration": {
                    "keywords": ["what", "show", "list", "explain", "describe"],
                },
                "implementation": {
                    "keywords": ["create", "implement", "build", "add"],
                },
            },
            "settings": {
                "min_confidence": 0.5,
                "default_type": "implementation",
                "default_complexity": "moderate",
            }
        }

    def classify(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Classify task type.

        Args:
            task: User's task description
            context: Optional context (not used yet)

        Returns:
            Task type string
        """
        task_lower = task.lower().strip()
        task_types = self.config.get("task_types", {})
        scores: Dict[str, float] = {}

        # Score each task type
        for task_type, type_config in task_types.items():
            score = self._score_task_type(task_lower, type_config)
            scores[task_type] = score

        self.last_scores = scores

        # Find highest scoring type
        if scores:
            best_type = max(scores, key=scores.get)
            self.last_confidence = scores[best_type]

            # Check minimum confidence
            min_confidence = self.config.get("settings", {}).get("min_confidence", 0.5)
            if self.last_confidence >= min_confidence:
                return best_type

        # Return default if no clear match
        return self.config.get("settings", {}).get("default_type", "implementation")

    def _score_task_type(self, task: str, type_config: Dict[str, Any]) -> float:
        """
        Score how well task matches a task type.

        Args:
            task: Task text (lowercase)
            type_config: Configuration for this task type

        Returns:
            Score (0.0 to 1.0+)
        """
        score = 0.0

        # Check pattern indicators
        indicators = type_config.get("indicators", [])
        for indicator in indicators:
            pattern = indicator.get("pattern", "")
            weight = indicator.get("weight", 0.5)

            if re.search(pattern, task, re.IGNORECASE):
                score += weight

        # Check negative indicators (subtract score)
        negative_indicators = type_config.get("negative_indicators", [])
        for indicator in negative_indicators:
            pattern = indicator.get("pattern", "")
            weight = indicator.get("weight", 0.5)

            if re.search(pattern, task, re.IGNORECASE):
                score -= weight

        # Check keywords
        keywords = type_config.get("keywords", [])
        keyword_weight = self.config.get("settings", {}).get("keyword_weight_multiplier", 0.5)
        for keyword in keywords:
            if keyword.lower() in task:
                score += keyword_weight

        # Normalize score to 0-1 range
        return max(0.0, min(1.0, score))

    def get_complexity(self, task: str) -> str:
        """
        Determine task complexity.

        Args:
            task: User's task description

        Returns:
            Complexity: "simple", "moderate", "complex"
        """
        task_lower = task.lower().strip()
        complexity_config = self.config.get("complexity", {})

        # Score each complexity level
        scores = {}
        for complexity_level in ["simple", "moderate", "complex"]:
            level_config = complexity_config.get(complexity_level, {})
            score = self._score_task_type(task_lower, level_config)
            scores[complexity_level] = score

        # Return highest scoring complexity
        if scores:
            return max(scores, key=scores.get)

        return self.config.get("settings", {}).get("default_complexity", "moderate")

    def get_confidence(self) -> float:
        """
        Get confidence score for last classification.

        Returns:
            Confidence score (0.0 to 1.0)
        """
        return self.last_confidence

    def is_read_only(self, task: str) -> bool:
        """
        Check if task is read-only (exploration/explanation).

        Replaces hardcoded logic from agent.py lines 1124-1182.

        Args:
            task: User's task description

        Returns:
            True if task doesn't require file modifications
        """
        task_type = self.classify(task)

        # Exploration and documentation are typically read-only
        # (though documentation might write docs)
        read_only_types = ["exploration"]

        return task_type in read_only_types

    def is_action_task(self, task: str) -> bool:
        """
        Check if task requires actions (file modifications, commands).

        Replaces hardcoded logic from agent.py lines 1285-1300.

        Args:
            task: User's task description

        Returns:
            True if task requires actions
        """
        task_type = self.classify(task)

        # These task types require actions
        action_types = [
            "implementation",
            "debugging",
            "refactoring",
            "testing",
            "configuration",
        ]

        return task_type in action_types

    def get_classification_details(self) -> Dict[str, Any]:
        """
        Get detailed classification information for debugging.

        Returns:
            Dict with scores, confidence, and classification
        """
        return {
            "scores": self.last_scores,
            "confidence": self.last_confidence,
            "all_types": list(self.config.get("task_types", {}).keys()),
        }
