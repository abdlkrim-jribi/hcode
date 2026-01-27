"""
Enhanced Reasoning System for AI Agents.

This module provides structured reasoning capabilities including:
- Multi-phase reasoning with strict output parsing
- Confidence calibration and tracking
- Self-critique and reflection
- Reasoning quality metrics
- Reasoning-to-todo integration

Designed for maximum performance with GPT-OSS and other LLMs.
"""

import json
import re
import statistics
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple


class ReasoningLevel(Enum):
    """Reasoning depth levels based on task complexity"""

    QUICK = 1  # Simple operations, fast decisions
    STANDARD = 2  # Most operations, moderate reasoning
    DEEP = 3  # Complex tasks, comprehensive analysis


class ReasoningPhase(Enum):
    """Enhanced reasoning phases for structured thinking"""

    # Phase 1: Perception
    PERCEPTION = "perception"

    # Phase 2: Comprehension
    COMPREHENSION = "comprehension"

    # Phase 3: Analysis
    ANALYSIS = "analysis"

    # Phase 4: Reasoning
    REASONING = "reasoning"

    # Phase 5: Change Impact Analysis (NEW)
    CHANGE_IMPACT = "change_impact"

    # Phase 6: Decision
    DECISION = "decision"

    # Phase 7: Pre-Execution Review (NEW)
    PRE_EXECUTION_REVIEW = "pre_execution_review"

    # Phase 8: Verification
    VERIFICATION = "verification"


@dataclass
class PerceptionOutput:
    """Structured output for perception phase"""

    observation: str = ""
    implicit_needs: List[str] = field(default_factory=list)
    key_entities: List[str] = field(default_factory=list)
    initial_interpretation: str = ""

    def is_complete(self) -> bool:
        return bool(self.observation and self.initial_interpretation)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation": self.observation,
            "implicit_needs": self.implicit_needs,
            "key_entities": self.key_entities,
            "initial_interpretation": self.initial_interpretation,
        }


@dataclass
class ComprehensionOutput:
    """Structured output for comprehension phase"""

    core_understanding: str = ""
    context: str = ""
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        return bool(self.core_understanding and self.assumptions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "core_understanding": self.core_understanding,
            "context": self.context,
            "assumptions": self.assumptions,
            "constraints": self.constraints,
            "success_criteria": self.success_criteria,
        }


@dataclass
class AnalysisOutput:
    """Structured output for analysis phase"""

    decomposition: List[str] = field(default_factory=list)
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    options: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    complexity_score: float = 0.0

    def is_complete(self) -> bool:
        return bool(self.decomposition and self.options)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decomposition": self.decomposition,
            "dependencies": self.dependencies,
            "options": self.options,
            "risks": self.risks,
            "complexity_score": self.complexity_score,
        }


@dataclass
class ReasoningOutput:
    """Structured output for reasoning phase"""

    hypothesis: str = ""
    evidence_for: List[str] = field(default_factory=list)
    evidence_against: List[str] = field(default_factory=list)
    counter_arguments: List[str] = field(default_factory=list)
    logical_chain: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def is_complete(self) -> bool:
        return bool(self.hypothesis and self.evidence_for and self.confidence > 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis": self.hypothesis,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "counter_arguments": self.counter_arguments,
            "logical_chain": self.logical_chain,
            "confidence": self.confidence,
        }


@dataclass
class DecisionOutput:
    """Structured output for decision phase"""

    decision: str = ""
    justification: str = ""
    confidence: float = 0.0
    fallback_plan: str = ""
    action_items: List[str] = field(default_factory=list)
    expected_outcome: str = ""

    def is_complete(self) -> bool:
        return bool(self.decision and self.justification and self.confidence > 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "justification": self.justification,
            "confidence": self.confidence,
            "fallback_plan": self.fallback_plan,
            "action_items": self.action_items,
            "expected_outcome": self.expected_outcome,
        }


@dataclass
class VerificationOutput:
    """Structured output for verification phase"""

    safety_check: str = ""
    validation_steps: List[str] = field(default_factory=list)
    potential_issues: List[str] = field(default_factory=list)
    risk_mitigation: List[str] = field(default_factory=list)
    final_confidence: float = 0.0
    ready_to_execute: bool = False

    def is_complete(self) -> bool:
        return bool(self.safety_check and self.final_confidence > 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "safety_check": self.safety_check,
            "validation_steps": self.validation_steps,
            "potential_issues": self.potential_issues,
            "risk_mitigation": self.risk_mitigation,
            "final_confidence": self.final_confidence,
            "ready_to_execute": self.ready_to_execute,
        }


@dataclass
class ChangeImpactOutput:
    """Structured output for change impact analysis phase (NEW)"""

    files_affected: List[str] = field(default_factory=list)
    dependencies_affected: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    rollback_strategy: str = ""
    impact_score: float = 0.0  # 0-1, higher means more impactful
    requires_review: bool = True

    def is_complete(self) -> bool:
        return bool(self.files_affected or self.impact_score > 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files_affected": self.files_affected,
            "dependencies_affected": self.dependencies_affected,
            "breaking_changes": self.breaking_changes,
            "side_effects": self.side_effects,
            "rollback_strategy": self.rollback_strategy,
            "impact_score": self.impact_score,
            "requires_review": self.requires_review,
        }


@dataclass
class PreExecutionReviewOutput:
    """Structured output for pre-execution review phase (NEW)"""

    changes_summary: List[str] = field(default_factory=list)
    what_will_change: str = ""
    what_could_go_wrong: List[str] = field(default_factory=list)
    alternative_approaches: List[str] = field(default_factory=list)
    confidence_in_approach: float = 0.0
    user_approval_needed: bool = True
    approval_reason: str = ""
    proceed_recommendation: bool = False

    def is_complete(self) -> bool:
        return bool(self.what_will_change and self.confidence_in_approach > 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "changes_summary": self.changes_summary,
            "what_will_change": self.what_will_change,
            "what_could_go_wrong": self.what_could_go_wrong,
            "alternative_approaches": self.alternative_approaches,
            "confidence_in_approach": self.confidence_in_approach,
            "user_approval_needed": self.user_approval_needed,
            "approval_reason": self.approval_reason,
            "proceed_recommendation": self.proceed_recommendation,
        }


