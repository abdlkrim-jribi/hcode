"""
Intelligent Tool Selection Engine for HCode.

Provides smart tool selection based on:
- Task type and complexity
- Past tool success rates
- Reasoning context hints
- File type associations

This improves tool usage accuracy by suggesting
the most relevant tools for each task.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import json


class TaskCategory(Enum):
    """Categories of tasks"""

    CODE_GENERATION = "code_generation"
    CODE_MODIFICATION = "code_modification"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    ANALYSIS = "analysis"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    FILE_OPERATIONS = "file_operations"
    WEB_RESEARCH = "web_research"
    INTERACTIVE = "interactive"
    UNKNOWN = "unknown"


@dataclass
class ToolSuccessRecord:
    """Record of tool execution success/failure"""

    tool_name: str
    task_category: TaskCategory
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None

    @property
    def total_uses(self) -> int:
        return self.success_count + self.failure_count

    @property
    def success_rate(self) -> float:
        if self.total_uses == 0:
            return 0.5  # Neutral for unused tools
        return self.success_count / self.total_uses


@dataclass
class ToolContext:
    """Context for tool selection"""

    task_category: TaskCategory = TaskCategory.UNKNOWN
    file_types: Set[str] = field(default_factory=set)
    reasoning_confidence: float = 0.5
    mentioned_tools: Set[str] = field(default_factory=set)
    keywords: Set[str] = field(default_factory=set)
    requires_write: bool = False
    requires_web: bool = False


@dataclass
class ToolSelection:
    """Result of tool selection"""

    primary_tools: List[str]  # Top recommended tools
    secondary_tools: List[str]  # Additional useful tools
    blocked_tools: List[str]  # Tools to avoid
    reasoning: str  # Explanation of selection


class ToolSuccessTracker:
    """
    Tracks tool success rates across task categories.

    Enables learning from past executions to improve
    future tool selections.
    """

    def __init__(self, persistence_path: Optional[Path] = None):
        """
        Initialize tracker.

        Args:
            persistence_path: Optional path to persist statistics
        """
        self._records: Dict[Tuple[str, TaskCategory], ToolSuccessRecord] = {}
        self._persistence_path = persistence_path

        if persistence_path and persistence_path.exists():
            self._load()

    def _get_key(self, tool_name: str, category: TaskCategory) -> Tuple[str, TaskCategory]:
        """Get record key"""
        return (tool_name.lower(), category)

    def record_success(self, tool_name: str, category: TaskCategory):
        """Record successful tool execution"""
        key = self._get_key(tool_name, category)

        if key not in self._records:
            self._records[key] = ToolSuccessRecord(
                tool_name=tool_name.lower(), task_category=category
            )

        self._records[key].success_count += 1
        self._records[key].last_used = datetime.now()
        self._save()

    def record_failure(self, tool_name: str, category: TaskCategory):
        """Record failed tool execution"""
        key = self._get_key(tool_name, category)

        if key not in self._records:
            self._records[key] = ToolSuccessRecord(
                tool_name=tool_name.lower(), task_category=category
            )

        self._records[key].failure_count += 1
        self._records[key].last_used = datetime.now()
        self._save()

    def get_success_rate(self, tool_name: str, category: TaskCategory) -> float:
        """Get success rate for tool in category"""
        key = self._get_key(tool_name, category)
        if key in self._records:
            return self._records[key].success_rate
        return 0.5  # Neutral for unknown

    def rank_tools(self, tools: List[str], category: TaskCategory) -> List[Tuple[str, float]]:
        """
        Rank tools by success rate for category.

        Args:
            tools: List of tool names
            category: Task category

        Returns:
            List of (tool_name, success_rate) sorted by rate
        """
        ranked = [(tool, self.get_success_rate(tool, category)) for tool in tools]
        return sorted(ranked, key=lambda x: x[1], reverse=True)

    def _save(self):
        """Persist records to disk"""
        if not self._persistence_path:
            return

        data = {}
        for (tool, cat), record in self._records.items():
            key = f"{tool}:{cat.value}"
            data[key] = {
                "tool_name": record.tool_name,
                "category": record.task_category.value,
                "success_count": record.success_count,
                "failure_count": record.failure_count,
                "last_used": record.last_used.isoformat() if record.last_used else None,
            }

        try:
            with open(self._persistence_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        """Load records from disk"""
        if not self._persistence_path or not self._persistence_path.exists():
            return

        try:
            with open(self._persistence_path, "r") as f:
                data = json.load(f)

            for key, record_data in data.items():
                tool = record_data["tool_name"]
                category = TaskCategory(record_data["category"])
                record = ToolSuccessRecord(
                    tool_name=tool,
                    task_category=category,
                    success_count=record_data["success_count"],
                    failure_count=record_data["failure_count"],
                    last_used=(
                        datetime.fromisoformat(record_data["last_used"])
                        if record_data["last_used"]
                        else None
                    ),
                )
                self._records[(tool, category)] = record

        except Exception:
            pass


class ToolSelectionRules:
    """
    Rule-based tool filtering and prioritization.

    Defines which tools are relevant for different
    task categories and file types.
    """

    # Tools for each task category
    CATEGORY_TOOLS = {
        TaskCategory.CODE_GENERATION: [
            "writetool",
            "edittool",
            "readtool",
            "globtool",
            "greptool",
            "bashtool",
        ],
        TaskCategory.CODE_MODIFICATION: [
            "edittool",
            "multiedittool",
            "readtool",
            "greptool",
            "globtool",
            "diffpreviewtool",
        ],
        TaskCategory.DEBUGGING: ["readtool", "greptool", "bashtool", "globtool", "edittool"],
        TaskCategory.REFACTORING: [
            "readtool",
            "edittool",
            "multiedittool",
            "greptool",
            "globtool",
            "diffpreviewtool",
        ],
        TaskCategory.ANALYSIS: ["readtool", "greptool", "globtool", "lstool", "bashtool"],
        TaskCategory.DOCUMENTATION: ["readtool", "writetool", "edittool", "globtool"],
        TaskCategory.TESTING: ["bashtool", "readtool", "edittool", "greptool"],
        TaskCategory.FILE_OPERATIONS: ["readtool", "writetool", "globtool", "lstool", "bashtool"],
        TaskCategory.WEB_RESEARCH: ["websearchtool", "webfetchtool"],
        TaskCategory.INTERACTIVE: ["askuserquestiontool", "todowritetool", "confirmtool"],
    }

    # File extension to relevant tools
    FILE_TYPE_TOOLS = {
        ".py": ["readtool", "edittool", "greptool", "bashtool"],
        ".js": ["readtool", "edittool", "greptool", "bashtool"],
        ".ts": ["readtool", "edittool", "greptool", "bashtool"],
        ".json": ["readtool", "edittool", "writetool"],
        ".yaml": ["readtool", "edittool", "writetool"],
        ".yml": ["readtool", "edittool", "writetool"],
        ".md": ["readtool", "writetool", "edittool"],
        ".html": ["readtool", "edittool", "webfetchtool"],
        ".css": ["readtool", "edittool"],
        ".sql": ["readtool", "edittool", "bashtool"],
    }

    # Keywords to task categories
    KEYWORD_CATEGORIES = {
        TaskCategory.CODE_GENERATION: [
            "create",
            "write",
            "generate",
            "implement",
            "add new",
            "build",
            "make",
        ],
        TaskCategory.CODE_MODIFICATION: [
            "modify",
            "change",
            "update",
            "edit",
            "replace",
            "alter",
            "adjust",
        ],
        TaskCategory.DEBUGGING: [
            "debug",
            "fix",
            "error",
            "bug",
            "issue",
            "problem",
            "crash",
            "fail",
            "broken",
        ],
        TaskCategory.REFACTORING: [
            "refactor",
            "restructure",
            "reorganize",
            "clean up",
            "improve",
            "optimize",
        ],
        TaskCategory.ANALYSIS: [
            "analyze",
            "find",
            "search",
            "look for",
            "show",
            "explain",
            "understand",
            "review",
        ],
        TaskCategory.DOCUMENTATION: ["document", "comment", "readme", "docstring"],
        TaskCategory.TESTING: ["test", "spec", "unittest", "pytest", "coverage"],
        TaskCategory.WEB_RESEARCH: [
            "search online",
            "google",
            "look up",
            "web",
            "documentation",
            "api docs",
        ],
    }

    # Tools that should be blocked in certain contexts
    BLOCKED_TOOLS = {
        "low_confidence": ["writetool", "bashtool"],  # Safer tools only
        "analysis_only": ["writetool", "edittool", "bashtool"],
        "read_only": ["writetool", "edittool", "bashtool", "multiedittool"],
    }

    def detect_category(self, task_text: str) -> TaskCategory:
        """
        Detect task category from task description.

        Args:
            task_text: Task description text

        Returns:
            Detected TaskCategory
        """
        task_lower = task_text.lower()

        # Check each category's keywords
        scores = defaultdict(int)

        for category, keywords in self.KEYWORD_CATEGORIES.items():
            for keyword in keywords:
                if keyword in task_lower:
                    scores[category] += 1

        if scores:
            best_category = max(scores.keys(), key=lambda c: scores[c])
            return best_category

        return TaskCategory.UNKNOWN

    def filter_by_category(self, category: TaskCategory) -> List[str]:
        """Get tools relevant for category"""
        return self.CATEGORY_TOOLS.get(category, [])

    def filter_by_file_types(self, file_types: Set[str]) -> Set[str]:
        """Get tools relevant for file types"""
        tools = set()
        for ext in file_types:
            tools.update(self.FILE_TYPE_TOOLS.get(ext, []))
        return tools

    def get_blocked_tools(self, context: ToolContext) -> List[str]:
        """Get tools that should be blocked given context"""
        blocked = []

        if context.reasoning_confidence < 0.4:
            blocked.extend(self.BLOCKED_TOOLS["low_confidence"])

        return list(set(blocked))


class ToolSelectionEngine:
    """
    Main tool selection engine.

    Combines rules, success tracking, and context
    to provide intelligent tool recommendations.
    """

    def __init__(self, available_tools: List[str], persistence_path: Optional[Path] = None):
        """
        Initialize selection engine.

        Args:
            available_tools: List of all available tool names
            persistence_path: Path for persisting success statistics
        """
        self.available_tools = set(t.lower() for t in available_tools)
        self.success_tracker = ToolSuccessTracker(persistence_path)
        self.rules = ToolSelectionRules()

    def _extract_context(self, task: str, reasoning: Optional[str] = None) -> ToolContext:
        """Extract tool context from task and reasoning"""
        context = ToolContext()

        # Detect task category
        context.task_category = self.rules.detect_category(task)

        # Extract file extensions mentioned
        file_pattern = r"[\w/\\]+\.(\w{1,5})\b"
        matches = re.findall(file_pattern, task)
        context.file_types = set(f".{m.lower()}" for m in matches)

        # Check for write requirements
        write_keywords = ["create", "write", "modify", "edit", "add", "update"]
        context.requires_write = any(kw in task.lower() for kw in write_keywords)

        # Check for web requirements
        web_keywords = ["search", "google", "web", "online", "documentation"]
        context.requires_web = any(kw in task.lower() for kw in web_keywords)

        # Extract keywords
        context.keywords = set(task.lower().split())

        # Extract confidence from reasoning if available
        if reasoning:
            confidence_match = re.search(r"confidence[:\s]*(\d+)%?", reasoning.lower())
            if confidence_match:
                context.reasoning_confidence = int(confidence_match.group(1)) / 100

            # Look for tool mentions
            for tool in self.available_tools:
                if tool in reasoning.lower():
                    context.mentioned_tools.add(tool)

        return context

    def select_tools(
        self,
        task: str,
        reasoning: Optional[str] = None,
        max_primary: int = 5,
        max_secondary: int = 5,
    ) -> ToolSelection:
        """
        Select tools for a task.

        Args:
            task: Task description
            reasoning: Optional reasoning context
            max_primary: Maximum primary tools to recommend
            max_secondary: Maximum secondary tools

        Returns:
            ToolSelection with recommendations
        """
        context = self._extract_context(task, reasoning)
        reasons = []

        # Get category-based tools
        category_tools = set(self.rules.filter_by_category(context.task_category))
        reasons.append(f"Task category: {context.task_category.value}")

        # Get file-type based tools
        file_tools = self.rules.filter_by_file_types(context.file_types)
        if file_tools:
            category_tools.update(file_tools)
            reasons.append(f"File types: {context.file_types}")

        # Add web tools if needed
        if context.requires_web:
            category_tools.update(["websearchtool", "webfetchtool"])
            reasons.append("Web research required")

        # Filter to available tools
        candidates = category_tools.intersection(self.available_tools)

        if not candidates:
            # Fallback to common tools
            candidates = {"readtool", "greptool", "globtool"}
            reasons.append("Using fallback tools")

        # Get blocked tools
        blocked = self.rules.get_blocked_tools(context)

        # Remove blocked from candidates
        candidates = candidates - set(blocked)

        # Rank by success rate
        ranked = self.success_tracker.rank_tools(list(candidates), context.task_category)

        # Boost tools mentioned in reasoning
        if context.mentioned_tools:
            for i, (tool, rate) in enumerate(ranked):
                if tool in context.mentioned_tools:
                    ranked[i] = (tool, min(1.0, rate + 0.2))
            ranked.sort(key=lambda x: x[1], reverse=True)

        # Split into primary and secondary
        primary = [t for t, r in ranked[:max_primary]]
        secondary = [t for t, r in ranked[max_primary : max_primary + max_secondary]]

        return ToolSelection(
            primary_tools=primary,
            secondary_tools=secondary,
            blocked_tools=blocked,
            reasoning="; ".join(reasons),
        )

    def record_execution(self, tool_name: str, task: str, success: bool):
        """
        Record tool execution result for learning.

        Args:
            tool_name: Name of executed tool
            task: Task description
            success: Whether execution succeeded
        """
        category = self.rules.detect_category(task)

        if success:
            self.success_tracker.record_success(tool_name, category)
        else:
            self.success_tracker.record_failure(tool_name, category)

    def get_stats(self) -> Dict[str, Any]:
        """Get selection engine statistics"""
        return {
            "available_tools": len(self.available_tools),
            "tracked_combinations": len(self.success_tracker._records),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_engine: Optional[ToolSelectionEngine] = None


def get_tool_selector(
    available_tools: Optional[List[str]] = None, persistence_path: Optional[Path] = None
) -> ToolSelectionEngine:
    """Get or create global tool selection engine"""
    global _engine

    if _engine is None:
        if available_tools is None:
            # Default common tools
            available_tools = [
                "readtool",
                "writetool",
                "edittool",
                "multiedittool",
                "globtool",
                "greptool",
                "lstool",
                "bashtool",
                "websearchtool",
                "webfetchtool",
                "askuserquestiontool",
                "todowritetool",
                "diffpreviewtool",
                "applychangetool",
            ]

        _engine = ToolSelectionEngine(available_tools, persistence_path)

    return _engine


def select_tools_for_task(task: str, reasoning: Optional[str] = None) -> ToolSelection:
    """Quick helper to select tools for a task"""
    engine = get_tool_selector()
    return engine.select_tools(task, reasoning)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "TaskCategory",
    "ToolContext",
    "ToolSelection",
    "ToolSuccessTracker",
    "ToolSelectionRules",
    "ToolSelectionEngine",
    "get_tool_selector",
    "select_tools_for_task",
]
