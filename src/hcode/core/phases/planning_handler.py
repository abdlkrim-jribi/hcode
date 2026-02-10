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

import json
import logging
import re
from pathlib import Path
from typing import List, Any, Dict, Tuple, Optional

from hcode.providers.base import Message
from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult

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
    MAX_ROUNDS = 20  # Maximum rounds for planning (increased from 8 to allow agent autonomy)
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

    def _get_thinking_instructions(self) -> str:
        """
        5-Phase thinking instructions for GPT-OSS-120B.

        Enforces the Evidence-First principle.
        """
        return """### DEEP REASONING PROTOCOL (5-Phase Planning)

    Use `<thinking>` and `<output>` tags to structure your reasoning.

    **Critical Requirements**:
    - Use `[Evidence: file.py:line]` to cite ALL code references in Phases 1 & 2.
    - Complete ALL checkpoints in a phase before proceeding.
    - You CANNOT write artifacts without reading the code first.

    **Phase Structure Template**:
    ```
    <thinking>
    [Phase Number]: [Phase Name]

    Step 1: [Specific Action]
      → Result: [Finding]
      → Evidence: [file:line] (If applicable)

    Step 2: [Specific Action]
      → Result: [Finding]
      → Evidence: [file:line]

    Self-validation checkpoint:
    - [ ] Specific requirement 1
    - [ ] Specific requirement 2
    - [ ] Ready to proceed to next phase

    Therefore: [Conclusion]
    </thinking>

    <output>
    [Brief summary]
    [Tool calls]
    </output>
    ```

    **The 5 Phases**:
    1. **Phase 0**: Requirements Deconstruction — Understand the user's intent.
    2. **Phase 1**: Deep Code Investigation — Read files. Gather evidence. NO SPECULATION.
    3. **Phase 2**: Solution Crystallization — Design the changes. Assess risks.
    4. **Phase 3**: Draft `task.md` — Create atomic subtasks.
    5. **Phase 4**: Draft `implementation_plan.md` — Create the technical blueprint.

    See `planning_mode.md` for detailed instructions for each phase.
    """

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Prioritize <output> tags for tool extraction."""
        if not response:
            return []

        # Check for <output>
        output_pattern = r'<output>(.*?)</output>'
        output_matches = re.findall(output_pattern, response, re.DOTALL | re.IGNORECASE)

        if output_matches:
            for output_content in output_matches:
                tool_calls = super()._extract_tool_calls(output_content.strip())
                if tool_calls:
                    return tool_calls

        return super()._extract_tool_calls(response)

    async def _execute_tools(self, tool_calls: List[Dict[str, Any]], context: AgentContext) -> List[Dict[str, Any]]:
        """Enforce write gate."""
        gated_calls = []
        results = []

        for tc in tool_calls:
            tool_name = (tc.get("tool") or "").lower()
            arguments = tc.get("arguments", {})

            if tool_name in ("write", "writetool"):
                target = (
                        arguments.get("TargetFile") or
                        arguments.get("file_path") or ""
                )
                norm_target = target.replace("\\", "/").rstrip("/")
                allowed = any(norm_target.endswith(a) for a in self._PLANNING_WRITE_ALLOWED)

                if not allowed:
                    results.append({
                        "tool": tc.get("tool"),
                        "success": False,
                        "error": f"PLANNING SCOPE: Cannot write '{target}'. Only {self._PLANNING_WRITE_ALLOWED} allowed.",
                    })
                    continue

            gated_calls.append(tc)

        if gated_calls:
            results.extend(await super()._execute_tools(gated_calls, context))

        return results

    def _build_continuation_prompt(
            self,
            round_results: List[Dict[str, Any]],
            all_results: List[Dict[str, Any]],
            round_num: int,
            context: Any = None,
    ) -> str:
        """
        5-Phase aware continuation prompt for GPT-OSS-120B.

        Detects the current phase and provides specific guidance to steer the AI
        from exploration to high-quality artifact generation.
        """
        # Detect state
        wrote_task = any(
            r.get("success") and "task.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        wrote_plan = any(
            r.get("success") and "implementation_plan.md" in str(r.get("file_path", ""))
            for r in all_results
        )

        read_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() == "read"
        )
        grep_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() == "grep"
        )
        glob_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() in ["glob", "globtool", "smartglobtool"]
        )

        # Check for errors
        recent_errors = [r for r in round_results if not r.get("success")]

        # ── PARAMETER FORMAT ERROR DETECTION ──────────────────────
        parameter_errors = [
            r for r in round_results
            if not r.get("success") and "Missing required parameter" in str(r.get("error", ""))
        ]

        if parameter_errors:
            error_details = parameter_errors[0].get("error", "")
            return f"""⚠️ TOOL FORMAT ERROR DETECTED

You called a tool with WRONG parameter format.

Error: {error_details}

**CORRECT FORMAT (copy this exactly):**

```json
{{"tool": "Glob", "arguments": {{"pattern": "**/*.py"}}}}
{{"tool": "Read", "arguments": {{"file_path": "path/file.py"}}}}
{{"tool": "Write", "arguments": {{"file_path": ".hcode/task.md", "content": "..."}}}}
{{"tool": "LS", "arguments": {{"path": "src/"}}}}
{{"tool": "Grep", "arguments": {{"pattern": "search", "path": "."}}}}
```

