"""
Smart Todo Extractor for HCode.

Fixes the disabled todo extraction by implementing:
- Validation that extracted items are actionable
- Filtering of speculative/non-actionable phrases
- Concrete target detection (files, functions, etc.)
- Duplicate prevention

This replaces the disabled todo extraction in agent.py.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Set, Dict, Any, Tuple
from enum import Enum


class TodoPriority(Enum):
    """Priority levels for todos"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ExtractedTodo:
    """A validated, actionable todo item"""
    content: str
    active_form: str  # Present participle form
    priority: TodoPriority = TodoPriority.MEDIUM
    source_phase: str = ""  # Which reasoning phase it came from
    target_file: Optional[str] = None
    target_function: Optional[str] = None
    confidence: float = 0.8
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "activeForm": self.active_form,
            "status": "pending",
            "priority": self.priority.value,
            "source": self.source_phase,
            "target_file": self.target_file,
            "confidence": self.confidence
        }


class SmartTodoExtractor:
    """
    Extracts actionable todos from reasoning output.

    Key improvements over naive extraction:
    1. Validates that items start with action verbs
    2. Filters speculative/thinking phrases
    3. Requires concrete targets when possible
    4. Deduplicates similar items
    """

    # Action verbs that indicate actionable todos
    ACTION_VERBS = {
        # Creation
        "create", "add", "implement", "write", "build", "generate",
        "define", "introduce", "establish", "set up", "initialize",

        # Modification
        "update", "modify", "change", "edit", "replace", "rename",
        "refactor", "restructure", "reorganize", "move", "convert",

        # Fixing
        "fix", "repair", "resolve", "correct", "patch", "debug",
        "address", "handle", "solve",

        # Removal
        "remove", "delete", "drop", "eliminate", "clean up",

        # Testing
        "test", "verify", "validate", "check", "ensure", "confirm",

        # Documentation
        "document", "comment", "describe", "explain",

        # Configuration
        "configure", "set", "enable", "disable", "install", "uninstall",

        # Integration
        "integrate", "connect", "link", "import", "export",

        # Review
        "review", "inspect", "audit", "analyze"
    }

    # Phrases that indicate speculative/non-actionable text
    GARBAGE_PATTERNS = [
        r"^(i think|i believe|maybe|perhaps|might|could|would|should consider)",
        r"^(it seems|it looks|it appears|this seems)",
        r"^(let me think|thinking about|considering)",
        r"^(the user|they|we should|one could)",
        r"(not sure|uncertain|unclear)",
        r"^(if|when|assuming|unless)",
        r"^\d+\.",  # Numbered items that might be analysis steps
        r"^(note:|important:|warning:|caution:)",
        r"(etc\.?|and so on|and more)",
    ]

    # Patterns for file paths
    FILE_PATTERNS = [
        r'[\w/\\-]+\.(?:py|js|ts|jsx|tsx|go|rs|java|rb|php|c|cpp|h|hpp|cs|swift|kt|scala)',
        r'[\w/\\-]+\.(?:json|yaml|yml|toml|xml|ini|cfg|conf|env)',
        r'[\w/\\-]+\.(?:md|txt|rst|html|css|scss|less)',
        r'[\w/\\-]+\.(?:sql|sh|bash|zsh|ps1|bat|cmd)',
    ]

    # Patterns for function/method names
    FUNCTION_PATTERNS = [
        r'(?:function|def|method|func)\s+(\w+)',
        r'(\w+)\s*\([^)]*\)',
        r'`(\w+)`',
    ]

    def __init__(self, min_length: int = 10, max_length: int = 200):
        """
        Initialize extractor.

        Args:
            min_length: Minimum todo length
            max_length: Maximum todo length
        """
        self.min_length = min_length
        self.max_length = max_length
        self._seen_hashes: Set[int] = set()

        # Compile patterns
        self._garbage_regex = [re.compile(p, re.IGNORECASE) for p in self.GARBAGE_PATTERNS]
        self._file_regex = re.compile('|'.join(self.FILE_PATTERNS), re.IGNORECASE)
        self._function_regex = [re.compile(p) for p in self.FUNCTION_PATTERNS]

    def _normalize_text(self, text: str) -> str:
        """Normalize text for processing"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove leading bullets/numbers
        text = re.sub(r'^[\s\-\*\•\d\.]+', '', text)
        return text.strip()

    def _get_action_verb(self, text: str) -> Optional[str]:
        """Extract action verb from text"""
        words = text.lower().split()
        if not words:
            return None

        # Check first word
        first_word = words[0]
        if first_word in self.ACTION_VERBS:
            return first_word

        # Check first two words (for phrasal verbs like "set up")
        if len(words) >= 2:
            two_words = f"{words[0]} {words[1]}"
            if two_words in self.ACTION_VERBS:
                return two_words

        return None

    def _is_garbage(self, text: str) -> bool:
        """Check if text is speculative/non-actionable"""
        for pattern in self._garbage_regex:
            if pattern.search(text):
                return True
        return False

    def _extract_file_target(self, text: str) -> Optional[str]:
        """Extract target file from text"""
        match = self._file_regex.search(text)
        if match:
            return match.group(0)
        return None

    def _extract_function_target(self, text: str) -> Optional[str]:
        """Extract target function from text"""
        for pattern in self._function_regex:
            match = pattern.search(text)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return None

    def _to_active_form(self, text: str) -> str:
        """Convert imperative to present participle"""
        verb = self._get_action_verb(text)
        if not verb:
            return text

        # Verb to gerund mappings
        gerund_map = {
            "create": "Creating",
            "add": "Adding",
            "implement": "Implementing",
            "write": "Writing",
            "build": "Building",
            "update": "Updating",
            "modify": "Modifying",
            "change": "Changing",
            "edit": "Editing",
            "fix": "Fixing",
            "remove": "Removing",
            "delete": "Deleting",
            "test": "Testing",
            "review": "Reviewing",
            "refactor": "Refactoring",
            "configure": "Configuring",
            "install": "Installing",
            "integrate": "Integrating",
            "document": "Documenting",
            "verify": "Verifying",
            "check": "Checking",
            "analyze": "Analyzing",
            "debug": "Debugging",
            "resolve": "Resolving",
            "set up": "Setting up",
            "clean up": "Cleaning up",
        }

        if verb in gerund_map:
            rest = text[len(verb):].strip()
            return f"{gerund_map[verb]} {rest}"

        # Default: add -ing
        if verb.endswith('e'):
            gerund = verb[:-1] + 'ing'
        elif len(verb) > 2 and verb[-1] not in 'aeiou' and verb[-2] in 'aeiou':
            gerund = verb + verb[-1] + 'ing'
        else:
            gerund = verb + 'ing'

        rest = text[len(verb):].strip()
        return f"{gerund.capitalize()} {rest}"

    def _is_duplicate(self, text: str) -> bool:
        """Check if we've seen a similar todo"""
        # Simple hash-based dedup
        normalized = text.lower()
        text_hash = hash(normalized)

        if text_hash in self._seen_hashes:
            return True

        self._seen_hashes.add(text_hash)
        return False

    def _calculate_priority(self, text: str, source_phase: str) -> TodoPriority:
        """Calculate todo priority"""
        text_lower = text.lower()

        # High priority indicators
        if any(kw in text_lower for kw in ["critical", "urgent", "important", "must", "required"]):
            return TodoPriority.HIGH

        # From decision/verification phases = higher priority
        if source_phase in ["decision", "verification"]:
            return TodoPriority.HIGH

        # Low priority indicators
        if any(kw in text_lower for kw in ["optional", "later", "consider", "might", "could"]):
            return TodoPriority.LOW

        # From analysis phase = medium
        return TodoPriority.MEDIUM

    def _calculate_confidence(self, text: str, has_target: bool) -> float:
        """Calculate confidence in the extracted todo"""
        confidence = 0.5

        # Action verb present
        if self._get_action_verb(text):
            confidence += 0.2

        # Has concrete target
        if has_target:
            confidence += 0.2

        # Appropriate length
        if self.min_length <= len(text) <= self.max_length:
            confidence += 0.1

        return min(confidence, 1.0)

    def extract_from_text(
        self,
        text: str,
        source_phase: str = "unknown"
    ) -> List[ExtractedTodo]:
        """
        Extract todos from a block of text.

        Args:
            text: Text to extract from
            source_phase: Which reasoning phase this came from

        Returns:
            List of validated ExtractedTodo items
        """
        todos = []

        # Split into sentences/lines
        lines = re.split(r'[.\n]', text)

        for line in lines:
            normalized = self._normalize_text(line)

            # Skip empty or too short
            if len(normalized) < self.min_length:
                continue

            # Skip too long
            if len(normalized) > self.max_length:
                # Try to truncate at a sensible point
                normalized = normalized[:self.max_length].rsplit(' ', 1)[0]

            # Skip garbage
            if self._is_garbage(normalized):
                continue

            # Must have action verb
            if not self._get_action_verb(normalized):
                continue

            # Skip duplicates
            if self._is_duplicate(normalized):
                continue

            # Extract targets
            target_file = self._extract_file_target(normalized)
            target_function = self._extract_function_target(normalized)
            has_target = bool(target_file or target_function)

            # Create todo
            todo = ExtractedTodo(
                content=normalized,
                active_form=self._to_active_form(normalized),
                priority=self._calculate_priority(normalized, source_phase),
                source_phase=source_phase,
                target_file=target_file,
                target_function=target_function,
                confidence=self._calculate_confidence(normalized, has_target),
                raw_text=line
            )

            todos.append(todo)

        return todos

    def extract_from_reasoning(
        self,
        reasoning: Dict[str, Any]
    ) -> List[ExtractedTodo]:
        """
        Extract todos from structured reasoning output.

        Args:
            reasoning: Structured reasoning dictionary

        Returns:
            List of validated ExtractedTodo items
        """
        all_todos = []

        # Priority order of phases to extract from
        phase_priority = [
            ("decision", "action_items"),
            ("decision", "decision"),
            ("analysis", "decomposition"),
            ("verification", "validation_steps"),
            ("verification", "risk_mitigation"),
            ("pre_execution_review", "changes_summary"),
        ]

        for phase, field in phase_priority:
            if phase in reasoning:
                phase_data = reasoning[phase]
                if isinstance(phase_data, dict):
                    content = phase_data.get(field, "")
                    if isinstance(content, list):
                        content = "\n".join(str(item) for item in content)
                    elif not isinstance(content, str):
                        content = str(content)
                else:
                    content = str(phase_data)

                todos = self.extract_from_text(content, source_phase=phase)
                all_todos.extend(todos)

        # Sort by priority and confidence
        all_todos.sort(key=lambda t: (
            0 if t.priority == TodoPriority.HIGH else 1 if t.priority == TodoPriority.MEDIUM else 2,
            -t.confidence
        ))

        return all_todos

    def clear_seen(self):
        """Clear seen hashes for new task"""
        self._seen_hashes.clear()


