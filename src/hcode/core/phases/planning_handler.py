"""
Planning Phase Handler
=======================

This module implements the *Planning* phase of the PEV (Planning → Execution → Verification) workflow used by the Hcode engine.

The handler is responsible for:

- **Deep analysis of user requirements** – parsing the initial prompt, extracting goals, and identifying constraints.
- **Research and understanding of the codebase** – locating relevant modules, classes, and functions, and building a mental model of the project structure.
- **Generating `task.md`** – a checklist of concrete tasks (with unique IDs) that guides subsequent phases.
- **Creating `implementation_plan.md`** – a step‑by‑step plan that outlines how each task will be tackled, including any required resources.
- **Determining completion** – the handler decides when the planning stage is sufficient to move on to execution.

The module currently provides only utility imports; the actual handler class/function will be added in future iterations. The enhanced docstring ensures that developers immediately understand the intended responsibilities and integration points.
"""

import logging
import re
from pathlib import Path
from typing import List, Any, Dict, Tuple, Optional

from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult
from hcode.providers.base import Message

# FileAction enum for HcodeDisplay tracking
try:
    from hcode.ui.hcode_display import FileAction
except ImportError:
    FileAction = None

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# META-COGNITIVE TRACKER CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


class UncertaintyTracker:
    """
    Tracks what the agent doesn't know and drives targeted research.
    
    Maintains three severity levels:
    - critical: Must resolve before planning (blocks artifact writing)
    - important: Should resolve for quality (generates warnings)
    - minor: Nice to know (informational only)
    """
    
    def __init__(self):
        self.uncertainties: Dict[str, List[Dict[str, Any]]] = {
            'critical': [],
            'important': [],
            'minor': []
        }
        self.current_round = 0
    
    def add_uncertainty(self, question: str, severity: str, context: str = "") -> None:
        """
        Record an uncertainty that needs resolution.
        
        Args:
            question: The uncertain aspect
            severity: 'critical', 'important', or 'minor'
            context: Additional context about where this came from
        """
        if severity not in self.uncertainties:
            severity = 'minor'
        
        self.uncertainties[severity].append({
            'question': question,
            'context': context,
            'round_identified': self.current_round,
            'resolved': False,
            'resolution': None
        })
    
    def resolve_uncertainty(self, question: str, resolution: str) -> bool:
        """Mark an uncertainty as resolved with explanation."""
        for severity in self.uncertainties:
            for unc in self.uncertainties[severity]:
                if unc['question'] == question and not unc['resolved']:
                    unc['resolved'] = True
                    unc['resolution'] = resolution
                    return True
        return False
    
    def get_unresolved(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get unresolved uncertainties, optionally filtered by severity."""
        if severity:
            return [u for u in self.uncertainties.get(severity, []) if not u['resolved']]
        
        all_unresolved = []
        for sev in ['critical', 'important', 'minor']:
            all_unresolved.extend([
                {**u, 'severity': sev} 
                for u in self.uncertainties[sev] 
                if not u['resolved']
            ])
        return all_unresolved
    
    def get_critical_count(self) -> int:
        """Get count of unresolved critical uncertainties."""
        return len([u for u in self.uncertainties['critical'] if not u['resolved']])
    
    def suggest_next_research(self) -> List[str]:
        """
        Suggest what to research next based on unresolved uncertainties.
        
        Returns:
            Prioritized list of research suggestions
        """
        suggestions = []
        
        # Critical first
        for unc in self.uncertainties['critical']:
            if not unc['resolved']:
                suggestions.append(
                    f"🚨 CRITICAL: {unc['question']}\n"
                    f"   Context: {unc['context']}\n"
                    f"   Suggested action: {self._suggest_tool_for(unc['question'])}"
                )
        
        # Then important
        for unc in self.uncertainties['important']:
            if not unc['resolved']:
                suggestions.append(
                    f"⚠️  IMPORTANT: {unc['question']}\n"
                    f"   Context: {unc['context']}\n"
                    f"   Suggested action: {self._suggest_tool_for(unc['question'])}"
                )
        
        return suggestions
    
    def _suggest_tool_for(self, question: str) -> str:
        """Suggest appropriate tool based on question type."""
        q_lower = question.lower()
        
        if 'where' in q_lower or 'which file' in q_lower:
            return "Use Glob to find relevant files"
        elif 'how does' in q_lower or 'what does' in q_lower:
            return "Use Read to understand implementation"
        elif 'search' in q_lower or 'find all' in q_lower:
            return "Use Grep to search across codebase"
        elif 'structure' in q_lower or 'directory' in q_lower:
            return "Use LS to explore directory structure"
        else:
            return "Use Read/Grep to investigate"
    
    def format_summary(self) -> str:
        """Format a summary of all uncertainties."""
        critical = self.get_unresolved('critical')
        important = self.get_unresolved('important')
        minor = self.get_unresolved('minor')
        
        summary = "## Uncertainty Summary\n\n"
        
        if critical:
            summary += f"🚨 **Critical Uncertainties ({len(critical)}):**\n"
            for u in critical:
                summary += f"  - {u['question']}\n"
            summary += "\n"
        
        if important:
            summary += f"⚠️  **Important Uncertainties ({len(important)}):**\n"
            for u in important:
                summary += f"  - {u['question']}\n"
            summary += "\n"
        
        if minor:
            summary += f"ℹ️  **Minor Uncertainties ({len(minor)}):**\n"
            for u in minor:
                summary += f"  - {u['question']}\n"
        
        if not (critical or important or minor):
            summary += "✓ No unresolved uncertainties\n"
        
        return summary
    
    def reset(self) -> None:
        """Reset all uncertainties for a new planning session."""
        self.uncertainties = {'critical': [], 'important': [], 'minor': []}
        self.current_round = 0


class ConfidenceTracker:
    """
    Tracks agent's confidence in different aspects of understanding.
    
    Confidence is scored 1-5 for each dimension:
    1 = No understanding
    2 = Minimal understanding
    3 = Moderate understanding (acceptable for some aspects)
    4 = Good understanding
    5 = Complete understanding
    """
    
    DIMENSIONS = ['requirements', 'architecture', 'dependencies', 'edge_cases', 'testing', 'patterns']
    
    def __init__(self):
        self.scores: Dict[str, int] = {dim: 1 for dim in self.DIMENSIONS}
        self.history: List[Dict[str, Any]] = []
    
    def update_score(self, dimension: str, score: int, reason: str = "") -> None:
        """
        Update confidence score for a dimension.
        
        Args:
            dimension: Which aspect to update
            score: New score (1-5)
            reason: Why this score (for debugging/logging)
        """
        if dimension not in self.scores:
            logger.warning(f"Unknown confidence dimension: {dimension}")
            return
        
        if not 1 <= score <= 5:
            logger.warning(f"Invalid confidence score: {score}")
            score = max(1, min(5, score))
        
        old_score = self.scores[dimension]
        self.scores[dimension] = score
        
        self.history.append({
            'dimension': dimension,
            'old_score': old_score,
            'new_score': score,
            'reason': reason,
            'timestamp': len(self.history)
        })
    
    def get_score(self, dimension: str) -> int:
        """Get current confidence score for a dimension."""
        return self.scores.get(dimension, 1)
    
    def get_average_score(self) -> float:
        """Get average confidence across all dimensions."""
        return sum(self.scores.values()) / len(self.scores)
    
    def get_low_confidence_areas(self, threshold: int = 3) -> List[str]:
        """Get dimensions with confidence below threshold."""
        return [
            dim for dim, score in self.scores.items()
            if score < threshold
        ]
    
    def is_ready_for_planning(self) -> Tuple[bool, List[str]]:
        """
        Determine if confidence is sufficient for artifact writing.
        
        Criteria:
        - Requirements must be >= 4 (critical)
        - Architecture must be >= 3 (important)
        - At least 4/6 dimensions must be >= 3
        
        Returns:
            (is_ready, blocking_issues)
        """
        blocking_issues = []
        
        if self.scores['requirements'] < 4:
            blocking_issues.append(
                f"Requirements understanding too low: {self.scores['requirements']}/5 (need >= 4)"
            )
        
        if self.scores['architecture'] < 3:
            blocking_issues.append(
                f"Architecture understanding too low: {self.scores['architecture']}/5 (need >= 3)"
            )
        
        sufficient_count = sum(1 for score in self.scores.values() if score >= 3)
        if sufficient_count < 4:
            blocking_issues.append(
                f"Only {sufficient_count}/6 dimensions have adequate confidence (need >= 4)"
            )
        
        return (len(blocking_issues) == 0, blocking_issues)
    
    def format_summary(self) -> str:
        """Format a confidence summary."""
        summary = "## Confidence Assessment\n\n"
        
        for dim, score in self.scores.items():
            stars = "★" * score + "☆" * (5 - score)
            label = dim.replace('_', ' ').title()
            summary += f"- **{label}**: {stars} ({score}/5)\n"
        
        avg = self.get_average_score()
        summary += f"\n**Average**: {avg:.1f}/5\n"
        
        low_areas = self.get_low_confidence_areas()
        if low_areas:
            summary += f"\n⚠️  **Low confidence areas**: {', '.join(low_areas)}\n"
        
        return summary
    
    def reset(self) -> None:
        """Reset all scores for a new planning session."""
        self.scores = {dim: 1 for dim in self.DIMENSIONS}
        self.history = []


class ResearchSaturationDetector:
    """
    Determines when further research has diminishing returns.
    
    Tracks:
    - Files read per round
    - New insights gained per round
    - Uncertainty trend (increasing, stable, decreasing)
    - Confidence trajectory
    """
    
    def __init__(self):
        self.read_files: set = set()
        self.new_insights_per_round: List[int] = []
        self.uncertainty_count_per_round: List[int] = []
        self.confidence_per_round: List[float] = []
        self.current_round = 0
    
    def record_round_completion(
        self,
        files_read: List[str],
        insights_gained: int,
        uncertainty_count: int,
        avg_confidence: float
    ) -> None:
        """Record metrics at end of round."""
        # Track new files (not re-reads)
        new_files = set(files_read) - self.read_files
        self.read_files.update(files_read)
        
        self.new_insights_per_round.append(insights_gained)
        self.uncertainty_count_per_round.append(uncertainty_count)
        self.confidence_per_round.append(avg_confidence)
        self.current_round += 1
    
    def is_saturated(self) -> bool:
        """
        Detect if research has reached saturation point.
        
        Saturation indicators:
        1. Last 2 rounds produced minimal new insights (< 2 each)
        2. Uncertainty count is stable or decreasing
        3. Confidence is high (>= 3.5) and stable
        4. No new files discovered in last round
        
        Returns:
            True if research is saturated
        """
        if self.current_round < 3:
            return False  # Too early to judge
        
        # Check insights trend
        if len(self.new_insights_per_round) >= 2:
            recent_insights = self.new_insights_per_round[-2:]
            if all(insights < 2 for insights in recent_insights):
                # Very low insights for 2 rounds
                if self.confidence_per_round[-1] >= 3.5:
                    return True
        
        # Check uncertainty trend
        if len(self.uncertainty_count_per_round) >= 2:
            if self.uncertainty_count_per_round[-1] == 0:
                # No uncertainties and high confidence
                if self.confidence_per_round[-1] >= 4.0:
                    return True
        
        # Check confidence plateau
        if len(self.confidence_per_round) >= 3:
            recent_conf = self.confidence_per_round[-3:]
            if all(c >= 4.0 for c in recent_conf):
                # High confidence for 3 rounds
                return True
        
        return False
    
    def get_saturation_level(self) -> str:
        """
        Get saturation level description.
        
        Returns:
            'low', 'moderate', or 'high'
        """
        if self.current_round < 2:
            return 'low'
        
        if self.is_saturated():
            return 'high'
        
        # Check if trending toward saturation
        if self.confidence_per_round and self.confidence_per_round[-1] >= 3.5:
            return 'moderate'
        
        return 'low'
    
    def recommend_action(self) -> str:
        """
        Recommend whether to continue research or move to planning.
        
        Returns:
            Action recommendation string
        """
        if self.is_saturated():
            return (
                "✓ Research SATURATED: Sufficient understanding achieved.\n"
                "→ Proceed to solution design or artifact writing."
            )
        
        level = self.get_saturation_level()
        
        if level == 'moderate':
            return (
                "⚠ Research MODERATE: Good progress made.\n"
                "→ Consider 1-2 more targeted reads to address remaining gaps, "
                "then proceed to design."
            )
        
        # Low saturation
        gaps = self._identify_knowledge_gaps()
        return (
            f"❌ Research LOW: Significant gaps remain.\n"
            f"→ Focus on: {gaps}"
        )
    
    def _identify_knowledge_gaps(self) -> str:
        """Identify what's missing based on metrics."""
        gaps = []
        
        if len(self.read_files) < 5:
            gaps.append("Read more files (minimum 5 for quality planning)")
        
        if self.current_round > 0:
            if self.confidence_per_round[-1] < 3.0:
                gaps.append("Build deeper understanding (confidence too low)")
            
            if self.uncertainty_count_per_round[-1] > 3:
                gaps.append("Resolve critical uncertainties")
        
        return ", ".join(gaps) if gaps else "Continue systematic exploration"
    
    def reset(self) -> None:
        """Reset all metrics for a new planning session."""
        self.read_files = set()
        self.new_insights_per_round = []
        self.uncertainty_count_per_round = []
        self.confidence_per_round = []
        self.current_round = 0


# ═══════════════════════════════════════════════════════════════════════════════
# PLANNING PHASE HANDLER
# ═══════════════════════════════════════════════════════════════════════════════


class PlanningPhaseHandler(BasePhaseHandler):
    """
    Handler for the Planning phase of PEV workflow.

    Creates:
    - .hcode/task.md: Task understanding and subtasks with checkbox format
    - .hcode/implementation_plan.md: Implementation steps with file paths

    The planning phase follows this workflow:
    1. Deep analysis of user requirements
    2. Research codebase to identify relevant files
    3. Create task breakdown with trackable subtasks
    4. Create detailed implementation plan with:
       - Goal description
       - User review required items
       - Proposed changes grouped by component
       - Verification plan

    Transition criteria:
    - Both artifacts exist and have valid content
    - Plan has concrete steps with file paths
    - Agent confirms plan is ready for user review
    """

    phase_name = "planning"

    # ──────────────────────────────────────────────────────────
    # Round configuration for multi-round thinking
    # ──────────────────────────────────────────────────────────
    MAX_ROUNDS = 8   # Maximum rounds for planning
    MIN_ROUNDS = 3   # Must complete at least 3 rounds
    
    # Research thresholds
    MIN_FILES_READ = 5
    MIN_GLOBS = 1
    
    # Confidence thresholds
    MIN_REQUIREMENTS_CONFIDENCE = 4
    MIN_ARCHITECTURE_CONFIDENCE = 3
    MIN_ADEQUATE_DIMENSIONS = 4
    
    # Reflection points (inject reflection after these rounds)
    REFLECTION_ROUNDS = [2, 4]

    # ──────────────────────────────────────────────────────────
    # Allowed write targets during the planning phase.
    # Any Write/Edit to a path outside this set is rejected and
    # reported back to the AI so it can self-correct.
    # ──────────────────────────────────────────────────────────
    _PLANNING_WRITE_ALLOWED = (".hcode/task.md", ".hcode/implementation_plan.md")

    def __init__(self, artifact_manager, provider, tool_executor, context_manager, console=None):
        """
        Initialize planning phase handler with meta-cognitive trackers.
        
        Args:
            artifact_manager: Manager for phase artifacts
            provider: AI provider for generating responses
            tool_executor: Executor for tool calls
            context_manager: Context manager
            console: Rich console for output (optional)
        """
        super().__init__(artifact_manager, provider, tool_executor, context_manager, console)
        
        # Initialize meta-cognitive trackers
        self.uncertainty_tracker = UncertaintyTracker()
        self.confidence_tracker = ConfidenceTracker()
        self.saturation_detector = ResearchSaturationDetector()

    def get_required_artifacts(self) -> List[str]:
        """Get artifacts this phase should produce."""
        return ["task.md", "implementation_plan.md"]


    async def _execute_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext,
    ) -> List[Dict[str, Any]]:
        """
        Planning-phase gate: reject Write/Edit calls that target files
        outside `.hcode/`.  Read-only tools (Read, LS, SmartGlob, Grep, Bash)
        pass through unchanged.

        Blocked writes are returned as failed results with a clear message
        so the multi-turn loop feeds the error back to the AI.
        """
        gated_calls = []
        results = []

        for tc in tool_calls:
            tool_name = (tc.get("tool") or "").lower()
            arguments = tc.get("arguments", {})

            # Only gate write-like tools
            if tool_name in ("write", "writetool"):
                target = (
                    arguments.get("TargetFile")
                    or arguments.get("file_path")
                    or arguments.get("path")
                    or ""
                )
                # Normalise path separators and check if target ends with an allowed artifact
                norm_target = target.replace("\\", "/").rstrip("/")
                allowed = any(norm_target.endswith(a) for a in self._PLANNING_WRITE_ALLOWED)
                if not allowed:
                    # Block and record
                    self._display(
                        f"  [>] {tc.get('tool')}: {target}  ← BLOCKED (planning scope)",
                        style="error",
                    )
                    results.append({
                        "tool": tc.get("tool"),
                        "success": False,
                        "output": None,
                        "error": (
                            f"PLANNING SCOPE VIOLATION: Write to '{target}' is not allowed "
                            f"during the planning phase. Only .hcode/task.md and "
                            f".hcode/implementation_plan.md may be written. "
                            f"Implementation files must be created in the Execution phase."
                        ),
                        "file_path": target,
                    })
                    logger.warning(f"Blocked planning-phase write to: {target}")
                    continue  # skip — don't add to gated_calls

            gated_calls.append(tc)

        # Execute the allowed calls via the parent implementation
        if gated_calls:
            parent_results = await super()._execute_tools(gated_calls, context)
            results.extend(parent_results)

        return results

    def _build_continuation_prompt(
        self,
        round_results: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]],
        round_num: int,
        context: Any = None,
    ) -> str:
        """
        Planning-phase continuation: use phase detection to route to appropriate prompts.

        This implements the multi-round thinking architecture:
        1. Detect current cognitive phase based on progress
        2. Update saturation detector with round metrics
        3. Route to phase-specific prompt
        4. Include reflection prompts at key checkpoints
        """
        # ── Update saturation detector with round metrics ──
        files_read_this_round = [
            r.get("file_path", "") 
            for r in round_results
            if r.get("success") and r.get("tool", "").lower() == "read"
        ]
        
        self.saturation_detector.record_round_completion(
            files_read=files_read_this_round,
            insights_gained=len(round_results),
            uncertainty_count=self.uncertainty_tracker.get_critical_count(),
            avg_confidence=self.confidence_tracker.get_average_score()
        )
        
        # ── Determine current phase ──
        current_phase = self._determine_current_phase(all_results, context)
        
        logger.info(
            f"[planning] Round {round_num + 1}, Phase: {current_phase}, "
            f"Files read: {len(self.saturation_detector.read_files)}, "
            f"Confidence: {self.confidence_tracker.get_average_score():.1f}/5"
        )
        
        # ── Check for phase-specific validation ──
        can_continue, blocking_reasons = self._can_continue_to_next_round(
            round_num, current_phase, all_results, context
        )
        
        # ── Check if we should inject reflection ──
        if self._should_inject_reflection(round_num, current_phase):
            return self._build_reflection_prompt(round_num, round_results, all_results)
        
        # ── Route to phase-specific prompt ──
        if current_phase == "discovery":
            return self._build_discovery_prompt(round_num, all_results, context)
        
        elif current_phase == "exploration":
            return self._build_exploration_prompt(round_num, all_results, context)
        
        elif current_phase == "consolidation":
            return self._build_consolidation_prompt(round_num, all_results, context)
        
        elif current_phase == "design":
            return self._build_design_prompt(round_num, all_results, context)
        
        elif current_phase == "specification":
            return self._build_specification_prompt(round_num, all_results, context)
        
        else:
            return self._build_generic_continuation(round_num, all_results, context)

    def _validate_task_quality(self, context: AgentContext) -> Dict[str, Any]:
        """
        Validate task.md content meets quality requirements.

        Checks for:
        - ## Goal section
        - At least 4 subtasks with <!-- id: N --> markers
        - Acceptance criteria after subtasks
        - ## Risks / Edge Cases section

        Args:
            context: Current agent context

        Returns:
            Dict with validation results:
            - is_valid: bool
            - subtask_count: int
            - has_goal: bool
            - has_acceptance: bool
            - has_risks: bool
            - issues: List[str]
        """
        result = {
            "is_valid": False,
            "subtask_count": 0,
            "has_goal": False,
            "has_acceptance": False,
            "has_risks": False,
            "issues": [],
        }

        try:
            task_content = self.artifact_manager.load_artifact("task.md", context)
            if not task_content:
                result["issues"].append("task.md is empty or could not be read")
                return result

            # Check for ## Goal section
            result["has_goal"] = "## Goal" in task_content

            # Count subtasks with ID markers
            subtask_count = task_content.count("<!-- id:")
            result["subtask_count"] = subtask_count

            # Check for acceptance criteria
            result["has_acceptance"] = (
                "Acceptance:" in task_content or
                "acceptance:" in task_content or
                "- Acceptance" in task_content
            )

            # Check for risks/edge cases section
            result["has_risks"] = (
                "## Risks" in task_content or
                "## Edge Cases" in task_content or
                "## Risks / Edge Cases" in task_content
            )

            # Build issues list
            if not result["has_goal"]:
                result["issues"].append("Missing ## Goal section")
            if subtask_count < 4:
                result["issues"].append(f"Only {subtask_count} subtasks (need >= 4)")
            if not result["has_acceptance"]:
                result["issues"].append("No acceptance criteria found after subtasks")
            if not result["has_risks"]:
                result["issues"].append("Missing ## Risks / Edge Cases section")

            # Valid if all checks pass
            result["is_valid"] = (
                result["has_goal"] and
                subtask_count >= 4 and
                result["has_acceptance"] and
                result["has_risks"]
            )

        except Exception as e:
            logger.warning(f"Failed to validate task.md quality: {e}")
            result["issues"].append(f"Validation error: {e}")

        return result

    async def _run_planning_loop(
        self,
        unified_prompt: str,
        context: AgentContext,
        system_prompt: str,
        max_rounds: int,
        max_tokens: int,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Custom execution loop for planning phase.
        
        Differs from base implementation by:
        1. Supporting "thinking rounds" (no tool calls)
        2. Using explicit phase completion check
        3. Forcing artifact creation if missing at end
        """
        all_results = []
        last_response = ""
        
        # Build initial messages
        thinking_instructions = self._get_thinking_instructions()
        messages = [Message(role="user", content=thinking_instructions + unified_prompt)]

        for round_num in range(max_rounds):
            logger.info(f"[{self.phase_name}] Planning round {round_num + 1}/{max_rounds}...")
            
            # Generate response
            try:
                response = await self.provider.generate_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                
                # Extract content
                if hasattr(response, 'content'):
                    last_response = response.content
                elif isinstance(response, dict):
                    last_response = response.get('content', '')
                else:
                    last_response = str(response)
                    
            except Exception as e:
                logger.error(f"Provider call failed on round {round_num + 1}: {e}")
                self._display(f"Generation error: {e}", style="error")
                break

            # Display text portion
            text_portion = self._extract_text_response(last_response)
            if text_portion and len(text_portion.strip()) > 20:
                self._display(text_portion, style="default")

            # Extract tools
            tool_calls = self._extract_tool_calls(last_response)
            
            # Execute tools
            round_results = await self._execute_tools(tool_calls, context)
            all_results.extend(round_results)
            
            # Add assistant message
            messages.append(Message(role="assistant", content=last_response))
            
            # CHECK COMPLETION
            if self._is_planning_complete(all_results, context, round_num):
                break
                
            # Handle continuation
            if not tool_calls:
                if round_num >= max_rounds - 2:
                    # Force write if running out of rounds
                    continuation = (
                        "WARNING: You are running out of rounds. "
                        "You must write task.md and implementation_plan.md NOW."
                    )
                else:
                    # Just thinking/reflection - prod to continue
                    continuation = "Proceed to the next step."
            else:
                # Build continuation based on results
                continuation = self._build_continuation_prompt(
                    round_results, all_results, round_num, context
                )
            
            # Add user message
            messages.append(Message(role="user", content=continuation))
            
        return last_response, all_results

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute planning phase — single unified multi-turn exchange.

        The AI does everything in one conversation:
          Round 1-N  : Explore the codebase (Read, Glob, Grep, LS …)
          Round N+1  : Write .hcode/task.md
          Round N+2+ : Write .hcode/implementation_plan.md
        The continuation prompt steers the AI after each round so it doesn't
        stop prematurely.  Fallbacks fire only if the AI exhausts max_rounds
        without producing an artifact.

        Args:
            context: Current agent context
            loop_controller: Loop controller

        Returns:
            PhaseResult with planning outcome
        """
        try:
            artifacts_created = []
            analysis_insights: Dict[str, Any] = {}

            logger.info(f"Planning phase iteration {context.iteration} for task: {context.task[:50]}...")

            # =====================================================================
            # CLEAN SLATE – delete stale artifacts from previous tasks
            # =====================================================================
            for _art in ("task.md", "implementation_plan.md", "walkthrough.md"):
                _path = self.artifact_manager._get_artifact_path(_art, context)
                if _path.exists():
                    _path.unlink()
                    logger.info(f"Removed stale artifact: {_art}")

            # =====================================================================
            # RESET TRACKERS – clean state for multi-round thinking
            # =====================================================================
            self._reset_trackers()
            logger.info("Reset meta-cognitive trackers for new planning session")

            # =====================================================================
            # PROGRAMMATIC EXPLORATION – ground the prompt with real data
            # =====================================================================
            exploration_context = self._explore_codebase(context)
            self._display("Exploring codebase...", style="info")

            # =====================================================================
            # SINGLE UNIFIED PROMPT – explore then create artifacts
            # =====================================================================
            unified_prompt = self._build_unified_planning_prompt(context, exploration_context)

            response = ""
            tool_results: List[Dict[str, Any]] = []

            if self.provider is not None:
                self._display("Planning…", style="info")

                if self._hcode_display:
                    self._hcode_display.start_thinking()

                # Use custom loop instead of base _generate_and_execute
                response, tool_results = await self._run_planning_loop(
                    unified_prompt,
                    context,
                    system_prompt=self._get_planning_system_prompt(context),
                    max_rounds=self.MAX_ROUNDS,
                    max_tokens=16384,
                )

                if self._hcode_display:
                    self._hcode_display.end_thinking()

                # Track which artifacts the AI actually wrote
                for result in tool_results:
                    if not result.get("success"):
                        continue
                    fp = str(result.get("file_path", ""))
                    if "task.md" in fp and "task.md" not in artifacts_created:
                        artifacts_created.append("task.md")
                        if self._hcode_display and FileAction:
                            self._hcode_display.track_file(".hcode/task.md", FileAction.CREATED)
                    if "implementation_plan.md" in fp and "implementation_plan.md" not in artifacts_created:
                        artifacts_created.append("implementation_plan.md")
                        if self._hcode_display and FileAction:
                            self._hcode_display.track_file(".hcode/implementation_plan.md", FileAction.CREATED)

                # Extract insights from the response (used by fallback if needed)
                analysis_insights = self._extract_analysis_insights(response)

            else:
                logger.warning("No AI provider configured for planning phase")
                self._display("No AI provider configured for planning!", style="error")

            # =====================================================================
            # ARTIFACT VALIDATION
            # The agent is solely responsible for generating task.md and 
            # implementation_plan.md using the guidance prompts. No fallbacks.
            # =====================================================================
            if not self.artifact_manager.artifact_exists("task.md", context):
                self._display("  [!] task.md missing — agent failed to generate it", style="error")
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output="Planning failed: Agent did not create task.md. Increase max_rounds or check prompts.",
                    artifacts_created=artifacts_created,
                    can_transition=False,
                    error="task.md not created by agent",
                )

            if not self.artifact_manager.artifact_exists("implementation_plan.md", context):
                self._display("  [!] implementation_plan.md missing — agent failed to generate it", style="error")
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output="Planning failed: Agent did not create implementation_plan.md. Increase max_rounds or check prompts.",
                    artifacts_created=artifacts_created,
                    can_transition=False,
                    error="implementation_plan.md not created by agent",
                )

            # =====================================================================
            # VALIDATE & TRANSITION
            # =====================================================================
            valid, error = self.validate_artifacts(context)
            if not valid:
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output=f"Planning phase validation failed: {error}",
                    artifacts_created=artifacts_created,
                    can_transition=False,
                    error=error,
                    metadata={"tool_results": tool_results, "analysis_insights": analysis_insights},
                )

            can_transition = self.can_transition_to_next(context)

            is_exploration = context.metadata.get("task_type") == "exploration"
            output = response if (is_exploration and response) else (
                f"Planning phase complete. Created: {', '.join(artifacts_created) or 'no new artifacts'}"
            )

            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output=output,
                artifacts_created=artifacts_created,
                can_transition=can_transition,
                metadata={"tool_results": tool_results, "analysis_insights": analysis_insights, "response": response},
            )

        except Exception as e:
            logger.exception(f"Planning phase failed: {e}")
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                output=f"Planning phase failed: {str(e)}",
                can_transition=False,
                error=str(e),
            )

    def _get_planning_system_prompt(self, context: AgentContext) -> str:
        """
        Get system prompt for planning phase.

        Uses core prompts from phases.yaml.

        Args:
            context: Current agent context

        Returns:
            Complete system prompt for planning
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            # Get identity and tool format
            identity = loader.get_identity()
            tool_format = loader.get_tool_format()

            # Get planning instruction from core prompts
            planning_prompt = loader.build_planning_prompt(task=context.task)

            # Load canonical guidance from .md files (more detailed than inline templates)
            task_guidance = loader.get_task_guidance()
            plan_guidance = loader.get_implementation_plan_guidance()

            # Build artifact templates section from guidance files
            artifact_templates = f"""### task.md Guidance