**COMMON MISTAKES (don't do this):**
❌ `{{"tool": "Glob"}}` - Missing arguments wrapper
❌ `{{"tool": "Glob", "arguments": {{"Pattern": "..."}}}}` - Uppercase parameter name
❌ `{{"Pattern": "..."}}` - Missing tool key
❌ `{{"tool": "Glob", "parameters": {{"pattern": "..."}}}}` - Use 'arguments' not 'parameters'
❌ `{{"tool": "Glob", "pattern": "..."}}` - Missing 'arguments' wrapper

**Your next action:**
Retry your last tool call using the CORRECT format from the table above.
Use LOWERCASE parameter names: pattern, file_path, content, path (not Pattern, AbsolutePath, etc)."""

        # ── LOOP DETECTION ────────────────────────────────────────
        # Detect if same tool called 2+ times with same args
        last_three_calls = []
        for result in all_results[-3:]:
            if result.get("success") and "tool" in result:
                # Create a signature of tool + arguments
                tool_name = result.get("tool", "")
                arguments = result.get("arguments", {})
                try:
                    args_str = json.dumps(arguments, sort_keys=True)
                    last_three_calls.append((tool_name, args_str))
                except:
                    pass

        # Check for duplicate calls
        if len(last_three_calls) >= 2:
            if last_three_calls[-1] == last_three_calls[-2]:
                tool_name = last_three_calls[-1][0]
                return f"""⚠️  LOOP DETECTED: You called {tool_name} with identical arguments twice in a row.

Recovery:
1. If Glob: STOP globbing. List what you found. Move to Read.
2. If Read failed: Check if file exists with a different path.
3. If stuck: Write artifacts with assumptions and flag them.

DO NOT call the same tool again. Progress to the next phase.

Status: Reads: {read_count}, Globs: {glob_count}, Greps: {grep_count}"""

        # ── ERROR RECOVERY ────────────────────────────────────────
        if recent_errors:
            return self._build_planning_error_recovery(recent_errors)

        # ── PHASE 0: START ─────────────────────────────────────────
        if read_count == 0 and glob_count == 0 and not wrote_task:
            return """📍 PHASE 0: Requirements Deconstruction

    You are at the start of planning.

    **Action:**
    1. Analyze the user's task request.
    2. Identify what you need to know.
    3. Formulate a search strategy (Glob/Grep).
    4. Begin Phase 1: Deep Code Investigation.

    **Do NOT write artifacts yet. You must read code first.**"""

        # ── PHASE 1: INVESTIGATION ────────────────────────────────
        if not wrote_task and not wrote_plan:
            # Agent is in exploration/investigation mode

            # If agent has read enough files, push toward design
            if read_count >= 3:
                return f"""📍 PHASE 1 → PHASE 2: Evidence Gathered

    Excellent! You have read {read_count} files.

    **Action:**
    1. Stop reading.
    2. Proceed to **Phase 2: Solution Crystallization**.
    3. Design your solution based on the evidence you gathered.
    4. Think about dependencies, risks, and atomicity.
    5. Do NOT write artifacts yet—wait for the next prompt to draft `task.md`.

    **Remember:**
    - Base your design on [Evidence: file.py:line].
    - Identify exact line numbers for changes."""

            # If agent hasn't read much, encourage it
            return f"""📍 PHASE 1: Deep Code Investigation

    You are gathering evidence. Reads: {read_count}, Globs: {glob_count}.

    **Action:**
    - Use **Glob** to find relevant files.
    - Use **Read** to inspect target files.
    - Use **Grep** to find usages/dependencies.
    - Extract context: Naming conventions, error handling, imports.

    **CRITICAL:** 
    - Do NOT guess file structures. Read them.
    - Cite evidence in your thinking: [Evidence: file.py:line].
    - Don't proceed to design until you understand the codebase.

    Target: Read at least 3-4 key files before designing."""

        # ── PHASE 3: WRITE task.md ─────────────────────────────────
        if wrote_task and not wrote_plan:
            # Validate task.md quality roughly before writing plan
            return """📍 PHASE 3 → PHASE 4: Task.md Complete

    You have created `task.md`. Now create the detailed blueprint.

    **Action:**
    Write `.hcode/implementation_plan.md` using the Write tool.

    **Required Structure:**
    1. **4-Dimension Deep Analysis** (Architecture, Dependencies, Quality, Context)
    2. **Proposed Changes** (Group by file)
       - [MODIFY] `file.py`
         - Target: function_name at line X [Evidence: file.py:X]
         - Current Behavior: ...
         - Required Change: ...
         - Why: ...
    3. **Verification Plan** (Exact commands)

    **Quality Check:**
    - Does every claim have [Evidence: file.py:line]?
    - Are changes specific (line numbers, function names)?
    - Is the verification command copy-pasteable?

    Write the plan now."""

        # ── PHASE 4: COMPLETE ──────────────────────────────────────
        if wrote_task and wrote_plan:
            return """✓ PLANNING COMPLETE

    Both artifacts have been created.
    - [x] task.md
    - [x] implementation_plan.md

    **Self-Check:**
    - [ ] Are subtasks atomic (doable in one session)?
    - [ ] Is the plan detailed enough for an agent to execute without research?
    - [ ] Are all changes backed by [Evidence: file.py:line]?

    If satisfied, you may end the phase."""

        # ── TIMEOUT / STUCK ─────────────────────────────────────────
        if round_num > 15:
            return f"""⚠️ ROUND LIMIT WARNING (Round {round_num + 1}/{self.MAX_ROUNDS})

    You have been researching for {round_num + 1} rounds.

    **Decision Time:**
    1. If you have read >= 3 files: Proceed to design (Phase 2) immediately.
    2. Write `task.md` now.
    3. Write `implementation_plan.md` now.
    4. Do not continue researching.

    Force the artifacts to be written now."""

        # Default fallback
        return "Continue with the 5-phase protocol. Read code, gather evidence, design solution, write artifacts."

    def _prompt_readiness_check(self, read_count: int, context: AgentContext) -> str:
        """Prompt to write task.md after sufficient exploration."""
        return f"""✓ Exploration complete ({read_count} files read).

Now write task.md:

```json
{{
  "tool": "Write",
  "arguments": {{
    "file_path": ".hcode/task.md",
    "content": "# Task: [Title]\\n\\n## Goal\\n[1-2 sentence description]\\n\\n## Subtasks\\n- [ ] Subtask 1 <!-- id: 0 -->\\n- [ ] Subtask 2 <!-- id: 1 -->\\n- [ ] Subtask 3 <!-- id: 2 -->\\n- [ ] Subtask 4 <!-- id: 3 -->\\n\\n## Risks / Edge Cases\\n- [Risk 1]\\n- [Risk 2]"
  }}
}}
```

Fill in the content based on what you learned from exploring the codebase."""

    def _prompt_for_implementation_plan(self, context: AgentContext) -> str:
        """Prompt to write implementation_plan.md after task.md is done."""
        return f"""✓ task.md created.

Now write implementation_plan.md using Write tool:
```json
{{
  "tool": "Write",
  "arguments": {{
    "file_path": ".hcode/implementation_plan.md",
    "content": "# Implementation Plan: [Title]\\n\\n## Overview\\n[Approach description]\\n\\n## File Changes\\n\\n### [MODIFY] file.py\\n**Changes**: ...\\n\\n### [NEW] new_file.py\\n**Purpose**: ...\\n\\n## Verification Plan\\n- [ ] Test command 1\\n- [ ] Test command 2"
  }}
}}
```"""


    def _validate_task_quality(self, context: AgentContext) -> Dict[str, Any]:
        """
        Validate task.md meets high standards for execution agent.
        """
        result = {
            "is_valid": False,
            "subtask_count": 0,
            "has_goal": False,
            "has_context": False,
            "has_risks": False,
            "issues": [],
        }

        try:
            content = self.artifact_manager.load_artifact("task.md", context)
            if not content:
                result["issues"].append("Empty task.md")
                return result

            # 1. Goal
            result["has_goal"] = "## Goal" in content
            if not result["has_goal"]:
                result["issues"].append("Missing ## Goal section")

            # 2. Context
            result["has_context"] = "## Context" in content or "## Current State" in content
            if not result["has_context"]:
                result["issues"].append("Missing ## Context section (Critical for execution agent)")

            # 3. Subtasks (Atomic)
            subtask_count = content.count("<!-- id:")
            result["subtask_count"] = subtask_count
            if subtask_count < 3:
                result["issues"].append(f"Too few subtasks ({subtask_count}). Break work down further.")

            # Check for non-atomic tasks (heuristic: long lines or "and")
            lines = content.split('\n')
            for line in lines:
                if '- [ ]' in line and len(line) > 150:
                    result["issues"].append(f"Potential non-atomic task (too long): {line[:50]}...")
                if '- [ ]' in line.lower() and ' and ' in line:
                    result["issues"].append(f"Potential non-atomic task (contains 'and'): {line[:50]}...")

            # 4. Risks
            result["has_risks"] = "## Risks" in content or "## Edge Cases" in content
            if not result["has_risks"]:
                result["issues"].append("Missing ## Risks / Edge Cases")

            result["is_valid"] = (
                result["has_goal"] and
                result["has_context"] and
                subtask_count >= 3 and
                result["has_risks"]
            )

        except Exception as e:
            logger.warning(f"Task validation error: {e}")
            result["issues"].append(f"Validation error: {e}")

        return result

    async def _run_planning_loop(
            self,
            unified_prompt: str,
            context: AgentContext,
            system_prompt: str,
            max_rounds: int,
            max_tokens: int,
            timeout_seconds: int = 600,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Custom execution loop with Loop Prevention.
        """
        from datetime import datetime

        all_results = []
        last_response = ""
        start_time = datetime.now()

        messages = [Message(role="user", content=system_prompt + "\n\n" + unified_prompt)]

        # Track tool signatures to detect loops
        last_tool_signature = None
        duplicate_count = 0

        for round_num in range(max_rounds):
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                logger.warning(f"Planning timeout after {elapsed:.1f}s")
                break

            logger.info(f"Planning round {round_num + 1}/{max_rounds}...")

            try:
                response = await self.provider.generate_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )

                if hasattr(response, 'content'):
                    last_response = response.content
                elif isinstance(response, dict):
                    last_response = response.get('content', '')
                else:
                    last_response = str(response)

            except Exception as e:
                logger.error(f"Provider call failed: {e}")
                break

            text_portion = self._extract_text_response(last_response)
            if text_portion:
                self._display(text_portion, style="default")

            tool_calls = self._extract_tool_calls(last_response)

            # ─────────────────────────────────────────────────────────────
            # LOOP BREAKER: Detect if agent is calling the EXACT same tool
            # ─────────────────────────────────────────────────────────────
            if tool_calls:
                current_sig = self._create_tool_signature(tool_calls[0])

                if current_sig == last_tool_signature:
                    duplicate_count += 1
                    logger.warning(f"Duplicate tool call detected (Count: {duplicate_count}): {current_sig}")

                    if duplicate_count >= 2:
                        # Force break the loop
                        self._display(
                            f"\n⚠️ INFINITE LOOP DETECTED: You have called `{tool_calls[0].get('tool')}` "
                            f"3 times with identical arguments. STOPPING.\n",
                            style="error"
                        )

                        # Inject a hard stop into results
                        loop_break_result = {
                            "tool": tool_calls[0].get("tool"),
                            "success": False,
                            "output": None,
                            "error": (
                                "INFINITE LOOP: You are repeating the exact same tool call. "
                                "Stop calling this tool. Analyze previous results and proceed differently "
                                "or write the artifacts now."
                            ),
                            "file_path": tool_calls[0].get("arguments", {}).get("TargetFile", ""),
                        }
                        all_results.append(loop_break_result)
                        messages.append(Message(role="assistant", content=last_response))

                        # Force continuation to break the cycle
                        messages.append(Message(role="user", content="STOP. Do not call tools anymore. Write task.md and implementation_plan.md immediately."))
                        duplicate_count = 0
                        last_tool_signature = None
                        continue
                else:
                    duplicate_count = 0
                    last_tool_signature = current_sig
            # ─────────────────────────────────────────────────────────────

            round_results = await self._execute_tools(tool_calls, context)
            all_results.extend(round_results)

            messages.append(Message(role="assistant", content=last_response))

            if self._is_planning_complete(all_results, context, round_num):
                break

            continuation = self._build_continuation_prompt(
                round_results, all_results, round_num, context
            )

            messages.append(Message(role="user", content=continuation))

        return last_response, all_results

    def _create_tool_signature(self, tool_call: Dict[str, Any]) -> str:
        """Create a unique hash for a tool call to detect duplicates."""
        import json
        return f"{tool_call.get('tool')}:{json.dumps(tool_call.get('arguments'), sort_keys=True)}"

    def _build_planning_error_recovery(self, errors: List[Dict[str, Any]]) -> Optional[str]:
        """
        Build specific error recovery for planning phase.

        FIXED: Removed incorrect super() call.
        """
        if not errors:
            return None

        # 1. Check for "Missing required parameter" (The current blocker)
        param_errors = [
            e for e in errors
            if 'missing required parameter' in str(e.get('error', '')).lower()
               or 'missing required parameter' in str(e.get('output', '')).lower()
        ]

        if param_errors:
            err_msg = param_errors[0].get('error', '')

            # Try to guess which tool failed from the error message
            tool_name = "Tool"
            if "Pattern" in err_msg:
                tool_name = "Glob"
            elif "TargetFile" in err_msg or "file_path" in err_msg:
                tool_name = "Read"

            return (
                f"🔴 CRITICAL ERROR: Tool Call Malformed\n\n"
                f"You tried to call `{tool_name}` but missed required arguments.\n\n"
                f"**IMMEDIATE FIX:**\n"
                f"You MUST use the exact JSON format below:\n\n"
                f"```json\n"
                f'{{"tool": "{tool_name}", "arguments": {{"Pattern": "src/**/*.py"}}}}\n' if tool_name == "Glob" else \
                    f'{{"tool": "{tool_name}", "arguments": {{"file_path": "path/to/file"}}}}\n'
                    f"```\n\n"
                    f"**Do NOT use just parameters.**\n"
                    f"- ❌ Wrong: {{\"Pattern\": \"...\"}}\n"
                    f"- ✅ Right: {{\"tool\": \"Glob\", \"arguments\": {{\"Pattern\": \"...\"}}}}\n\n"
                    f"Retry the tool call with the CORRECT format."
            )

        # 2. Check for "File not found" (Hallucinated paths)
        file_not_found_errors = [
            e for e in errors
            if 'file not found' in str(e.get('error', '')).lower()
        ]

        if file_not_found_errors:
            bad_files = set()
            for e in file_not_found_errors:
                path = e.get('file_path', '')
                if path:
                    bad_files.add(path.split('/')[-1])

            return (
                f"🔴 FATAL ERROR: Files Do Not Exist\n\n"
                f"You tried to read: {', '.join(list(bad_files)[:3])}\n\n"
                f"**IMMEDIATE ACTION REQUIRED:**\n"
                f"1. STOP trying to read these files. They do not exist.\n"
                f"2. DO NOT run Glob again to find them. You already have the file list.\n"
                f"3. Only use files found in initial Glob results.\n"
                f"4. Proceed to write artifacts based on files you HAVE read.\n\n"
                f"Write task.md NOW."
            )

        # 3. Check for "Write Gate" violations
        write_gate_errors = [
            e for e in errors
            if 'write gate' in str(e.get('error', '')).lower()
               or 'planning scope' in str(e.get('error', '')).lower()
        ]

        if write_gate_errors:
            return (
                "🔴 ERROR: Write Gate Violation\n\n"
                "You tried to write a file that is not allowed.\n\n"
                "PLANNING RULES:\n"
                "- You can ONLY write `.hcode/task.md` and `.hcode/implementation_plan.md`\n"
                "- Do NOT write implementation code files yet.\n\n"
                "Focus on reading files and gathering evidence (Phase 1)."
            )

        # 4. Generic Fallback (Previously the crashing super() call)
        err_details = []
        for e in errors[:2]:
            err_details.append(f"- {e.get('tool', 'Unknown')}: {str(e.get('error', ''))[:50]}")

        return (
            "🔴 ERROR DETECTED\n\n"
            "Review the error messages above:\n"
            f"{chr(10).join(err_details)}\n\n"
            "Common Fixes:\n"
            "- Ensure JSON has 'tool' and 'arguments' keys.\n"
            "- Ensure arguments match tool definition (e.g., Pattern for Glob).\n"
            "- Ensure paths are correct and files exist."
        )

    async def handle(
            self,
            context: AgentContext,
            loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute planning phase — 5-Phase Reasoning Protocol.
        """
        try:
            # Clean slate
            for _art in ("task.md", "implementation_plan.md", "walkthrough.md"):
                _path = self.artifact_manager._get_artifact_path(_art, context)
                if _path.exists():
                    _path.unlink()

            self._reset_trackers()
            logger.info("Starting 5-Phase Planning Protocol...")

            artifacts_created = []

            # Build prompt
            unified_prompt = self._build_unified_planning_prompt(context, "")

            response = ""
            tool_results: List[Dict[str, Any]] = []

            if self.provider is not None:
                self._display("Planning (5-Phase Protocol)...", style="info")

                if self._hcode_display:
                    self._hcode_display.start_thinking()

                # Use custom loop for 5-phase handling
                response, tool_results = await self._run_planning_loop(
                    unified_prompt,
                    context,
                    system_prompt=self._get_planning_system_prompt(context),
                    max_rounds=self.MAX_ROUNDS,
                    max_tokens=16384,
                    timeout_seconds=900,  # 15 mins
                )

                if self._hcode_display:
                    self._hcode_display.end_thinking()

                # Track artifacts
                for result in tool_results:
                    if result.get("success"):
                        fp = str(result.get("file_path", ""))
                        if "task.md" in fp and "task.md" not in artifacts_created:
                            artifacts_created.append("task.md")
                            if self._hcode_display and FileAction:
                                self._hcode_display.track_file(".hcode/task.md", FileAction.CREATED)
                        if "implementation_plan.md" in fp and "implementation_plan.md" not in artifacts_created:
                            artifacts_created.append("implementation_plan.md")
                            if self._hcode_display and FileAction:
                                self._hcode_display.track_file(".hcode/implementation_plan.md", FileAction.CREATED)

            # Validation
            if not self.artifact_manager.artifact_exists("task.md", context):
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output="Failed: task.md not created.",
                    can_transition=False,
                    error="task.md missing",
                )

            if not self.artifact_manager.artifact_exists("implementation_plan.md", context):
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output="Failed: implementation_plan.md not created.",
                    can_transition=False,
                    error="implementation_plan.md missing",
                )

            # Quality Validation
            valid, error = self.validate_artifacts(context)
            if not valid:
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output=f"Validation failed: {error}",
                    can_transition=False,
                    error=error,
                )

            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output=f"Planning complete. Created: {', '.join(artifacts_created)}",
                artifacts_created=artifacts_created,
                can_transition=True,
                metadata={"tool_results": tool_results}
            )

        except Exception as e:
            logger.exception(f"Planning phase failed: {e}")
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                output=f"Planning failed: {str(e)}",
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

            # Load task memory
            task_memory = self._load_hcode_memory(context)

            # Add context information
            context_info = f"""
## PROJECT KNOWLEDGE  (generated by /init — read this before anything else)

{pk_section}
{task_memory}
---

## Hcode Context

Working Directory: {context.working_dir}
Artifact Directory: .hcode
Current Iteration: {context.iteration}

### PEV Workflow (ALWAYS ENFORCED)

1. **PLANNING** ← you are here: create task.md and implementation_plan.md
2. **EXECUTION**: implement the plan
3. **VERIFICATION**: test and create walkthrough.md

### Reasoning Protocol (GPT OSS 120B)

Use <thinking> tags for ALL internal reasoning:

<thinking>
Step 1: [Action] — [Reasoning]
Step 2: [Action] — [Reasoning]
...
Therefore: [Conclusion leading to next action]
</thinking>

After reasoning, produce structured output with tool calls or text.

**Key principles:**
- Keep each thought LINEAR — no nested reasoning
- Use "Therefore..." transitions between reasoning and conclusions
- Validate each step before proceeding
- Use analytical reasoning; prioritize precision over novelty

**Tools you should use in planning:**
- Read: `{{"tool": "Read", "arguments": {{"file_path": "path/to/file.py"}}}}`  ← primary tool
- Grep: `{{"tool": "Grep", "arguments": {{"pattern": "pattern", "path": "."}}}}`  ← find symbols
- Write: `{{"tool": "Write", "arguments": {{"file_path": ".hcode/task.md", "content": "..."}}}}`  ← artifacts only

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
  • `[Evidence: file.py:line_num]` citations for key claims

### Example — think first, then read, then plan:

I need to add error logging to CLI startup.  From the project knowledge
I can see the CLI entry is `src/hcode/main_cli.py` and observability lives
in `src/hcode/core/observability/`.  Let me read the actual files before
deciding anything.

```json
{{"tool": "Read", "arguments": {{"file_path": "src/hcode/main_cli.py"}}}}
```

(… receives file contents …)

The startup sequence is at line 42 — a bare try block with no logging.
Now let me check how the logger factory works:

```json
{{"tool": "Read", "arguments": {{"file_path": "src/hcode/core/observability/logger.py"}}}}
```

(… receives file contents …)

`get_logger(name)` returns a stdlib Logger.  I now know the exact import,
the call site, and what the current code does.  Writing task.md:

```json
{{"tool": "Write", "arguments": {{"file_path": ".hcode/task.md", "content": "# Task\\n\\nAdd error logging to CLI startup\\n\\n## Goal\\n\\nErrors during CLI initialisation are captured by the observability logger.\\n\\n## Subtasks\\n\\n- [ ] Add `from hcode.core.observability.logger import get_logger` to main_cli.py <!-- id: 0 -->\\n  - Acceptance: `python -m py_compile src/hcode/main_cli.py` exits 0\\n- [ ] Insert `logger.error(exc)` in the except block at startup (line 42) <!-- id: 1 -->\\n  - Acceptance: error path produces a log entry in output\\n- [ ] Run `pytest tests/unit/test_cli.py -v` <!-- id: 2 -->\\n  - Acceptance: all tests pass\\n\\n## Risks\\n\\n- Logger must be initialised before the call site at line 42"}}}}
```

task.md written.  Now writing implementation_plan.md with full detail:

```json
{{"tool": "Write", "arguments": {{"file_path": ".hcode/implementation_plan.md", "content": "# Add error logging to CLI startup\\n\\nThe CLI startup at line 42 does not log errors — they propagate uncaught.\\nThis change adds a logger call so failures are captured.\\n\\n## Approach\\n\\n`get_logger` in the observability layer is the project convention.\\nReuse it — no new abstractions needed.\\n\\n## Execution Context\\n\\n- **Import convention:** absolute imports, one per line\\n- **Error handling:** try/except + logger.error()\\n- **Test framework:** pytest\\n- **Key interfaces:** none affected by this change\\n\\n## Proposed Changes\\n\\n### CLI Entry Point\\n\\n#### [MODIFY] `src/hcode/main_cli.py`\\n\\n**Target:** startup block, line 42\\n**Current behavior:** exceptions during init propagate uncaught (bare except)\\n**Required change:**\\n- Add import: `from hcode.core.observability.logger import get_logger`\\n- Add `logger = get_logger(__name__)` after existing imports\\n- In the except block at line 42: add `logger.error(\\\"Startup failed\\\", exc_info=True)`\\n**Why:** observability layer is the project convention for error capture\\n\\n## Dependencies Between Changes\\n\\nSingle file changed — no ordering constraints.\\n\\n## Verification Plan\\n\\n- `python -m py_compile src/hcode/main_cli.py`\\n- `pytest tests/unit/test_cli.py -v`\\n- `python -m hcode --help` — confirm no crash"}}}}
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
        Build a structured planning prompt with clear workflow examples.

        Provides enough guidance to prevent infinite exploration while
        allowing intelligent decision-making.
        """
        return f"""# Planning Phase — 3-Phase Analysis Protocol