# =============================================================================
# REASONING-TO-TODO BRIDGE
# =============================================================================

class ReasoningTodoBridge:
    """
    Bridge between reasoning system and todo manager.

    Provides intelligent syncing of todos based on
    reasoning output and execution feedback.
    """

    def __init__(self, todo_manager=None):
        """
        Initialize bridge.

        Args:
            todo_manager: Optional TodoManager instance
        """
        self.extractor = SmartTodoExtractor()
        self.todo_manager = todo_manager
        self._last_todos: List[ExtractedTodo] = []

    def set_todo_manager(self, manager):
        """Set the todo manager"""
        self.todo_manager = manager

    def sync_from_reasoning(
        self,
        reasoning: Dict[str, Any],
        replace: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Sync todos from reasoning output.

        Args:
            reasoning: Structured reasoning dict
            replace: If True, replace all todos; if False, merge

        Returns:
            List of todo dicts
        """
        # Clear extractor state for new sync
        self.extractor.clear_seen()

        # Extract todos
        extracted = self.extractor.extract_from_reasoning(reasoning)
        self._last_todos = extracted

        # Convert to dict format
        todo_dicts = [t.to_dict() for t in extracted]

        # Apply to todo manager if available
        if self.todo_manager:
            if replace:
                self.todo_manager.batch_update(todo_dicts)
            else:
                # Merge: add new, keep existing
                current = self.todo_manager.to_dict_list()
                current_contents = {t.get("content", "").lower() for t in current}

                for todo in todo_dicts:
                    if todo["content"].lower() not in current_contents:
                        current.append(todo)

                # Ensure one is in progress
                has_in_progress = any(t.get("status") == "in_progress" for t in current)
                if not has_in_progress:
                    for todo in current:
                        if todo.get("status") == "pending":
                            todo["status"] = "in_progress"
                            break

                self.todo_manager.batch_update(current)

        return todo_dicts

    def mark_completed(self, content_match: str):
        """Mark a todo as completed by content match"""
        if not self.todo_manager:
            return

        current = self.todo_manager.to_dict_list()

        for todo in current:
            if content_match.lower() in todo.get("content", "").lower():
                todo["status"] = "completed"
                break

        self.todo_manager.batch_update(current)

    def get_current_task(self) -> Optional[Dict[str, Any]]:
        """Get the current in-progress task"""
        if not self.todo_manager:
            return None

        current = self.todo_manager.to_dict_list()
        for todo in current:
            if todo.get("status") == "in_progress":
                return todo

        return None

    def advance_to_next(self):
        """Mark current as complete and advance to next"""
        if not self.todo_manager:
            return

        current = self.todo_manager.to_dict_list()

        # Find and complete current in_progress
        found_in_progress = False
        for todo in current:
            if todo.get("status") == "in_progress":
                todo["status"] = "completed"
                found_in_progress = True
                break

        # Find next pending and mark in_progress
        if found_in_progress:
            for todo in current:
                if todo.get("status") == "pending":
                    todo["status"] = "in_progress"
                    break

        self.todo_manager.batch_update(current)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def extract_todos_from_text(text: str) -> List[Dict[str, Any]]:
    """Quick helper to extract todos from text"""
    extractor = SmartTodoExtractor()
    todos = extractor.extract_from_text(text)
    return [t.to_dict() for t in todos]


def extract_todos_from_reasoning(reasoning: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Quick helper to extract todos from reasoning"""
    extractor = SmartTodoExtractor()
    todos = extractor.extract_from_reasoning(reasoning)
    return [t.to_dict() for t in todos]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "TodoPriority",
    "ExtractedTodo",
    "SmartTodoExtractor",
    "ReasoningTodoBridge",
    "extract_todos_from_text",
    "extract_todos_from_reasoning",
]