{task_guidance}

---

### implementation_plan.md Guidance

{plan_guidance}"""

            # Build system prompt with identity, tool format, and templates
            system_base = f"""{identity}

{tool_format}

---

{planning_prompt}

---

## ARTIFACT CREATION GUIDANCE

Follow these guidelines EXACTLY when creating task.md and implementation_plan.md:

{artifact_templates}"""

            # ── Load project knowledge from /init ──────────────────
            project_knowledge = ""
            try:
                _hcode_md = Path(context.working_dir) / ".hcode" / "hcode.md"
                if _hcode_md.exists():
                    project_knowledge = _hcode_md.read_text(encoding='utf-8')
            except Exception:
                pass

            pk_section = (
                project_knowledge
                if project_knowledge
                else "(Run /init first to generate project knowledge.)"
            )

            # Add context information
            context_info = f"""
## PROJECT KNOWLEDGE  (generated by /init — read this before anything else)

{pk_section}

---

## Hcode Context

Working Directory: {context.working_dir}
Artifact Directory: .hcode
Current Iteration: {context.iteration}

### PEV Workflow (ALWAYS ENFORCED)

1. **PLANNING** ← you are here: create task.md and implementation_plan.md
2. **EXECUTION**: implement the plan
3. **VERIFICATION**: test and create walkthrough.md