You are a Senior Software Architect in PLANNING mode.
Your task: Analyze the codebase and create two planning artifacts.

**Core Directive:** Do not just list files. Understand the *code*, the *patterns*, and the *requirements*.

---

## USER REQUEST

{context.task}

Working directory: {context.working_dir}

---

## YOUR GOAL

Generate two planning artifacts:
1. `.hcode/task.md` - Breakdown of subtasks
2. `.hcode/implementation_plan.md` - Implementation details

---

## CRITICAL PATH REQUIREMENTS

**Working Directory:** {context.working_dir}

**Path Rules:**
- ALL file paths must be relative to working directory
- Glob patterns: `src/**/*.py` (NOT `{context.working_dir}/src/**/*.py`)
- Read paths: `src/module/file.py` (NOT `/home/sandbox/...` or `D:/absolute/...`)
- Write paths: `.hcode/task.md` or `.hcode/implementation_plan.md` ONLY

---

## TOOL USAGE PROTOCOL

**CRITICAL**: ALL tools require specific parameters in "arguments". Missing parameters will fail.

```json
{{"tool": "ToolName", "arguments": {{"param": "value"}}}}
```

**Available Tools:**
*   **Glob** [REQUIRED: pattern]: `{{"tool": "Glob", "arguments": {{"pattern": "src/hcode/utils/**/*.py"}}}}` — Find files
*   **Read** [REQUIRED: file_path]: `{{"tool": "Read", "arguments": {{"file_path": "src/hcode/utils/config.py"}}}}` — Read files
*   **Grep** [REQUIRED: pattern]: `{{"tool": "Grep", "arguments": {{"pattern": "class.*Test", "path": "."}}}}` — Search patterns
*   **Write** [REQUIRED: file_path, content]: `{{"tool": "Write", "arguments": {{"file_path": ".hcode/task.md", "content": "..."}}}}` — Create artifacts

