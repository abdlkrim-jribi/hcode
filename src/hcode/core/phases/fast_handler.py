"""
Fast Mode Handler
=================

Single-pass implementation flow (no separate planning/verification phases):

  1. Understand — deep query analysis + codebase exploration
  2. Plan inline — write .hcode/todo.md with a focused task list
  3. Implement — execute each todo task, marking progress
  4. Summarize — produce a clear completion summary

Inspired by the PEV execution/verification prompt patterns but compressed into
one continuous multi-turn loop so simple/moderate tasks don't pay the overhead
of a full three-phase workflow.
"""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hcode.providers.base import Message
from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult

try:
    from hcode.ui.hcode_display import FileAction
except ImportError:
    FileAction = None

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

class FastConfig:
    TEMPERATURE = 0.2
    MAX_TOKENS = 2000
    MAX_ROUNDS = 50                # increased — allows deep exploration + full implementation
    EXPLORATION_BUDGET = 8         # rounds before todo.md must exist; urgency escalates after
    TIMEOUT_SECONDS = 1800  # 30 minutes


# ─────────────────────────────────────────────────────────────────────────────
# Handler
# ─────────────────────────────────────────────────────────────────────────────

class FastModeHandler(BasePhaseHandler):
    """
    Fast mode: understand → todo.md → implement → summary.

    Replaces the EV (execution + verification) pair when use_planning=False.
    Runs a single multi-turn AI loop that:

    - Explores the codebase
    - Writes .hcode/todo.md
    - Implements each task (marking [/] → [x])
    - Outputs a final summary
    """

    phase_name = "fast"
    TODO_PATH = ".hcode/todo.md"

    def __init__(self, artifact_manager, provider, tool_executor, context_manager, console=None):
        super().__init__(artifact_manager, provider, tool_executor, context_manager, console)

    # ── System prompt ─────────────────────────────────────────────────────────

    def _get_system_prompt(self, context: AgentContext) -> str:
        """
        Build the system prompt for fast mode, following the same structure
        as all other phase handlers:

          identity + tool_format + user_memory + hcode_architecture
          + fast_mode protocol + hcode_memory + current context
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            identity = loader.get_identity()
            tool_format = loader.get_tool_format()
            fast_protocol = self._load_fast_protocol()

            return (
                f"{identity}\n\n"
                f"{tool_format}\n\n"
                f"{self._load_user_memory(context)}"
                f"{self._load_hcode_architecture(context)}"
                f"---\n\n"
                f"{fast_protocol}\n\n"
                f"---\n"
                f"{self._load_hcode_memory(context)}"
                f"## CURRENT CONTEXT\n\n"
                f"Working directory: {context.working_dir}\n"
                f"Artifacts directory: .hcode\n"
                f"Todo file: {self.TODO_PATH}\n"
            )

        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            return self._fallback_system_prompt(context)

    def _load_fast_protocol(self) -> str:
        """Load fast_mode.md, fall back to inline default."""
        path = (
            Path(__file__).parent.parent.parent
            / "config" / "core_prompts" / "core" / "pev_prompts" / "fast_mode.md"
        )
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return (
                "# Fast Mode\n"
                "Understand the task, write .hcode/todo.md, implement each item, "
                "then summarise.\n"
                "Rules: GLOB before READ, READ before EDIT, ONE task at a time, "
                "mark [/] then [x].\n"
                "Bash timeout in MILLISECONDS (30000 = 30s).\n"
            )

    def _fallback_system_prompt(self, context: AgentContext) -> str:
        return (
            f"You are Hcode in Fast Mode.\n"
            f"Working directory: {context.working_dir}\n\n"
            f"Workflow: understand task → write .hcode/todo.md → implement each item "
            f"(mark [/] then [x]) → summarise.\n\n"
            f"Rules: GLOB before READ, READ before EDIT, ONE task at a time.\n"
            f"Bash timeout in MILLISECONDS (30000 = 30s).\n"
        )

    # ── Prompt builders ───────────────────────────────────────────────────────

    def _build_initial_prompt(self, context: AgentContext) -> str:
        """
        Build the user-turn prompt.

        The system prompt already carries identity, tool format, project architecture
        (hcode.md), and the fast-mode protocol — so this prompt stays task-focused.
        """
        return f"""# TASK