**Tools you should use in planning:**
- Read: `{{"tool": "Read", "arguments": {{"AbsolutePath": "/full/path"}}}}`  ← primary tool
- Grep: `{{"tool": "Grep", "arguments": {{"Query": "pattern", "SearchPath": "."}}}}`  ← find symbols
- Write: `{{"tool": "Write", "arguments": {{"TargetFile": "/full/path", "CodeContent": "content"}}}}`  ← artifacts only

**Tools you should NOT need in planning:**
- LS / SmartGlob: project structure is already in PROJECT KNOWLEDGE above.
  Use them only if you genuinely need to discover something not covered there.

### Artifact Detail Requirements

Each artifact must be granular — the execution phase reads these to know
exactly what to do.  Generic placeholders are not acceptable.

**task.md** must contain:
  • A `## Goal` section (1-2 sentences)
  • 4-8 subtasks, each naming a specific file + function/class
  • Acceptance criteria after every subtask
  • A `## Risks / Edge Cases` section

**implementation_plan.md** must contain:
  • Each `[MODIFY]` block: exact target (function/line), current behavior,
    before/after pseudocode, imports to add, and a one-line "Why"
  • Each `[NEW]` block: purpose, file-structure outline, what imports it
  • A `## Execution Context` section: conventions, interfaces, error patterns, test infra
  • A `## Dependencies Between Changes` section
  • Exact verification commands — language-appropriate (syntax check, tests, smoke test)