**Common Errors:**
- ❌ `{{"tool": "Glob"}}` → FAILS (missing "pattern")
- ❌ `{{"tool": "Read"}}` → FAILS (missing "file_path")
- ✅ `{{"tool": "Glob", "arguments": {{"pattern": "**/*.py"}}}}` → WORKS

---

## THE 3-PHASE ANALYSIS PROTOCOL

Execute these phases **sequentially**.

### Phase A: CODE DISCOVERY (Rounds 1–2)

**Goal:** Find all relevant files.

<thinking>
Step 1: What files relate to this task?
Step 2: Use Glob to discover them
Therefore: I know which files to read.
</thinking>

**Required Actions:**
1. Use Glob to find target files (e.g., "src/module/**/*.py")
2. If creating tests, find existing tests (e.g., "tests/**/*.py")

**After completion:** List of 3-10 relevant file paths.

---

### Phase B: CODE UNDERSTANDING (Rounds 3–5)

**Goal:** Understand code structure and patterns.

<thinking>
Step 1: Review the file list from Phase A Glob results
Step 2: Select 2-4 most relevant files from that list
Step 3: Read ONLY those specific files — no other files
Therefore: I understand what needs to be done.
</thinking>

**Required Actions:**
1. Read 2-4 key files **from the Phase A Glob results above** (use exact paths from Glob output)
2. **CRITICAL**: Do NOT read files that were not returned by Glob
3. **CRITICAL**: Do NOT read the same file multiple times
4. Use Grep if needed to find specific patterns