@dataclass
class StructuredReasoning:
    """Complete structured reasoning output across all phases (8 phases)"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    level: ReasoningLevel = ReasoningLevel.STANDARD

    # Phase outputs (8 phases)
    perception: PerceptionOutput = field(default_factory=PerceptionOutput)
    comprehension: ComprehensionOutput = field(default_factory=ComprehensionOutput)
    analysis: AnalysisOutput = field(default_factory=AnalysisOutput)
    reasoning: ReasoningOutput = field(default_factory=ReasoningOutput)
    change_impact: ChangeImpactOutput = field(default_factory=ChangeImpactOutput)  # NEW
    decision: DecisionOutput = field(default_factory=DecisionOutput)
    pre_execution_review: PreExecutionReviewOutput = field(
        default_factory=PreExecutionReviewOutput
    )  # NEW
    verification: VerificationOutput = field(default_factory=VerificationOutput)

    # Metadata
    raw_content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    tokens_used: int = 0
    duration_ms: int = 0

    # Quality metrics
    completeness_score: float = 0.0
    coherence_score: float = 0.0
    depth_score: float = 0.0

    def quality_score(self) -> float:
        """Calculate overall quality score (0-1)"""
        phase_scores = []

        # Check each phase completeness (8 phases)
        if self.perception.is_complete():
            phase_scores.append(1.0)
        if self.comprehension.is_complete():
            phase_scores.append(1.0)
        if self.analysis.is_complete():
            phase_scores.append(1.0)
        if self.reasoning.is_complete():
            phase_scores.append(1.0)
        if self.change_impact.is_complete():
            phase_scores.append(1.0)
        if self.decision.is_complete():
            phase_scores.append(1.0)
        if self.pre_execution_review.is_complete():
            phase_scores.append(1.0)
        if self.verification.is_complete():
            phase_scores.append(1.0)

        # Completeness (40%) - now 8 phases
        completeness = len(phase_scores) / 8.0
        self.completeness_score = completeness

        # Depth - evidence and counter-arguments (30%)
        evidence_count = len(self.reasoning.evidence_for) + len(self.reasoning.evidence_against)
        counter_count = len(self.reasoning.counter_arguments)
        depth = min(1.0, (evidence_count + counter_count) / 6.0)
        self.depth_score = depth

        # Coherence - has logical chain and fallback (30%)
        coherence_factors = [
            len(self.reasoning.logical_chain) > 0,
            bool(self.decision.fallback_plan),
            len(self.decision.action_items) > 0,
            self.verification.ready_to_execute or len(self.verification.potential_issues) > 0,
        ]
        coherence = sum(coherence_factors) / len(coherence_factors)
        self.coherence_score = coherence

        return (completeness * 0.4) + (depth * 0.3) + (coherence * 0.3)

    def get_confidence(self) -> float:
        """Get final confidence level"""
        if self.verification.final_confidence > 0:
            return self.verification.final_confidence
        if self.decision.confidence > 0:
            return self.decision.confidence
        if self.reasoning.confidence > 0:
            return self.reasoning.confidence
        return 0.0

    def has_fallback(self) -> bool:
        """Check if fallback plan exists"""
        return bool(self.decision.fallback_plan)

    def is_self_critical(self) -> bool:
        """Check if reasoning includes self-critique"""
        return (
            len(self.reasoning.evidence_against) > 0
            or len(self.reasoning.counter_arguments) > 0
            or len(self.verification.potential_issues) > 0
            or len(self.pre_execution_review.what_could_go_wrong) > 0
            or len(self.change_impact.breaking_changes) > 0
        )

    def requires_user_approval(self) -> bool:
        """Check if change requires user approval based on impact"""
        return (
            self.pre_execution_review.user_approval_needed
            or self.change_impact.requires_review
            or self.change_impact.impact_score > 0.7
            or len(self.change_impact.breaking_changes) > 0
        )

    def get_change_summary(self) -> str:
        """Get a summary of the proposed changes"""
        summary_parts = []

        if self.change_impact.files_affected:
            summary_parts.append(f"Files affected: {len(self.change_impact.files_affected)}")

        if self.change_impact.breaking_changes:
            summary_parts.append(f"Breaking changes: {len(self.change_impact.breaking_changes)}")

        if self.pre_execution_review.what_will_change:
            summary_parts.append(f"Changes: {self.pre_execution_review.what_will_change[:100]}...")

        return " | ".join(summary_parts) if summary_parts else "No changes identified"

    def get_action_items(self) -> List[str]:
        """Extract all action items for todo list"""
        items = []

        # From analysis decomposition
        items.extend(self.analysis.decomposition)

        # From decision action items
        items.extend(self.decision.action_items)

        # From verification validation steps
        items.extend(self.verification.validation_steps)

        return items

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "level": self.level.name,
            "perception": self.perception.to_dict(),
            "comprehension": self.comprehension.to_dict(),
            "analysis": self.analysis.to_dict(),
            "reasoning": self.reasoning.to_dict(),
            "change_impact": self.change_impact.to_dict(),
            "decision": self.decision.to_dict(),
            "pre_execution_review": self.pre_execution_review.to_dict(),
            "verification": self.verification.to_dict(),
            "quality_score": self.quality_score(),
            "confidence": self.get_confidence(),
            "requires_approval": self.requires_user_approval(),
            "change_summary": self.get_change_summary(),
            "timestamp": self.timestamp.isoformat(),
            "tokens_used": self.tokens_used,
            "duration_ms": self.duration_ms,
        }


class ReasoningParser:
    """
    Parses structured reasoning from model output.

    Supports multiple formats:
    - XML-style <thinking> blocks
    - Markdown-style headers
    - JSON structured output
    """

    # Phase header patterns (8 phases)
    PHASE_PATTERNS = {
        ReasoningPhase.PERCEPTION: [
            r"\[?PHASE\s*1[:\s-]*PERCEPTION\]?",
            r"\[PERCEPTION\]",
            r"##?\s*PERCEPTION",
            r"OBSERVE:",
            r"OBSERVATION:",
        ],
        ReasoningPhase.COMPREHENSION: [
            r"\[?PHASE\s*2[:\s-]*COMPREHENSION\]?",
            r"\[COMPREHENSION\]",
            r"##?\s*COMPREHENSION",
            r"\[UNDERSTAND\]",
            r"UNDERSTANDING:",
        ],
        ReasoningPhase.ANALYSIS: [
            r"\[?PHASE\s*3[:\s-]*ANALYSIS\]?",
            r"\[ANALYSIS\]",
            r"##?\s*ANALYSIS",
            r"DECOMPOSE:",
            r"ANALYZE:",
        ],
        ReasoningPhase.REASONING: [
            r"\[?PHASE\s*4[:\s-]*REASONING\]?",
            r"\[REASONING\]",
            r"##?\s*REASONING",
            r"HYPOTHESIS:",
            r"REASON:",
        ],
        ReasoningPhase.CHANGE_IMPACT: [
            r"\[?PHASE\s*5[:\s-]*CHANGE[\s_-]*IMPACT\]?",
            r"\[CHANGE[\s_-]*IMPACT\]",
            r"##?\s*CHANGE[\s_-]*IMPACT",
            r"IMPACT[\s_-]*ANALYSIS:",
            r"FILES[\s_-]*AFFECTED:",
        ],
        ReasoningPhase.DECISION: [
            r"\[?PHASE\s*6[:\s-]*DECISION\]?",
            r"\[DECISION\]",
            r"##?\s*DECISION",
            r"DECIDE:",
            r"CHOICE:",
        ],
        ReasoningPhase.PRE_EXECUTION_REVIEW: [
            r"\[?PHASE\s*7[:\s-]*PRE[\s_-]*EXECUTION[\s_-]*REVIEW\]?",
            r"\[PRE[\s_-]*EXECUTION[\s_-]*REVIEW\]",
            r"##?\s*PRE[\s_-]*EXECUTION",
            r"WHAT[\s_-]*WILL[\s_-]*CHANGE:",
            r"BEFORE[\s_-]*EXECUTING:",
        ],
        ReasoningPhase.VERIFICATION: [
            r"\[?PHASE\s*8[:\s-]*VERIFICATION\]?",
            r"\[VERIFICATION\]",
            r"##?\s*VERIFICATION",
            r"VERIFY:",
            r"VALIDATE:",
        ],
    }

    # Field extraction patterns
    # Field extraction patterns
    FIELD_PATTERNS = {
        # Perception
        "observation": r"(?:OBSERVE|OBSERVATION|What I see)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "implicit_needs": r"(?:IMPLICIT|Implicit needs?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        # Comprehension
        "core_understanding": r"(?:UNDERSTAND|Core understanding|CORE)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "context": r"(?:CONTEXT|Context)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "assumptions": r"(?:ASSUMPTIONS?|Assumptions?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        # Analysis
        "decomposition": r"(?:DECOMPOSE|Decomposition|Steps?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "options": r"(?:OPTIONS?|Alternatives?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "risks": r"(?:RISKS?|Risk factors?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        # Reasoning
        "hypothesis": r"(?:HYPOTHESIS|Hypothesis)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "evidence_for": r"(?:EVIDENCE FOR|Evidence for|Supporting)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "evidence_against": r"(?:EVIDENCE AGAINST|Evidence against|Opposing)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "counter_arguments": r"(?:COUNTER|Counter-?arguments?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        # Decision
        "decision": r"(?:DECISION|Decision|CHOICE|Choice)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "justification": r"(?:JUSTIFICATION|Justification|WHY|Why)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "confidence": r"(?:CONFIDENCE|Confidence)[:\s]*(\d+(?:\.\d+)?)",
        "fallback": r"(?:FALLBACK|Fallback|Plan B)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "action_items": r"(?:ACTIONS?|Action items?|TODO|Tasks?|Action)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        # Verification
        "safety_check": r"(?:SAFETY|Safety check|RISK CHECK)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "validation": r"(?:VALIDATE|Validation|VERIFY)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "potential_issues": r"(?:ISSUES?|Potential issues?|Problems?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        # Change Impact (NEW)
        "files_affected": r"(?:FILES?\s*AFFECTED|Affected files?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "dependencies_affected": r"(?:DEPENDENCIES?\s*AFFECTED|Affected dependencies?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "breaking_changes": r"(?:BREAKING\s*CHANGES?|Breaking changes?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "side_effects": r"(?:SIDE\s*EFFECTS?|Side effects?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "rollback_strategy": r"(?:ROLLBACK|Rollback strategy)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "impact_score": r"(?:IMPACT\s*SCORE|Impact score)[:\s]*(\d+(?:\.\d+)?)",
        # Pre-Execution Review (NEW)
        "what_will_change": r"(?:WHAT\s*WILL\s*CHANGE|What will change)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "what_could_go_wrong": r"(?:WHAT\s*COULD\s*GO\s*WRONG|Risks?|What could go wrong)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "alternative_approaches": r"(?:ALTERNATIVES?|Alternative approaches?)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
        "approval_reason": r"(?:APPROVAL\s*REASON|Why approve)[:\s]*(.+?)(?=\r?\n\s*[A-Z]|\r?\n\s*\r?\n|$)",
    }

    def __init__(self):
        self._compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency"""
        for phase, patterns in self.PHASE_PATTERNS.items():
            self._compiled_patterns[phase] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns
            ]

        for name, pattern in self.FIELD_PATTERNS.items():
            self._compiled_patterns[f"field_{name}"] = re.compile(
                pattern, re.IGNORECASE | re.DOTALL
            )

    def parse(self, content: str) -> StructuredReasoning:
        """
        Parse reasoning content into structured format.

        Args:
            content: Raw model output containing reasoning

        Returns:
            StructuredReasoning object
        """
        result = StructuredReasoning(raw_content=content)

        # Extract thinking block if present
        thinking_content = self._extract_thinking_block(content)
        if not thinking_content:
            thinking_content = content

        # Try JSON parsing first
        json_result = self._try_parse_json(thinking_content)
        if json_result:
            return self._populate_from_dict(result, json_result)

        # Parse by phases
        phase_contents = self._split_by_phases(thinking_content)

        # Parse each phase
        if ReasoningPhase.PERCEPTION in phase_contents:
            result.perception = self._parse_perception(phase_contents[ReasoningPhase.PERCEPTION])

        if ReasoningPhase.COMPREHENSION in phase_contents:
            result.comprehension = self._parse_comprehension(
                phase_contents[ReasoningPhase.COMPREHENSION]
            )

        if ReasoningPhase.ANALYSIS in phase_contents:
            result.analysis = self._parse_analysis(phase_contents[ReasoningPhase.ANALYSIS])

        if ReasoningPhase.REASONING in phase_contents:
            result.reasoning = self._parse_reasoning(phase_contents[ReasoningPhase.REASONING])

        if ReasoningPhase.CHANGE_IMPACT in phase_contents:
            result.change_impact = self._parse_change_impact(
                phase_contents[ReasoningPhase.CHANGE_IMPACT]
            )

        if ReasoningPhase.DECISION in phase_contents:
            result.decision = self._parse_decision(phase_contents[ReasoningPhase.DECISION])

        if ReasoningPhase.PRE_EXECUTION_REVIEW in phase_contents:
            result.pre_execution_review = self._parse_pre_execution_review(
                phase_contents[ReasoningPhase.PRE_EXECUTION_REVIEW]
            )

        if ReasoningPhase.VERIFICATION in phase_contents:
            result.verification = self._parse_verification(
                phase_contents[ReasoningPhase.VERIFICATION]
            )

        # Determine reasoning level based on content
        result.level = self._determine_level(result)

        return result

    def _extract_thinking_block(self, content: str) -> Optional[str]:
        """Extract content from <thinking> tags"""
        pattern = re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL | re.IGNORECASE)
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
        return None

    def _try_parse_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Try to parse content as JSON"""
        # Look for JSON block
        json_pattern = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)
        match = json_pattern.search(content)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try direct JSON parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        return None

    def _split_by_phases(self, content: str) -> Dict[ReasoningPhase, str]:
        """Split content by phase markers"""
        result = {}

        # Find all phase positions
        phase_positions = []
        for phase, patterns in self._compiled_patterns.items():
            if isinstance(phase, ReasoningPhase):
                for pattern in patterns:
                    for match in pattern.finditer(content):
                        phase_positions.append((match.start(), phase, match.end()))

        # Sort by position
        phase_positions.sort(key=lambda x: x[0])

        # Extract content between phases
        for i, (start, phase, content_start) in enumerate(phase_positions):
            if i + 1 < len(phase_positions):
                end = phase_positions[i + 1][0]
            else:
                end = len(content)

            phase_content = content[content_start:end].strip()
            result[phase] = phase_content

        # If no phases found, try to parse as single block
        if not result:
            result[ReasoningPhase.REASONING] = content

        return result

    def _extract_field(self, content: str, field_name: str) -> str:
        """Extract a field value from content"""
        pattern = self._compiled_patterns.get(f"field_{field_name}")
        if pattern:
            match = pattern.search(content)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_list(self, content: str, field_name: str) -> List[str]:
        """Extract a list field from content"""
        raw = self._extract_field(content, field_name)
        if not raw:
            return []

        # Try numbered list first (e.g., "1. Step one\n2. Step two")
        numbered_items = re.findall(
            r"^\s*\d+\.\s*(.+?)(?=(?:^\s*\d+\.|\Z))", raw, re.MULTILINE | re.DOTALL
        )
        if numbered_items:
            return [
                item.strip() for item in numbered_items if item.strip() and len(item.strip()) > 3
            ]

        # Try bullet points (e.g., "- Step one\n- Step two")
        bullet_items = re.findall(
            r"^\s*[\-\*]\s*(.+?)(?=(?:^\s*[\-\*]|\Z))", raw, re.MULTILINE | re.DOTALL
        )
        if bullet_items:
            return [item.strip() for item in bullet_items if item.strip() and len(item.strip()) > 3]

        # Fall back to splitting by newlines for non-list content
        lines = [line.strip() for line in raw.split("\n") if line.strip() and len(line.strip()) > 5]
        return lines[:10]  # Limit to 10 items

    def _parse_perception(self, content: str) -> PerceptionOutput:
        """Parse perception phase content"""
        return PerceptionOutput(
            observation=self._extract_field(content, "observation") or content[:200],
            implicit_needs=self._extract_list(content, "implicit_needs"),
            key_entities=self._extract_list(content, "key_entities"),
            initial_interpretation=self._extract_field(content, "interpretation") or "",
        )

    def _parse_comprehension(self, content: str) -> ComprehensionOutput:
        """Parse comprehension phase content"""
        return ComprehensionOutput(
            core_understanding=self._extract_field(content, "core_understanding") or content[:200],
            context=self._extract_field(content, "context"),
            assumptions=self._extract_list(content, "assumptions"),
            constraints=self._extract_list(content, "constraints"),
            success_criteria=self._extract_list(content, "success_criteria"),
        )

    def _parse_analysis(self, content: str) -> AnalysisOutput:
        """Parse analysis phase content"""
        decomposition = self._extract_list(content, "decomposition")

        # Parse options with pros/cons if available
        options_raw = self._extract_field(content, "options")
        options = []
        if options_raw:
            option_parts = re.split(r"\n(?=\d+\.|\-)", options_raw)
            for part in option_parts:
                if part.strip():
                    options.append({"description": part.strip()})

        return AnalysisOutput(
            decomposition=decomposition or self._split_into_steps(content),
            dependencies=self._extract_dependencies(content),
            options=options,
            risks=self._extract_list(content, "risks"),
            complexity_score=self._estimate_complexity(content),
        )

    def _parse_reasoning(self, content: str) -> ReasoningOutput:
        """Parse reasoning phase content"""
        confidence_str = self._extract_field(content, "confidence")
        confidence = 0.0
        if confidence_str:
            try:
                confidence = float(confidence_str)
                if confidence > 1:
                    confidence = confidence / 100.0  # Convert percentage
            except ValueError:
                pass

        return ReasoningOutput(
            hypothesis=self._extract_field(content, "hypothesis") or content[:200],
            evidence_for=self._extract_list(content, "evidence_for"),
            evidence_against=self._extract_list(content, "evidence_against"),
            counter_arguments=self._extract_list(content, "counter_arguments"),
            logical_chain=self._extract_logical_chain(content),
            confidence=confidence,
        )

    def _parse_decision(self, content: str) -> DecisionOutput:
        """Parse decision phase content"""
        confidence_str = self._extract_field(content, "confidence")
        confidence = 0.0
        if confidence_str:
            try:
                confidence = float(confidence_str)
                if confidence > 1:
                    confidence = confidence / 100.0
            except ValueError:
                pass

        return DecisionOutput(
            decision=self._extract_field(content, "decision") or content[:200],
            justification=self._extract_field(content, "justification"),
            confidence=confidence,
            fallback_plan=self._extract_field(content, "fallback"),
            action_items=self._extract_list(content, "action_items"),
            expected_outcome=self._extract_field(content, "expected_outcome"),
        )

    def _parse_verification(self, content: str) -> VerificationOutput:
        """Parse verification phase content"""
        confidence_str = self._extract_field(content, "confidence")
        confidence = 0.0
        if confidence_str:
            try:
                confidence = float(confidence_str)
                if confidence > 1:
                    confidence = confidence / 100.0
            except ValueError:
                pass

        # Determine if ready to execute
        ready_indicators = ["ready", "proceed", "execute", "safe to", "approved"]
        ready = any(ind in content.lower() for ind in ready_indicators)

        return VerificationOutput(
            safety_check=self._extract_field(content, "safety_check") or "Not specified",
            validation_steps=self._extract_list(content, "validation"),
            potential_issues=self._extract_list(content, "potential_issues"),
            risk_mitigation=self._extract_list(content, "risk_mitigation"),
            final_confidence=confidence,
            ready_to_execute=ready,
        )

    def _parse_change_impact(self, content: str) -> ChangeImpactOutput:
        """Parse change impact phase content (NEW)"""
        impact_str = self._extract_field(content, "impact_score")
        impact_score = 0.0
        if impact_str:
            try:
                impact_score = float(impact_str)
                if impact_score > 1:
                    impact_score = impact_score / 100.0
            except ValueError:
                pass

        # Determine if review is required
        review_indicators = ["review", "approval", "breaking", "critical", "major"]
        requires_review = any(ind in content.lower() for ind in review_indicators)

        # If breaking changes found, always require review
        breaking_changes = self._extract_list(content, "breaking_changes")
        if breaking_changes:
            requires_review = True

        return ChangeImpactOutput(
            files_affected=self._extract_list(content, "files_affected"),
            dependencies_affected=self._extract_list(content, "dependencies_affected"),
            breaking_changes=breaking_changes,
            side_effects=self._extract_list(content, "side_effects"),
            rollback_strategy=self._extract_field(content, "rollback_strategy"),
            impact_score=impact_score,
            requires_review=requires_review,
        )

    def _parse_pre_execution_review(self, content: str) -> PreExecutionReviewOutput:
        """Parse pre-execution review phase content (NEW)"""
        confidence_str = self._extract_field(content, "confidence")
        confidence = 0.0
        if confidence_str:
            try:
                confidence = float(confidence_str)
                if confidence > 1:
                    confidence = confidence / 100.0
            except ValueError:
                pass

        # Determine if approval needed
        approval_indicators = ["approval", "confirm", "review", "check"]
        approval_needed = any(ind in content.lower() for ind in approval_indicators)

        # Determine if proceed is recommended
        proceed_indicators = ["proceed", "safe", "ready", "recommend"]
        proceed = any(ind in content.lower() for ind in proceed_indicators)

        # Extract what could go wrong
        what_could_go_wrong = self._extract_list(content, "what_could_go_wrong")
        if not what_could_go_wrong:
            # Also look for risks
            what_could_go_wrong = self._extract_list(content, "risks")

        return PreExecutionReviewOutput(
            changes_summary=self._extract_list(content, "changes"),
            what_will_change=self._extract_field(content, "what_will_change") or content[:200],
            what_could_go_wrong=what_could_go_wrong,
            alternative_approaches=self._extract_list(content, "alternative_approaches"),
            confidence_in_approach=confidence,
            user_approval_needed=approval_needed,
            approval_reason=self._extract_field(content, "approval_reason"),
            proceed_recommendation=proceed,
        )

    def _split_into_steps(self, content: str) -> List[str]:
        """Split content into logical steps"""
        # Try numbered list (e.g., "1. Create user model\n2. Implement auth")
        numbered = re.findall(
            r"^\s*\d+\.\s*(.+?)(?=(?:^\s*\d+\.|\n\n|\Z))", content, re.MULTILINE | re.DOTALL
        )
        if numbered:
            return [s.strip() for s in numbered if s.strip() and len(s.strip()) > 5]

        # Try bullet points (e.g., "- Create user model\n- Implement auth")
        bullets = re.findall(
            r"^\s*[\-\*]\s*(.+?)(?=(?:^\s*[\-\*]|\n\n|\Z))", content, re.MULTILINE | re.DOTALL
        )
        if bullets:
            return [s.strip() for s in bullets if s.strip() and len(s.strip()) > 5]

        # Try splitting by newlines for line-based content
        lines = [
            line.strip() for line in content.split("\n") if line.strip() and len(line.strip()) > 10
        ]
        if lines:
            return lines[:10]  # Limit to 10 steps

        # Split by sentences as fallback
        sentences = re.split(r"[.!?]\s+", content)
        return [s.strip() for s in sentences if len(s.strip()) > 10][:5]

    def _extract_dependencies(self, content: str) -> List[Dict[str, str]]:
        """Extract dependency relationships"""
        deps = []
        patterns = [
            r"(\w+)\s+depends on\s+(\w+)",
            r"(\w+)\s+requires\s+(\w+)",
            r"before\s+(\w+).*?(\w+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                deps.append({"from": match[0], "to": match[1]})

        return deps

    def _extract_logical_chain(self, content: str) -> List[str]:
        """Extract logical reasoning chain"""
        chain = []

        # Look for therefore/because/since patterns
        patterns = [
            r"because\s+(.+?)(?:[,.]|therefore|since|$)",
            r"therefore\s+(.+?)(?:[,.]|because|$)",
            r"since\s+(.+?)(?:[,.]|therefore|$)",
            r"thus\s+(.+?)(?:[,.]|$)",
            r"hence\s+(.+?)(?:[,.]|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            chain.extend([m.strip() for m in matches if m.strip()])

        return chain[:5]  # Limit to 5 items

    def _estimate_complexity(self, content: str) -> float:
        """Estimate task complexity from analysis content"""
        score = 0.0

        # Length factor
        if len(content) > 1000:
            score += 0.3
        elif len(content) > 500:
            score += 0.2
        elif len(content) > 200:
            score += 0.1

        # Multiple options mentioned
        if re.search(r"option|alternative|approach", content, re.IGNORECASE):
            score += 0.2

        # Dependencies mentioned
        if re.search(r"depends|requires|before|after", content, re.IGNORECASE):
            score += 0.2

        # Risks mentioned
        if re.search(r"risk|danger|careful|warning", content, re.IGNORECASE):
            score += 0.2

        # Multiple files/components
        file_refs = re.findall(r"\w+\.\w{2,4}", content)
        if len(file_refs) > 3:
            score += 0.1

        return min(1.0, score)

    def _determine_level(self, reasoning: StructuredReasoning) -> ReasoningLevel:
        """Determine reasoning level from content"""
        quality = reasoning.quality_score()

        if quality >= 0.7:
            return ReasoningLevel.DEEP
        elif quality >= 0.4:
            return ReasoningLevel.STANDARD
        else:
            return ReasoningLevel.QUICK

    def _populate_from_dict(
        self, result: StructuredReasoning, data: Dict[str, Any]
    ) -> StructuredReasoning:
        """Populate StructuredReasoning from dictionary"""
        if "perception" in data:
            result.perception = PerceptionOutput(**data["perception"])
        if "comprehension" in data:
            result.comprehension = ComprehensionOutput(**data["comprehension"])
        if "analysis" in data:
            result.analysis = AnalysisOutput(**data["analysis"])
        if "reasoning" in data:
            result.reasoning = ReasoningOutput(**data["reasoning"])
        if "decision" in data:
            result.decision = DecisionOutput(**data["decision"])
        if "verification" in data:
            result.verification = VerificationOutput(**data["verification"])

        return result


class ConfidenceCalibrator:
    """
    Tracks and calibrates confidence predictions against outcomes.

    Maintains a history of predictions and actual results to measure
    and improve calibration over time.
    """

    def __init__(self, history_size: int = 100):
        """
        Initialize calibrator.

        Args:
            history_size: Maximum predictions to track
        """
        self.history_size = history_size
        self.predictions: deque = deque(maxlen=history_size)
        self.calibration_buckets: Dict[str, List[Tuple[float, bool]]] = {
            "0-20": [],
            "20-40": [],
            "40-60": [],
            "60-80": [],
            "80-100": [],
        }

    def record_prediction(self, confidence: float, task_type: str, reasoning_id: str) -> str:
        """
        Record a confidence prediction.

        Args:
            confidence: Predicted confidence (0-1)
            task_type: Type of task
            reasoning_id: ID of the reasoning that made prediction

        Returns:
            Prediction ID for later outcome recording
        """
        prediction_id = str(uuid.uuid4())
        self.predictions.append(
            {
                "id": prediction_id,
                "confidence": confidence,
                "task_type": task_type,
                "reasoning_id": reasoning_id,
                "timestamp": datetime.now(),
                "outcome": None,
            }
        )
        return prediction_id

    def record_outcome(self, prediction_id: str, success: bool):
        """
        Record the actual outcome of a prediction.

        Args:
            prediction_id: ID from record_prediction
            success: Whether the task succeeded
        """
        for pred in self.predictions:
            if pred["id"] == prediction_id:
                pred["outcome"] = success

                # Add to calibration bucket
                confidence = pred["confidence"]
                bucket = self._get_bucket(confidence)
                self.calibration_buckets[bucket].append((confidence, success))
                break

    def _get_bucket(self, confidence: float) -> str:
        """Get calibration bucket for confidence value"""
        pct = confidence * 100
        if pct < 20:
            return "0-20"
        elif pct < 40:
            return "20-40"
        elif pct < 60:
            return "40-60"
        elif pct < 80:
            return "60-80"
        else:
            return "80-100"

    def get_calibration_error(self) -> float:
        """
        Calculate Expected Calibration Error (ECE).

        Returns:
            ECE value (0-1), lower is better
        """
        total_samples = 0
        weighted_error = 0.0

        for bucket_name, samples in self.calibration_buckets.items():
            if not samples:
                continue

            n = len(samples)
            total_samples += n

            # Average confidence in bucket
            avg_confidence = statistics.mean([s[0] for s in samples])

            # Actual accuracy in bucket
            accuracy = sum([1 for s in samples if s[1]]) / n

            # Weighted error contribution
            weighted_error += n * abs(avg_confidence - accuracy)

        if total_samples == 0:
            return 0.0

        return weighted_error / total_samples

    def get_calibration_report(self) -> Dict[str, Any]:
        """
        Generate calibration report.

        Returns:
            Dictionary with calibration statistics
        """
        report = {
            "total_predictions": len(self.predictions),
            "predictions_with_outcomes": sum(
                1 for p in self.predictions if p["outcome"] is not None
            ),
            "expected_calibration_error": self.get_calibration_error(),
            "buckets": {},
        }

        for bucket_name, samples in self.calibration_buckets.items():
            if samples:
                avg_conf = statistics.mean([s[0] for s in samples])
                accuracy = sum([1 for s in samples if s[1]]) / len(samples)
                report["buckets"][bucket_name] = {
                    "count": len(samples),
                    "avg_confidence": avg_conf,
                    "actual_accuracy": accuracy,
                    "gap": abs(avg_conf - accuracy),
                }

        return report

    def adjust_confidence(self, raw_confidence: float) -> float:
        """
        Adjust confidence based on historical calibration.

        Args:
            raw_confidence: Model's predicted confidence

        Returns:
            Calibrated confidence
        """
        bucket = self._get_bucket(raw_confidence)
        samples = self.calibration_buckets.get(bucket, [])

        if len(samples) < 5:  # Not enough data
            return raw_confidence

        # Calculate historical accuracy for this confidence range
        accuracy = sum([1 for s in samples if s[1]]) / len(samples)

        # Blend raw confidence with historical accuracy
        # Weight historical data more as we get more samples
        weight = min(0.5, len(samples) / 20.0)
        calibrated = (1 - weight) * raw_confidence + weight * accuracy

        return calibrated

    def should_request_verification(self, confidence: float) -> bool:
        """
        Determine if low confidence warrants additional verification.

        Args:
            confidence: Current confidence level

        Returns:
            True if verification recommended
        """
        # Check if this confidence bucket historically underperforms
        bucket = self._get_bucket(confidence)
        samples = self.calibration_buckets.get(bucket, [])

        if len(samples) < 10:
            # Not enough data, be conservative
            return confidence < 0.6

        accuracy = sum([1 for s in samples if s[1]]) / len(samples)

        # If historical accuracy is significantly lower than confidence
        if confidence - accuracy > 0.15:
            return True

        # If confidence is low anyway
        return confidence < 0.5


class ReasoningToTodoIntegrator:
    """
    Integrates reasoning outputs with todo management.

    Automatically extracts action items from reasoning and
    updates todo lists based on reasoning progress.
    """

    def __init__(self, todo_manager: Any = None):
        """
        Initialize integrator.

        Args:
            todo_manager: TodoManager instance to update
        """
        self.todo_manager = todo_manager
        self.reasoning_todo_map: Dict[str, List[str]] = {}  # reasoning_id -> todo_ids

    def set_todo_manager(self, todo_manager: Any):
        """Set the todo manager instance"""
        self.todo_manager = todo_manager

    def extract_todos_from_reasoning(self, reasoning: StructuredReasoning) -> List[Dict[str, Any]]:
        """
        Extract todo items from structured reasoning.

        Args:
            reasoning: Parsed reasoning output

        Returns:
            List of todo dictionaries ready for TodoManager
        """
        todos = []

        # Priority 1: Action items from decision phase
        for item in reasoning.decision.action_items:
            todos.append(
                {
                    "content": item,
                    "status": "pending",
                    "activeForm": self._to_active_form(item),
                    "source": "decision",
                    "reasoning_id": reasoning.id,
                }
            )

        # Priority 2: Decomposition steps from analysis
        for i, step in enumerate(reasoning.analysis.decomposition):
            if step not in [t["content"] for t in todos]:
                todos.append(
                    {
                        "content": step,
                        "status": "pending",
                        "activeForm": self._to_active_form(step),
                        "source": "analysis",
                        "reasoning_id": reasoning.id,
                        "order": i,
                    }
                )

        # Priority 3: Validation steps from verification
        for step in reasoning.verification.validation_steps:
            if step not in [t["content"] for t in todos]:
                todos.append(
                    {
                        "content": f"Verify: {step}",
                        "status": "pending",
                        "activeForm": f"Verifying: {step}",
                        "source": "verification",
                        "reasoning_id": reasoning.id,
                    }
                )

        # Priority 4: Risk mitigation steps
        for mitigation in reasoning.verification.risk_mitigation:
            if mitigation not in [t["content"] for t in todos]:
                todos.append(
                    {
                        "content": f"Mitigate: {mitigation}",
                        "status": "pending",
                        "activeForm": f"Mitigating: {mitigation}",
                        "source": "risk_mitigation",
                        "reasoning_id": reasoning.id,
                    }
                )

        return todos

    def _to_active_form(self, content: str) -> str:
        """Convert imperative to active form"""
        # Common verb transformations
        transformations = [
            (r"^(Add|Create|Build|Write|Make)\s+", r"\1ing "),
            (r"^(Fix|Test|Check|Debug)\s+", r"\1ing "),
            (r"^(Update|Configure|Implement)\s+", r"\1ing "),
            (r"^(Remove|Delete|Clean)\s+", r"\1ing "),
            (r"^(Analyze|Optimize|Refactor)\s+", r"\1ing "),
            (
                r"^(Run|Set|Get)\s+",
                lambda m: m.group(1) + "ning " if m.group(1) == "Run" else m.group(1) + "ting ",
            ),
        ]

        for pattern, replacement in transformations:
            if re.match(pattern, content, re.IGNORECASE):
                return re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        # Default: just add "ing" to first word
        words = content.split()
        if words:
            first = words[0]
            if first.endswith("e"):
                words[0] = first[:-1] + "ing"
            else:
                words[0] = first + "ing"
            return " ".join(words)

        return content

    def sync_todos_with_reasoning(
        self, reasoning: StructuredReasoning, current_todos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Synchronize todos with reasoning output.

        Merges new reasoning-derived todos with existing ones,
        avoiding duplicates and maintaining consistency.

        Args:
            reasoning: New reasoning output
            current_todos: Existing todo list

        Returns:
            Updated todo list
        """
        new_todos = self.extract_todos_from_reasoning(reasoning)

        # Build map of existing todos by content
        existing_map = {t["content"].lower(): t for t in current_todos}

        # Track which existing todos are still relevant
        updated_todos = []

        # Keep completed todos
        for todo in current_todos:
            if todo.get("status") == "completed":
                updated_todos.append(todo)

        # Merge new todos
        for new_todo in new_todos:
            key = new_todo["content"].lower()

            if key in existing_map:
                # Update existing todo
                existing = existing_map[key]
                if existing.get("status") != "completed":
                    updated_todos.append(existing)
            else:
                # Add new todo
                updated_todos.append(new_todo)

        # Keep in-progress todos that aren't in new reasoning
        for todo in current_todos:
            if todo.get("status") == "in_progress":
                if todo["content"].lower() not in [t["content"].lower() for t in updated_todos]:
                    updated_todos.append(todo)

        # Sort by order if available, then by source priority
        source_priority = {"decision": 0, "analysis": 1, "verification": 2, "risk_mitigation": 3}
        updated_todos.sort(
            key=lambda t: (
                0 if t.get("status") == "in_progress" else 1,
                source_priority.get(t.get("source", ""), 99),
                t.get("order", 999),
            )
        )

        return updated_todos

    def update_todo_from_phase(
        self, phase: ReasoningPhase, phase_output: Any, current_todos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Update todos based on a specific reasoning phase completion.

        Allows incremental todo updates as reasoning progresses.

        Args:
            phase: The completed reasoning phase
            phase_output: Output from that phase
            current_todos: Current todo list

        Returns:
            Updated todo list
        """
        new_items = []

        if phase == ReasoningPhase.ANALYSIS and isinstance(phase_output, AnalysisOutput):
            # Add decomposition steps
            for step in phase_output.decomposition:
                new_items.append(
                    {
                        "content": step,
                        "status": "pending",
                        "activeForm": self._to_active_form(step),
                        "source": "analysis",
                    }
                )

        elif phase == ReasoningPhase.DECISION and isinstance(phase_output, DecisionOutput):
            # Add action items
            for item in phase_output.action_items:
                new_items.append(
                    {
                        "content": item,
                        "status": "pending",
                        "activeForm": self._to_active_form(item),
                        "source": "decision",
                    }
                )

        elif phase == ReasoningPhase.VERIFICATION and isinstance(phase_output, VerificationOutput):
            # Add validation steps
            for step in phase_output.validation_steps:
                new_items.append(
                    {
                        "content": f"Verify: {step}",
                        "status": "pending",
                        "activeForm": f"Verifying: {step}",
                        "source": "verification",
                    }
                )

        # Merge with existing
        existing_contents = {t["content"].lower() for t in current_todos}

        for item in new_items:
            if item["content"].lower() not in existing_contents:
                current_todos.append(item)

        return current_todos


class SelfCritiqueEngine:
    """
    Generates self-critique and reflection on reasoning quality.

    Identifies blind spots, weak points, and areas for improvement
    in the reasoning process.
    """

    CRITIQUE_ASPECTS = [
        "completeness",
        "logical_coherence",
        "evidence_quality",
        "assumption_validity",
        "risk_awareness",
        "alternative_consideration",
    ]

    def __init__(self):
        self.critique_history: List[Dict[str, Any]] = []

    def critique(self, reasoning: StructuredReasoning) -> Dict[str, Any]:
        """
        Generate comprehensive critique of reasoning.

        Args:
            reasoning: Structured reasoning to critique

        Returns:
            Critique results with scores and suggestions
        """
        critique = {
            "reasoning_id": reasoning.id,
            "timestamp": datetime.now().isoformat(),
            "overall_score": 0.0,
            "aspects": {},
            "blind_spots": [],
            "weak_points": [],
            "suggestions": [],
            "strengths": [],
        }

        # Analyze each aspect
        critique["aspects"]["completeness"] = self._critique_completeness(reasoning)
        critique["aspects"]["logical_coherence"] = self._critique_coherence(reasoning)
        critique["aspects"]["evidence_quality"] = self._critique_evidence(reasoning)
        critique["aspects"]["assumption_validity"] = self._critique_assumptions(reasoning)
        critique["aspects"]["risk_awareness"] = self._critique_risk_awareness(reasoning)
        critique["aspects"]["alternative_consideration"] = self._critique_alternatives(reasoning)

        # Calculate overall score
        aspect_scores = [a["score"] for a in critique["aspects"].values()]
        critique["overall_score"] = statistics.mean(aspect_scores) if aspect_scores else 0.0

        # Identify blind spots
        critique["blind_spots"] = self._identify_blind_spots(reasoning)

        # Identify weak points
        critique["weak_points"] = self._identify_weak_points(reasoning, critique["aspects"])

        # Generate suggestions
        critique["suggestions"] = self._generate_suggestions(reasoning, critique)

        # Identify strengths
        critique["strengths"] = self._identify_strengths(reasoning, critique["aspects"])

        # Store in history
        self.critique_history.append(critique)

        return critique

    def _critique_completeness(self, reasoning: StructuredReasoning) -> Dict[str, Any]:
        """Critique reasoning completeness"""
        result = {"score": 0.0, "issues": [], "details": ""}

        # Check phase completeness
        phases_complete = 0
        phases_total = 6

        if reasoning.perception.is_complete():
            phases_complete += 1
        else:
            result["issues"].append("Perception phase incomplete")

        if reasoning.comprehension.is_complete():
            phases_complete += 1
        else:
            result["issues"].append("Comprehension phase incomplete")

        if reasoning.analysis.is_complete():
            phases_complete += 1
        else:
            result["issues"].append("Analysis phase incomplete")

        if reasoning.reasoning.is_complete():
            phases_complete += 1
        else:
            result["issues"].append("Reasoning phase incomplete")

        if reasoning.decision.is_complete():
            phases_complete += 1
        else:
            result["issues"].append("Decision phase incomplete")

        if reasoning.verification.is_complete():
            phases_complete += 1
        else:
            result["issues"].append("Verification phase incomplete")

        result["score"] = phases_complete / phases_total
        result["details"] = f"{phases_complete}/{phases_total} phases complete"

        return result

    def _critique_coherence(self, reasoning: StructuredReasoning) -> Dict[str, Any]:
        """Critique logical coherence"""
        result = {"score": 0.0, "issues": [], "details": ""}

        score = 0.0
        max_score = 4.0

        # Check if decision aligns with analysis
        if reasoning.decision.decision and reasoning.analysis.decomposition:
            score += 1.0
        else:
            result["issues"].append("Decision may not align with analysis")

        # Check if logical chain exists
        if reasoning.reasoning.logical_chain:
            score += 1.0
        else:
            result["issues"].append("Missing logical reasoning chain")

        # Check if justification supports decision
        if reasoning.decision.justification:
            score += 1.0
        else:
            result["issues"].append("Decision lacks justification")

        # Check if fallback exists for lower confidence
        if reasoning.decision.confidence < 0.7 and not reasoning.decision.fallback_plan:
            result["issues"].append("Low confidence without fallback plan")
        else:
            score += 1.0

        result["score"] = score / max_score
        result["details"] = f"Coherence: {score}/{max_score} checks passed"

        return result

    def _critique_evidence(self, reasoning: StructuredReasoning) -> Dict[str, Any]:
        """Critique evidence quality"""
        result = {"score": 0.0, "issues": [], "details": ""}

        evidence_for = len(reasoning.reasoning.evidence_for)
        evidence_against = len(reasoning.reasoning.evidence_against)
        total_evidence = evidence_for + evidence_against

        score = 0.0

        # Check evidence quantity
        if total_evidence >= 3:
            score += 0.4
        elif total_evidence >= 1:
            score += 0.2
        else:
            result["issues"].append("Insufficient evidence provided")

        # Check balance (having counter-evidence shows thoroughness)
        if evidence_against > 0:
            score += 0.3
        else:
            result["issues"].append("No counter-evidence considered")

        # Check counter-arguments
        if reasoning.reasoning.counter_arguments:
            score += 0.3
        else:
            result["issues"].append("No counter-arguments addressed")

        result["score"] = score
        result["details"] = f"Evidence: {evidence_for} for, {evidence_against} against"

        return result

    def _critique_assumptions(self, reasoning: StructuredReasoning) -> Dict[str, Any]:
        """Critique assumption handling"""
        result = {"score": 0.0, "issues": [], "details": ""}

        assumptions = reasoning.comprehension.assumptions

        if not assumptions:
            result["score"] = 0.3
            result["issues"].append("No assumptions explicitly stated")
            result["details"] = "Assumptions should be explicitly stated and validated"
        else:
            # More assumptions explicitly stated is better
            score = min(1.0, len(assumptions) / 3.0)
            result["score"] = score
            result["details"] = f"{len(assumptions)} assumptions identified"

            # Check if assumptions are validated
            if not reasoning.verification.validation_steps:
                result["issues"].append("Assumptions not validated")
                result["score"] *= 0.7

        return result

    def _critique_risk_awareness(self, reasoning: StructuredReasoning) -> Dict[str, Any]:
        """Critique risk awareness"""
        result = {"score": 0.0, "issues": [], "details": ""}

        score = 0.0

        # Check if risks identified
        if reasoning.analysis.risks:
            score += 0.4
        else:
            result["issues"].append("No risks identified in analysis")

        # Check safety check
        if (
            reasoning.verification.safety_check
            and reasoning.verification.safety_check != "Not specified"
        ):
            score += 0.3
        else:
            result["issues"].append("No safety check performed")

        # Check risk mitigation
        if reasoning.verification.risk_mitigation:
            score += 0.3
        else:
            result["issues"].append("No risk mitigation strategies")

        result["score"] = score
        result["details"] = (
            f"Risks: {len(reasoning.analysis.risks)}, Mitigations: {len(reasoning.verification.risk_mitigation)}"
        )

        return result

    def _critique_alternatives(self, reasoning: StructuredReasoning) -> Dict[str, Any]:
        """Critique consideration of alternatives"""
        result = {"score": 0.0, "issues": [], "details": ""}

        options = reasoning.analysis.options

        if not options:
            result["score"] = 0.2
            result["issues"].append("No alternative approaches considered")
            result["details"] = "Should consider multiple approaches"
        elif len(options) == 1:
            result["score"] = 0.5
            result["issues"].append("Only one option considered")
            result["details"] = "Consider at least 2-3 alternatives"
        else:
            result["score"] = min(1.0, len(options) / 3.0)
            result["details"] = f"{len(options)} alternatives considered"

            # Check if fallback uses alternative
            if reasoning.decision.fallback_plan:
                result["score"] = min(1.0, result["score"] + 0.2)

        return result

    def _identify_blind_spots(self, reasoning: StructuredReasoning) -> List[str]:
        """Identify potential blind spots in reasoning"""
        blind_spots = []

        # No implicit needs identified
        if not reasoning.perception.implicit_needs:
            blind_spots.append("May have missed implicit requirements or needs")

        # No constraints identified
        if not reasoning.comprehension.constraints:
            blind_spots.append("No constraints considered - may overlook limitations")

        # No dependencies identified
        if not reasoning.analysis.dependencies:
            blind_spots.append("No dependencies mapped - may miss ordering issues")

        # High confidence without counter-evidence
        if reasoning.get_confidence() > 0.8 and not reasoning.reasoning.evidence_against:
            blind_spots.append("High confidence without considering counter-evidence")

        # No potential issues in verification
        if not reasoning.verification.potential_issues:
            blind_spots.append("No potential issues identified - may miss failure modes")

        return blind_spots

    def _identify_weak_points(
        self, reasoning: StructuredReasoning, aspects: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Identify weak points based on aspect scores"""
        weak_points = []

        for aspect_name, aspect_data in aspects.items():
            if aspect_data["score"] < 0.5:
                for issue in aspect_data.get("issues", []):
                    weak_points.append(f"[{aspect_name}] {issue}")

        return weak_points

    def _generate_suggestions(
        self, reasoning: StructuredReasoning, critique: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []

        # Based on weak aspects
        for aspect_name, aspect_data in critique["aspects"].items():
            if aspect_data["score"] < 0.5:
                if aspect_name == "completeness":
                    suggestions.append("Complete all reasoning phases for thorough analysis")
                elif aspect_name == "logical_coherence":
                    suggestions.append(
                        "Add explicit logical chain connecting premises to conclusion"
                    )
                elif aspect_name == "evidence_quality":
                    suggestions.append("Gather more evidence and consider counter-arguments")
                elif aspect_name == "assumption_validity":
                    suggestions.append("Explicitly state and validate all assumptions")
                elif aspect_name == "risk_awareness":
                    suggestions.append("Identify risks and develop mitigation strategies")
                elif aspect_name == "alternative_consideration":
                    suggestions.append("Evaluate at least 2-3 alternative approaches")

        # Based on blind spots
        if critique["blind_spots"]:
            suggestions.append("Address identified blind spots before proceeding")

        # Based on confidence
        if reasoning.get_confidence() < 0.5:
            suggestions.append(
                "Low confidence - consider gathering more information or using fallback"
            )

        return suggestions[:5]  # Limit to top 5

    def _identify_strengths(
        self, reasoning: StructuredReasoning, aspects: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Identify reasoning strengths"""
        strengths = []

        for aspect_name, aspect_data in aspects.items():
            if aspect_data["score"] >= 0.8:
                strengths.append(f"Strong {aspect_name.replace('_', ' ')}")

        if reasoning.is_self_critical():
            strengths.append("Demonstrates self-critical thinking")

        if reasoning.has_fallback():
            strengths.append("Has fallback plan for resilience")

        if reasoning.quality_score() >= 0.7:
            strengths.append("High overall reasoning quality")

        return strengths


class ReasoningQualityMetrics:
    """
    Comprehensive metrics for reasoning quality assessment.

    Tracks various dimensions of reasoning quality over time.
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def evaluate(self, reasoning: StructuredReasoning) -> Dict[str, float]:
        """
        Evaluate reasoning quality across multiple dimensions.

        Args:
            reasoning: Structured reasoning to evaluate

        Returns:
            Dictionary of metric scores (0-1)
        """
        metrics = {}

        # Completeness (0-1)
        metrics["completeness"] = self._calculate_completeness(reasoning)

        # Depth (0-1)
        metrics["depth"] = self._calculate_depth(reasoning)

        # Coherence (0-1)
        metrics["coherence"] = self._calculate_coherence(reasoning)

        # Actionability (0-1)
        metrics["actionability"] = self._calculate_actionability(reasoning)

        # Self-criticism (0-1)
        metrics["self_criticism"] = self._calculate_self_criticism(reasoning)

        # Risk awareness (0-1)
        metrics["risk_awareness"] = self._calculate_risk_awareness(reasoning)

        # Confidence calibration (0-1)
        metrics["confidence_appropriateness"] = self._calculate_confidence_appropriateness(
            reasoning
        )

        # Overall score (weighted average)
        weights = {
            "completeness": 0.15,
            "depth": 0.20,
            "coherence": 0.20,
            "actionability": 0.15,
            "self_criticism": 0.10,
            "risk_awareness": 0.10,
            "confidence_appropriateness": 0.10,
        }

        metrics["overall"] = sum(metrics[k] * weights[k] for k in weights.keys())

        # Store in history
        self.history.append(
            {
                "reasoning_id": reasoning.id,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
            }
        )

        return metrics

    def _calculate_completeness(self, reasoning: StructuredReasoning) -> float:
        """Calculate phase completeness score"""
        complete_count = sum(
            [
                reasoning.perception.is_complete(),
                reasoning.comprehension.is_complete(),
                reasoning.analysis.is_complete(),
                reasoning.reasoning.is_complete(),
                reasoning.decision.is_complete(),
                reasoning.verification.is_complete(),
            ]
        )
        return complete_count / 6.0

    def _calculate_depth(self, reasoning: StructuredReasoning) -> float:
        """Calculate reasoning depth score"""
        depth_factors = []

        # Evidence depth
        evidence_count = len(reasoning.reasoning.evidence_for) + len(
            reasoning.reasoning.evidence_against
        )
        depth_factors.append(min(1.0, evidence_count / 4.0))

        # Analysis depth
        decomposition_count = len(reasoning.analysis.decomposition)
        depth_factors.append(min(1.0, decomposition_count / 5.0))

        # Options considered
        options_count = len(reasoning.analysis.options)
        depth_factors.append(min(1.0, options_count / 3.0))

        # Logical chain length
        chain_length = len(reasoning.reasoning.logical_chain)
        depth_factors.append(min(1.0, chain_length / 3.0))

        return statistics.mean(depth_factors) if depth_factors else 0.0

    def _calculate_coherence(self, reasoning: StructuredReasoning) -> float:
        """Calculate logical coherence score"""
        coherence_factors = []

        # Has logical chain
        coherence_factors.append(1.0 if reasoning.reasoning.logical_chain else 0.0)

        # Decision has justification
        coherence_factors.append(1.0 if reasoning.decision.justification else 0.0)

        # Verification aligns with decision
        coherence_factors.append(1.0 if reasoning.verification.is_complete() else 0.0)

        # Fallback exists for low confidence
        if reasoning.decision.confidence < 0.7:
            coherence_factors.append(1.0 if reasoning.decision.fallback_plan else 0.0)
        else:
            coherence_factors.append(1.0)

        return statistics.mean(coherence_factors) if coherence_factors else 0.0

    def _calculate_actionability(self, reasoning: StructuredReasoning) -> float:
        """Calculate actionability score"""
        factors = []

        # Has action items
        factors.append(min(1.0, len(reasoning.decision.action_items) / 3.0))

        # Has decomposition steps
        factors.append(min(1.0, len(reasoning.analysis.decomposition) / 3.0))

        # Has expected outcome
        factors.append(1.0 if reasoning.decision.expected_outcome else 0.0)

        # Ready to execute
        factors.append(1.0 if reasoning.verification.ready_to_execute else 0.5)

        return statistics.mean(factors) if factors else 0.0

    def _calculate_self_criticism(self, reasoning: StructuredReasoning) -> float:
        """Calculate self-criticism score"""
        factors = []

        # Has counter-evidence
        factors.append(min(1.0, len(reasoning.reasoning.evidence_against) / 2.0))

        # Has counter-arguments
        factors.append(min(1.0, len(reasoning.reasoning.counter_arguments) / 2.0))

        # Has potential issues
        factors.append(min(1.0, len(reasoning.verification.potential_issues) / 2.0))

        # Has risks identified
        factors.append(min(1.0, len(reasoning.analysis.risks) / 2.0))

        return statistics.mean(factors) if factors else 0.0

    def _calculate_risk_awareness(self, reasoning: StructuredReasoning) -> float:
        """Calculate risk awareness score"""
        factors = []

        # Risks identified
        factors.append(min(1.0, len(reasoning.analysis.risks) / 3.0))

        # Safety check performed
        factors.append(1.0 if reasoning.verification.safety_check != "Not specified" else 0.0)

        # Risk mitigation present
        factors.append(min(1.0, len(reasoning.verification.risk_mitigation) / 2.0))

        # Has fallback
        factors.append(1.0 if reasoning.decision.fallback_plan else 0.0)

        return statistics.mean(factors) if factors else 0.0

    def _calculate_confidence_appropriateness(self, reasoning: StructuredReasoning) -> float:
        """Calculate confidence appropriateness score"""
        confidence = reasoning.get_confidence()

        # Check if confidence aligns with reasoning quality
        quality = reasoning.quality_score()

        # Confidence should roughly match quality
        gap = abs(confidence - quality)

        # Penalize overconfidence more than underconfidence
        if confidence > quality:
            gap *= 1.5

        return max(0.0, 1.0 - gap)

    def get_trend(self, window: int = 10) -> Dict[str, float]:
        """
        Get trend in metrics over recent history.

        Args:
            window: Number of recent evaluations to consider

        Returns:
            Dictionary of metric trends (positive = improving)
        """
        if len(self.history) < 2:
            return {}

        recent = self.history[-window:]
        if len(recent) < 2:
            return {}

        trends = {}
        metrics_names = recent[0]["metrics"].keys()

        for metric in metrics_names:
            values = [h["metrics"][metric] for h in recent]
            # Calculate simple trend (last half vs first half average)
            mid = len(values) // 2
            first_half = statistics.mean(values[:mid]) if mid > 0 else values[0]
            second_half = statistics.mean(values[mid:])
            trends[metric] = second_half - first_half

        return trends

    def get_summary_report(self) -> Dict[str, Any]:
        """Generate summary report of all metrics"""
        if not self.history:
            return {"error": "No evaluations recorded"}

        report = {
            "total_evaluations": len(self.history),
            "averages": {},
            "trends": self.get_trend(),
            "best": {},
            "worst": {},
        }

        # Calculate averages
        metrics_names = self.history[0]["metrics"].keys()
        for metric in metrics_names:
            values = [h["metrics"][metric] for h in self.history]
            report["averages"][metric] = statistics.mean(values)
            report["best"][metric] = max(values)
            report["worst"][metric] = min(values)

        return report
