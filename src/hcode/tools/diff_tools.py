"""
Diff Preview Tools for Hcode.

Provides change preview and approval workflow before applying modifications.
Allows users to review proposed changes with detailed diffs before execution.
"""

import os
import difflib
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum

from .base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class ChangeOperation(Enum):
    """Types of file change operations"""
    EDIT = "edit"
    WRITE = "write"
    DELETE = "delete"
    CREATE = "create"
    MULTI_EDIT = "multi_edit"


class ChangeStatus(Enum):
    """Status of a proposed change"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"


@dataclass
class DiffLine:
    """Represents a single line in a diff"""
    line_number_old: Optional[int]
    line_number_new: Optional[int]
    content: str
    change_type: Literal["unchanged", "added", "removed", "context"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line_number_old": self.line_number_old,
            "line_number_new": self.line_number_new,
            "content": self.content,
            "change_type": self.change_type
        }


@dataclass
class DiffHunk:
    """Represents a hunk (section) of changes in a diff"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[DiffLine] = field(default_factory=list)
    header: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "lines": [line.to_dict() for line in self.lines],
            "header": self.header
        }


@dataclass
class SafetyWarning:
    """A safety warning about a proposed change"""
    level: Literal["info", "warning", "critical"]
    message: str
    category: str  # e.g., "syntax", "security", "breaking_change"
    line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "message": self.message,
            "category": self.category,
            "line_number": self.line_number
        }


