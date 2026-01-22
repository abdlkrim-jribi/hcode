"""
Enhanced Thinking Manager with Integrated Reasoning System.

This module provides a comprehensive thinking management system that integrates:
- Structured reasoning with multi-phase analysis
- Confidence calibration and tracking
- Self-critique and reflection
- Reasoning-to-todo integration
- Thinking-execution feedback loops
- Quality metrics and monitoring

Designed for maximum reasoning performance with GPT-OSS and other LLMs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, AsyncGenerator, Tuple

from hcode.agent.feedback_loop import (
    ThinkingExecutionFeedbackLoop,
    ExecutionResult,
    ExecutionStatus,
    FeedbackEntry,
    ReasoningRevision,
)
from hcode.agent.reasoning import (
    StructuredReasoning,
    ReasoningParser,
    ReasoningLevel,
    ConfidenceCalibrator,
    ReasoningToTodoIntegrator,
    SelfCritiqueEngine,
    ReasoningQualityMetrics,
    ChangeImpactOutput,
    PreExecutionReviewOutput,
)
from hcode.agent.thinking import ThinkingBlock, ThinkingSession, ThinkingPhase
from hcode.agent.todo import TodoManager
from hcode.config.reasoning_prompts import (
    ReasoningPromptBuilder,
    ReasoningDepth,
    get_reasoning_system_prompt,
    detect_task_type,
    determine_reasoning_depth,
)
from hcode.config.thinking import ThinkingConfig


class EnhancedThinkingMode(Enum):
    """Extended thinking modes with reasoning integration"""

    DISABLED = "disabled"
    QUICK = "quick"  # Level 1 reasoning
    STANDARD = "standard"  # Level 2 reasoning
    DEEP = "deep"  # Level 3 reasoning
    ADAPTIVE = "adaptive"  # Auto-select based on task


@dataclass
class ThinkingResult:
    """Complete result of a thinking session"""

    session: ThinkingSession
    structured_reasoning: Optional[StructuredReasoning] = None
    quality_metrics: Optional[Dict[str, float]] = None
    critique: Optional[Dict[str, Any]] = None
    action_items: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    requires_revision: bool = False
    revision: Optional[ReasoningRevision] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session.id,
            "session_summary": self.session.get_summary(),
            "structured_reasoning": (
                self.structured_reasoning.to_dict() if self.structured_reasoning else None
            ),
            "quality_metrics": self.quality_metrics,
            "critique": self.critique,
            "action_items": self.action_items,
            "confidence": self.confidence,
            "requires_revision": self.requires_revision,
            "revision": self.revision.to_dict() if self.revision else None,
        }


class EnhancedThinkingManager:
    """
    Enhanced thinking manager with full reasoning integration.

    This manager orchestrates:
    - Multi-phase structured thinking
    - Reasoning parsing and validation
    - Confidence calibration
    - Self-critique generation
    - Todo integration
    - Execution feedback loops
    """

    def __init__(
        self,
        config: Optional[ThinkingConfig] = None,
        llm_client: Optional[Any] = None,
        todo_manager: Optional[TodoManager] = None,
    ):
        """
        Initialize enhanced thinking manager.

        Args:
            config: Thinking configuration
            llm_client: LLM client for generating thoughts
            todo_manager: Todo manager for task integration
        """
        self.config = config or ThinkingConfig()
        self.llm_client = llm_client
        self.todo_manager = todo_manager

        # Core components
        self.parser = ReasoningParser()
        self.prompt_builder = ReasoningPromptBuilder()
        self.calibrator = ConfidenceCalibrator()
        self.critique_engine = SelfCritiqueEngine()
        self.quality_metrics = ReasoningQualityMetrics()
        self.todo_integrator = ReasoningToTodoIntegrator(todo_manager)
        self.feedback_loop = ThinkingExecutionFeedbackLoop(
            confidence_calibrator=self.calibrator, quality_metrics=self.quality_metrics
        )

        # Session state
        self.current_session: Optional[ThinkingSession] = None
        self.current_reasoning: Optional[StructuredReasoning] = None
        self.current_result: Optional[ThinkingResult] = None

        # Listeners
        self.thinking_listeners: List[Callable[[ThinkingBlock], None]] = []
        self.reasoning_listeners: List[Callable[[StructuredReasoning], None]] = []
        self.todo_listeners: List[Callable[[List[Dict[str, Any]]], None]] = []

        # History
        self.session_history: List[ThinkingResult] = []
        self.max_history = 50

    def set_llm_client(self, client: Any):
        """Set the LLM client"""
        self.llm_client = client

    def set_todo_manager(self, manager: TodoManager):
        """Set the todo manager"""
        self.todo_manager = manager
        self.todo_integrator.set_todo_manager(manager)

    def add_reasoning_listener(self, listener: Callable[[StructuredReasoning], None]):
        """Add listener for reasoning events"""
        self.reasoning_listeners.append(listener)


    # =========================================================================
    # MAIN THINKING INTERFACE
    # =========================================================================

    async def think(
        self,
        prompt: str,
        mode: Optional[EnhancedThinkingMode] = None,
        context: Optional[Dict[str, Any]] = None,
        task_type: Optional[str] = None,
    ) -> ThinkingResult:
        """
        Perform comprehensive thinking with full reasoning integration.

        Args:
            prompt: The task/question to think about
            mode: Thinking mode (defaults to ADAPTIVE)
            context: Additional context
            task_type: Optional task type hint

        Returns:
            Complete thinking result
        """
        if not self.config.enabled:
            return self._create_empty_result()

        # Determine mode and depth
        mode = mode or EnhancedThinkingMode.ADAPTIVE
        depth = self._determine_depth(prompt, mode, context)

        # Detect task type if not provided
        task_type = task_type or detect_task_type(prompt)

        # Start session
        session = self._start_session(
            metadata={
                "prompt": prompt,
                "mode": mode.value,
                "depth": depth.value,
                "task_type": task_type,
                "context": context,
            }
        )

        # Generate thinking based on depth
        if depth == ReasoningDepth.QUICK:
            raw_thinking = await self._think_quick(prompt, context)
        elif depth == ReasoningDepth.STANDARD:
            raw_thinking = await self._think_standard(prompt, context, task_type)
        else:
            raw_thinking = await self._think_deep(prompt, context, task_type)

        # Parse structured reasoning
        structured = self.parser.parse(raw_thinking)
        structured.level = self._map_depth_to_level(depth)
        self.current_reasoning = structured

        # Notify reasoning listeners
        for listener in self.reasoning_listeners:
            try:
                listener(structured)
            except Exception:
                pass

        # Evaluate quality
        quality = self.quality_metrics.evaluate(structured)

        # Generate critique for standard and deep
        critique = None
        if depth in [ReasoningDepth.STANDARD, ReasoningDepth.DEEP]:
            critique = self.critique_engine.critique(structured)

        # Record prediction for calibration
        self.calibrator.record_prediction(
            confidence=structured.get_confidence(),
            task_type=task_type or "general",
            reasoning_id=structured.id,
        )

        # Extract and update todos
        action_items = self._update_todos_from_reasoning(structured)

        # Create thinking blocks for session
        self._populate_session_blocks(session, structured, raw_thinking)

        # End session
        self._end_session(session)

        # Create result
        result = ThinkingResult(
            session=session,
            structured_reasoning=structured,
            quality_metrics=quality,
            critique=critique,
            action_items=action_items,
            confidence=structured.get_confidence(),
            requires_revision=self._check_requires_revision(critique, quality),
        )

        # Store in history
        self._add_to_history(result)
        self.current_result = result

        # Set up feedback loop
        self.feedback_loop.set_reasoning(structured)

        return result

    async def _think_quick(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate quick Level 1 thinking"""
        from hcode.config.prompts import get_generation_params

        system_prompt = get_reasoning_system_prompt()
        thinking_prompt = self.prompt_builder.build_thinking_prompt(
            task=prompt, depth=ReasoningDepth.QUICK, context=context
        )

        params = get_generation_params(task_type="thinking_quick")
        return await self._generate_thinking(
            system_prompt=system_prompt,
            user_prompt=thinking_prompt,
            max_tokens=params.max_tokens,
            temperature=params.temperature,
        )

    async def _think_standard(
        self, prompt: str, context: Optional[Dict[str, Any]], task_type: Optional[str]
    ) -> str:
        """Generate standard Level 2 thinking"""
        from hcode.config.prompts import get_generation_params

        system_prompt = get_reasoning_system_prompt(task_type=task_type)
        thinking_prompt = self.prompt_builder.build_thinking_prompt(
            task=prompt, depth=ReasoningDepth.STANDARD, context=context
        )

        params = get_generation_params(task_type="thinking_standard")
        return await self._generate_thinking(
            system_prompt=system_prompt,
            user_prompt=thinking_prompt,
            max_tokens=params.max_tokens,
            temperature=params.temperature,
        )

    async def _think_deep(
        self, prompt: str, context: Optional[Dict[str, Any]], task_type: Optional[str]
    ) -> str:
        """Generate deep Level 3 thinking"""
        from hcode.config.prompts import get_generation_params

        system_prompt = get_reasoning_system_prompt(task_type=task_type)
        thinking_prompt = self.prompt_builder.build_thinking_prompt(
            task=prompt, depth=ReasoningDepth.DEEP, context=context
        )

        params = get_generation_params(task_type="thinking_deep")
        return await self._generate_thinking(
            system_prompt=system_prompt,
            user_prompt=thinking_prompt,
            max_tokens=params.max_tokens,
            temperature=params.temperature,
        )

    async def _generate_thinking(
        self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float = 0.7
    ) -> str:
        """Generate thinking using LLM"""
        if not self.llm_client:
            # Return template for manual thinking
            return f"<thinking>\n[Manual thinking required for: {user_prompt[:100]}]\n</thinking>"

        try:
            response = await self.llm_client.generate(
                prompt=user_prompt,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.get("content", "")
            return content

        except Exception as e:
            return f"<thinking>\n[Error generating thinking: {e}]\n</thinking>"

    # =========================================================================
    # STREAMING INTERFACE
    # =========================================================================

    async def stream_thinking(
        self,
        prompt: str,
        mode: Optional[EnhancedThinkingMode] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Tuple[str, ThinkingBlock], None]:
        """
        Stream thinking blocks as they are generated.

        Args:
            prompt: Task to think about
            mode: Thinking mode
            context: Additional context

        Yields:
            Tuples of (phase_name, thinking_block)
        """
        mode = mode or EnhancedThinkingMode.ADAPTIVE
        depth = self._determine_depth(prompt, mode, context)

        # Get phases for depth
        phases = self._get_phases_for_depth(depth)

        # Start session
        session = self._start_session(metadata={"prompt": prompt})

        task_type = detect_task_type(prompt)

        for phase in phases:
            # Generate thinking for this phase
            phase_content = await self._generate_phase_thinking(
                prompt=prompt,
                phase=phase,
                context=context,
                task_type=task_type,
                previous_phases=session.blocks,
            )

            # Create block
            block = ThinkingBlock(
                phase=phase,
                content=phase_content,
                summary=phase_content[:100] if phase_content else "",
                timestamp=datetime.now(),
            )

            # Add to session
            session.add_block(block)

            # Notify listeners
            for listener in self.thinking_listeners:
                try:
                    listener(block)
                except Exception:
                    pass

            yield (phase.value, block)

            # Update todos after analysis/decision phases
            if phase in [ThinkingPhase.PLANNING, ThinkingPhase.DECIDING]:
                await self._stream_update_todos(session)

        # End session and create result
        self._end_session(session)

        # Parse complete reasoning
        full_content = session.get_full_content()
        structured = self.parser.parse(full_content)
        self.current_reasoning = structured
        self.feedback_loop.set_reasoning(structured)

    async def _generate_phase_thinking(
        self,
        prompt: str,
        phase: ThinkingPhase,
        context: Optional[Dict[str, Any]],
        task_type: Optional[str],
        previous_phases: List[ThinkingBlock],
    ) -> str:
        """Generate thinking for a specific phase"""
        from hcode.config.prompts import get_generation_params

        phase_instructions = self._get_phase_instructions(phase)

        # Build context from previous phases
        previous_context = "\n".join(
            [f"[{b.phase.value.upper()}]: {b.content[:200]}" for b in previous_phases]
        )

        phase_prompt = f"""Task: {prompt}

{f"Previous reasoning:{chr(10)}{previous_context}" if previous_context else ""}

Now complete the {phase.value.upper()} phase:
{phase_instructions}

Respond with your {phase.value} analysis:"""

        if not self.llm_client:
            return f"[{phase.value}] Requires manual analysis"

        try:
            # Use summary task type for phase-based thinking (concise output)
            params = get_generation_params(task_type="summary")
            response = await self.llm_client.generate(
                prompt=phase_prompt,
                system=get_reasoning_system_prompt(task_type),
                max_tokens=params.max_tokens,
                temperature=params.temperature,
            )
            return response.get("content", "")
        except Exception as e:
            return f"[{phase.value}] Error: {e}"

    def _get_phase_instructions(self, phase: ThinkingPhase) -> str:
        """Get instructions for a thinking phase"""
        from hcode.config.prompts import get_phase_instruction
        return get_phase_instruction(phase.value)

    # =========================================================================
    # FEEDBACK AND REVISION
    # =========================================================================

    def record_execution(
        self,
        tool_name: str,
        action: str,
        output: str,
        success: bool,
        error: Optional[str] = None,
        duration_ms: int = 0,
    ) -> FeedbackEntry:
        """
        Record an execution result and get feedback.

        Args:
            tool_name: Name of the tool executed
            action: Description of the action
            output: Output from execution
            success: Whether execution succeeded
            error: Error message if failed
            duration_ms: Execution duration

        Returns:
            Feedback entry with analysis
        """
        result = ExecutionResult(
            tool_name=tool_name,
            action_description=action,
            status=ExecutionStatus.SUCCESS if success else ExecutionStatus.FAILED,
            output=output,
            error=error,
            duration_ms=duration_ms,
        )

        feedback = self.feedback_loop.record_execution(result)

        # Update todos based on feedback
        if feedback.requires_replanning:
            self._update_todos_from_feedback(feedback)

        return feedback

    async def revise_thinking(self, feedback: str, outcome: str) -> ThinkingResult:
        """
        Revise thinking based on feedback.

        Args:
            feedback: Feedback received
            outcome: What actually happened

        Returns:
            Revised thinking result
        """
        if not self.current_reasoning:
            raise ValueError("No current reasoning to revise")

        # Build refinement prompt
        refinement_prompt = self.prompt_builder.build_refinement_prompt(
            original_reasoning=self.current_reasoning.raw_content,
            feedback=feedback,
            outcome=outcome,
        )

        # Generate refined thinking (use exploration params for iterative refinement)
        from hcode.config.prompts import get_generation_params
        params = get_generation_params(task_type="exploration")

        refined_content = await self._generate_thinking(
            system_prompt=get_reasoning_system_prompt(),
            user_prompt=refinement_prompt,
            max_tokens=params.max_tokens,
            temperature=params.temperature,
        )

        # Parse refined reasoning
        refined_reasoning = self.parser.parse(refined_content)

        # Create revision record
        revision = ReasoningRevision(
            original_reasoning_id=self.current_reasoning.id,
            revised_hypothesis=refined_reasoning.reasoning.hypothesis,
            revised_decision=refined_reasoning.decision.decision,
            revised_confidence=refined_reasoning.get_confidence(),
            new_action_items=refined_reasoning.decision.action_items,
            revision_reason=f"Feedback: {feedback[:100]}",
        )

        # Update current reasoning
        self.current_reasoning = refined_reasoning
        self.feedback_loop.set_reasoning(refined_reasoning)

        # Update todos
        action_items = self._update_todos_from_reasoning(refined_reasoning)

        # Create new session for revised thinking
        session = ThinkingSession(metadata={"revision": True})
        self._populate_session_blocks(session, refined_reasoning, refined_content)

        # Create result
        result = ThinkingResult(
            session=session,
            structured_reasoning=refined_reasoning,
            quality_metrics=self.quality_metrics.evaluate(refined_reasoning),
            critique=self.critique_engine.critique(refined_reasoning),
            action_items=action_items,
            confidence=refined_reasoning.get_confidence(),
            requires_revision=False,
            revision=revision,
        )

        self.current_result = result
        return result

    # =========================================================================
    # TODO INTEGRATION
    # =========================================================================

    def _update_todos_from_reasoning(self, reasoning: StructuredReasoning) -> List[Dict[str, Any]]:
        """Update todos based on reasoning output"""
        self.todo_integrator.extract_todos_from_reasoning(reasoning)

        # Get current todos if manager exists
        current_todos = []
        if self.todo_manager:
            current_todos = self.todo_manager.to_dict_list()

        # Sync with reasoning
        updated_todos = self.todo_integrator.sync_todos_with_reasoning(
            reasoning=reasoning, current_todos=current_todos
        )

        # Update todo manager if exists
        if self.todo_manager and updated_todos:
            # Convert to format expected by batch_update
            formatted_todos = []
            for todo in updated_todos:
                formatted_todos.append(
                    {
                        "content": todo["content"],
                        "status": todo.get("status", "pending"),
                        "activeForm": todo.get("activeForm", todo["content"]),
                    }
                )

            # Mark first pending as in_progress
            in_progress_found = False
            for todo in formatted_todos:
                if todo["status"] == "in_progress":
                    in_progress_found = True
                    break

            if not in_progress_found:
                for todo in formatted_todos:
                    if todo["status"] == "pending":
                        todo["status"] = "in_progress"
                        break

            self.todo_manager.batch_update(formatted_todos)

        # Notify listeners
        for listener in self.todo_listeners:
            try:
                listener(updated_todos)
            except Exception:
                pass

        return updated_todos

    def _update_todos_from_feedback(self, feedback: FeedbackEntry):
        """Update todos based on execution feedback"""
        if not self.todo_manager:
            return

        current_todos = self.todo_manager.to_dict_list()

        # Add adjustment tasks from feedback
        for adjustment in feedback.suggested_adjustments:
            new_todo = {
                "content": adjustment,
                "status": "pending",
                "activeForm": self.todo_integrator._to_active_form(adjustment),
            }
            if new_todo not in current_todos:
                current_todos.append(new_todo)

        # Ensure one is in progress
        in_progress = any(t.get("status") == "in_progress" for t in current_todos)
        if not in_progress:
            for todo in current_todos:
                if todo.get("status") == "pending":
                    todo["status"] = "in_progress"
                    break

        self.todo_manager.batch_update(current_todos)

    async def _stream_update_todos(self, session: ThinkingSession):
        """Update todos during streaming"""
        # Parse partial reasoning from session so far
        content = session.get_full_content()
        partial_reasoning = self.parser.parse(content)
        self._update_todos_from_reasoning(partial_reasoning)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _determine_depth(
        self, prompt: str, mode: EnhancedThinkingMode, context: Optional[Dict[str, Any]]
    ) -> ReasoningDepth:
        """Determine appropriate reasoning depth"""
        if mode == EnhancedThinkingMode.QUICK:
            return ReasoningDepth.QUICK
        elif mode == EnhancedThinkingMode.STANDARD:
            return ReasoningDepth.STANDARD
        elif mode == EnhancedThinkingMode.DEEP:
            return ReasoningDepth.DEEP
        else:
            # Adaptive mode
            complexity = self._estimate_complexity(prompt, context)
            return determine_reasoning_depth(prompt, complexity)

    def _estimate_complexity(self, prompt: str, context: Optional[Dict[str, Any]]) -> float:
        """Estimate task complexity (0-1)"""
        complexity = 0.0

        # Length factor
        if len(prompt) > 500:
            complexity += 0.2
        elif len(prompt) > 200:
            complexity += 0.1

        # Keyword analysis
        complex_keywords = [
            "refactor",
            "architecture",
            "design",
            "migration",
            "security",
            "optimize",
            "debug",
            "complex",
            "multiple",
            "entire",
            "comprehensive",
        ]
        simple_keywords = ["read", "show", "list", "check", "what", "how", "help"]

        prompt_lower = prompt.lower()
        for kw in complex_keywords:
            if kw in prompt_lower:
                complexity += 0.15

        for kw in simple_keywords:
            if kw in prompt_lower:
                complexity -= 0.1

        # Context factor
        if context:
            if context.get("files_count", 0) > 3:
                complexity += 0.2
            if context.get("has_errors", False):
                complexity += 0.15

        return max(0.0, min(1.0, complexity))

    def _map_depth_to_level(self, depth: ReasoningDepth) -> ReasoningLevel:
        """Map reasoning depth to level"""
        mapping = {
            ReasoningDepth.QUICK: ReasoningLevel.QUICK,
            ReasoningDepth.STANDARD: ReasoningLevel.STANDARD,
            ReasoningDepth.DEEP: ReasoningLevel.DEEP,
        }
        return mapping.get(depth, ReasoningLevel.STANDARD)

    def _get_phases_for_depth(self, depth: ReasoningDepth) -> List[ThinkingPhase]:
        """Get thinking phases for a depth level"""
        if depth == ReasoningDepth.QUICK:
            return [ThinkingPhase.UNDERSTANDING, ThinkingPhase.DECIDING]
        elif depth == ReasoningDepth.STANDARD:
            return [
                ThinkingPhase.UNDERSTANDING,
                ThinkingPhase.PLANNING,
                ThinkingPhase.ANALYZING,
                ThinkingPhase.DECIDING,
                ThinkingPhase.VERIFYING,
            ]
        else:
            return [
                ThinkingPhase.UNDERSTANDING,
                ThinkingPhase.PLANNING,
                ThinkingPhase.ANALYZING,
                ThinkingPhase.REASONING,
                ThinkingPhase.EVALUATING,
                ThinkingPhase.DECIDING,
                ThinkingPhase.VERIFYING,
            ]

    def _start_session(self, metadata: Optional[Dict[str, Any]] = None) -> ThinkingSession:
        """Start a new thinking session"""
        session = ThinkingSession(metadata=metadata or {})
        self.current_session = session
        return session

    def _end_session(self, session: ThinkingSession):
        """End a thinking session"""
        session.complete()
        self.current_session = None

    def _populate_session_blocks(
        self, session: ThinkingSession, reasoning: StructuredReasoning, raw_content: str
    ):
        """Populate session with thinking blocks from reasoning"""
        # Map structured phases to thinking phases
        if reasoning.perception.is_complete():
            session.add_block(
                ThinkingBlock(
                    phase=ThinkingPhase.UNDERSTANDING,
                    content=reasoning.perception.observation,
                    summary=reasoning.perception.initial_interpretation[:100],
                )
            )

        if reasoning.comprehension.is_complete():
            session.add_block(
                ThinkingBlock(
                    phase=ThinkingPhase.UNDERSTANDING,
                    content=reasoning.comprehension.core_understanding,
                    summary=f"Assumptions: {len(reasoning.comprehension.assumptions)}",
                )
            )

        if reasoning.analysis.is_complete():
            session.add_block(
                ThinkingBlock(
                    phase=ThinkingPhase.ANALYZING,
                    content=str(reasoning.analysis.decomposition),
                    summary=f"Options: {len(reasoning.analysis.options)}",
                )
            )

        if reasoning.reasoning.is_complete():
            session.add_block(
                ThinkingBlock(
                    phase=ThinkingPhase.REASONING,
                    content=reasoning.reasoning.hypothesis,
                    summary=f"Confidence: {reasoning.reasoning.confidence:.0%}",
                )
            )

        if reasoning.change_impact.is_complete():
            session.add_block(
                ThinkingBlock(
                    phase=ThinkingPhase.EVALUATING,
                    content=f"Impact: {reasoning.change_impact.files_affected}",
                    summary=f"Breaking changes: {len(reasoning.change_impact.breaking_changes)}",
                )
            )

        if reasoning.decision.is_complete():
            session.add_block(
                ThinkingBlock(
                    phase=ThinkingPhase.DECIDING,
                    content=reasoning.decision.decision,
                    summary=f"Actions: {len(reasoning.decision.action_items)}",
                )
            )

        if reasoning.pre_execution_review.is_complete():
            session.add_block(
                ThinkingBlock(
                    phase=ThinkingPhase.EVALUATING,
                    content=reasoning.pre_execution_review.what_will_change,
                    summary=f"Approval needed: {reasoning.pre_execution_review.user_approval_needed}",
                )
            )

        if reasoning.verification.is_complete():
            session.add_block(
                ThinkingBlock(
                    phase=ThinkingPhase.VERIFYING,
                    content=reasoning.verification.safety_check,
                    summary=f"Ready: {reasoning.verification.ready_to_execute}",
                )
            )

    def _check_requires_revision(
        self, critique: Optional[Dict[str, Any]], quality: Dict[str, float]
    ) -> bool:
        """Check if reasoning requires revision"""
        if not critique:
            return False

        # Check quality threshold
        if quality.get("overall", 0) < 0.5:
            return True

        # Check critique score
        if critique.get("overall_score", 0) < 0.5:
            return True

        # Check for critical weak points
        if len(critique.get("weak_points", [])) > 3:
            return True

        return False

    def _create_empty_result(self) -> ThinkingResult:
        """Create an empty result when thinking is disabled"""
        session = ThinkingSession()
        session.complete()
        return ThinkingResult(session=session)

    def _add_to_history(self, result: ThinkingResult):
        """Add result to history"""
        self.session_history.append(result)
        if len(self.session_history) > self.max_history:
            self.session_history.pop(0)

    # =========================================================================
    # REPORTING AND METRICS
    # =========================================================================

    def get_calibration_report(self) -> Dict[str, Any]:
        """Get confidence calibration report"""
        return self.calibrator.get_calibration_report()

    def get_quality_trend(self, window: int = 10) -> Dict[str, float]:
        """Get quality metrics trend"""
        return self.quality_metrics.get_trend(window)

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        if not self.current_result:
            return {"status": "no_session"}

        return {
            "session_id": self.current_result.session.id,
            "confidence": self.current_result.confidence,
            "quality_score": (
                self.current_result.quality_metrics.get("overall", 0)
                if self.current_result.quality_metrics
                else 0
            ),
            "action_items": len(self.current_result.action_items),
            "requires_revision": self.current_result.requires_revision,
            "feedback_summary": self.feedback_loop.get_feedback_summary(),
        }

    def should_continue_execution(self) -> Tuple[bool, str]:
        """Check if execution should continue"""
        return self.feedback_loop.should_continue()

    def get_adjusted_action_items(self) -> List[str]:
        """Get action items adjusted for feedback"""
        return self.feedback_loop.get_adjusted_action_items()

    # =========================================================================
    # CHANGE-AWARE THINKING (NEW)
    # =========================================================================

    async def think_about_changes(
        self, proposed_changes: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None
    ) -> ThinkingResult:
        """
        Think specifically about proposed file changes.

        This method analyzes proposed changes and determines:
        - Impact of the changes
        - What could go wrong
        - Whether user approval is needed
        - Alternative approaches

        Args:
            proposed_changes: List of change proposals with file_path, old_content, new_content
            context: Additional context

        Returns:
            ThinkingResult with change-specific analysis
        """
        # Build change summary
        change_summary = []
        for change in proposed_changes:
            file_path = change.get("file_path", "unknown")
            operation = change.get("operation", "edit")
            additions = change.get("additions", 0)
            deletions = change.get("deletions", 0)
            change_summary.append(f"- {file_path}: {operation} (+{additions}/-{deletions})")

        changes_text = "\n".join(change_summary)

        # Build prompt for change analysis
        prompt = f"""Analyze the following proposed changes:

{changes_text}

Consider:
1. What files will be affected?
2. Are there any breaking changes?
3. What could go wrong?
4. Is user approval needed?
5. What's the rollback strategy?
"""

        # Use deep thinking for change analysis
        result = await self.think(
            prompt=prompt,
            mode=EnhancedThinkingMode.DEEP,
            context={**(context or {}), "proposed_changes": proposed_changes},
            task_type="change_analysis",
        )

        return result

    def requires_user_approval(self) -> bool:
        """Check if current reasoning requires user approval for changes"""
        if not self.current_reasoning:
            return False

        return self.current_reasoning.requires_user_approval()

    def get_change_summary(self) -> str:
        """Get summary of proposed changes from current reasoning"""
        if not self.current_reasoning:
            return "No changes analyzed"

        return self.current_reasoning.get_change_summary()

    def get_change_impact(self) -> Optional[ChangeImpactOutput]:
        """Get the change impact analysis from current reasoning"""
        if not self.current_reasoning:
            return None

        return self.current_reasoning.change_impact

    def get_pre_execution_review(self) -> Optional[PreExecutionReviewOutput]:
        """Get the pre-execution review from current reasoning"""
        if not self.current_reasoning:
            return None

        return self.current_reasoning.pre_execution_review


# =============================================================================
# CONVENIENCE FACTORY
# =============================================================================


def create_enhanced_thinking_manager(
    llm_client: Optional[Any] = None,
    todo_manager: Optional[TodoManager] = None,
    config: Optional[ThinkingConfig] = None,
) -> EnhancedThinkingManager:
    """
    Create an enhanced thinking manager with default configuration.

    Args:
        llm_client: LLM client instance
        todo_manager: Todo manager instance
        config: Optional thinking config

    Returns:
        Configured EnhancedThinkingManager
    """
    return EnhancedThinkingManager(
        config=config or ThinkingConfig(), llm_client=llm_client, todo_manager=todo_manager
    )