### Example — think first, then read, then plan:

I need to add error logging to CLI startup.  From the project knowledge
I can see the CLI entry is `src/hcode/main_cli.py` and observability lives
in `src/hcode/core/observability/`.  Let me read the actual files before
deciding anything.

```json
{{"tool": "Read", "arguments": {{"AbsolutePath": "{context.working_dir}/src/hcode/main_cli.py"}}}}
```

(… receives file contents …)

The startup sequence is at line 42 — a bare try block with no logging.
Now let me check how the logger factory works:

```json
{{"tool": "Read", "arguments": {{"AbsolutePath": "{context.working_dir}/src/hcode/core/observability/logger.py"}}}}
```

(… receives file contents …)

`get_logger(name)` returns a stdlib Logger.  I now know the exact import,
the call site, and what the current code does.  Writing task.md:

```json
{{"tool": "Write", "arguments": {{"TargetFile": "{context.working_dir}/.hcode/task.md", "CodeContent": "# Task\\n\\nAdd error logging to CLI startup\\n\\n## Goal\\n\\nErrors during CLI initialisation are captured by the observability logger.\\n\\n## Subtasks\\n\\n- [ ] Add `from hcode.core.observability.logger import get_logger` to main_cli.py <!-- id: 0 -->\\n  - Acceptance: `python -m py_compile src/hcode/main_cli.py` exits 0\\n- [ ] Insert `logger.error(exc)` in the except block at startup (line 42) <!-- id: 1 -->\\n  - Acceptance: error path produces a log entry in output\\n- [ ] Run `pytest tests/unit/test_cli.py -v` <!-- id: 2 -->\\n  - Acceptance: all tests pass\\n\\n## Risks\\n\\n- Logger must be initialised before the call site at line 42"}}}}
```

task.md written.  Now writing implementation_plan.md with full detail:

