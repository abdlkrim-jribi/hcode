"""
Thinking-Execution Feedback Loop.

This module provides mechanisms for:
- Capturing execution results and feeding them back to reasoning
- Validating hypotheses against actual outcomes
- Refining reasoning based on new information
- Enabling iterative improvement of decisions

Designed for continuous learning and adaptation during task execution.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any, Callable, Tuple

logger = logging.getLogger(__name__)

from hcode.core.reasoning import (
    StructuredReasoning,
    ReasoningParser,
    ConfidenceCalibrator,
    ReasoningQualityMetrics,
)


class ExecutionStatus(Enum):
    """Status of an execution"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class FeedbackType(Enum):
    """Types of feedback from execution"""

    CONFIRMATION = "confirmation"  # Hypothesis confirmed
    CONTRADICTION = "contradiction"  # Hypothesis contradicted
    UNEXPECTED = "unexpected"  # Unexpected result
    PARTIAL = "partial"  # Partially as expected
    ERROR = "error"  # Execution error
    TIMEOUT = "timeout"  # Operation timed out


@dataclass
class ExecutionResult:
    """Result of a tool/action execution"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    action_description: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    output: str = ""
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_success(self) -> bool:
        return self.status in [ExecutionStatus.SUCCESS, ExecutionStatus.PARTIAL]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "action_description": self.action_description,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class FeedbackEntry:
    """A single feedback entry from execution to reasoning"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reasoning_id: str = ""
    execution_id: str = ""
    feedback_type: FeedbackType = FeedbackType.CONFIRMATION

    # What was expected vs what happened
    expected: str = ""
    actual: str = ""
    deviation: str = ""

    # Impact assessment
    impact_level: str = "low"  # low, medium, high, critical
    requires_replanning: bool = False

    # Lessons learned
    lessons: List[str] = field(default_factory=list)

    # Suggested adjustments
    suggested_adjustments: List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "reasoning_id": self.reasoning_id,
            "execution_id": self.execution_id,
            "feedback_type": self.feedback_type.value,
            "expected": self.expected,
            "actual": self.actual,
            "deviation": self.deviation,
            "impact_level": self.impact_level,
            "requires_replanning": self.requires_replanning,
            "lessons": self.lessons,
            "suggested_adjustments": self.suggested_adjustments,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ReasoningRevision:
    """A revision to reasoning based on feedback"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_reasoning_id: str = ""
    feedback_ids: List[str] = field(default_factory=list)

    # What changed
    revised_hypothesis: str = ""
    revised_decision: str = ""
    revised_confidence: float = 0.0
    new_action_items: List[str] = field(default_factory=list)
    removed_action_items: List[str] = field(default_factory=list)

    # Revision metadata
    revision_reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "original_reasoning_id": self.original_reasoning_id,
            "feedback_ids": self.feedback_ids,
            "revised_hypothesis": self.revised_hypothesis,
            "revised_decision": self.revised_decision,
            "revised_confidence": self.revised_confidence,
            "new_action_items": self.new_action_items,
            "removed_action_items": self.removed_action_items,
            "revision_reason": self.revision_reason,
            "timestamp": self.timestamp.isoformat(),
        }


class HypothesisValidator:
    """
    Validates reasoning hypotheses against execution results.

    Compares expected outcomes with actual results and
    determines the validity of the original reasoning.
    """

    def __init__(self):
        self.validation_history: List[Dict[str, Any]] = []

    def validate(
            self, reasoning: StructuredReasoning, execution_result: ExecutionResult
    ) -> Tuple[FeedbackType, Dict[str, Any]]:
        """
        Validate hypothesis against execution result.

        Args:
            reasoning: Original reasoning with hypothesis
            execution_result: Result of execution

        Returns:
            Tuple of (feedback_type, validation_details)
        """
        details = {
            "reasoning_id": reasoning.id,
            "execution_id": execution_result.id,
            "hypothesis": reasoning.reasoning.hypothesis,
            "expected_outcome": reasoning.decision.expected_outcome,
            "actual_outcome": execution_result.output,
            "execution_success": execution_result.is_success(),
            "timestamp": datetime.now().isoformat(),
        }

        # Determine feedback type based on execution result
        if execution_result.status == ExecutionStatus.FAILED:
            feedback_type = FeedbackType.ERROR
            details["reason"] = f"Execution failed: {execution_result.error}"

        elif execution_result.status == ExecutionStatus.TIMEOUT:
            feedback_type = FeedbackType.TIMEOUT
            details["reason"] = "Execution timed out"

        else:
            # Compare expected vs actual outcome
            feedback_type = self._compare_outcomes(
                expected=reasoning.decision.expected_outcome,
                actual=execution_result.output,
                hypothesis=reasoning.reasoning.hypothesis,
            )
            details["comparison"] = self._get_comparison_details(
                expected=reasoning.decision.expected_outcome, actual=execution_result.output
            )

        # Store in history
        self.validation_history.append({"feedback_type": feedback_type.value, **details})

        return feedback_type, details

    def _compare_outcomes(self, expected: str, actual: str, hypothesis: str) -> FeedbackType:
        """Compare expected vs actual outcomes"""
        if not expected or not actual:
            return FeedbackType.UNEXPECTED

        expected_lower = expected.lower()
        actual_lower = actual.lower()

        # Check for success indicators
        success_indicators = [
            "success",
            "completed",
            "done",
            "passed",
            "created",
            "updated",
            "fixed",
            "resolved",
            "ok",
            "true",
        ]

        failure_indicators = [
            "error",
            "failed",
            "exception",
            "not found",
            "denied",
            "invalid",
            "false",
            "timeout",
            "refused",
        ]

        # Count indicators in actual output
        success_count = sum(1 for ind in success_indicators if ind in actual_lower)
        failure_count = sum(1 for ind in failure_indicators if ind in actual_lower)

        # Determine feedback type
        if failure_count > success_count:
            return FeedbackType.CONTRADICTION
        elif success_count > 0 and failure_count == 0:
            return FeedbackType.CONFIRMATION
        elif success_count > 0 and failure_count > 0:
            return FeedbackType.PARTIAL
        else:
            # Check for keyword overlap between expected and actual
            expected_words = set(expected_lower.split())
            actual_words = set(actual_lower.split())
            overlap = len(expected_words & actual_words)

            if overlap > len(expected_words) * 0.5:
                return FeedbackType.CONFIRMATION
            elif overlap > len(expected_words) * 0.2:
                return FeedbackType.PARTIAL
            else:
                return FeedbackType.UNEXPECTED

    def _get_comparison_details(self, expected: str, actual: str) -> Dict[str, Any]:
        """Get detailed comparison between expected and actual"""
        return {
            "expected_length": len(expected),
            "actual_length": len(actual),
            "expected_preview": expected[:200] if expected else "",
            "actual_preview": actual[:200] if actual else "",
            "length_ratio": len(actual) / max(1, len(expected)),
        }

    def get_success_rate(self) -> float:
        """Get historical validation success rate"""
        if not self.validation_history:
            return 0.0

        confirmations = sum(
            1 for v in self.validation_history if v["feedback_type"] in ["confirmation", "partial"]
        )
        return confirmations / len(self.validation_history)


class FeedbackProcessor:
    """
    Processes execution feedback and determines required actions.

    Analyzes feedback to determine:
    - Whether replanning is needed
    - What adjustments to make
    - Lessons to incorporate
    """

    def __init__(self, confidence_calibrator: Optional[ConfidenceCalibrator] = None):
        self.calibrator = confidence_calibrator or ConfidenceCalibrator()
        self.processed_feedback: List[FeedbackEntry] = []

    def process(
            self,
            reasoning: StructuredReasoning,
            execution_result: ExecutionResult,
            feedback_type: FeedbackType,
            validation_details: Dict[str, Any],
    ) -> FeedbackEntry:
        """
        Process feedback and create feedback entry.

        Args:
            reasoning: Original reasoning
            execution_result: Execution result
            feedback_type: Type of feedback
            validation_details: Details from validation

        Returns:
            Processed feedback entry
        """
        entry = FeedbackEntry(
            reasoning_id=reasoning.id,
            execution_id=execution_result.id,
            feedback_type=feedback_type,
            expected=reasoning.decision.expected_outcome,
            actual=execution_result.output[:500] if execution_result.output else "",
        )

        # Calculate deviation
        entry.deviation = self._calculate_deviation(
            expected=entry.expected, actual=entry.actual, feedback_type=feedback_type
        )

        # Assess impact level
        entry.impact_level = self._assess_impact(
            feedback_type=feedback_type, reasoning=reasoning, execution_result=execution_result
        )

        # Determine if replanning needed
        entry.requires_replanning = self._requires_replanning(
            feedback_type=feedback_type,
            impact_level=entry.impact_level,
            confidence=reasoning.get_confidence(),
        )

        # Extract lessons
        entry.lessons = self._extract_lessons(
            feedback_type=feedback_type, reasoning=reasoning, execution_result=execution_result
        )

        # Generate suggested adjustments
        entry.suggested_adjustments = self._suggest_adjustments(
            feedback_type=feedback_type, reasoning=reasoning, execution_result=execution_result
        )

        # Update calibrator with outcome
        success = feedback_type in [FeedbackType.CONFIRMATION, FeedbackType.PARTIAL]
        self.calibrator.record_outcome(reasoning.id, success)

        # Store processed feedback
        self.processed_feedback.append(entry)

        return entry

    def _calculate_deviation(self, expected: str, actual: str, feedback_type: FeedbackType) -> str:
        """Calculate description of deviation"""
        if feedback_type == FeedbackType.CONFIRMATION:
            return "Outcome matches expectations"
        elif feedback_type == FeedbackType.PARTIAL:
            return "Outcome partially matches expectations"
        elif feedback_type == FeedbackType.CONTRADICTION:
            return "Outcome contradicts expectations"
        elif feedback_type == FeedbackType.UNEXPECTED:
            return "Unexpected outcome - neither confirms nor denies hypothesis"
        elif feedback_type == FeedbackType.ERROR:
            return f"Execution error prevented outcome verification"
        elif feedback_type == FeedbackType.TIMEOUT:
            return "Execution timed out before completion"
        return "Unknown deviation"

    def _assess_impact(
            self,
            feedback_type: FeedbackType,
            reasoning: StructuredReasoning,
            execution_result: ExecutionResult,
    ) -> str:
        """Assess impact level of the feedback"""
        if feedback_type == FeedbackType.ERROR:
            # Errors on high-confidence decisions are critical
            if reasoning.get_confidence() > 0.8:
                return "critical"
            return "high"

        elif feedback_type == FeedbackType.CONTRADICTION:
            return "high"

        elif feedback_type == FeedbackType.TIMEOUT:
            return "medium"

        elif feedback_type == FeedbackType.UNEXPECTED:
            return "medium"

        elif feedback_type == FeedbackType.PARTIAL:
            return "low"

        else:  # CONFIRMATION
            return "low"

    def _requires_replanning(
            self, feedback_type: FeedbackType, impact_level: str, confidence: float
    ) -> bool:
        """Determine if replanning is required"""
        # Always replan on critical impact
        if impact_level == "critical":
            return True

        # Replan on high impact with high original confidence
        if impact_level == "high" and confidence > 0.7:
            return True

        # Replan on contradictions
        if feedback_type == FeedbackType.CONTRADICTION:
            return True

        # Replan on errors
        if feedback_type == FeedbackType.ERROR:
            return True

        return False

    def _extract_lessons(
            self,
            feedback_type: FeedbackType,
            reasoning: StructuredReasoning,
            execution_result: ExecutionResult,
    ) -> List[str]:
        """Extract lessons from the feedback"""
        lessons = []

        if feedback_type == FeedbackType.CONTRADICTION:
            lessons.append("Initial hypothesis was incorrect")
            if reasoning.reasoning.evidence_against:
                lessons.append("Counter-evidence was more significant than initially assessed")
            else:
                lessons.append("Needed more counter-evidence consideration")

        elif feedback_type == FeedbackType.ERROR:
            lessons.append(f"Execution failed: {execution_result.error}")
            if reasoning.verification.potential_issues:
                lessons.append("Potential issues identified but not fully mitigated")
            else:
                lessons.append("Failed to identify execution risks")

        elif feedback_type == FeedbackType.TIMEOUT:
            lessons.append("Underestimated execution time")
            lessons.append("Consider breaking into smaller operations")

        elif feedback_type == FeedbackType.PARTIAL:
            lessons.append("Partial success - some assumptions held, others did not")

        elif feedback_type == FeedbackType.CONFIRMATION:
            lessons.append("Reasoning approach was effective")
            if reasoning.is_self_critical():
                lessons.append("Self-critical reasoning led to good outcome")

        return lessons

    def _suggest_adjustments(
            self,
            feedback_type: FeedbackType,
            reasoning: StructuredReasoning,
            execution_result: ExecutionResult,
    ) -> List[str]:
        """Suggest adjustments based on feedback"""
        adjustments = []

        if feedback_type == FeedbackType.CONTRADICTION:
            adjustments.append("Revise hypothesis based on new evidence")
            if reasoning.decision.fallback_plan:
                adjustments.append(f"Consider fallback: {reasoning.decision.fallback_plan}")
            adjustments.append("Re-evaluate assumptions that led to original decision")

        elif feedback_type == FeedbackType.ERROR:
            adjustments.append("Investigate error cause before retrying")
            if reasoning.verification.risk_mitigation:
                adjustments.append("Apply risk mitigation strategies")
            adjustments.append("Consider alternative approach from analysis phase")

        elif feedback_type == FeedbackType.TIMEOUT:
            adjustments.append("Increase timeout or break into smaller steps")
            adjustments.append("Verify resource availability")

        elif feedback_type == FeedbackType.PARTIAL:
            adjustments.append("Identify which parts succeeded and build on them")
            adjustments.append("Address failed components individually")

        elif feedback_type == FeedbackType.UNEXPECTED:
            adjustments.append("Analyze unexpected result to understand system behavior")
            adjustments.append("Update mental model of the system")

        return adjustments


class ReasoningReviser:
    """
    Revises reasoning based on accumulated feedback.

    Creates updated reasoning that incorporates lessons
    learned from execution feedback.
    """

    def __init__(self, parser: Optional[ReasoningParser] = None):
        self.parser = parser or ReasoningParser()
        self.revisions: List[ReasoningRevision] = []

    def revise(
            self, original_reasoning: StructuredReasoning, feedback_entries: List[FeedbackEntry]
    ) -> ReasoningRevision:
        """
        Create a revision based on feedback.

        Args:
            original_reasoning: Original reasoning to revise
            feedback_entries: Feedback from executions

        Returns:
            Reasoning revision with updates
        """
        revision = ReasoningRevision(
            original_reasoning_id=original_reasoning.id,
            feedback_ids=[f.id for f in feedback_entries],
        )

        # Analyze feedback patterns
        feedback_summary = self._summarize_feedback(feedback_entries)

        # Revise hypothesis if needed
        if feedback_summary["contradictions"] > 0 or feedback_summary["errors"] > 0:
            revision.revised_hypothesis = self._revise_hypothesis(
                original=original_reasoning.reasoning.hypothesis, feedback_entries=feedback_entries
            )

        # Revise decision if needed
        revision.revised_decision = self._revise_decision(
            original=original_reasoning.decision.decision,
            feedback_entries=feedback_entries,
            has_fallback=original_reasoning.has_fallback(),
            fallback=original_reasoning.decision.fallback_plan,
        )

        # Adjust confidence
        revision.revised_confidence = self._calculate_revised_confidence(
            original_confidence=original_reasoning.get_confidence(),
            feedback_summary=feedback_summary,
        )

        # Update action items
        revision.new_action_items, revision.removed_action_items = self._update_action_items(
            original_items=original_reasoning.decision.action_items,
            feedback_entries=feedback_entries,
        )

        # Generate revision reason
        revision.revision_reason = self._generate_revision_reason(feedback_summary=feedback_summary)

        # Store revision
        self.revisions.append(revision)

        return revision

    def _summarize_feedback(self, feedback_entries: List[FeedbackEntry]) -> Dict[str, Any]:
        """Summarize feedback entries"""
        summary = {
            "total": len(feedback_entries),
            "confirmations": 0,
            "contradictions": 0,
            "partials": 0,
            "errors": 0,
            "timeouts": 0,
            "unexpected": 0,
            "requires_replanning": 0,
            "lessons": [],
            "adjustments": [],
        }

        for entry in feedback_entries:
            if entry.feedback_type == FeedbackType.CONFIRMATION:
                summary["confirmations"] += 1
            elif entry.feedback_type == FeedbackType.CONTRADICTION:
                summary["contradictions"] += 1
            elif entry.feedback_type == FeedbackType.PARTIAL:
                summary["partials"] += 1
            elif entry.feedback_type == FeedbackType.ERROR:
                summary["errors"] += 1
            elif entry.feedback_type == FeedbackType.TIMEOUT:
                summary["timeouts"] += 1
            elif entry.feedback_type == FeedbackType.UNEXPECTED:
                summary["unexpected"] += 1

            if entry.requires_replanning:
                summary["requires_replanning"] += 1

            summary["lessons"].extend(entry.lessons)
            summary["adjustments"].extend(entry.suggested_adjustments)

        return summary

    def _revise_hypothesis(self, original: str, feedback_entries: List[FeedbackEntry]) -> str:
        """Revise hypothesis based on feedback"""
        contradictions = [
            f for f in feedback_entries if f.feedback_type == FeedbackType.CONTRADICTION
        ]

        if contradictions:
            # Build revised hypothesis incorporating contradicting evidence
            revision_points = []
            for c in contradictions:
                revision_points.append(f"- Original expectation: {c.expected[:100]}")
                revision_points.append(f"- Actual result: {c.actual[:100]}")

            return f"REVISED: {original}\n\nContradicting evidence:\n" + "\n".join(revision_points)

        return original

    def _revise_decision(
            self,
            original: str,
            feedback_entries: List[FeedbackEntry],
            has_fallback: bool,
            fallback: str,
    ) -> str:
        """Revise decision based on feedback"""
        errors = [f for f in feedback_entries if f.feedback_type == FeedbackType.ERROR]
        contradictions = [
            f for f in feedback_entries if f.feedback_type == FeedbackType.CONTRADICTION
        ]

        if errors or contradictions:
            if has_fallback and fallback:
                return f"SWITCH TO FALLBACK: {fallback}"
            else:
                adjustments = []
                for entry in feedback_entries:
                    adjustments.extend(entry.suggested_adjustments)

                if adjustments:
                    return f"REVISED: {original}\n\nAdjustments needed:\n" + "\n".join(
                        f"- {a}" for a in adjustments[:3]
                    )

        return original

    def _calculate_revised_confidence(
            self, original_confidence: float, feedback_summary: Dict[str, Any]
    ) -> float:
        """Calculate revised confidence based on feedback"""
        # Start with original
        confidence = original_confidence

        # Adjust based on feedback
        total = feedback_summary["total"]
        if total == 0:
            return confidence

        # Reduce confidence for contradictions and errors
        contradiction_rate = feedback_summary["contradictions"] / total
        error_rate = feedback_summary["errors"] / total

        confidence -= contradiction_rate * 0.3
        confidence -= error_rate * 0.2

        # Increase confidence for confirmations
        confirmation_rate = feedback_summary["confirmations"] / total
        confidence += confirmation_rate * 0.1

        # Clamp to valid range
        return max(0.1, min(0.95, confidence))

    def _update_action_items(
            self, original_items: List[str], feedback_entries: List[FeedbackEntry]
    ) -> Tuple[List[str], List[str]]:
        """Update action items based on feedback"""
        new_items = []
        removed_items = []

        # Collect all suggested adjustments
        all_adjustments = []
        for entry in feedback_entries:
            all_adjustments.extend(entry.suggested_adjustments)

        # Add new items from adjustments
        for adjustment in all_adjustments:
            if adjustment not in original_items and adjustment not in new_items:
                new_items.append(adjustment)

        # Mark items as removed if they caused errors
        error_entries = [f for f in feedback_entries if f.feedback_type == FeedbackType.ERROR]
        for error in error_entries:
            # Try to match error to original action item
            for item in original_items:
                if any(word in item.lower() for word in error.expected.lower().split()[:3]):
                    if item not in removed_items:
                        removed_items.append(item)

        return new_items, removed_items

    def _generate_revision_reason(self, feedback_summary: Dict[str, Any]) -> str:
        """Generate human-readable revision reason"""
        reasons = []

        if feedback_summary["contradictions"] > 0:
            reasons.append(f"{feedback_summary['contradictions']} hypothesis contradictions")

        if feedback_summary["errors"] > 0:
            reasons.append(f"{feedback_summary['errors']} execution errors")

        if feedback_summary["timeouts"] > 0:
            reasons.append(f"{feedback_summary['timeouts']} timeouts")

        if feedback_summary["requires_replanning"] > 0:
            reasons.append("replanning required")

        if reasons:
            return "Revision triggered by: " + ", ".join(reasons)

        return "No significant revision needed"


class ThinkingExecutionFeedbackLoop:
    """
    Main orchestrator for the thinking-execution feedback loop.

    Coordinates between reasoning, execution, validation,
    and revision components.
    """

    def __init__(
            self,
            confidence_calibrator: Optional[ConfidenceCalibrator] = None,
            quality_metrics: Optional[ReasoningQualityMetrics] = None,
    ):
        self.parser = ReasoningParser()
        self.validator = HypothesisValidator()
        self.calibrator = confidence_calibrator or ConfidenceCalibrator()
        self.processor = FeedbackProcessor(self.calibrator)
        self.reviser = ReasoningReviser(self.parser)
        self.metrics = quality_metrics or ReasoningQualityMetrics()

        # State tracking
        self.current_reasoning: Optional[StructuredReasoning] = None
        self.execution_results: List[ExecutionResult] = []
        self.feedback_entries: List[FeedbackEntry] = []
        self.pending_revisions: List[ReasoningRevision] = []

        # Listeners
        self.feedback_listeners: List[Callable[[FeedbackEntry], None]] = []
        self.revision_listeners: List[Callable[[ReasoningRevision], None]] = []

    def add_feedback_listener(self, listener: Callable[[FeedbackEntry], None]):
        """Add listener for feedback events"""
        self.feedback_listeners.append(listener)

    def add_revision_listener(self, listener: Callable[[ReasoningRevision], None]):
        """Add listener for revision events"""
        self.revision_listeners.append(listener)

    def set_reasoning(self, reasoning: StructuredReasoning):
        """
        Set the current reasoning being executed.

        Args:
            reasoning: Structured reasoning to track
        """
        self.current_reasoning = reasoning
        self.execution_results.clear()
        self.feedback_entries.clear()

        # Record confidence prediction for calibration
        self.calibrator.record_prediction(
            confidence=reasoning.get_confidence(),
            task_type=reasoning.level.name,
            reasoning_id=reasoning.id,
        )

        # Evaluate initial quality
        self.metrics.evaluate(reasoning)

    def record_execution(self, result: ExecutionResult) -> FeedbackEntry:
        """
        Record an execution result and generate feedback.

        Args:
            result: Result of tool/action execution

        Returns:
            Generated feedback entry
        """
        if not self.current_reasoning:
            raise ValueError("No current reasoning set")

        # Store result
        self.execution_results.append(result)

        # Validate against hypothesis
        feedback_type, validation_details = self.validator.validate(
            reasoning=self.current_reasoning, execution_result=result
        )

        # Process feedback
        feedback = self.processor.process(
            reasoning=self.current_reasoning,
            execution_result=result,
            feedback_type=feedback_type,
            validation_details=validation_details,
        )

        # Store feedback
        self.feedback_entries.append(feedback)

        # Notify listeners
        for listener in self.feedback_listeners:
            try:
                listener(feedback)
            except Exception as e:
                logger.error(f"[feedback] feedback listener failed: {e}")

        # Check if revision needed
        if feedback.requires_replanning:
            revision = self.reviser.revise(
                original_reasoning=self.current_reasoning, feedback_entries=self.feedback_entries
            )
            self.pending_revisions.append(revision)

            # Notify revision listeners
            for listener in self.revision_listeners:
                try:
                    listener(revision)
                except Exception as e:
                    logger.error(f"[feedback] revision listener failed: {e}")

        return feedback

    def get_feedback_summary(self) -> Dict[str, Any]:
        """Get summary of all feedback for current reasoning"""
        if not self.feedback_entries:
            return {"status": "no_feedback"}

        summary = {
            "total_executions": len(self.execution_results),
            "total_feedback": len(self.feedback_entries),
            "feedback_types": {},
            "requires_replanning": any(f.requires_replanning for f in self.feedback_entries),
            "pending_revisions": len(self.pending_revisions),
            "overall_success_rate": self.validator.get_success_rate(),
        }

        # Count feedback types
        for entry in self.feedback_entries:
            ft = entry.feedback_type.value
            summary["feedback_types"][ft] = summary["feedback_types"].get(ft, 0) + 1

        return summary

    def get_latest_revision(self) -> Optional[ReasoningRevision]:
        """Get the most recent revision if any"""
        return self.pending_revisions[-1] if self.pending_revisions else None

    def should_continue(self) -> Tuple[bool, str]:
        """
        Determine if execution should continue or pause for replanning.

        Returns:
            Tuple of (should_continue, reason)
        """
        if not self.feedback_entries:
            return True, "No feedback yet"

        # Check for critical issues
        critical_feedback = [f for f in self.feedback_entries if f.impact_level == "critical"]
        if critical_feedback:
            return False, "Critical issue detected - manual intervention needed"

        # Check for multiple failures
        errors = [f for f in self.feedback_entries if f.feedback_type == FeedbackType.ERROR]
        if len(errors) >= 3:
            return False, "Multiple execution errors - stopping for review"

        # Check for replanning requirement
        if self.pending_revisions:
            latest = self.pending_revisions[-1]
            if latest.revised_confidence < 0.3:
                return False, "Confidence too low after revision"

        return True, "Continue execution"

    def finalize(self) -> Dict[str, Any]:
        """
        Finalize the feedback loop and generate summary.

        Returns:
            Final summary with metrics and lessons
        """
        summary = {
            "reasoning_id": self.current_reasoning.id if self.current_reasoning else None,
            "total_executions": len(self.execution_results),
            "total_revisions": len(self.pending_revisions),
            "feedback_summary": self.get_feedback_summary(),
            "calibration": self.calibrator.get_calibration_report(),
            "lessons_learned": [],
            "success": True,
        }

        # Aggregate lessons
        for entry in self.feedback_entries:
            summary["lessons_learned"].extend(entry.lessons)

        # Deduplicate lessons
        summary["lessons_learned"] = list(set(summary["lessons_learned"]))

        # Determine overall success
        error_count = sum(
            1
            for f in self.feedback_entries
            if f.feedback_type in [FeedbackType.ERROR, FeedbackType.CONTRADICTION]
        )
        summary["success"] = error_count < len(self.feedback_entries) / 2

        return summary
