"""
Change Reviewer for Hcode.

Provides an interactive workflow for reviewing and approving proposed changes
before they are applied to files. Integrates with the reasoning system to
provide context-aware change analysis.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Awaitable

from hcode.tools.diff_tools import (
    ChangeProposal,
    ChangeOperation,
    ChangeStatus,
)


class ReviewMode(Enum):
    """Review mode determines how changes are handled"""

    AUTO_APPROVE = "auto"  # Apply changes without review (dangerous)
    PREVIEW_ONLY = "preview"  # Show preview, require explicit apply
    INTERACTIVE = "interactive"  # Interactive approval for each change
    BATCH = "batch"  # Collect changes, review all at once


class ReviewDecision(Enum):
    """User's decision on a proposed change"""

    APPROVE = "approve"
    APPROVE_ALL = "approve_all"
    REJECT = "reject"
    REJECT_ALL = "reject_all"
    SKIP = "skip"
    EDIT = "edit"  # User wants to modify the change


@dataclass
class ReviewResult:
    """Result of a change review"""

    proposal_id: str
    decision: ReviewDecision
    modified_content: Optional[str] = None  # If user edited the change
    reason: Optional[str] = None
    reviewed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "decision": self.decision.value,
            "modified_content": self.modified_content is not None,
            "reason": self.reason,
            "reviewed_at": self.reviewed_at.isoformat(),
        }


