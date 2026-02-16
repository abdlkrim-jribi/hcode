"""
Task completion detection for Hcode agent.

This module determines when an agent task is complete using multiple
heuristics including explicit completion phrases, substantive answer
detection, todo status, and action counts.
"""

import re
from typing import Dict, Any, List

from hcode.core.todo import TodoManager
from ..protocols import CompletionState


class TaskCompletionDetector:
    """
    Determine when an agent task is complete.
    
    Uses multiple signals to detect completion:
    - Explicit completion phrases ("task completed", "all done")
    - Substantive answer detection (actual prose content)
    - Todo list status (all todos completed)
    - Action count thresholds
    - Response structure analysis
    """
    
    # Strong completion indicators - signal task is done
    COMPLETION_PHRASES = [
        "task completed",
        "task is complete",
        "task has been completed",
        "all done",
        "i have completed",
        "i've completed",
        "successfully completed",
        "finished the task",
        "that completes",
        "this completes",
        "all tasks are complete",
        "all tasks completed",
        "nothing more to do",
        "no further action",
    ]
    
    # Weaker phrases that might appear mid-task
    WEAK_COMPLETION_PHRASES = [
        "let me know if you need",
        "feel free to ask",
        "is there anything else",
        "hope this helps",
        "here's the summary",
        "here is the summary",
        "in conclusion",
        "to summarize",
        "summary:",
        "changes have been made",
        "changes are complete",
        "implementation is complete",
        "done!",
        "that's it",
        "everything is",
    ]
    
    # Indicators that suggest task is continuing
    CONTINUING_INDICATORS = [
        "next",
        "now i",
        "let me",
        "i will",
        "need to",
        "should",
        "investigate",
        "check",
        "fix",
        "error",
        "issue",
    ]
    
    # Thinking block patterns to strip
    THINKING_PATTERNS = [
        r"<thinking>[\s\S]*?(?:</thinking>|$)",
        r"<think>[\s\S]*?(?:</think>|$)",
        r"\[UNDERSTAND\][\s\S]*?(?=\[(?:CONTEXT|OPTIONS|DECISION|RISK|ASSUMPTIONS)\]|$)",
        r"\[CONTEXT\][\s\S]*?(?=\[(?:UNDERSTAND|OPTIONS|DECISION|RISK|ASSUMPTIONS)\]|$)",
        r"\[OPTIONS\][\s\S]*?(?=\[(?:UNDERSTAND|CONTEXT|DECISION|RISK|ASSUMPTIONS)\]|$)",
        r"\[DECISION\][\s\S]*?(?=\[(?:UNDERSTAND|CONTEXT|OPTIONS|RISK|ASSUMPTIONS)\]|$)",
        r"\[RISK\][\s\S]*?(?=\[(?:UNDERSTAND|CONTEXT|OPTIONS|DECISION|ASSUMPTIONS)\]|$)",
        r"\[ASSUMPTIONS\][\s\S]*?(?=\[(?:UNDERSTAND|CONTEXT|OPTIONS|DECISION|RISK)\]|$)",
    ]
    
    # Action completion indicators for imperative tasks
    ACTION_COMPLETION_INDICATORS = [
        "i have created", "i created", "file was created", "file has been created",
        "successfully created", "i have written", "i wrote", "file was written",
        "successfully written", "i have read", "i read the", "content of the file",
        "file contents", "task completed", "task is complete", "completed successfully",
        "done.", "finished.", "complete.", "verified", "verification complete",
        "confirmed", "matches", "correct", "i have listed", "directory contains",
        "files found", "here are the files",
    ]
    
    # Answer indicators for Q&A style responses
    ANSWER_INDICATORS = [
        "here is a summary", "here is an overview", "here is the",
        "the repository contains", "this repository is", "this project is",
        "the codebase includes", "the main components are", "in summary,",
        "to summarize,", "overall,", "in conclusion,", "the structure is",
        "it contains the following", "the following", "consists of",
        "is organized as", "includes:",
    ]
    
    # Summary keywords for pending summary tasks
    SUMMARY_KEYWORDS = [
        "summarize", "summarise", "summary", "compile", "overview",
        "describe", "provide", "write", "generate", "create",
    ]
    
    def __init__(
        self, 
        todo_manager: TodoManager, 
        console=None,
        debug_mode: bool = False,
        min_actions_for_completion: int = 3,
        min_iterations_for_phrase: int = 5,
    ):
        """
        Initialize the completion detector.
        
        Args:
            todo_manager: TodoManager instance for checking todo status
            console: Optional Rich console for debug output
            debug_mode: Whether to print debug messages
            min_actions_for_completion: Minimum actions before strong completion phrases work
            min_iterations_for_phrase: Minimum iterations before weak completion phrases work
        """
        self.todo_manager = todo_manager
        self.console = console
        self.debug_mode = debug_mode
        self.min_actions_for_completion = min_actions_for_completion
        self.min_iterations_for_phrase = min_iterations_for_phrase
    
    def is_complete(
        self,
        response_text: str,
        completed_actions: List[Dict[str, Any]],
        iteration: int,
    ) -> CompletionState:
        """
        Check if the task has been completed.
        
        Args:
            response_text: The model's response text
            completed_actions: List of completed tool actions
            iteration: Current iteration number
            
        Returns:
            CompletionState with completion details
        """
        response_lower = response_text.lower()
        response_stripped = response_text.strip()
        action_count = len(completed_actions) if completed_actions else 0
        
        # Get todo state
        todos_state = self.todo_manager.get_completion_state()
        has_todos = todos_state["total"] > 0
        all_todos_completed = (
            todos_state["completed"] == todos_state["total"] if has_todos else True
        )
        has_pending_todos = has_todos and not all_todos_completed
        
        # Check substantive content
        has_substantive = self.has_substantive_answer(response_text)
        
        # === STRICT: If pending todos, require substantive content ===
        if has_pending_todos and not has_substantive:
            pending_is_summary = self._check_pending_is_summary()
            if pending_is_summary:
                reason = f"Pending summary task ({todos_state['completed']}/{todos_state['total']}) - need actual summary"
            else:
                reason = f"Pending todos ({todos_state['completed']}/{todos_state['total']}) - need substantive answer"
            self._debug_print(f"[?] {reason}")
            return CompletionState(
                is_complete=False,
                reason=reason,
                has_pending_work=True,
            )
        
        # Extra check for summary tasks
        if has_pending_todos and has_substantive:
            pending_is_summary = self._check_pending_is_summary()
            if pending_is_summary and not self._has_summary_structure(response_text):
                reason = "Summary task pending - need actual summary output"
                self._debug_print(f"[?] {reason}")
                return CompletionState(
                    is_complete=False,
                    reason=reason,
                    has_pending_work=True,
                )
        
        # === Strong completion phrases ===
        if action_count >= self.min_actions_for_completion:
            if any(phrase in response_lower for phrase in self.COMPLETION_PHRASES):
                if has_substantive or all_todos_completed:
                    return CompletionState(
                        is_complete=True,
                        reason="Strong completion phrase with substantive content",
                    )
                else:
                    self._debug_print("[?] Completion phrase found but no substantive answer")
        
        # === Weak completion phrases ===
        if (
            iteration >= self.min_iterations_for_phrase
            and action_count >= self.min_actions_for_completion
        ):
            if any(phrase in response_lower for phrase in self.WEAK_COMPLETION_PHRASES):
                if not self._looks_like_tool_call(response_text) and has_substantive:
                    return CompletionState(
                        is_complete=True,
                        reason="Weak completion phrase with substantive content",
                    )
        
        # === All todos completed ===
        if all_todos_completed and has_todos:
            return CompletionState(
                is_complete=True,
                reason="All todos marked as completed",
            )
        
        # === Many actions with conclusion indicators ===
        if action_count >= 5:
            conclusion_indicators = [
                "completed" in response_lower and ("all" in response_lower or "task" in response_lower),
                "finished" in response_lower and "all" in response_lower,
                "done" in response_lower and "all" in response_lower,
                "successful" in response_lower and ("completed" in response_lower or "all" in response_lower),
            ]
            if len(response_stripped) > 100 and sum(conclusion_indicators) >= 1 and has_substantive:
                return CompletionState(
                    is_complete=True,
                    reason="Multiple conclusion indicators with substantive content",
                )
        
        # === Long response without tool calls ===
        if len(response_stripped) > 500 and not self._looks_like_tool_call(response_text):
            explicit_completion = any(
                phrase in response_lower
                for phrase in [
                    "have completed", "has been completed", "is now complete",
                    "all tasks done", "all done", "finished all",
                ]
            )
            if explicit_completion and has_substantive:
                return CompletionState(
                    is_complete=True,
                    reason="Long response with explicit completion",
                )
        
        # === Safety: Many iterations without continuing indicators ===
        if iteration > 8 and action_count > 5:
            has_continuing = any(ind in response_lower for ind in self.CONTINUING_INDICATORS)
            if not has_continuing and has_substantive:
                return CompletionState(
                    is_complete=True,
                    reason="Many iterations without continuation indicators",
                )
        
        return CompletionState(
            is_complete=False,
            reason="No completion criteria met",
            has_pending_work=self.has_pending_work(response_text),
        )
    
    def has_pending_work(self, response_text: str) -> bool:
        """
        Check if there's pending work that model should continue.
        
        Args:
            response_text: Model's response text
            
        Returns:
            True if there appears to be pending work
        """
        # Check for pending todos
        if self.todo_manager.has_pending():
            if not self.has_substantive_answer(response_text):
                return True
        
        response_stripped = response_text.strip()
        
        # Check for JSON fragments or incomplete tool calls
        json_fragment_patterns = [
            r"^\s*\{[^}]*$",  # Opening brace without closing
            r'^\s*\{"tool"',  # Start of tool call
            r'"parameters"\s*:\s*\{[^}]*$',  # Incomplete parameters
        ]
        for pattern in json_fragment_patterns:
            if re.match(pattern, response_stripped, re.DOTALL):
                return True
        
        # Check for continuing work indicators
        response_lower = response_stripped.lower()
        for indicator in self.CONTINUING_INDICATORS:
            if indicator in response_lower:
                # Check it's not negated
                if f"don't {indicator}" not in response_lower and f"no {indicator}" not in response_lower:
                    return True
        
        return False
    
    def has_substantive_answer(self, response_text: str) -> bool:
        """
        Check if response contains actual answer to user's question.
        
        Very strict - only returns True if there's clear user-facing prose
        that actually answers a question (not just tool calls or thinking).
        
        Also recognizes imperative task completions.
        
        Args:
            response_text: Model's response text
            
        Returns:
            True if response has substantive content
        """
        # Strip non-user-facing content
        clean_text = self._strip_metadata(response_text)
        response_stripped = clean_text.strip()
        response_lower = response_stripped.lower()
        
        # === Imperative task completion check ===
        has_action_completion = any(
            ind in response_lower for ind in self.ACTION_COMPLETION_INDICATORS
        )
        if has_action_completion and len(response_stripped) >= 5:
            return True
        
        # === Question detection ===
        if response_stripped.endswith("?") and len(response_stripped) >= 20:
            return True
        
        # === Q&A answer detection ===
        if len(response_stripped) < 100:
            return False
        
        # Code blocks are substantive
        if "```" in response_stripped and response_stripped.count("```") >= 2:
            return True
        
        # Check for answer indicators
        has_answer_indicator = any(
            ind in response_lower for ind in self.ANSWER_INDICATORS
        )
        if not has_answer_indicator:
            return False
        
        # Check for prose structure
        sentence_count = len(re.findall(r"[.!?]\s+[A-Z]", response_stripped))
        return sentence_count >= 2
    
    def is_response_truncated(self, response_text: str, finish_reason: str) -> bool:
        """
        Check if response was truncated (model cut off mid-response).
        
        Args:
            response_text: Model's response text
            finish_reason: API finish reason
            
        Returns:
            True if response appears truncated
        """
        # Explicit truncation from API
        if finish_reason == "length":
            return True
        
        response_stripped = response_text.strip()
        
        # Check for truncation indicators
        truncation_indicators = [
            response_stripped.endswith("{"),
            response_stripped.endswith("["),
            response_stripped.endswith(","),
            response_stripped.endswith(":"),
            # Incomplete code block
            response_stripped.count("```") % 2 == 1,
        ]
        
        return any(truncation_indicators)
    
    def _strip_metadata(self, text: str) -> str:
        """Strip thinking blocks and JSON metadata from text."""
        clean = text
        
        # Strip thinking blocks
        for pattern in self.THINKING_PATTERNS:
            clean = re.sub(pattern, "", clean, flags=re.IGNORECASE | re.DOTALL)
        
        # Strip JSON blocks
        json_patterns = [
            r'\{[^{}]*"tool"[^{}]*\}',
            r'\{[^{}]*"parameters"[^{}]*\}',
            r'\{"[^"]+"\s*:\s*"[^"]*"\}',
            r"\{[\s\S]*?\}",
        ]
        for pattern in json_patterns:
            clean = re.sub(pattern, "", clean, flags=re.DOTALL)
        
        # Strip status lines
        clean = re.sub(r"\*\s*GOAL:.*", "", clean)
        clean = re.sub(r"\[OK\].*", "", clean)
        clean = re.sub(r"\[!\].*", "", clean)
        clean = re.sub(r"\[CHALLENGE\].*", "", clean)
        
        # Clean whitespace
        clean = re.sub(r"\n\s*\n\s*\n+", "\n\n", clean)
        
        return clean
    
    def _check_pending_is_summary(self) -> bool:
        """Check if any pending todo is a summary-type task."""
        try:
            for todo in self.todo_manager.get_pending_todos():
                content = todo.get("content", "").lower()
                if any(kw in content for kw in self.SUMMARY_KEYWORDS):
                    return True
        except Exception:
            pass
        return False
    
    def _has_summary_structure(self, text: str) -> bool:
        """Check if response has summary-like structure."""
        clean = self._strip_metadata(text).strip()
        return (
            "## " in clean
            or "### " in clean
            or "summary" in clean.lower()
            or "overview" in clean.lower()
            or (clean.count("\n") > 10 and len(clean) > 500)
        )
    
    def _looks_like_tool_call(self, text: str) -> bool:
        """Check if text looks like it contains a tool call."""
        tool_patterns = [
            r'\{\s*"tool"\s*:',
            r'\{\s*"parameters"\s*:',
            r'"file_path"\s*:\s*"',
            r'"command"\s*:\s*"',
        ]
        return any(re.search(p, text) for p in tool_patterns)
    
    def _debug_print(self, message: str) -> None:
        """Print debug message if console available."""
        if self.console and self.debug_mode:
            self.console.print(f"[dim yellow]{message}[/dim yellow]")