@dataclass
class ChangeProposal:
    """
    Represents a proposed change to a file.

    Contains all information needed to preview, review, and apply a change.
    """
    id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:12])

    # File information
    file_path: str = ""
    operation: ChangeOperation = ChangeOperation.EDIT

    # Content
    old_content: str = ""
    new_content: str = ""

    # For edit operations
    old_string: Optional[str] = None
    new_string: Optional[str] = None
    replace_all: bool = False

    # Diff information
    hunks: List[DiffHunk] = field(default_factory=list)
    unified_diff: str = ""

    # Statistics
    additions: int = 0
    deletions: int = 0
    modifications: int = 0

    # Safety & Analysis
    safety_warnings: List[SafetyWarning] = field(default_factory=list)
    impact_analysis: str = ""
    reasoning_context: str = ""
    confidence_level: float = 0.0

    # Status
    status: ChangeStatus = ChangeStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None

    # Review info
    approval_reason: Optional[str] = None
    rejection_reason: Optional[str] = None

    def compute_diff(self) -> None:
        """Compute diff between old and new content"""
        old_lines = self.old_content.splitlines(keepends=True)
        new_lines = self.new_content.splitlines(keepends=True)

        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{os.path.basename(self.file_path)}",
            tofile=f"b/{os.path.basename(self.file_path)}",
            lineterm=""
        ))
        self.unified_diff = "\n".join(diff_lines)

        # Parse into hunks
        self.hunks = self._parse_unified_diff(diff_lines)

        # Calculate statistics
        self._calculate_stats()

    def _parse_unified_diff(self, diff_lines: List[str]) -> List[DiffHunk]:
        """Parse unified diff into structured hunks"""
        hunks = []
        current_hunk = None
        old_line = 0
        new_line = 0

        for line in diff_lines:
            # Skip file headers
            if line.startswith('---') or line.startswith('+++'):
                continue

            # Hunk header
            if line.startswith('@@'):
                if current_hunk:
                    hunks.append(current_hunk)

                # Parse @@ -old_start,old_count +new_start,new_count @@
                import re
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)', line)
                if match:
                    current_hunk = DiffHunk(
                        old_start=int(match.group(1)),
                        old_count=int(match.group(2) or 1),
                        new_start=int(match.group(3)),
                        new_count=int(match.group(4) or 1),
                        header=match.group(5).strip() if match.group(5) else ""
                    )
                    old_line = current_hunk.old_start
                    new_line = current_hunk.new_start
                continue

            if current_hunk is None:
                continue

            # Parse diff lines
            if line.startswith('+'):
                current_hunk.lines.append(DiffLine(
                    line_number_old=None,
                    line_number_new=new_line,
                    content=line[1:],
                    change_type="added"
                ))
                new_line += 1
            elif line.startswith('-'):
                current_hunk.lines.append(DiffLine(
                    line_number_old=old_line,
                    line_number_new=None,
                    content=line[1:],
                    change_type="removed"
                ))
                old_line += 1
            elif line.startswith(' '):
                current_hunk.lines.append(DiffLine(
                    line_number_old=old_line,
                    line_number_new=new_line,
                    content=line[1:],
                    change_type="unchanged"
                ))
                old_line += 1
                new_line += 1
            else:
                # Context line without prefix
                current_hunk.lines.append(DiffLine(
                    line_number_old=old_line,
                    line_number_new=new_line,
                    content=line,
                    change_type="context"
                ))
                old_line += 1
                new_line += 1

        if current_hunk:
            hunks.append(current_hunk)

        return hunks

    def _calculate_stats(self) -> None:
        """Calculate change statistics"""
        self.additions = 0
        self.deletions = 0

        for hunk in self.hunks:
            for line in hunk.lines:
                if line.change_type == "added":
                    self.additions += 1
                elif line.change_type == "removed":
                    self.deletions += 1

        # Modifications are paired additions/deletions
        self.modifications = min(self.additions, self.deletions)

    def analyze_safety(self) -> None:
        """Analyze the change for potential safety issues"""
        self.safety_warnings = []

        # Check for syntax issues in Python files
        if self.file_path.endswith('.py'):
            self._check_python_syntax()

        # Check for potential security issues
        self._check_security_patterns()

        # Check for breaking changes
        self._check_breaking_changes()

        # Check for large changes
        self._check_change_size()

    def _check_python_syntax(self) -> None:
        """Check for Python syntax issues"""
        # Bracket matching
        brackets = {'(': ')', '[': ']', '{': '}'}
        for char, closing in brackets.items():
            if self.new_content.count(char) != self.new_content.count(closing):
                self.safety_warnings.append(SafetyWarning(
                    level="warning",
                    message=f"Mismatched {char}{closing} brackets",
                    category="syntax"
                ))

        # Triple quote matching
        if self.new_content.count('"""') % 2 != 0:
            self.safety_warnings.append(SafetyWarning(
                level="warning",
                message="Unclosed triple-quote string",
                category="syntax"
            ))

        # Try to compile for syntax errors
        try:
            compile(self.new_content, self.file_path, 'exec')
        except SyntaxError as e:
            self.safety_warnings.append(SafetyWarning(
                level="critical",
                message=f"Syntax error: {e.msg}",
                category="syntax",
                line_number=e.lineno
            ))

    def _check_security_patterns(self) -> None:
        """Check for potential security issues"""
        security_patterns = [
            (r'eval\s*\(', "Use of eval() - potential code injection"),
            (r'exec\s*\(', "Use of exec() - potential code injection"),
            (r'__import__\s*\(', "Dynamic import - potential security risk"),
            (r'os\.system\s*\(', "Shell command execution - verify input sanitization"),
            (r'subprocess\..*shell\s*=\s*True', "Shell=True in subprocess - potential injection"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
        ]

        import re
        for pattern, message in security_patterns:
            # Check if pattern is newly introduced
            if re.search(pattern, self.new_content, re.IGNORECASE):
                if not re.search(pattern, self.old_content, re.IGNORECASE):
                    self.safety_warnings.append(SafetyWarning(
                        level="warning",
                        message=message,
                        category="security"
                    ))

    def _check_breaking_changes(self) -> None:
        """Check for potential breaking changes"""
        import re

        # Check for removed function/class definitions
        old_funcs = set(re.findall(r'def\s+(\w+)\s*\(', self.old_content))
        new_funcs = set(re.findall(r'def\s+(\w+)\s*\(', self.new_content))
        removed_funcs = old_funcs - new_funcs

        for func in removed_funcs:
            self.safety_warnings.append(SafetyWarning(
                level="warning",
                message=f"Function '{func}' removed - may break dependent code",
                category="breaking_change"
            ))

        old_classes = set(re.findall(r'class\s+(\w+)\s*[:\(]', self.old_content))
        new_classes = set(re.findall(r'class\s+(\w+)\s*[:\(]', self.new_content))
        removed_classes = old_classes - new_classes

        for cls in removed_classes:
            self.safety_warnings.append(SafetyWarning(
                level="warning",
                message=f"Class '{cls}' removed - may break dependent code",
                category="breaking_change"
            ))

    def _check_change_size(self) -> None:
        """Check if change is unusually large"""
        total_changes = self.additions + self.deletions

        if total_changes > 100:
            self.safety_warnings.append(SafetyWarning(
                level="info",
                message=f"Large change: {total_changes} lines affected",
                category="size"
            ))

        # Check if most of the file is being changed
        old_lines = len(self.old_content.splitlines())
        if old_lines > 0:
            change_ratio = self.deletions / old_lines
            if change_ratio > 0.5:
                self.safety_warnings.append(SafetyWarning(
                    level="info",
                    message=f"Significant rewrite: {change_ratio:.0%} of file changed",
                    category="size"
                ))

    def get_summary(self) -> str:
        """Get a brief summary of the change"""
        op_name = self.operation.value.replace("_", " ").title()
        return f"{op_name}: {self.file_path} (+{self.additions}/-{self.deletions})"

    def has_critical_warnings(self) -> bool:
        """Check if there are any critical warnings"""
        return any(w.level == "critical" for w in self.safety_warnings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "operation": self.operation.value,
            "old_content_length": len(self.old_content),
            "new_content_length": len(self.new_content),
            "hunks": [h.to_dict() for h in self.hunks],
            "unified_diff": self.unified_diff,
            "additions": self.additions,
            "deletions": self.deletions,
            "modifications": self.modifications,
            "safety_warnings": [w.to_dict() for w in self.safety_warnings],
            "impact_analysis": self.impact_analysis,
            "confidence_level": self.confidence_level,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None
        }


@dataclass
class ChangeSet:
    """A collection of related changes to be reviewed together"""
    id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:12])
    name: str = ""
    description: str = ""
    proposals: List[ChangeProposal] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_proposal(self, proposal: ChangeProposal) -> None:
        """Add a change proposal to the set"""
        self.proposals.append(proposal)

    def get_total_stats(self) -> Dict[str, int]:
        """Get aggregate statistics for all changes"""
        return {
            "files": len(self.proposals),
            "additions": sum(p.additions for p in self.proposals),
            "deletions": sum(p.deletions for p in self.proposals),
            "warnings": sum(len(p.safety_warnings) for p in self.proposals),
            "critical_warnings": sum(1 for p in self.proposals if p.has_critical_warnings())
        }

    def all_approved(self) -> bool:
        """Check if all proposals are approved"""
        return all(p.status == ChangeStatus.APPROVED for p in self.proposals)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "proposals": [p.to_dict() for p in self.proposals],
            "stats": self.get_total_stats(),
            "created_at": self.created_at.isoformat()
        }