**After completion:** Understand code well enough to plan.

**Anti-Hallucination Check:**
- [ ] Every Read uses a path that was in the Glob results
- [ ] No duplicate Read calls
- [ ] No invented filenames

---

### Phase C: ARTIFACT GENERATION (Rounds 6–7)

**Goal:** Write the planning artifacts.

**CRITICAL:** Output Write tool calls in JSON format.

<thinking>
Step 1: Draft task breakdown
Step 2: Draft implementation plan
Therefore: Ready to write both artifacts.
</thinking>

**Required Actions:**
1. Write `.hcode/task.md`
2. Write `.hcode/implementation_plan.md`

---

## QUALITY GATE CHECKLIST

Before writing artifacts:

* [ ] Files discovered with Glob
* [ ] 2-4 key files read
* [ ] Patterns/conventions understood
* [ ] Content ready for both artifacts

---

## INITIATE SEQUENCE

Begin **Phase A, Step 1**. Use Glob to find relevant files."""

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

        Note: With simplified planning approach, this is primarily for logging.
        Actual continuation logic is in _build_continuation_prompt.

        Returns:
            Current phase name
        """
        wrote_task = any(
            r.get("success") and "task.md" in str(r.get("file_path", ""))
            for r in all_results
        )
        wrote_plan = any(
            r.get("success") and "implementation_plan.md" in str(r.get("file_path", ""))
            for r in all_results
        )

        if wrote_task and wrote_plan:
            return "complete"
        if wrote_task:
            return "writing_plan"

        read_count = sum(
            1 for r in all_results
            if r.get("success") and r.get("tool", "").lower() == "read"
        )

        if read_count >= 3:
            return "ready_to_write"
        if read_count >= 1:
            return "exploring"

        return "starting"

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
        """Build prompt for Phase 1: Problem Space Exploration (Rounds 1-2)."""

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
ROUND {round_num + 1}: PHASE 1 — PROBLEM SPACE EXPLORATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Progress
- Files discovered: {glob_count} searches | Files read: {read_count} | Tool calls: {len(all_results)}

