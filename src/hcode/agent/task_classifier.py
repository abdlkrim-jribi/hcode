"""
Task Classification Module

Determines if user requests require ACTION (making changes) or ADVISORY (reporting only).
This helps the agent decide whether to apply fixes or just generate recommendations.
"""

from enum import Enum
from typing import Set


class TaskMode(Enum):
    """Represents the execution mode for a task."""
    ACTION = "action"       # Fix, modify, update files
    ADVISORY = "advisory"   # Report, analyze, recommend only


class TaskClassifier:
    """
    Classify user requests to determine if agent should take action or just advise.

    This classifier analyzes user messages to determine whether the agent should:
    - ACTION mode: Actually modify files using Edit/Write tools
    - ADVISORY mode: Only analyze and report findings
    """

    # Keywords that indicate user wants changes applied
    ACTION_KEYWORDS: Set[str] = {
        "fix", "correct", "update", "modify", "change", "apply",
        "implement", "add", "remove", "refactor", "optimize",
        "ensure", "make sure", "validate and fix", "check and update",
        "check and fix", "review and update", "review and fix",
        "repair", "resolve", "address", "improve"
    }

    # Keywords that indicate user wants advisory output only
    ADVISORY_KEYWORDS: Set[str] = {
        "just report", "only analyze", "don't modify", "don't change",
        "what should", "how should", "recommend", "suggest",
        "analyze only", "report only", "just tell me", "just show",
        "don't fix", "don't update", "don't apply"
    }

    # Ambiguous keywords that need context
    AMBIGUOUS_KEYWORDS: Set[str] = {
        "check", "review", "validate", "inspect", "examine", "analyze"
    }

    @staticmethod
    def classify_task(user_message: str) -> TaskMode:
        """
        Determine if the user wants action or advisory mode.

        Args:
            user_message: The user's request message

        Returns:
            TaskMode.ACTION if agent should make changes
            TaskMode.ADVISORY if agent should only report

        Examples:
            >>> TaskClassifier.classify_task("fix the syntax errors")
            TaskMode.ACTION

            >>> TaskClassifier.classify_task("just report what's wrong, don't modify")
            TaskMode.ADVISORY

            >>> TaskClassifier.classify_task("check the test syntax")
            TaskMode.ACTION  # "check" + code object implies fixing
        """
        message_lower = user_message.lower()

        # Check for explicit advisory keywords first (highest priority)
        if any(keyword in message_lower for keyword in TaskClassifier.ADVISORY_KEYWORDS):
            return TaskMode.ADVISORY

        # Check for explicit action keywords
        if any(keyword in message_lower for keyword in TaskClassifier.ACTION_KEYWORDS):
            return TaskMode.ACTION

        # Handle ambiguous cases like "check", "review", etc.
        if any(keyword in message_lower for keyword in TaskClassifier.AMBIGUOUS_KEYWORDS):
            # Check if it's checking code/syntax/tests (implies fixing if issues found)
            code_targets = ["syntax", "test", "code", "file", "function", "class",
                           "method", "bug", "error", "issue", "scenario", "testcase"]
            if any(target in message_lower for target in code_targets):
                # "check the syntax" → ACTION (check implies fixing issues found)
                return TaskMode.ACTION

        # If still unclear, check for question patterns (advisory)
        question_patterns = ["what", "how", "why", "which", "when", "who"]
        if any(pattern in message_lower.split()[:3] for pattern in question_patterns):
            # Questions starting with what/how/why are usually asking for advice
            return TaskMode.ADVISORY

        # Default to ACTION (proactive agent behavior)
        # Better to apply fixes than to just report and make user do it
        return TaskMode.ACTION

    @staticmethod
    def should_apply_fixes(task_mode: TaskMode, issues_found: bool) -> bool:
        """
        Determine if agent should apply fixes based on mode and findings.

        Args:
            task_mode: The classified task mode
            issues_found: Whether issues were identified during analysis

        Returns:
            True if fixes should be applied, False otherwise

        Examples:
            >>> TaskClassifier.should_apply_fixes(TaskMode.ACTION, True)
            True

            >>> TaskClassifier.should_apply_fixes(TaskMode.ADVISORY, True)
            False

            >>> TaskClassifier.should_apply_fixes(TaskMode.ACTION, False)
            False  # No issues to fix
        """
        if task_mode == TaskMode.ADVISORY:
            return False

        # Only apply fixes if there are actual issues
        return issues_found

    @staticmethod
    def get_mode_description(task_mode: TaskMode) -> str:
        """
        Get a human-readable description of the task mode.

        Args:
            task_mode: The task mode

        Returns:
            Description string for the mode
        """
        if task_mode == TaskMode.ACTION:
            return "ACTION - Will apply fixes to files"
        else:
            return "ADVISORY - Will report findings without modifying files"


# Convenience function for quick classification
def classify_user_request(message: str) -> TaskMode:
    """
    Quick classification of user request.

    Args:
        message: User's request message

    Returns:
        TaskMode.ACTION or TaskMode.ADVISORY
    """
    return TaskClassifier.classify_task(message)
