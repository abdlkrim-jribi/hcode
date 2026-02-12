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
                        arguments.get("file_path") or
                        arguments.get("TargetFile") or ""
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
                            f"\n⚠ INFINITE LOOP DETECTED: You have called `{tool_calls[0].get('tool')}` "
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

            # Format tool outputs for context
            tool_outputs_str = ""
            if round_results:
                tool_outputs_str = "## Tool Results\n\n"
                for res in round_results:
                    status = "✅ Success" if res.get('success') else "❌ Failed"
                    tool_outputs_str += f"### {res.get('tool')} ({status})\n"
                    if res.get('file_path'):
                         tool_outputs_str += f"Target: {res.get('file_path')}\n"

                    output_content = str(res.get('output')) if res.get('output') else ""
                    if output_content:
                        # Truncate very long outputs to save context
                        if len(output_content) > 5000:
                            output_content = output_content[:5000] + "\n... (truncated)"
                        tool_outputs_str += f"```\n{output_content}\n```\n"

                    if res.get('error'):
                         tool_outputs_str += f"Error: {res.get('error')}\n"
                    tool_outputs_str += "\n"

            continuation = self._build_continuation_prompt(
                round_results, all_results, round_num, context
            )

            # combine
            full_content = tool_outputs_str + "\n" + continuation
            messages.append(Message(role="user", content=full_content))

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
            if "pattern" in err_msg.lower():
                tool_name = "Glob"
            elif "TargetFile" in err_msg or "file_path" in err_msg:
                tool_name = "Read"

            return (
                f"🔴 CRITICAL ERROR: Tool Call Malformed\n\n"
                f"You tried to call `{tool_name}` but missed required arguments.\n\n"
                f"**IMMEDIATE FIX:**\n"
                f"You MUST use the exact JSON format below:\n\n"
                f"```json\n"
                f'{{"tool": "{tool_name}", "arguments": {{"pattern": "src/**/*.py"}}}}\n' if tool_name == "Glob" else \
                    f'{{"tool": "{tool_name}", "arguments": {{"file_path": "path/to/file"}}}}\n'
                    f"```\n\n"
                    f"**Do NOT use just parameters.**\n"
                    f"- ❌ Wrong: {{\"pattern\": \"...\"}}\n"
                    f"- ✅ Right: {{\"tool\": \"Glob\", \"arguments\": {{\"pattern\": \"...\"}}}}\n\n"
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
            "- Ensure arguments match tool definition (e.g., pattern for Glob).\n"
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

                if self._hcode_display:
                    self._hcode_display.start_thinking()

                # Use planning-specific loop with completion check
                response, tool_results = await self._run_planning_loop(
                    unified_prompt=unified_prompt,
                    context=context,
                    system_prompt=self._get_planning_system_prompt(context),
                    max_rounds=self.MAX_ROUNDS,
                    max_tokens=8192,
                    timeout_seconds=900,
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

        Uses core prompts from phases.yaml and MD files.

        Args:
            context: Current agent context

        Returns:
            Complete system prompt for planning
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            # 1. Identity & Tool Format
            identity = loader.get_identity()
            tool_format = loader.get_tool_format()

            # 2. Planning Mode Protocol (The 5-Phase Protocol)
            planning_mode = loader.get_planning_mode()

            # 3. Artifact Guidance
            task_guidance = loader.get_task_guidance()
            plan_guidance = loader.get_implementation_plan_guidance()

            # 4. Project Knowledge (from /init)
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
                else "(Run /init commands to generate project knowledge if needed.)"
            )

            # 5. Task Memory
            task_memory = self._load_hcode_memory(context)

            # Construct the full system prompt
            system_prompt = f"""{identity}

{tool_format}

---

# PLANNING MODE PROTOCOL

{planning_mode}

---

# ARTIFACT GUIDANCE

## valid `task.md`
{task_guidance}

## valid `implementation_plan.md`
{plan_guidance}

---

# CONTEXT & KNOWLEDGE

## Project Knowledge
{pk_section}

## Task Memory
{task_memory}

## Current Context
Working Directory: {context.working_dir}
Artifact Directory: .hcode
Current Iteration: {context.iteration}
"""
            return system_prompt

        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            # Fallback to basic prompt
            return f"""You are Hcode, an AI coding assistant in PLANNING mode.

Your task: {context.task}

Working Directory: {context.working_dir}

## Protocol
1. Analyze request
2. Explore codebase (Glob/Read) - DO NOT GUESS PATHS
3. Create .hcode/task.md
4. Create .hcode/implementation_plan.md

Use format: {{"tool": "ToolName", "arguments": {{...}}}}
"""



    def _build_unified_planning_prompt(self, context: AgentContext, exploration_context: str) -> str:
        """
        Build a simplified user prompt for the planning phase.
        
        The protocol is now fully contained in the system prompt (from planning_mode.md).
        This prompt just provides the user's specific request and context.
        """
        return f"""# PLANNING REQUEST

## User Task
{context.task}

## Context
Working Directory: {context.working_dir}

## Objective
Follow the **5-Phase Reasoning Protocol** (defined in system prompt) to:
1.  Explore the codebase (Glob -> Read)
2.  Understand the architecture and patterns
3.  Create `.hcode/task.md` (roadmap)
4.  Create `.hcode/implementation_plan.md` (technical blueprint)

**Rules:**
-   **Evidence-First**: Do not write plans without reading code.
-   **Correct Tool Syntax**: Use `{{'tool': 'Tool', 'arguments': {{'param': 'val'}}}}`
-   **No Hallucinations**: Only use paths you have verified exist.

Begin with **Phase 0: Requirements Deconstruction**.
"""

    # NOTE: The agent generates task.md and implementation_plan.md directly from
    # the guidance prompts in src/hcode/config/core_prompts/core/task.md and
    # implementation_plan.md. Template methods have been removed.

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
    def _reset_trackers(self) -> None:
        """Reset all meta-cognitive trackers for a new planning session."""
        self.uncertainty_tracker.reset()
        self.confidence_tracker.reset()
        self.saturation_detector.reset()