@dataclass
class ReviewSession:
    """A session of reviewing multiple changes"""

    id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    proposals: List[ChangeProposal] = field(default_factory=list)
    results: List[ReviewResult] = field(default_factory=list)
    mode: ReviewMode = ReviewMode.INTERACTIVE
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def add_proposal(self, proposal: ChangeProposal) -> None:
        """Add a proposal to the session"""
        self.proposals.append(proposal)

    def add_result(self, result: ReviewResult) -> None:
        """Add a review result"""
        self.results.append(result)

    def is_complete(self) -> bool:
        """Check if all proposals have been reviewed"""
        return len(self.results) >= len(self.proposals)

    def get_approved_count(self) -> int:
        """Get count of approved changes"""
        return sum(
            1
            for r in self.results
            if r.decision in (ReviewDecision.APPROVE, ReviewDecision.APPROVE_ALL)
        )

    def get_rejected_count(self) -> int:
        """Get count of rejected changes"""
        return sum(
            1
            for r in self.results
            if r.decision in (ReviewDecision.REJECT, ReviewDecision.REJECT_ALL)
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        return {
            "id": self.id,
            "total_proposals": len(self.proposals),
            "reviewed": len(self.results),
            "approved": self.get_approved_count(),
            "rejected": self.get_rejected_count(),
            "pending": len(self.proposals) - len(self.results),
            "complete": self.is_complete(),
        }


class ChangeReviewer:
    """
    Manages the change review workflow.

    Provides methods to:
    - Queue changes for review
    - Display change previews
    - Collect user approval/rejection
    - Apply approved changes
    - Track review history
    """

    def __init__(
        self,
        mode: ReviewMode = ReviewMode.INTERACTIVE,
        console: Optional[Any] = None,
        auto_approve_threshold: float = 0.9,  # Confidence threshold for auto-approve
    ):
        """
        Initialize the change reviewer.

        Args:
            mode: Review mode to use
            console: Rich console for display
            auto_approve_threshold: Confidence level above which to auto-approve
        """
        self.mode = mode
        self.console = console
        self.auto_approve_threshold = auto_approve_threshold

        # Current session
        self.current_session: Optional[ReviewSession] = None

        # Pending proposals not yet in a session
        self.pending_proposals: Dict[str, ChangeProposal] = {}

        # History of all sessions
        self.session_history: List[ReviewSession] = []

        # Callbacks for custom approval logic
        self._approval_callback: Optional[Callable[[ChangeProposal], Awaitable[ReviewDecision]]] = (
            None
        )

    def set_mode(self, mode: ReviewMode) -> None:
        """Set the review mode"""
        self.mode = mode

    def set_approval_callback(
        self, callback: Callable[[ChangeProposal], Awaitable[ReviewDecision]]
    ) -> None:
        """Set custom approval callback"""
        self._approval_callback = callback

    def propose_change(self, proposal: ChangeProposal) -> str:
        """
        Queue a change for review.

        Args:
            proposal: The change proposal

        Returns:
            Proposal ID
        """
        # Compute diff and analyze safety
        proposal.compute_diff()
        proposal.analyze_safety()

        # Store in pending
        self.pending_proposals[proposal.id] = proposal

        return proposal.id

    def start_session(self) -> ReviewSession:
        """Start a new review session with all pending proposals"""
        session = ReviewSession(mode=self.mode)

        # Move pending proposals to session
        for proposal in self.pending_proposals.values():
            session.add_proposal(proposal)

        self.pending_proposals.clear()
        self.current_session = session

        return session

    async def review_proposal(self, proposal: ChangeProposal) -> ReviewResult:
        """
        Review a single proposal.

        Args:
            proposal: The proposal to review

        Returns:
            Review result
        """
        # Display the preview
        self._display_proposal(proposal)

        # Determine decision based on mode
        if self.mode == ReviewMode.AUTO_APPROVE:
            decision = self._auto_decide(proposal)
        elif self._approval_callback:
            decision = await self._approval_callback(proposal)
        else:
            decision = await self._interactive_decide(proposal)

        result = ReviewResult(proposal_id=proposal.id, decision=decision)

        # Update proposal status based on decision
        if decision in (ReviewDecision.APPROVE, ReviewDecision.APPROVE_ALL):
            proposal.status = ChangeStatus.APPROVED
            proposal.reviewed_at = datetime.now()
        elif decision in (ReviewDecision.REJECT, ReviewDecision.REJECT_ALL):
            proposal.status = ChangeStatus.REJECTED
            proposal.reviewed_at = datetime.now()

        return result

    def _auto_decide(self, proposal: ChangeProposal) -> ReviewDecision:
        """Auto-decide based on confidence and safety"""
        # Reject if critical warnings
        if proposal.has_critical_warnings():
            return ReviewDecision.REJECT

        # Approve if confidence is high enough
        if proposal.confidence_level >= self.auto_approve_threshold:
            return ReviewDecision.APPROVE

        # Default to requiring manual review
        return ReviewDecision.SKIP

    async def _interactive_decide(self, proposal: ChangeProposal) -> ReviewDecision:
        """Get interactive decision from user"""
        if not self.console:
            return ReviewDecision.APPROVE  # Fallback

        try:
            from rich.prompt import Prompt

            # Show options
            self.console.print("\n[bold yellow]Review this change?[/bold yellow]")
            self.console.print(
                "[green]y/yes[/green] - Approve | [red]n/no[/red] - Reject | [blue]s/skip[/blue] - Skip"
            )
            self.console.print(
                "[cyan]a/all[/cyan] - Approve all | [magenta]r/reject-all[/magenta] - Reject all"
            )

            response = Prompt.ask(
                "[bold]Decision[/bold]",
                default="y",
                choices=["y", "yes", "n", "no", "s", "skip", "a", "all", "r", "reject-all"],
            )

            response = response.lower()
            if response in ("y", "yes"):
                return ReviewDecision.APPROVE
            elif response in ("n", "no"):
                return ReviewDecision.REJECT
            elif response in ("s", "skip"):
                return ReviewDecision.SKIP
            elif response in ("a", "all"):
                return ReviewDecision.APPROVE_ALL
            elif response in ("r", "reject-all"):
                return ReviewDecision.REJECT_ALL

        except (EOFError, KeyboardInterrupt):
            return ReviewDecision.SKIP

        return ReviewDecision.APPROVE

    def _display_proposal(self, proposal: ChangeProposal) -> None:
        """Display a proposal preview"""
        if not self.console:
            return

        try:
            from rich.panel import Panel
            from rich.text import Text
            from rich.table import Table
            from ..ui import DiffDisplay

            # Header
            header = Text()
            header.append("\n")
            header.append("=" * 60 + "\n", style="dim")
            header.append("CHANGE PREVIEW: ", style="bold cyan")
            header.append(proposal.file_path, style="bold white")
            header.append("\n")
            header.append(f"Operation: {proposal.operation.value.upper()}", style="yellow")
            header.append(f" | ID: {proposal.id}", style="dim")
            header.append("\n" + "=" * 60, style="dim")

            self.console.print(header)

            # Statistics
            stats = Table(show_header=False, box=None)
            stats.add_column("Label", style="dim")
            stats.add_column("Value")
            stats.add_row("Additions", f"[green]+{proposal.additions}[/green]")
            stats.add_row("Deletions", f"[red]-{proposal.deletions}[/red]")
            stats.add_row("Modifications", f"[yellow]~{proposal.modifications}[/yellow]")
            self.console.print(stats)

            # Safety warnings
            if proposal.safety_warnings:
                self.console.print("\n[bold yellow]Safety Warnings:[/bold yellow]")
                for warning in proposal.safety_warnings:
                    style = {"info": "blue", "warning": "yellow", "critical": "red bold"}[
                        warning.level
                    ]
                    line_info = f" (line {warning.line_number})" if warning.line_number else ""
                    self.console.print(
                        f"  [{style}][{warning.level.upper()}][/{style}] {warning.message}{line_info}"
                    )

            # Diff display
            diff_panel = DiffDisplay.render(
                filename=os.path.basename(proposal.file_path),
                old_content=proposal.old_content,
                new_content=proposal.new_content,
                context_lines=3,
                show_stats=False,
            )
            self.console.print(diff_panel)

        except ImportError:
            # Fallback text display
            self.console.print(f"\n{'='*60}")
            self.console.print(f"CHANGE: {proposal.file_path}")
            self.console.print(f"Operation: {proposal.operation.value}")
            self.console.print(f"+{proposal.additions} / -{proposal.deletions}")
            if proposal.safety_warnings:
                for w in proposal.safety_warnings:
                    self.console.print(f"[{w.level}] {w.message}")
            self.console.print(proposal.unified_diff)
            self.console.print("=" * 60)

    async def review_all(self) -> List[ReviewResult]:
        """
        Review all proposals in the current session.

        Returns:
            List of review results
        """
        if not self.current_session:
            self.start_session()

        results = []
        approve_all = False
        reject_all = False

        for proposal in self.current_session.proposals:
            if approve_all:
                result = ReviewResult(proposal_id=proposal.id, decision=ReviewDecision.APPROVE)
                proposal.status = ChangeStatus.APPROVED
            elif reject_all:
                result = ReviewResult(proposal_id=proposal.id, decision=ReviewDecision.REJECT)
                proposal.status = ChangeStatus.REJECTED
            else:
                result = await self.review_proposal(proposal)

                # Check for all decisions
                if result.decision == ReviewDecision.APPROVE_ALL:
                    approve_all = True
                    result.decision = ReviewDecision.APPROVE
                    proposal.status = ChangeStatus.APPROVED
                elif result.decision == ReviewDecision.REJECT_ALL:
                    reject_all = True
                    result.decision = ReviewDecision.REJECT
                    proposal.status = ChangeStatus.REJECTED

            results.append(result)
            self.current_session.add_result(result)

        self.current_session.completed_at = datetime.now()
        self.session_history.append(self.current_session)

        return results

    async def apply_approved(self) -> Dict[str, Any]:
        """
        Apply all approved changes from the current session.

        Returns:
            Summary of applied changes
        """
        if not self.current_session:
            return {"error": "No active session"}

        applied = []
        failed = []

        for proposal in self.current_session.proposals:
            if proposal.status != ChangeStatus.APPROVED:
                continue

            try:
                path = Path(proposal.file_path)
                path.parent.mkdir(parents=True, exist_ok=True)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(proposal.new_content)

                proposal.status = ChangeStatus.APPLIED
                proposal.applied_at = datetime.now()
                applied.append(proposal.id)

            except Exception as e:
                proposal.status = ChangeStatus.FAILED
                failed.append({"id": proposal.id, "error": str(e)})

        return {
            "applied": len(applied),
            "failed": len(failed),
            "applied_ids": applied,
            "failures": failed,
        }

    def get_pending_count(self) -> int:
        """Get count of pending proposals"""
        return len(self.pending_proposals)

    def get_session_summary(self) -> Optional[Dict[str, Any]]:
        """Get current session summary"""
        if self.current_session:
            return self.current_session.get_summary()
        return None

    def clear_session(self) -> None:
        """Clear the current session"""
        self.current_session = None
        self.pending_proposals.clear()


class ChangeReviewContext:
    """
    Context manager for scoped change review.

    Usage:
        async with ChangeReviewContext(reviewer) as ctx:
            ctx.propose(edit_proposal)
            ctx.propose(write_proposal)
            # Changes reviewed and applied on exit if approved
    """

    def __init__(self, reviewer: ChangeReviewer, auto_apply: bool = True):
        self.reviewer = reviewer
        self.auto_apply = auto_apply
        self.proposals: List[ChangeProposal] = []

    def propose(self, proposal: ChangeProposal) -> str:
        """Add a proposal to this context"""
        proposal_id = self.reviewer.propose_change(proposal)
        self.proposals.append(proposal)
        return proposal_id

    async def __aenter__(self) -> "ChangeReviewContext":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            # Exception occurred, don't apply changes
            self.reviewer.clear_session()
            return

        # Start review session
        self.reviewer.start_session()

        # Review all changes
        results = await self.reviewer.review_all()

        # Apply if requested
        if self.auto_apply:
            await self.reviewer.apply_approved()


# Helper function for quick change review
async def review_change(
    file_path: str,
    old_content: str,
    new_content: str,
    operation: ChangeOperation = ChangeOperation.EDIT,
    console: Optional[Any] = None,
    mode: ReviewMode = ReviewMode.INTERACTIVE,
) -> bool:
    """
    Quick helper to review a single change.

    Args:
        file_path: Path to the file
        old_content: Current content
        new_content: Proposed new content
        operation: Type of operation
        console: Rich console for display
        mode: Review mode

    Returns:
        True if change was approved
    """
    proposal = ChangeProposal(
        file_path=file_path, operation=operation, old_content=old_content, new_content=new_content
    )

    reviewer = ChangeReviewer(mode=mode, console=console)
    reviewer.propose_change(proposal)
    reviewer.start_session()

    results = await reviewer.review_all()

    if results and results[0].decision == ReviewDecision.APPROVE:
        await reviewer.apply_approved()
        return True

    return False