```json
{{"tool": "Write", "arguments": {{"TargetFile": "{context.working_dir}/.hcode/implementation_plan.md", "CodeContent": "# Add error logging to CLI startup\\n\\nThe CLI startup at line 42 does not log errors — they propagate uncaught.\\nThis change adds a logger call so failures are captured.\\n\\n## Approach\\n\\n`get_logger` in the observability layer is the project convention.\\nReuse it — no new abstractions needed.\\n\\n## Execution Context\\n\\n- **Import convention:** absolute imports, one per line\\n- **Error handling:** try/except + logger.error()\\n- **Test framework:** pytest\\n- **Key interfaces:** none affected by this change\\n\\n## Proposed Changes\\n\\n### CLI Entry Point\\n\\n#### [MODIFY] `src/hcode/main_cli.py`\\n\\n**Target:** startup block, line 42\\n**Current behavior:** exceptions during init propagate uncaught (bare except)\\n**Required change:**\\n- Add import: `from hcode.core.observability.logger import get_logger`\\n- Add `logger = get_logger(__name__)` after existing imports\\n- In the except block at line 42: add `logger.error(\\\"Startup failed\\\", exc_info=True)`\\n**Why:** observability layer is the project convention for error capture\\n\\n## Dependencies Between Changes\\n\\nSingle file changed — no ordering constraints.\\n\\n## Verification Plan\\n\\n- `python -m py_compile src/hcode/main_cli.py`\\n- `pytest tests/unit/test_cli.py -v`\\n- `python -m hcode --help` — confirm no crash"}}}}
```

Both artifacts written.  Planning complete.

⚠️  SCOPE BOUNDARY: In planning mode you ONLY create `.hcode/task.md` and `.hcode/implementation_plan.md`.
Do NOT create any implementation / source files. Those are created during EXECUTION.
"""
            return system_base + context_info

        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            # Fallback to basic prompt
            return f"""You are Hcode, an AI coding assistant in PLANNING mode.

Your task: {context.task}

Working Directory: {context.working_dir}

## Instructions

1. Analyze the user's request
2. Explore the codebase using tools (LS, Glob, Read)
3. Create .hcode/task.md with task breakdown
4. Create .hcode/implementation_plan.md with implementation approach

IMPORTANT: Always provide text explanations along with tool usage.
DO NOT just output JSON silently.
"""

    def _explore_codebase(self, context: AgentContext) -> str:
        """
        Language-agnostic file-path index for the planning prompt.

        Single rglob pass: discovers source, config, web, and doc files
        across all supported languages/frameworks.  Groups output by
        extension with source files first so the AI can target Read
        calls with precise paths.  Project knowledge (architecture,
        conventions) lives in the system prompt via hcode.md — this
        method only provides the file inventory.
        """
        from collections import defaultdict

        working_dir = Path(context.working_dir)
        lines = [f"Working directory: {context.working_dir}\n"]

        _EXCLUDE = {'.git', '.venv', 'node_modules', '__pycache__', '.idea',
                    'dist', 'build', '.mypy_cache', '.next', '.cache'}

        # ── Extension sets (language-agnostic) ──
        _SOURCE = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.mjs', '.cjs',
            '.go', '.rs', '.java', '.rb', '.cs', '.swift', '.kt', '.kts',
            '.scala', '.c', '.cpp', '.h', '.hpp', '.cc', '.cxx',
            '.vue', '.svelte', '.php', '.lua', '.sh', '.bash',
        }
        _CONFIG = {'.yaml', '.yml', '.json', '.toml', '.cfg', '.ini', '.env'}
        _WEB    = {'.html', '.css', '.scss', '.sass', '.less'}
        _DOC    = {'.md', '.rst', '.txt'}
        _ALL    = _SOURCE | _CONFIG | _WEB | _DOC

        by_ext: Dict[str, List[Path]] = defaultdict(list)
        for p in sorted(working_dir.rglob("*")):
            if not p.is_file():
                continue
            if any(ex in p.parts for ex in _EXCLUDE):
                continue
            ext = p.suffix.lower()
            if ext in _ALL:
                by_ext[ext].append(p)

        # Priority: source → config → web → docs; within tier sort by count desc
        def _priority(ext):
            if ext in _SOURCE: return 0
            if ext in _CONFIG: return 1
            if ext in _WEB:    return 2
            return 3

        for ext, files in sorted(by_ext.items(), key=lambda kv: (_priority(kv[0]), -len(kv[1]))):
            lines.append(f"{ext} files ({len(files)}):")
            for f in files[:35]:
                lines.append(f"  {f.relative_to(working_dir)}")
            if len(files) > 35:
                lines.append(f"  ... and {len(files) - 35} more")
            lines.append("")

        return "\n".join(lines)

    def _get_task_template_guide(self) -> str:
        """
        Get the task.md guidance from the core prompts.
        
        Loads the full content from src/hcode/config/core_prompts/core/task.md
        which provides detailed instructions for creating task.md artifacts.
        
        Returns:
            Task.md guidance content
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()
            return loader.get_task_guidance()
        except Exception as e:
            logger.warning(f"Failed to load task.md guidance: {e}")
            # Fallback to inline summary
            return """
## task.md Guidelines

Create a task breakdown with:
- A clear ## Goal section (1-2 sentences)
- 4-8 concrete subtasks with `<!-- id: N -->` markers
- Each subtask should name specific files and functions
- Acceptance criteria for each subtask
- A ## Risks / Edge Cases section

Use the following format:
- [ ] for pending tasks
- [/] for in-progress tasks  
- [x] for completed tasks
"""

    def _get_plan_template_guide(self) -> str:
        """
        Get the implementation_plan.md guidance from the core prompts.
        
        Loads the full content from src/hcode/config/core_prompts/core/implementation_plan.md
        which provides detailed instructions for creating implementation plans.
        
        Returns:
            Implementation plan guidance content
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()
            return loader.get_implementation_plan_guidance()
        except Exception as e:
            logger.warning(f"Failed to load implementation_plan.md guidance: {e}")
            # Fallback to inline summary
            return """
## implementation_plan.md Guidelines

Create a detailed implementation plan with:

### Structure
- # Goal Description (brief problem description)
- ## User Review Required (critical decisions)
- ## Proposed Changes (grouped by component)
  - ### [Component Name]
  - #### [MODIFY] [filename](file:///path) - for modifications
  - #### [NEW] [filename](file:///path) - for new files
  - #### [DELETE] [filename](file:///path) - for deletions
- ## Verification Plan
  - ### Automated Tests (exact commands)
  - ### Manual Verification (what to check)

### Requirements
- Every file marked with [NEW], [MODIFY], or [DELETE]
- Exact targets: function/class names and line numbers
- Current behavior and required changes
- Dependencies between changes
- Concrete verification commands
"""

    def _build_unified_planning_prompt(self, context: AgentContext, exploration_context: str) -> str:
        """
        Build the single unified prompt that drives the entire planning phase.

        The system prompt already contains the full project knowledge
        (hcode.md).  This prompt drives a think → read → synthesize →
        write flow.  No repo-discovery rounds — the AI already knows the
        project; it must only read the *specific* files relevant to this
        task before writing artifacts.
        """
        task_template = self._get_task_template_guide()
        plan_template = self._get_plan_template_guide()

        return f"""You are an expert AI developer in PLANNING mode.  You already know the
project structure and conventions from the PROJECT KNOWLEDGE in your system
prompt.  Your job: understand this specific request deeply, read the files
that matter, then produce two planning artifacts — and NOTHING else.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context.task}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE INDEX  (use these paths in Read calls — do NOT run LS or Glob)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{exploration_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — THINK  (write this out before calling any tool)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before touching any tool, reason through:

  • What exactly does the user want to happen?
  • Which existing files are directly involved?  (use your project knowledge)
  • Is this an addition, a modification, or a removal?
  • What are the likely risks or edge cases?
  • Which files do I need to READ to make confident decisions?

Write this reasoning out loud.  Every line of reasoning here saves a wasted
round later.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — READ  (tools: Read and Grep only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Open every file your Step 1 identified as relevant.  Use Read with
absolute paths.  Use Grep only if you need to locate a specific symbol
or pattern inside a file.

⚠️  Do NOT use LS or SmartGlob — the file index above and the
    PROJECT KNOWLEDGE in the system prompt already cover the layout.
⚠️  Do NOT assume file contents.  Read first, decide second.
⚠️  After each Read, state concretely what you learned and how it
    affects the plan.  This reasoning feeds directly into the artifacts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — SYNTHESIZE  (text only, no tools)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Now that you have read the real code, pin down:

  • Exactly which functions / classes / lines need changing?
  • What new files or code blocks are needed?
  • What imports, signatures, or interfaces must be respected?
  • What tests should verify correctness?  (exact commands)
  • What conventions / patterns must execution follow? (imports, error handling, naming, tests)
  • Any dependencies between changes — ordering matters.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — WRITE task.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Path: {context.working_dir}/.hcode/task.md

{task_template}

Rules:
  • Every subtask gets a unique `<!-- id: N -->` comment.
  • Use `- [ ]` for pending, `- [/]` for in-progress, `- [x]` for done.
  • Break work into 4-8 concrete subtasks grounded in what you Read.
  • Every subtask MUST name the specific file + function/class it touches.
  • Include acceptance criteria after each subtask (what proves it is done).
  • Add a ## Goal section (1-2 sentences: what success looks like).
  • Add a ## Risks / Edge Cases section with findings from your reads.
  • No generic boilerplate — if you cannot tie a subtask to real code, omit it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — WRITE implementation_plan.md  (immediately after task.md)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Path: {context.working_dir}/.hcode/implementation_plan.md

{plan_template}

Rules:
  • Approach: WHY this approach — reference real code / patterns you Read.
  • Every file that will be created or modified must have a [NEW] or
    [MODIFY] marker with an absolute path.
  • Each [MODIFY] block MUST contain:
      – Exact target: function/class name and line number
      – Current behavior: what the code does RIGHT NOW (from your Reads)
      – Required change: before/after pseudocode or code snippets
      – Imports to add (if any)
      – Why: one sentence linking this change to the goal
  • Each [NEW] block MUST contain:
      – Purpose: why this file is needed
      – Structure: outline of classes/functions it will contain
      – What other files will import from it
  • Include a ## Execution Context section: conventions, interfaces, error patterns,
      test framework details the execution phase must follow — no re-reading required.
  • Include a ## Dependencies Between Changes section: ordering constraints.
  • Verification Plan: exact shell commands for syntax, unit, and integration tests.
  • Nothing in this plan may be speculation — every claim must trace
    back to something you actually Read.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE RULES  (hard boundaries)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  You may ONLY write two files:
      {context.working_dir}/.hcode/task.md
      {context.working_dir}/.hcode/implementation_plan.md
    Any write to any other path will be BLOCKED by the system.

⚠️  Do NOT create implementation files (scripts, modules, configs).
    Those are created during the Execution phase.

⚠️  Do NOT stop until BOTH artifacts have been written.
    The system will tell you after each tool round whether an artifact
    is still missing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BEGIN.  Start with Step 1 — think out loud before calling any tool.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    # NOTE: The agent generates task.md and implementation_plan.md directly from
    # the guidance prompts in src/hcode/config/core_prompts/core/task.md and
    # implementation_plan.md. Template methods have been removed.

    def _extract_analysis_insights(self, response: str) -> Dict[str, Any]:
        """
        Extract analysis insights from AI response.

        Parses the <analysis> block from the AI's deep analysis.

        Args:
            response: AI response containing analysis

        Returns:
            Dict with extracted insights
        """
        insights = {
            "understanding": "",
            "relevant_files": [],
            "components": [],
            "dependencies": [],
            "questions": [],
            "approach": "",
        }

        if not response:
            return insights

        # Try to extract analysis block
        analysis_match = re.search(
            r'<analysis>(.*?)</analysis>',
            response,
            re.DOTALL | re.IGNORECASE
        )

        if analysis_match:
            analysis_content = analysis_match.group(1)
        else:
            # Use full response if no block found
            analysis_content = response

        # Extract understanding section
        understanding_match = re.search(
            r'##\s*Understanding\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if understanding_match:
            insights["understanding"] = understanding_match.group(1).strip()

        # Extract relevant files
        files_match = re.search(
            r'##\s*Relevant Files?\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if files_match:
            files_text = files_match.group(1)
            file_lines = re.findall(r'-\s*([^\n:]+)', files_text)
            insights["relevant_files"] = [f.strip() for f in file_lines if f.strip()]

        # Extract components
        components_match = re.search(
            r'##\s*Components?\s*(?:Affected)?\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if components_match:
            components_text = components_match.group(1)
            component_lines = re.findall(r'-\s*([^\n]+)', components_text)
            insights["components"] = [c.strip() for c in component_lines if c.strip()]

        # Extract approach
        approach_match = re.search(
            r'##\s*(?:Recommended\s*)?Approach\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if approach_match:
            insights["approach"] = approach_match.group(1).strip()

        # Extract questions/ambiguities
        questions_match = re.search(
            r'##\s*(?:Questions?|Ambiguities?)\s*\n(.*?)(?=##|\Z)',
            analysis_content,
            re.DOTALL | re.IGNORECASE
        )
        if questions_match:
            questions_text = questions_match.group(1)
            question_lines = re.findall(r'-\s*([^\n]+)', questions_text)
            insights["questions"] = [q.strip() for q in question_lines if q.strip()]

        return insights

    # NOTE: _extract_read_insights, _create_fallback_task_md, and _create_fallback_implementation_plan
    # have been removed. The agent generates artifacts directly from the guidance prompts.

    # NOTE: _extract_read_insights, _create_fallback_task_md, and _create_fallback_implementation_plan
    # have been removed. The agent generates artifacts directly from the guidance prompts.

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """
        Check if ready to transition to execution phase.

        Criteria:
        - Both task.md and implementation_plan.md exist
        - Both have valid content
        - Plan has concrete steps (not just placeholders)

        Args:
            context: Current agent context

        Returns:
            True if planning is complete
        """
        # Check if required artifacts exist
        if not self.artifact_manager.artifact_exists("task.md", context):
            return False

        if not self.artifact_manager.artifact_exists("implementation_plan.md", context):
            return False

        # Validate content
        valid, _ = self.validate_artifacts(context)
        if not valid:
            return False

        # Check plan has concrete steps (accept multiple plan formats)
        plan_content = self.artifact_manager.load_artifact("implementation_plan.md", context)
        if plan_content:
            has_concrete_steps = (
                "file://" in plan_content or
                "[MODIFY]" in plan_content or
                "[NEW]" in plan_content or
                "####" in plan_content or
                "## Steps" in plan_content or
                "## Proposed Changes" in plan_content or
                "## Files to Modify" in plan_content or
                "## Approach" in plan_content or
                ".py" in plan_content or
                ".js" in plan_content or
                ".ts" in plan_content
            )
            if not has_concrete_steps:
                return False

        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # MULTI-ROUND THINKING: Phase Detection
    # ═══════════════════════════════════════════════════════════════════════════

    def _determine_current_phase(
        self, 
        all_results: List[Dict[str, Any]], 
        context: AgentContext
    ) -> str:
        """
        Determine the current cognitive phase based on progress.
        
        Phase transitions:
        - discovery: Initial phase, until 3+ files identified
        - exploration: Once files identified, until 5+ files read
        - consolidation: Once sufficient reading done, until uncertainties resolved
        - design: Once understanding solid, ready to design solution
        - specification: Final phase, writing detailed artifacts
        
        Returns:
            Current phase name
        """
        read_count = sum(
            1 for r in all_results 
            if r.get("success") and r.get("tool", "").lower() == "read"
        )
        glob_count = sum(
            1 for r in all_results 
            if r.get("success") and r.get("tool", "").lower() in ("glob", "smartglob")
        )
        
        wrote_task = any(
            r.get("success") and "task.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        wrote_plan = any(
            r.get("success") and "implementation_plan.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        
        # Specification phase: Writing artifacts
        if wrote_task or wrote_plan:
            return "specification"
        
        # Design phase: Sufficient research done, ready to design
        if read_count >= 5 and self._has_resolved_critical_uncertainties():
            return "design"
        
        # Consolidation phase: Done initial reading, verifying understanding
        if read_count >= 3:
            return "consolidation"
        
        # Exploration phase: Files identified, reading them
        if glob_count >= 1 or read_count >= 1:
            return "exploration"
        
        # Discovery phase: Initial understanding
        return "discovery"

    def _is_planning_complete(
        self,
        all_results: List[Dict[str, Any]],
        context: AgentContext,
        round_num: int
    ) -> bool:
        """
        Determine if planning phase is complete.
        
        Completion criteria:
        1. Both task.md and implementation_plan.md exist
        2. Both artifacts have valid content
        3. Minimum rounds completed (prevent rushing)
        4. Quality validation passes
        
        Args:
            all_results: All tool results across rounds
            context: Agent context
            round_num: Current round number
            
        Returns:
            True if planning is complete
        """
        # Must complete minimum rounds
        if round_num < self.MIN_ROUNDS:
            return False
        
        # Check artifacts exist
        wrote_task = any(
            r.get("success") and "task.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        wrote_plan = any(
            r.get("success") and "implementation_plan.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        
        if not (wrote_task and wrote_plan):
            return False
        
        # Validate artifact quality
        valid, _ = self.validate_artifacts(context)
        
        return valid

    # ═══════════════════════════════════════════════════════════════════════════
    # MULTI-ROUND THINKING: Validation Gates
    # ═══════════════════════════════════════════════════════════════════════════

    def _can_write_artifacts(self, context: AgentContext) -> Tuple[bool, List[str]]:
        """
        Determine if sufficient understanding exists to write quality artifacts.
        
        Validation gates:
        1. Minimum research threshold met
        2. No critical uncertainties remain
        3. Confidence scores are adequate
        4. Edge cases identified
        
        Returns:
            (can_write, blocking_issues)
        """
        blocking_issues = []
        
        # Gate 1: Minimum research
        read_count = len(self.saturation_detector.read_files)
        
        if read_count < self.MIN_FILES_READ:
            blocking_issues.append(
                f"❌ Insufficient research: {read_count}/{self.MIN_FILES_READ} minimum files read\n"
                f"   → Use Glob to find more relevant files, then Read them"
            )
        
        # Gate 2: Critical uncertainties
        critical_uncertainties = self.uncertainty_tracker.get_unresolved('critical')
        if critical_uncertainties:
            blocking_issues.append(
                f"❌ {len(critical_uncertainties)} critical uncertainties remain:\n" +
                "\n".join(f"   → {u['question']}" for u in critical_uncertainties)
            )
        
        # Gate 3: Confidence scores
        ready, confidence_issues = self.confidence_tracker.is_ready_for_planning()
        if not ready:
            blocking_issues.append(
                "❌ Confidence too low in key areas:\n" +
                "\n".join(f"   → {issue}" for issue in confidence_issues)
            )
        
        # Gate 4: Edge cases identified
        if self.confidence_tracker.get_score('edge_cases') < 3:
            blocking_issues.append(
                "❌ Edge cases not adequately identified\n"
                "   → Think through: What could go wrong? What are unusual scenarios?"
            )
        
        # Gate 5: Warn if skipping important uncertainties (non-blocking)
        important_uncertainties = self.uncertainty_tracker.get_unresolved('important')
        if important_uncertainties and not any(b.startswith("❌") for b in blocking_issues):
            blocking_issues.append(
                f"⚠️  {len(important_uncertainties)} important uncertainties remain (non-blocking):\n" +
                "\n".join(f"   → {u['question']}" for u in important_uncertainties)
            )
        
        return (len([b for b in blocking_issues if b.startswith("❌")]) == 0, blocking_issues)

    def _can_continue_to_next_round(
        self,
        round_num: int,
        current_phase: str,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> Tuple[bool, List[str]]:
        """
        Validate if agent can progress to next round.
        
        Phase-specific validation:
        - Discovery: Must have identified files
        - Exploration: Must have read files
        - Consolidation: Must have resolved uncertainties
        - Design: Must have evaluated approaches
        - Specification: Must have written artifacts
        
        Returns:
            (can_continue, reasons_if_not)
        """
        reasons = []
        
        if current_phase == "discovery":
            # Must have done some exploration
            glob_count = sum(
                1 for r in all_results
                if r.get("success") and r.get("tool", "").lower() in ("glob", "smartglob")
            )
            if glob_count == 0:
                reasons.append(
                    "Discovery incomplete: No files identified yet. "
                    "Use Glob to find relevant files."
                )
        
        elif current_phase == "exploration":
            # Must have read files
            read_count = sum(
                1 for r in all_results
                if r.get("success") and r.get("tool", "").lower() == "read"
            )
            if read_count < 3:
                reasons.append(
                    f"Exploration incomplete: Only {read_count} files read. "
                    f"Read at least 3 files to understand the codebase."
                )
        
        elif current_phase == "consolidation":
            # Critical uncertainties must be resolved
            critical_count = self.uncertainty_tracker.get_critical_count()
            if critical_count > 0:
                reasons.append(
                    f"Consolidation incomplete: {critical_count} critical uncertainties remain. "
                    f"Resolve these before proceeding to design."
                )
        
        elif current_phase == "design":
            # Check if design was considered (conservative default)
            pass  # Allow progression in design phase
        
        return (len(reasons) == 0, reasons)

    # ═══════════════════════════════════════════════════════════════════════════
    # MULTI-ROUND THINKING: Helper Methods
    # ═══════════════════════════════════════════════════════════════════════════

    def _has_resolved_critical_uncertainties(self) -> bool:
        """Check if all critical uncertainties have been resolved."""
        return self.uncertainty_tracker.get_critical_count() == 0

    def _has_documented_approach_selection(self, all_results: List[Dict[str, Any]]) -> bool:
        """
        Check if agent has documented evaluation of multiple approaches.
        
        Returns:
            True if approach selection was properly documented
        """
        # Conservative default - this would need to parse conversation history
        # to verify structured evaluation was done
        return False

    def _format_readiness_check(self, can_write: bool, blocking_issues: List[str]) -> str:
        """Format the readiness check section for prompts."""
        if can_write:
            return """
✅ **READY TO PROCEED TO DESIGN**

All validation gates passed:
- Sufficient research completed
- No critical uncertainties
- Confidence scores adequate
- Edge cases identified

You may proceed to design phase or write artifacts.
"""
        else:
            return """
❌ **NOT READY - BLOCKING ISSUES REMAIN**

The following issues must be resolved before writing artifacts:

""" + "\n".join(blocking_issues)

    def _process_reflection_response(self, reflection_response: str) -> None:
        """
        Process agent's reflection response to update trackers.
        
        Attempts to parse confidence scores and update tracker.
        
        Args:
            reflection_response: Agent's reflection text
        """
        # Try to extract confidence scores from reflection
        # Pattern: "dimension: X/5"
        confidence_pattern = r'(\w+(?:\s+\w+)*?):\s*(\d)/5'
        
        matches = re.findall(confidence_pattern, reflection_response, re.IGNORECASE)
        
        dimension_mapping = {
            'requirements': 'requirements',
            'user requirements': 'requirements',
            'architecture': 'architecture',
            'codebase architecture': 'architecture',
            'dependencies': 'dependencies',
            'edge cases': 'edge_cases',
            'testing': 'testing',
            'approach': 'patterns',
            'patterns': 'patterns',
        }
        
        for dim_text, score in matches:
            dim_text_clean = dim_text.lower().strip()
            if dim_text_clean in dimension_mapping:
                dimension = dimension_mapping[dim_text_clean]
                score_int = int(score)
                self.confidence_tracker.update_score(
                    dimension, score_int, "From reflection"
                )

    def _should_inject_reflection(self, round_num: int, current_phase: str) -> bool:
        """Determine if reflection should be injected after this round."""
        return round_num in self.REFLECTION_ROUNDS or current_phase in ['exploration', 'design']

    # ═══════════════════════════════════════════════════════════════════════════
    # MULTI-ROUND THINKING: Phase-Specific Prompts
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_discovery_prompt(
        self,
        round_num: int,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for discovery phase (Round 1-2)."""
        
        glob_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() in ("glob", "smartglob")
        )
        read_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() == "read"
        )
        working_dir = context.working_dir if context else "."
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUND {round_num + 1}: DISCOVERY PHASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📊 Current Progress
- Files discovered: {glob_count} searches
- Files read: {read_count}
- Tool calls made: {len(all_results)}

## 🎯 Phase Objective
Build foundational understanding of the problem and codebase.

## 🧠 Thinking Framework for This Round

### 1. Requirement Deconstruction
Ask yourself:
- What is the user asking for at the surface level?
- What are the unstated requirements or assumptions?
- What context am I missing to fully understand this request?
- What does "done" look like for this task?

### 2. Codebase Mapping
Identify:
- What parts of the codebase are relevant to this request?
- How is the codebase organized? (directories, modules, patterns)
- What patterns or conventions exist that I should follow?
- Where would similar functionality exist currently?

### 3. Initial Hypothesis Formation
Based on your limited information so far:
- What seems to be needed at a high level?
- What are 2-3 different ways this could be approached?
- What questions or uncertainties do I have?

## ✅ Success Criteria for This Phase
By end of this round, you should have:
- [ ] Listed 5-10 potentially relevant files or directories
- [ ] Initial understanding of the problem domain
- [ ] List of critical questions that need answers
- [ ] Hypothesis about what components will be affected

## 🛠️ Recommended Actions
1. **Use Glob** to discover relevant files
2. **Read README** or documentation files if they exist
3. **Use LS** to understand directory structure
4. **Document uncertainties** as you discover them

## ⚠️ Important Reminders
- DO NOT write task.md or implementation_plan.md yet
- Focus on breadth (what exists) more than depth (how it works)

## 🚫 Scope Reminder
You may ONLY write:
  - {working_dir}/.hcode/task.md
  - {working_dir}/.hcode/implementation_plan.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Proceed with exploration. Think out loud before calling tools.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_exploration_prompt(
        self,
        round_num: int,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for exploration phase (Round 2-3)."""
        
        read_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() == "read"
        )
        
        saturation_level = self.saturation_detector.get_saturation_level()
        saturation_advice = self.saturation_detector.recommend_action()
        
        confidence_summary = self.confidence_tracker.format_summary()
        uncertainty_summary = self.uncertainty_tracker.format_summary()
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUND {round_num + 1}: EXPLORATION PHASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📊 Research Progress
- Files read: {read_count}
- Saturation level: {saturation_level.upper()}

{saturation_advice}

{confidence_summary}

{uncertainty_summary}

## 🎯 Phase Objective
Build comprehensive mental model of how the system works.

## 🧠 Thinking Framework for This Round

### 1. System Behavior Analysis
Understand:
- How do the components I've read actually interact?
- What's the data flow through the system?
- What's the control flow? (What calls what?)

### 2. Dependency Mapping
Identify:
- What depends on what?
- If I change component X, what else might be affected?

### 3. Edge Case Identification
Think through:
- What happens in unusual scenarios?
- What error conditions exist?

### 4. Pattern Recognition
Observe:
- What coding patterns or conventions are used?
- How is error handling done?

## ✅ Success Criteria for This Phase
- [ ] Trace a typical request/flow through the system
- [ ] Explain how key components interact
- [ ] List major dependencies
- [ ] Identify at least 3-5 edge cases

## 🛠️ Recommended Actions

### If Saturation is LOW:
1. **Read more files** - Focus on entry points, core logic, tests

### If Saturation is MODERATE:
1. **Target remaining gaps**
2. **Prepare for transition** to design phase

## ⚠️ Critical Reminders
- DO NOT write artifacts yet
- Focus on understanding BEHAVIOR, not just structure

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Continue exploration. Document what you learn.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_consolidation_prompt(
        self,
        round_num: int,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for consolidation phase (Round 3-4)."""
        
        critical_uncertainties = self.uncertainty_tracker.get_unresolved('critical')
        important_uncertainties = self.uncertainty_tracker.get_unresolved('important')
        
        can_write, blocking_issues = self._can_write_artifacts(context)
        
        confidence_summary = self.confidence_tracker.format_summary()
        readiness_check = self._format_readiness_check(can_write, blocking_issues)
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUND {round_num + 1}: CONSOLIDATION PHASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📊 Understanding Status

{confidence_summary}

### Uncertainties Remaining
- Critical: {len(critical_uncertainties)}
- Important: {len(important_uncertainties)}

## 🎯 Phase Objective
Verify your understanding and resolve any remaining critical uncertainties.

## 🧠 Thinking Framework for This Round

### 1. Mental Model Validation
Test your understanding:
- Can you explain the system end-to-end without looking at code?
- If you change Y, what breaks?

### 2. Uncertainty Resolution
For each remaining uncertainty:
- Is it critical to the planning? (Must resolve now)
- Is it important but non-blocking? (Note it)

### 3. Edge Case Verification
Double-check:
- What happens with invalid input?
- What happens in error conditions?

## ✅ Artifact Writing Readiness Check

{readiness_check}

## 🚦 Decision Point

Based on the readiness check above:
- ✅ **READY**: Proceed to design phase
- ❌ **NOT READY**: Resolve blocking issues first
- ⚠️  **BORDERLINE**: Do 1-2 more targeted reads

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Consolidate your understanding. Resolve critical gaps.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_design_prompt(
        self,
        round_num: int,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for design phase (Round 4-5)."""
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUND {round_num + 1}: SOLUTION DESIGN PHASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 Phase Objective
Generate and evaluate multiple solution approaches, then select the optimal one.

**YOU HAVE COMPLETED RESEARCH. NOW YOU MUST DESIGN THE SOLUTION.**

## 🧠 Structured Thinking Required

### Step 1: Generate Alternatives (Divergent Thinking)

Create at least **2-3 different approaches** to solve this problem:
- **Minimal Change**: Smallest modification to existing code
- **Comprehensive**: More significant restructuring for better design
- **Alternative**: Completely different approach (if applicable)

### Step 2: Evaluation

For each approach, consider:
- Maintainability
- Testability
- Risk Level
- Implementation Effort

### Step 3: Selection & Justification

**Recommended Approach**: [Your choice]

**Justification**: Why this approach is optimal

**Key Trade-offs**: What are you sacrificing? What are you gaining?

## ✅ Success Criteria for This Phase

- [ ] Generated 2+ distinct approaches
- [ ] Evaluated each approach
- [ ] Selected optimal approach with clear justification
- [ ] Identified risks

## 🛠️ Recommended Actions

1. **Think divergently first**: Don't settle on the first idea
2. **Be honest about trade-offs**: Every approach has pros and cons
3. **Document your reasoning**: Future you will thank you

## ⚠️ You Are Still in Planning

Do NOT write implementation code yet. After design, you will write:
- task.md (task breakdown)
- implementation_plan.md (detailed steps)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Think deeply about trade-offs. The best solution is rarely obvious.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_specification_prompt(
        self,
        round_num: int,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for specification phase (Round 5+)."""
        
        wrote_task = any(
            r.get("success") and "task.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        wrote_plan = any(
            r.get("success") and "implementation_plan.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        working_dir = context.working_dir if context else "."
        
        if wrote_task and wrote_plan:
            return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Both task.md and implementation_plan.md have been created.

✓ Planning phase is complete
✓ Artifacts will be validated
✓ Ready to transition to execution phase

DO NOT create any more files or continue planning.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if wrote_task and not wrote_plan:
            # Validate task.md quality first
            task_quality = self._validate_task_quality(context)
            
            if not task_quality["is_valid"]:
                issues = task_quality["issues"]
                return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK.MD QUALITY CHECK FAILED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  task.md was written but is INCOMPLETE.

**Quality Check Results:**
- Subtask count: {task_quality['subtask_count']} (need >= 4)
- Has ## Goal section: {task_quality['has_goal']}
- Has acceptance criteria: {task_quality['has_acceptance']}
- Has ## Risks / Edge Cases: {task_quality['has_risks']}

**Issues to fix:**
{chr(10).join(f"  - {issue}" for issue in issues)}

**Actions Required:**
1. Read .hcode/task.md to see what you wrote
2. REWRITE task.md with all required sections

DO NOT write implementation_plan.md until task.md passes validation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # task.md is valid — demand implementation plan
            return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATE IMPLEMENTATION_PLAN.MD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ task.md is valid and complete.

Now create `.hcode/implementation_plan.md` with detailed implementation steps.

## 📝 Required Structure

The plan MUST include:
- **Goal**: Restate the goal
- **Approach**: Summary of solution approach
- **Proposed Changes**: Every [MODIFY] and [NEW] file with details
- **Execution Context**: Conventions, testing, error handling
- **Dependencies Between Changes**: What must happen first
- **Verification Plan**: Exact commands to run

## ✅ Quality Requirements

- [ ] Every file marked with [NEW] or [MODIFY]
- [ ] Every [MODIFY] has: target, current behavior, required change
- [ ] Execution Context section
- [ ] Dependencies Between Changes section
- [ ] Verification Plan with actual commands

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create implementation_plan.md now. Use Write tool with:
TargetFile = `{working_dir}/.hcode/implementation_plan.md`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Neither artifact written yet — provide full instructions
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUND {round_num + 1}: SPECIFICATION PHASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 Phase Objective
Create detailed planning artifacts based on your research and design.

**YOU ARE NOW READY TO WRITE PLANNING ARTIFACTS.**

## 📝 Required Artifacts

### 1. task.md (Write First)

Create `.hcode/task.md` with this structure:
- **# Task Title**
- **## Goal** (1-2 sentences)
- **## Subtasks** (at least 4, with <!-- id: N --> markers)
- **## Risks / Edge Cases**

### 2. implementation_plan.md (Write Second)

After task.md is created, write `.hcode/implementation_plan.md`.

## 🛠️ How to Create task.md

Use Write tool with:
- TargetFile = `{working_dir}/.hcode/task.md`
- CodeContent = [your markdown content]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create task.md now. Be thorough and specific.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_reflection_prompt(
        self,
        round_num: int,
        round_results: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate reflection prompt for end of round.
        
        Encourages agent to think about thinking.
        """
        files_read_this_round = [
            r.get("file_path", "")
            for r in round_results
            if r.get("success") and r.get("tool", "").lower() == "read"
        ]
        
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFLECTION CHECKPOINT - End of Round {round_num}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔍 Round {round_num} Summary
- Tool calls made: {len(round_results)}
- Files read this round: {len(files_read_this_round)}

## 🧠 Reflection Questions

### 1. What did you learn this round?
[List 3-5 key insights]

### 2. Confidence Self-Assessment

Rate your confidence (1-5) in each area:

- Requirements: __/5
- Architecture: __/5
- Dependencies: __/5
- Edge cases: __/5
- Testing: __/5
- Patterns: __/5

### 3. Next Steps Decision

Choose ONE:
- [ ] **I need more research** - Specifically: [what?]
- [ ] **I'm ready to move to design phase**
- [ ] **I'm ready to write artifacts**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Respond with your reflection, then continue.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_generic_continuation(
        self,
        round_num: int,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Fallback generic continuation prompt."""
        working_dir = context.working_dir if context else "."
        
        read_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() == "read"
        )
        
        return f"""
[Round {round_num + 1}] You have read {read_count} file(s).

Continue your analysis. When ready, write:
  1. {working_dir}/.hcode/task.md
  2. {working_dir}/.hcode/implementation_plan.md
"""

    def _reset_trackers(self) -> None:
        """Reset all meta-cognitive trackers for a new planning session."""
        self.uncertainty_tracker.reset()
        self.confidence_tracker.reset()
        self.saturation_detector.reset()
