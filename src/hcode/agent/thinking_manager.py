"""
Thinking manager for coordinating extended reasoning.

Integrates with LLM to generate thinking content and manages sessions.
"""

import time
from typing import Optional, List, Callable, AsyncGenerator, Dict, Any

from hcode.agent.thinking import ThinkingBlock, ThinkingSession, ThinkingPhase
from hcode.config.thinking import ThinkingConfig, ThinkingVisibility


class ThinkingManager:
    """
    Manages extended thinking sessions.

    Coordinates with LLM to generate thinking content and manages
    the complete thinking lifecycle.
    """

    def __init__(self, config: ThinkingConfig, llm_client: Optional[Any] = None):
        """
        Initialize thinking manager.

        Args:
            config: Thinking configuration
            llm_client: LLM client for generating thoughts
        """
        self.config = config
        self.llm_client = llm_client
        self.current_session: Optional[ThinkingSession] = None
        self.listeners: List[Callable[[ThinkingBlock], None]] = []

    def add_listener(self, listener: Callable[[ThinkingBlock], None]) -> None:
        """
        Add a listener for thinking events.

        Args:
            listener: Callback function for thinking blocks
        """
        self.listeners.append(listener)

    def notify_listeners(self, block: ThinkingBlock) -> None:
        """
        Notify all listeners of a new thinking block.

        Args:
            block: Thinking block to notify about
        """
        for listener in self.listeners:
            try:
                listener(block)
            except Exception as e:
                # Don't let listener errors break thinking
                print(f"Listener error: {e}")

    def start_session(self, metadata: Optional[Dict[str, Any]] = None) -> ThinkingSession:
        """
        Start a new thinking session.

        Args:
            metadata: Optional metadata for the session

        Returns:
            New thinking session
        """
        self.current_session = ThinkingSession(metadata=metadata or {})
        return self.current_session

    def end_session(self) -> Optional[ThinkingSession]:
        """
        End the current thinking session.

        Returns:
            Completed session or None
        """
        if self.current_session:
            self.current_session.complete()
            session = self.current_session
            self.current_session = None
            return session
        return None

    async def think(
        self,
        prompt: str,
        phases: Optional[List[ThinkingPhase]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ThinkingSession:
        """
        Perform extended thinking on a prompt.

        Args:
            prompt: The prompt to think about
            phases: Specific phases to use (defaults to all)
            context: Additional context

        Returns:
            Completed thinking session
        """
        if not self.config.enabled:
            # Return empty session if disabled
            session = ThinkingSession()
            session.complete()
            return session

        # Use provided phases or default to all
        if phases is None:
            phases = [
                ThinkingPhase.UNDERSTANDING,
                ThinkingPhase.PLANNING,
                ThinkingPhase.ANALYZING,
                ThinkingPhase.REASONING,
                ThinkingPhase.EVALUATING,
                ThinkingPhase.DECIDING,
                ThinkingPhase.VERIFYING,
            ]

        # Start session
        session = self.start_session(metadata=context or {})

        # Process each phase
        for phase in phases:
            block = await self._think_phase(prompt, phase, context)
            session.add_block(block)

            # Notify listeners if visibility allows
            if self.config.visibility != ThinkingVisibility.HIDDEN:
                self.notify_listeners(block)

        # End session
        self.end_session()
        return session

    async def _think_phase(
        self, prompt: str, phase: ThinkingPhase, context: Optional[Dict[str, Any]] = None
    ) -> ThinkingBlock:
        """
        Perform thinking for a specific phase.

        Args:
            prompt: The prompt to think about
            phase: The thinking phase
            context: Additional context

        Returns:
            Thinking block for this phase
        """
        start_time = time.time()

        # Build phase-specific prompt
        phase_prompt = self._build_phase_prompt(prompt, phase, context)

        # Generate thinking content using LLM if available
        if self.llm_client:
            content, tokens = await self._generate_thinking(phase_prompt)
        else:
            # Fallback to simple analysis
            content = f"[{phase.value}] Analyzing: {prompt}"
            tokens = 0

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Create summary
        summary = self._create_summary(content, phase)

        # Create thinking block
        block = ThinkingBlock(
            phase=phase,
            content=content,
            summary=summary,
            tokens_used=tokens,
            duration_ms=duration_ms,
            metadata=context or {},
        )

        return block

    def _build_phase_prompt(
        self, prompt: str, phase: ThinkingPhase, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build a phase-specific thinking prompt.

        Args:
            prompt: Original prompt
            phase: Thinking phase
            context: Additional context

        Returns:
            Phase-specific prompt
        """
        phase_instructions = {
            ThinkingPhase.UNDERSTANDING: "Carefully analyze and understand the problem. What is being asked? What are the key requirements?",
            ThinkingPhase.PLANNING: "Plan your approach. What steps will you take? What tools or files are needed?",
            ThinkingPhase.ANALYZING: "Analyze the options and tradeoffs. What are different ways to solve this?",
            ThinkingPhase.REASONING: "Think deeply about the best solution. Why is one approach better than others?",
            ThinkingPhase.EVALUATING: "Evaluate your planned solution. What could go wrong? What are the edge cases?",
            ThinkingPhase.DECIDING: "Make concrete decisions. What exactly will you do?",
            ThinkingPhase.VERIFYING: "Verify your approach is sound. Does this solve the problem completely?",
        }

        instruction = phase_instructions.get(phase, "Think about this problem.")

        parts = [f"=== {phase.value.upper()} PHASE ===", instruction, "", "Task:", prompt]

        if context:
            parts.extend(["", "Context:", str(context)])

        return "\n".join(parts)

    async def _generate_thinking(self, prompt: str) -> tuple[str, int]:
        """
        Generate thinking content using LLM.

        Args:
            prompt: Prompt to think about

        Returns:
            Tuple of (content, tokens_used)
        """
        if not self.llm_client:
            return prompt, 0

        try:
            # Use higher temperature for creative thinking
            response = await self.llm_client.generate(
                prompt=prompt,
                max_tokens=self.config.budget_tokens,
                temperature=1.0,  # Higher temperature for exploration
                system="You are an expert reasoning assistant. Think deeply and systematically about problems.",
            )

            content = response.get("content", "")
            tokens = response.get("usage", {}).get("total_tokens", 0)

            return content, tokens

        except Exception as e:
            # Fallback on error
            return f"Error generating thinking: {e}", 0

    def _create_summary(self, content: str, phase: ThinkingPhase) -> str:
        """
        Create a brief summary of thinking content.

        Args:
            content: Full thinking content
            phase: Thinking phase

        Returns:
            Brief summary
        """
        # Take first meaningful line or first 100 chars
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        if not lines:
            return f"Completed {phase.value}"

        first_line = lines[0]
        if len(first_line) > 100:
            return first_line[:97] + "..."

        return first_line

    async def stream_thinking(
        self,
        prompt: str,
        phases: Optional[List[ThinkingPhase]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[ThinkingBlock, None]:
        """
        Stream thinking blocks as they are generated.

        Args:
            prompt: The prompt to think about
            phases: Specific phases to use
            context: Additional context

        Yields:
            Thinking blocks as they are created
        """
        if not self.config.enabled:
            return

        # Use provided phases or default
        if phases is None:
            phases = [
                ThinkingPhase.UNDERSTANDING,
                ThinkingPhase.PLANNING,
                ThinkingPhase.ANALYZING,
                ThinkingPhase.REASONING,
                ThinkingPhase.EVALUATING,
                ThinkingPhase.DECIDING,
                ThinkingPhase.VERIFYING,
            ]

        # Start session
        self.start_session(metadata=context or {})

        # Process and yield each phase
        for phase in phases:
            block = await self._think_phase(prompt, phase, context)

            if self.current_session:
                self.current_session.add_block(block)

            yield block

        # End session
        self.end_session()