class DiffPreviewTool(BaseTool):
    """
    Preview file changes before applying them.

    Generates a detailed diff preview with safety analysis.
    Does NOT modify any files - only shows what would change.
    """

    def __init__(self, root_dir: Optional[str] = None, console: Optional[Any] = None):
        super().__init__()
        self.name = "DiffPreview"
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())
        self._console = console
        self._pending_proposals: Dict[str, ChangeProposal] = {}

    def get_description(self) -> str:
        return """Preview file changes before applying them.

Shows a detailed diff of proposed changes including:
- Line-by-line comparison
- Safety warnings (syntax errors, security issues)
- Change statistics (additions, deletions)

Use this before Edit or Write to review changes safely."""

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("file_path", "string", "Path to the file to preview changes for", required=True),
            ToolParameter("old_string", "string", "String to be replaced (for edit preview)", required=False),
            ToolParameter("new_string", "string", "Replacement string (for edit preview)", required=False),
            ToolParameter("new_content", "string", "New file content (for write preview)", required=False),
            ToolParameter("replace_all", "boolean", "Replace all occurrences", default=False),
            ToolParameter("context_lines", "integer", "Lines of context around changes", default=3),
        ]

    async def execute(
        self,
        file_path: str,
        old_string: Optional[str] = None,
        new_string: Optional[str] = None,
        new_content: Optional[str] = None,
        replace_all: bool = False,
        context_lines: int = 3,
        **kwargs
    ) -> ToolResult:
        """Generate a preview of proposed changes"""
        try:
            path = Path(file_path)

            # Determine operation type
            if new_content is not None:
                operation = ChangeOperation.WRITE if path.exists() else ChangeOperation.CREATE
            elif old_string is not None and new_string is not None:
                operation = ChangeOperation.EDIT
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Must provide either (old_string, new_string) for edit or new_content for write"
                )

            # Get current content
            old_content = ""
            if path.exists():
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    old_content = f.read()

            # Calculate new content
            if operation in (ChangeOperation.WRITE, ChangeOperation.CREATE):
                final_new_content = new_content
            else:
                # Edit operation
                if old_string not in old_content:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"String not found in file: {old_string[:100]}..."
                    )

                count = old_content.count(old_string)
                if not replace_all and count > 1:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"String appears {count} times. Use replace_all=True or provide more context."
                    )

                if replace_all:
                    final_new_content = old_content.replace(old_string, new_string)
                else:
                    final_new_content = old_content.replace(old_string, new_string, 1)

            # Create proposal
            proposal = ChangeProposal(
                file_path=str(path),
                operation=operation,
                old_content=old_content,
                new_content=final_new_content,
                old_string=old_string,
                new_string=new_string,
                replace_all=replace_all
            )

            # Compute diff and analyze
            proposal.compute_diff()
            proposal.analyze_safety()

            # Store for later application
            self._pending_proposals[proposal.id] = proposal

            # Display the preview
            preview_output = self._format_preview(proposal, context_lines)

            # Display using Rich if available
            if self._console:
                self._display_rich_preview(proposal)

            return ToolResult(
                success=True,
                output=preview_output,
                metadata={
                    "proposal_id": proposal.id,
                    "file_path": str(path),
                    "operation": operation.value,
                    "additions": proposal.additions,
                    "deletions": proposal.deletions,
                    "warnings_count": len(proposal.safety_warnings),
                    "has_critical": proposal.has_critical_warnings()
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _format_preview(self, proposal: ChangeProposal, context_lines: int = 3) -> str:
        """Format the preview as text output"""
        lines = []

        # Header
        lines.append(f"{'='*60}")
        lines.append(f"CHANGE PREVIEW: {proposal.file_path}")
        lines.append(f"Operation: {proposal.operation.value.upper()}")
        lines.append(f"Proposal ID: {proposal.id}")
        lines.append(f"{'='*60}")

        # Statistics
        lines.append(f"\nStatistics:")
        lines.append(f"  + {proposal.additions} additions")
        lines.append(f"  - {proposal.deletions} deletions")
        lines.append(f"  ~ {proposal.modifications} modifications")

        # Safety warnings
        if proposal.safety_warnings:
            lines.append(f"\n{'!'*40}")
            lines.append("SAFETY WARNINGS:")
            for warning in proposal.safety_warnings:
                icon = {"info": "i", "warning": "!", "critical": "X"}[warning.level]
                line_info = f" (line {warning.line_number})" if warning.line_number else ""
                lines.append(f"  [{icon}] [{warning.category}] {warning.message}{line_info}")
            lines.append(f"{'!'*40}")

        # Diff
        lines.append(f"\nDiff:")
        lines.append("-" * 40)

        for hunk in proposal.hunks:
            lines.append(f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@")
            for diff_line in hunk.lines:
                prefix = {
                    "added": "+",
                    "removed": "-",
                    "unchanged": " ",
                    "context": " "
                }[diff_line.change_type]
                lines.append(f"{prefix}{diff_line.content}")

        lines.append("-" * 40)
        lines.append(f"\nTo apply this change, use: apply_change(proposal_id='{proposal.id}')")

        return "\n".join(lines)

    def _display_rich_preview(self, proposal: ChangeProposal) -> None:
        """Display preview using Rich console"""
        try:
            from ..ui import DiffDisplay
            from rich.panel import Panel
            from rich.text import Text

            # Create diff panel
            diff_panel = DiffDisplay.render(
                filename=os.path.basename(proposal.file_path),
                old_content=proposal.old_content,
                new_content=proposal.new_content,
                context_lines=3,
                show_stats=True
            )

            self._console.print(diff_panel)

            # Show warnings if any
            if proposal.safety_warnings:
                warning_text = Text()
                warning_text.append("Safety Warnings:\n", style="bold yellow")
                for w in proposal.safety_warnings:
                    style = {"info": "blue", "warning": "yellow", "critical": "red bold"}[w.level]
                    warning_text.append(f"  [{w.level.upper()}] ", style=style)
                    warning_text.append(f"{w.message}\n")

                self._console.print(Panel(warning_text, border_style="yellow"))

        except ImportError:
            pass  # Rich not available

    def get_pending_proposal(self, proposal_id: str) -> Optional[ChangeProposal]:
        """Get a pending proposal by ID"""
        return self._pending_proposals.get(proposal_id)

    def clear_pending(self, proposal_id: Optional[str] = None) -> None:
        """Clear pending proposals"""
        if proposal_id:
            self._pending_proposals.pop(proposal_id, None)
        else:
            self._pending_proposals.clear()


class ApplyChangeTool(BaseTool):
    """
    Apply a previously previewed change.

    Requires a proposal_id from DiffPreview.
    """

    def __init__(self, diff_preview_tool: DiffPreviewTool):
        super().__init__()
        self.name = "ApplyChange"
        self.category = ToolCategory.FILE_OPERATION
        self.diff_preview = diff_preview_tool

    def get_description(self) -> str:
        return """Apply a previously previewed change.

Requires a proposal_id from a DiffPreview call.
The change will only be applied if it was previously previewed."""

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("proposal_id", "string", "ID of the change proposal to apply", required=True),
            ToolParameter("force", "boolean", "Apply even with critical warnings", default=False),
        ]

    async def execute(
        self,
        proposal_id: str,
        force: bool = False,
        **kwargs
    ) -> ToolResult:
        """Apply a previewed change"""
        try:
            # Get proposal
            proposal = self.diff_preview.get_pending_proposal(proposal_id)

            if not proposal:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"No pending proposal found with ID: {proposal_id}"
                )

            # Check for critical warnings
            if proposal.has_critical_warnings() and not force:
                warnings = [w.message for w in proposal.safety_warnings if w.level == "critical"]
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Critical warnings found. Use force=True to override:\n" + "\n".join(warnings)
                )

            # Apply the change
            path = Path(proposal.file_path)

            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write new content
            with open(path, 'w', encoding='utf-8') as f:
                f.write(proposal.new_content)

            # Update proposal status
            proposal.status = ChangeStatus.APPLIED
            proposal.applied_at = datetime.now()

            # Clear from pending
            self.diff_preview.clear_pending(proposal_id)

            return ToolResult(
                success=True,
                output=f"Change applied successfully: {proposal.get_summary()}",
                metadata={
                    "proposal_id": proposal_id,
                    "file_path": proposal.file_path,
                    "additions": proposal.additions,
                    "deletions": proposal.deletions
                }
            )

        except Exception as e:
            if proposal:
                proposal.status = ChangeStatus.FAILED
            return ToolResult(success=False, output=None, error=str(e))


class RejectChangeTool(BaseTool):
    """
    Reject a previously previewed change.
    """

    def __init__(self, diff_preview_tool: DiffPreviewTool):
        super().__init__()
        self.name = "RejectChange"
        self.category = ToolCategory.FILE_OPERATION
        self.diff_preview = diff_preview_tool

    def get_description(self) -> str:
        return "Reject a previously previewed change, removing it from pending proposals."

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("proposal_id", "string", "ID of the change proposal to reject", required=True),
            ToolParameter("reason", "string", "Reason for rejection", required=False),
        ]

    async def execute(
        self,
        proposal_id: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Reject a change proposal"""
        try:
            proposal = self.diff_preview.get_pending_proposal(proposal_id)

            if not proposal:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"No pending proposal found with ID: {proposal_id}"
                )

            proposal.status = ChangeStatus.REJECTED
            proposal.rejection_reason = reason
            proposal.reviewed_at = datetime.now()

            self.diff_preview.clear_pending(proposal_id)

            return ToolResult(
                success=True,
                output=f"Change rejected: {proposal.file_path}" + (f" - {reason}" if reason else ""),
                metadata={"proposal_id": proposal_id, "reason": reason}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