{context.task}

---

## YOUR JOB (4 steps)

1. **Understand** — the PROJECT ARCHITECTURE is in your system prompt (hcode.md).
   Use it to locate relevant files, then Read them to understand the current state.
   If hcode.md is absent, use Glob to discover files first.
2. **Write `.hcode/todo.md`** — a focused task list (max 8 items, checkbox format)
3. **Implement** — for each task: mark `[/]`, implement, verify, mark `[x]`
4. **Summarize** — when all tasks are `[x]`, write what was done and which files changed

Start by exploring the codebase, then write `.hcode/todo.md`.
"""

    _BRIDGE_REMINDER = (
        "\n\n> Reminder: wrap your next reasoning in `<thinking>` — "
        "Learned → Impact → Next → Verify."
    )

    def _build_continuation(
        self,
        context: AgentContext,
        round_num: int,
        fast_phase: str = "exploration",
        last_tool_results: Optional[List[Dict]] = None,
        edit_failures: Optional[Dict[str, int]] = None,
    ) -> str:
        """Return a phase-aware, failure-aware nudge with periodic bridge reminder."""

        edit_failures = edit_failures or {}

        # Append bridge reasoning reminder every 4 rounds so the agent doesn't
        # drift into shallow thinking mid-session. Skipped on failure messages
        # (they already contain explicit instructions).
        remind = self._BRIDGE_REMINDER if round_num > 0 and round_num % 4 == 0 else ""

        # ── Tool failure recovery (always takes priority) ──────────────────────
        if last_tool_results:
            failures = [r for r in last_tool_results if not r.get("success")]
            if failures:
                failed_tools = [r.get("tool", "unknown") for r in failures]
                errors = [r.get("error", "") or r.get("output", "") for r in failures]
                error_summary = "; ".join(str(e)[:200] for e in errors if e)

                if any("edit" in t.lower() for t in failed_tools):
                    # Check if any file has hit the switch-to-Write threshold
                    chronic = [f for f, n in edit_failures.items() if n >= 2]
                    if chronic:
                        files_str = ", ".join(f"`{f}`" for f in chronic)
                        return (
                            f"⚠ Edit failed {edit_failures.get(chronic[0], 2)}× on {files_str}. "
                            f"SWITCH TO WRITE — use Write to replace the entire file.\n"
                            "Do NOT attempt Edit on this file again."
                        )
                    return (
                        f"⚠ Edit failed: {error_summary}\n\n"
                        "Recovery steps:\n"
                        "1. Use Read to see the EXACT current content of the file\n"
                        "2. Copy the precise text for old_string — every character must match\n"
                        "3. After 2 consecutive failures on the same file, use Write instead\n"
                        "4. Never retry Edit with the same old_string that already failed"
                    )

                if any("bash" in t.lower() for t in failed_tools):
                    return (
                        f"⚠ Command failed: {error_summary}\n\n"
                        "Fix the error before continuing. "
                        "Read the traceback carefully — it tells you exactly what to fix."
                    )

                return (
                    f"⚠ Tool failure ({', '.join(failed_tools)}): {error_summary}\n\n"
                    "Fix this error before moving to the next task."
                )

        # ── Phase: exploration ─────────────────────────────────────────────────
        if fast_phase == "exploration":
            over_budget = round_num >= FastConfig.EXPLORATION_BUDGET
            rounds_over = round_num - FastConfig.EXPLORATION_BUDGET + 1

            if over_budget:
                urgency = "CRITICAL" if rounds_over >= 3 else "URGENT"
                return (
                    f"⚠ {urgency}: You have been exploring for {round_num + 1} rounds "
                    f"without writing `.hcode/todo.md`. "
                    f"STOP EXPLORING NOW.\n\n"
                    "You have enough context. Write `.hcode/todo.md` immediately:\n"
                    "```\n"
                    "- [ ] <first specific task> <!-- id: 0 -->\n"
                    "- [ ] <next specific task> <!-- id: 1 -->\n"
                    "```\n"
                    "Every round without a todo list wastes implementation budget."
                )

            remaining = FastConfig.EXPLORATION_BUDGET - round_num - 1
            return (
                f"Continue exploring to understand the codebase. "
                f"You have {remaining} exploration round(s) before todo.md is required."
                + remind
            )

        # ── Phase: implementation ──────────────────────────────────────────────
        if fast_phase == "implementation":
            todo_path = Path(context.working_dir) / self.TODO_PATH
            try:
                content = todo_path.read_text(encoding="utf-8")
            except Exception:
                return "Continue implementing." + remind

            unchecked = content.count("- [ ]")
            in_progress = content.count("- [/]")

            if in_progress > 0:
                return (
                    "Continue with the current in-progress `[/]` task. "
                    "Complete and verify it fully before moving on."
                    + remind
                )

            if unchecked > 0:
                return (
                    f"{unchecked} task(s) remaining. "
                    "Mark the next `[ ]` as `[/]`, implement it, verify it, then mark `[x]`."
                    + remind
                )

            return "All tasks appear done — verify and mark `[x]` if not already done." + remind

        # ── Phase: summary ─────────────────────────────────────────────────────
        if fast_phase == "summary":
            return (
                "All tasks are complete! Write the final summary now: "
                "what was implemented, which files changed, and what the user can now do."
            )

        return "Continue with your next action." + remind

    # ── Todo state ────────────────────────────────────────────────────────────

    def _todo_complete(self, context: AgentContext) -> bool:
        """True when todo.md exists and has no unchecked/in-progress tasks."""
        todo_path = Path(context.working_dir) / self.TODO_PATH
        if not todo_path.exists():
            return False
        try:
            content = todo_path.read_text(encoding="utf-8")
        except Exception:
            return False
        has_any = "- [" in content
        has_pending = "- [ ]" in content or "- [/]" in content
        return has_any and not has_pending

    # ── Main execution loop ───────────────────────────────────────────────────

    async def handle(self, context: AgentContext, loop_controller: Any) -> PhaseResult:
        """Run the fast mode flow end-to-end."""

        # Clean up stale todo from previous run
        todo_path = Path(context.working_dir) / self.TODO_PATH
        if todo_path.exists():
            todo_path.unlink()

        self._display("\n[Fast] Analyzing task...", style="info")

        if self._hcode_display:
            self._hcode_display.start_thinking()

        try:
            summary, tool_count, final_phase = await self._run_fast_loop(context)

            # Only mark success when the agent actually reached the summary phase.
            # If the loop exited due to timeout, MAX_ROUNDS, or persistent loop,
            # final_phase will be "exploration" or "implementation" — that's a failure.
            completed = final_phase == "summary"
            if not completed:
                todo_done = self._todo_complete(context)
                # Edge case: todo never written (trivial task answered in text)
                todo_existed = (Path(context.working_dir) / self.TODO_PATH).exists()
                completed = todo_done or (not todo_existed and bool(summary and len(summary) > 50))

            return PhaseResult(
                phase_name="fast",
                success=completed,
                output=summary or ("Task complete." if completed else "Fast mode did not complete all tasks."),
                can_transition=completed,
                metadata={
                    "phase": "fast",
                    "final_phase": final_phase,
                    "tools_used": tool_count,
                    "response": summary,
                },
            )

        except Exception as e:
            logger.exception(f"Fast mode failed: {e}")
            return PhaseResult(
                phase_name="fast",
                success=False,
                output=f"Fast mode error: {e}",
                can_transition=False,
                error=str(e),
            )

        finally:
            if self._hcode_display:
                self._hcode_display.end_thinking()

    # Max recent conversation turns to seed (each turn = 2 messages: user + assistant).
    # Prevents old history from bloating context when conversation is long.
    _MAX_HISTORY_TURNS = 6

    async def _run_fast_loop(self, context: AgentContext) -> Tuple[str, int, str]:
        """
        Custom multi-turn loop.

        Returns:
            (summary_text, total_tool_count, final_phase)
            final_phase is "summary" when the agent completed normally.
        """
        from datetime import datetime

        system_prompt = self._get_system_prompt(context)
        thinking_instructions = self._get_thinking_instructions()
        initial_prompt = self._build_initial_prompt(context)

        # Seed with recent conversation history only — truncate to avoid token bloat.
        messages: List[Message] = []
        if self.context_manager:
            all_history = self.context_manager.get_messages(include_system=False)
            # Keep only the last MAX_HISTORY_TURNS pairs (user+assistant = 2 messages each)
            max_msgs = self._MAX_HISTORY_TURNS * 2
            messages = all_history[-max_msgs:] if len(all_history) > max_msgs else all_history

        messages.append(Message(role="user", content=thinking_instructions + initial_prompt))

        all_tool_results: List[Dict] = []
        last_response = ""
        response_hashes: List[str] = []
        start_time = datetime.now()
        # Phase tracker: exploration → implementation → summary
        fast_phase = "exploration"
        # Per-file consecutive Edit failure counter for targeted recovery advice
        edit_failures: Dict[str, int] = {}

        for round_num in range(FastConfig.MAX_ROUNDS):
            # Wall-clock timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > FastConfig.TIMEOUT_SECONDS:
                self._display(f"⚠ Fast mode timeout ({int(elapsed)}s)", style="error")
                break

            logger.info(f"[fast] round {round_num + 1}/{FastConfig.MAX_ROUNDS} phase={fast_phase}")

            # Generate response
            try:
                response_obj = await self.provider.generate_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=FastConfig.TEMPERATURE,
                    max_tokens=FastConfig.MAX_TOKENS,
                )
                if hasattr(response_obj, "content"):
                    last_response = response_obj.content
                elif isinstance(response_obj, dict):
                    last_response = response_obj.get("content", "")
                elif isinstance(response_obj, str):
                    last_response = response_obj
                else:
                    last_response = str(response_obj)
            except Exception as e:
                logger.error(f"[fast] provider error round {round_num + 1}: {e}")
                break

            # Loop detection — same response twice means the agent is stuck.
            # Instead of hard-breaking, inject an explicit recovery prompt once.
            response_for_hash = (
                self._extract_text_response(last_response)
                + str(self._extract_tool_calls(last_response))
            )
            response_hash = hashlib.sha256(response_for_hash.encode()).hexdigest()
            if response_hash in response_hashes[-2:]:
                if response_hashes.count(response_hash) >= 3:
                    # Truly stuck after recovery attempt — stop
                    logger.warning("[fast] persistent loop — stopping")
                    self._display("⚠ Agent stuck in loop, stopping.", style="error")
                    break
                logger.warning("[fast] loop detected — injecting recovery prompt")
                messages.append(Message(role="assistant", content=last_response))
                messages.append(Message(
                    role="user",
                    content=(
                        "⚠ You repeated the same response. You are stuck.\n\n"
                        "STOP and change strategy:\n"
                        "1. Read the file that is failing to understand its CURRENT content\n"
                        "2. Use the EXACT text from the file in old_string — never guess\n"
                        "3. If Edit keeps failing, use Write to replace the entire file\n"
                        "4. After 2 failed Edits on the same file, always switch to Write"
                    )
                ))
                response_hashes.append(response_hash)
                continue
            response_hashes.append(response_hash)

            # Display thinking
            self._display_thinking_blocks(last_response)

            # Extract tool calls
            tool_calls = self._extract_tool_calls(last_response)

            # ── Phase transition detection ────────────────────────────────────
            # Check after every round (not just after tool calls) so early
            # completion advances immediately without waiting for next action.
            todo_path = Path(context.working_dir) / self.TODO_PATH

            if fast_phase == "exploration" and todo_path.exists():
                try:
                    _td = todo_path.read_text(encoding="utf-8")
                    if "- [" in _td:  # at least one task item written
                        fast_phase = "implementation"
                        logger.info("[fast] phase: exploration → implementation")
                        self._display("[Fast] Todo ready — starting implementation", style="info")
                except Exception:
                    pass

            if fast_phase == "implementation" and self._todo_complete(context):
                fast_phase = "summary"
                logger.info("[fast] phase: implementation → summary")
                self._display("[Fast] All tasks done — writing summary", style="success")

            if not tool_calls:
                # No tool calls — display any text response
                text = self._extract_text_response(last_response)
                if text and len(text.strip()) > 20:
                    self._display(text, style="default")

                # Summary phase: this text IS the summary — done
                if fast_phase == "summary":
                    break

                # Todo not yet complete — inject a phase-aware nudge and continue
                nudge = self._build_continuation(
                    context, round_num,
                    fast_phase=fast_phase,
                    edit_failures=edit_failures,
                )
                messages.append(Message(role="assistant", content=last_response))
                messages.append(Message(role="user", content=nudge))
                continue

            # Execute tool calls
            tool_results = await self._execute_tools(tool_calls, context)
            all_tool_results.extend(tool_results)

            # ── Track modified files + Edit failure counts ────────────────────
            for result in tool_results:
                tool_name = (result.get("tool") or "").lower()
                args = result.get("arguments") or result.get("args") or {}

                # Collect paths written/edited into context.modified_files
                if tool_name in ("write", "writetool", "edit", "edittool"):
                    file_path = (
                        args.get("file_path")
                        or args.get("path")
                        or args.get("target_file")
                        or ""
                    )
                    if file_path and result.get("success"):
                        if file_path not in context.modified_files:
                            context.modified_files.append(file_path)
                        # Successful edit resets the failure counter for this file
                        edit_failures.pop(file_path, None)

                    # Track consecutive Edit failures per file for targeted recovery
                    if tool_name in ("edit", "edittool") and not result.get("success") and file_path:
                        edit_failures[file_path] = edit_failures.get(file_path, 0) + 1

            # Re-check phase transitions after tool execution (todo.md may have just been written)
            if fast_phase == "exploration" and todo_path.exists():
                try:
                    _td = todo_path.read_text(encoding="utf-8")
                    if "- [" in _td:
                        fast_phase = "implementation"
                        logger.info("[fast] phase: exploration → implementation (post-tool)")
                        self._display("[Fast] Todo ready — starting implementation", style="info")
                except Exception:
                    pass

            if fast_phase == "implementation" and self._todo_complete(context):
                fast_phase = "summary"
                logger.info("[fast] phase: implementation → summary (post-tool)")
                self._display("[Fast] All tasks done — writing summary", style="success")

            # Feed results + phase-aware nudge back to AI
            results_text = self._format_tool_results(tool_results)
            nudge = self._build_continuation(
                context, round_num,
                fast_phase=fast_phase,
                last_tool_results=tool_results,
                edit_failures=edit_failures,
            )

            messages.append(Message(role="assistant", content=last_response))
            messages.append(Message(
                role="user",
                content=f"Tool results:\n\n{results_text}\n\n{nudge}"
            ))

        return self._extract_text_response(last_response), len(all_tool_results), fast_phase

    # ── Tool extraction ───────────────────────────────────────────────────────

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Override base extraction to also scan <thinking> tag content.

        The base class already handles <output> tags, JSON code blocks, and
        inline JSON. This override adds a pass over <thinking> blocks so tool
        calls embedded in reasoning text are not missed.

        Search order: base extraction (covers <output> + JSON) → <thinking> blocks.
        """
        if not response:
            return []

        # Run the full base extraction first (handles <output>, JSON blocks, inline JSON)
        base_calls = super()._extract_tool_calls(response)

        # Additionally scan <thinking> blocks — the reasoning protocol encourages
        # the AI to put tool calls there and they may not appear in <output> tags.
        thinking_calls: List[Dict[str, Any]] = []
        for block in re.findall(r"<thinking>(.*?)</thinking>", response, re.DOTALL | re.IGNORECASE):
            # Re-use base extraction on the block content
            calls = super()._extract_tool_calls(block.strip())
            thinking_calls.extend(calls)

        all_calls = base_calls + thinking_calls

        # Deduplicate by content hash (base calls take priority)
        seen: set = set()
        unique: List[Dict[str, Any]] = []
        for call in all_calls:
            key = json.dumps(call, sort_keys=True)
            if key not in seen:
                seen.add(key)
                unique.append(call)

        return unique

    # ── PhaseHandlerProtocol ──────────────────────────────────────────────────

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """Fast mode is a terminal phase — no next phase."""
        return False

    def get_required_artifacts(self) -> List[str]:
        return []