## Objective
Understand the ACTUAL problem behind the stated request.

## Required Reasoning

Use <thinking> tags to work through:

<thinking>
Step 1: Decompose the request — What is the user explicitly asking for?
Step 2: Identify implicit needs — What unstated requirements exist?
Step 3: Define success criteria — What does "done" look like?
Step 4: Map relevant files — Which parts of the codebase are involved?
Step 5: Form hypotheses — What are 2-3 different approaches?
Therefore: [Your conclusion and what to investigate next]
</thinking>

## Self-Validation Before Moving On
- [ ] Can I explain the problem clearly?
- [ ] Have I identified at least 3 relevant files from project knowledge?
- [ ] Do I have at least 2 alternative approaches in mind?
- [ ] Have I listed my knowledge gaps?

## Actions
1. Read relevant files identified from project knowledge
2. Use Grep to locate specific symbols if needed
3. Document what you learn after each Read

## Constraints
- DO NOT write task.md or implementation_plan.md yet
- Focus on understanding before designing
- You may ONLY write: {working_dir}/.hcode/task.md and {working_dir}/.hcode/implementation_plan.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use <thinking> tags, then take action.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_exploration_prompt(
        self,
        round_num: int,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for Phase 2: Deep Code Investigation (Rounds 2-4)."""

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
ROUND {round_num + 1}: PHASE 2 — DEEP CODE INVESTIGATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Research Progress
- Files read: {read_count} | Saturation: {saturation_level.upper()}

{saturation_advice}

{confidence_summary}

{uncertainty_summary}

## Objective
Build comprehensive code-level understanding of involved components.

## Required Reasoning

Use <thinking> tags:

<thinking>
Step 1: What files have I read so far, and what did I learn from each?
Step 2: What files still need reading to answer my remaining questions?
Step 3: How do the components I've read interact (data flow, control flow)?
Step 4: What dependencies exist? If I change X, what else is affected?
Step 5: What edge cases or error conditions exist?
Therefore: [What to read next, or that I have sufficient understanding]
</thinking>

## Self-Validation Before Moving On
- [ ] Have I read at least 5 files?
- [ ] Can I trace a request/data flow through the system?
- [ ] Do I know the exact functions/classes that need changing?
- [ ] Have I identified import patterns, naming conventions, error handling style?

## Actions

If saturation is LOW: Read more files — focus on entry points, core logic, tests.
If saturation is MODERATE: Target remaining gaps, then prepare to transition.

## Anti-Hallucination Rule
If you are about to claim something about code you haven't Read — STOP and Read it first.

## Constraints
- DO NOT write artifacts yet — focus on understanding
- After each Read, state: what you learned, how it affects the plan, new questions
- 🚨 Glob, LS, SmartGlob are FORBIDDEN — use Read and Grep only

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ NEXT ACTION: Read the next relevant file. DO NOT use Glob/LS/SmartGlob.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_consolidation_prompt(
        self,
        round_num: int,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for transition between Phase 2 and Phase 3 (Rounds 3-4)."""

        critical_uncertainties = self.uncertainty_tracker.get_unresolved('critical')
        important_uncertainties = self.uncertainty_tracker.get_unresolved('important')

        can_write, blocking_issues = self._can_write_artifacts(context)

        confidence_summary = self.confidence_tracker.format_summary()
        readiness_check = self._format_readiness_check(can_write, blocking_issues)

        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUND {round_num + 1}: CONSOLIDATION — VALIDATING UNDERSTANDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{confidence_summary}

### Uncertainties: Critical={len(critical_uncertainties)} | Important={len(important_uncertainties)}

## Objective
Verify your understanding is sufficient, then transition to solution design.

## Required Reasoning

<thinking>
Step 1: Can I explain the system end-to-end without looking at code?
Step 2: If I change the target components, what else breaks?
Step 3: Are there critical uncertainties I must resolve before designing?
Step 4: What edge cases exist (invalid input, error conditions, concurrency)?
Step 5: Am I ready to evaluate solution approaches?
Therefore: [Ready to proceed, or need to resolve specific gaps]
</thinking>

## Readiness Check

{readiness_check}

## Decision Point

Based on the readiness check:
- If READY: Proceed to Phase 3 (Solution Crystallization)
- If NOT READY: Do targeted reads to resolve blocking issues
- If BORDERLINE: 1-2 more targeted reads

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use <thinking> to assess readiness, then act accordingly.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_design_prompt(
        self,
        round_num: int,
        all_results: List[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for Phase 3: Solution Crystallization (Rounds 4-5)."""

        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUND {round_num + 1}: PHASE 3 — SOLUTION CRYSTALLIZATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Objective
Select the optimal approach with explicit justification and documented risks.

YOU HAVE COMPLETED RESEARCH. NOW DESIGN THE SOLUTION.

## Required Reasoning

<thinking>
Step 1: Evaluate Approach A — [describe approach]
  - Complexity: [1-5, with justification from code you Read]
  - Risk: [1-5, what could go wrong]
  - Alignment: [1-5, does it follow existing patterns?]
Step 2: Evaluate Approach B — [describe approach]
  - Complexity: [1-5]
  - Risk: [1-5]
  - Alignment: [1-5]
Step 3: Select approach — "I chose Approach X because [concrete reasons from code]"
Step 4: Identify risks — [3-5 specific risks or edge cases]
Step 5: Plan testing — [exact commands to validate]
Therefore: I have a concrete solution design ready for artifact generation.
</thinking>

## Self-Validation Before Moving On
- [ ] Did I evaluate at least 2 approaches (not just pick the first one)?
- [ ] Is my justification grounded in code I actually read?
- [ ] Have I identified at least 3 risks?
- [ ] Do I have concrete test commands?

## Next Step
After completing solution design, proceed to write:
1. task.md (Phase 4)
2. implementation_plan.md (Phase 5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use <thinking> to evaluate approaches, then proceed to artifact writing.
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
ROUND {round_num + 1}: SPECIFICATION PHASE — WRITE ARTIFACTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 Phase Objective
You have completed research and design. NOW CREATE THE PLANNING ARTIFACTS.

**STOP EXPLORING. START WRITING.**

## 📝 Step 1: Create task.md

Use the Write tool in this EXACT JSON format:

<thinking>
Step 1: I have completed exploration and design
Step 2: I understand the task requirements and approach
Step 3: I will now write task.md with proper structure
Step 4: Content includes: Goal, Subtasks with IDs, Risks/Edge Cases
Therefore: Writing task.md now
</thinking>

<output>
```json
{{
  "tool": "Write",
  "arguments": {{
    "file_path": "{working_dir}/.hcode/task.md",
    "content": "# Task: [Your Task Title]\\n\\n## Goal\\n[1-2 sentence description of what needs to be done]\\n\\n## Subtasks\\n- [ ] First subtask <!-- id: 0 -->\\n- [ ] Second subtask <!-- id: 1 -->\\n- [ ] Third subtask <!-- id: 2 -->\\n- [ ] Fourth subtask <!-- id: 3 -->\\n\\n## Risks / Edge Cases\\n- [Specific risk 1]\\n- [Specific risk 2]\\n- [Specific risk 3]"
  }}
}}
```
</output>

## 📝 Step 2: After task.md, create implementation_plan.md

Same format, different file:

```json
{{
  "tool": "Write",
  "arguments": {{
    "file_path": "{working_dir}/.hcode/implementation_plan.md",
    "content": "# Implementation Plan: [Title]\\n\\n## Overview\\n[2-3 sentences]\\n\\n## File Changes\\n\\n### [MODIFY] path/to/file.py\\n**Purpose**: ...\\n**Changes**: ...\\n\\n### [NEW] path/to/new_file.py\\n**Purpose**: ...\\n**Contents**: ...\\n\\n## Verification Plan\\n- [ ] Test command 1\\n- [ ] Test command 2"
  }}
}}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 ACTION REQUIRED: Write task.md NOW using the exact JSON format above.
Replace placeholder text with your actual analysis from previous rounds.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _build_reflection_prompt(
        self,
        round_num: int,
        round_results: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate reflection prompt using structured <thinking> format.

        Forces the AI to assess its own understanding and decide next steps.
        """
        files_read_this_round = [
            r.get("file_path", "")
            for r in round_results
            if r.get("success") and r.get("tool", "").lower() == "read"
        ]

        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REFLECTION CHECKPOINT — End of Round {round_num}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Round {round_num}: {len(round_results)} tool calls | {len(files_read_this_round)} files read

## Reflect using <thinking> tags:

<thinking>
Step 1: Key insights from this round — What 3-5 things did I learn?
Step 2: Confidence self-assessment:
  - Requirements: __/5
  - Architecture: __/5
  - Dependencies: __/5
  - Edge cases: __/5
  - Testing: __/5
  - Patterns: __/5
Step 3: What gaps remain? What questions are still unanswered?
Step 4: Decision — Choose ONE:
  (a) I need more research — specifically: [what?]
  (b) I'm ready to design the solution (Phase 3)
  (c) I'm ready to write artifacts (Phase 4-5)
Therefore: [Next concrete action]
</thinking>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Respond with your <thinking> reflection, then continue.
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
