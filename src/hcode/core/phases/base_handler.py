"""
Base class for phase handlers.

Provides common functionality for all PEV phase handlers.
"""

import re
import json
import logging
from typing import List, Optional, Tuple, Any, Dict
from ..protocols import (
    PhaseHandlerProtocol,
    AgentContext,
    PhaseResult,
    ArtifactManagerProtocol,
)
from hcode.providers.base import Message

# FileAction enum for HcodeDisplay tracking
try:
    from hcode.ui.hcode_display import FileAction
except ImportError:
    FileAction = None

logger = logging.getLogger(__name__)


class BasePhaseHandler(PhaseHandlerProtocol):
    """
    Base implementation for phase handlers.

    Subclasses should override:
    - handle(): Execute phase-specific logic
    - get_required_artifacts(): Return list of artifacts this phase produces
    """

    phase_name: str = "base"

    def __init__(
        self,
        artifact_manager: ArtifactManagerProtocol,
        provider: Any,
        tool_executor: Any,
        context_manager: Any,
        console: Any = None,
    ):
        """
        Initialize base phase handler.

        Args:
            artifact_manager: Manager for phase artifacts
            provider: AI provider for generating responses
            tool_executor: Executor for tool calls
            context_manager: Manager for conversation context
            console: Rich console for output (optional)
        """
        self.artifact_manager = artifact_manager
        self.provider = provider
        self.tool_executor = tool_executor
        self.context_manager = context_manager
        self.console = console

        # Initialize HcodeDisplay for modern UI
        self._hcode_display = None
        if console:
            try:
                from hcode.ui.hcode_display import get_hcode_display
                self._hcode_display = get_hcode_display(console)
            except ImportError:
                pass

    def _display(self, message: str, style: str = "default"):
        """Display message using HcodeDisplay or fallback to print."""
        if self.console:
            if style == "thinking":
                self.console.print(f"[dim]{message}[/dim]")
            elif style == "success":
                self.console.print(f"[bold green]{message}[/bold green]")
            elif style == "error":
                self.console.print(f"[bold red]{message}[/bold red]")
            elif style == "info":
                self.console.print(f"[cyan]{message}[/cyan]")
            else:
                self.console.print(message)
        else:
            print(message)

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute this phase's logic.

        Must be implemented by subclasses.

        Args:
            context: Current agent context
            loop_controller: Loop controller for tracking iterations

        Returns:
            PhaseResult with execution outcome
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement handle()")

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """
        Check if ready to transition to next phase.

        Default implementation: Check if all required artifacts exist.

        Args:
            context: Current agent context

        Returns:
            True if phase is complete
        """
        required_artifacts = self.get_required_artifacts()

        for artifact_name in required_artifacts:
            if not self.artifact_manager.artifact_exists(artifact_name, context):
                return False

        return True

    def get_required_artifacts(self) -> List[str]:
        """
        Get list of artifacts this phase should produce.

        Must be implemented by subclasses.

        Returns:
            List of artifact names
        """
        return []

    def validate_artifacts(self, context: AgentContext) -> Tuple[bool, Optional[str]]:
        """
        Validate that required artifacts were created and are valid.

        Args:
            context: Current agent context

        Returns:
            Tuple of (valid, error_message)
        """
        required_artifacts = self.get_required_artifacts()

        for artifact_name in required_artifacts:
            # Check existence
            if not self.artifact_manager.artifact_exists(artifact_name, context):
                return False, f"Missing required artifact: {artifact_name}"

            # Load and validate content
            content = self.artifact_manager.load_artifact(artifact_name, context)
            if content is None:
                return False, f"Could not load artifact: {artifact_name}"

            valid, error = self.artifact_manager.validate_artifact_content(
                artifact_name, content
            )
            if not valid:
                return False, error

        return True, None

    def _build_phase_prompt(self, context: AgentContext) -> str:
        """
        Build prompt for this phase.

        Can be overridden by subclasses for phase-specific prompts.

        Args:
            context: Current agent context

        Returns:
            Prompt string for this phase
        """
        return context.task

    def _get_thinking_instructions(self) -> str:
        """
        Get standard thinking instructions to prepend to prompts.

        Returns:
            Thinking instructions string
        """
        return """### THINKING PROTOCOL

You MUST think systematically before every action:

<thinking>
1. COMPREHENSION: What exactly am I being asked to do?
2. VERIFICATION: What assumptions am I making that I should verify?
3. ANTI-HALLUCINATION: Am I about to output code I haven't read? If yes, READ FIRST.
4. TOOL SELECTION: What tool is most appropriate and why?
5. EXPECTED OUTCOME: What should happen if I do this correctly?
</thinking>

CRITICAL RULES:
- NEVER show code in response text without using Write/Edit tools
- ALWAYS read files before editing them
- VERIFY assumptions before acting on them
- ONE change at a time, verify each before proceeding

"""

    async def _generate_response(
        self,
        prompt: str,
        context: AgentContext,
        system_prompt: Optional[str] = None,
        include_thinking: bool = True,
    ) -> str:
        """
        Generate AI response for this phase.

        Args:
            prompt: User prompt
            context: Current agent context
            system_prompt: Optional system prompt override
            include_thinking: Whether to include thinking instructions

        Returns:
            Generated response text
        """
        if self.provider is None:
            logger.warning("No AI provider configured, returning empty response")
            self._display("No AI provider configured!", style="error")
            return ""

        try:
            # Optionally prepend thinking instructions
            enhanced_prompt = prompt
            if include_thinking:
                thinking_instructions = self._get_thinking_instructions()
                enhanced_prompt = thinking_instructions + prompt

            # Build messages list
            messages = [Message(role="user", content=enhanced_prompt)]

            logger.debug(f"Calling provider.generate_completion (prompt length: {len(enhanced_prompt)})")

            # Generate completion from provider
            response = await self.provider.generate_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=4000,
            )

            # Extract content from response
            if hasattr(response, 'content'):
                result = response.content
            elif isinstance(response, dict):
                result = response.get('content', '')
            elif isinstance(response, str):
                result = response
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                result = str(response)

            logger.debug(f"Response length: {len(result) if result else 0}")
            return result

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            self._display(f"Failed to generate response: {e}", style="error")
            return f"[Error generating response: {e}]"

    def _extract_text_response(self, response: str) -> str:
        """
        Extract text portions from response (excluding JSON tool calls).

        Removes code blocks (which contain tool calls) and thinking/analysis
        tags, keeping only the conversational text.

        Args:
            response: Full AI response text

        Returns:
            Text portions without JSON code blocks or thinking blocks
        """
        if not response:
            return ""

        # Remove all ```...``` code blocks (tool calls live in these)
        text = re.sub(r'```[^\n]*\n?.*?```', '', response, flags=re.DOTALL)

        # Remove <thinking>...</thinking> blocks
        text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)

        # Remove <analysis>...</analysis> blocks
        text = re.sub(r'<analysis>.*?</analysis>', '', text, flags=re.DOTALL)

        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from response.

        Primary path: parses JSON from ```json code blocks (handles nested objects).
        Fallback: brace-balanced extraction for inline JSON tool calls.

        Args:
            response: AI response text

        Returns:
            List of parsed tool calls as dicts with 'tool' and 'arguments' keys
        """
        tool_calls = []

        # Primary: Extract content from all code blocks, parse as JSON
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?\s*```'
        code_blocks = re.findall(code_block_pattern, response, re.DOTALL)

        for block in code_blocks:
            block = block.strip()
            if not block or not block.startswith('{'):
                continue
            try:
                parsed = json.loads(block)
                if isinstance(parsed, dict) and "tool" in parsed:
                    tool_calls.append({
                        "tool": parsed.get("tool"),
                        "arguments": parsed.get("arguments", parsed.get("parameters", {}))
                    })
            except json.JSONDecodeError:
                continue

        # Fallback: brace-balanced extraction for inline JSON (no code blocks)
        if not tool_calls:
            tool_calls = self._extract_inline_json_tools(response)

        if tool_calls:
            logger.debug(f"Extracted {len(tool_calls)} tool calls from response")

        return tool_calls

    def _extract_inline_json_tools(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract tool call JSON from inline text using brace-balanced matching.

        Handles nested objects correctly by tracking brace depth and
        respecting string boundaries.

        Args:
            text: Response text to search

        Returns:
            List of parsed tool call dicts
        """
        tool_calls = []
        i = 0
        while i < len(text):
            if text[i] == '{':
                depth = 0
                in_str = False
                escaped = False
                j = i
                while j < len(text):
                    c = text[j]
                    if escaped:
                        escaped = False
                        j += 1
                        continue
                    if c == '\\' and in_str:
                        escaped = True
                        j += 1
                        continue
                    if c == '"':
                        in_str = not in_str
                    elif not in_str:
                        if c == '{':
                            depth += 1
                        elif c == '}':
                            depth -= 1
                            if depth == 0:
                                candidate = text[i:j + 1]
                                if '"tool"' in candidate:
                                    try:
                                        parsed = json.loads(candidate)
                                        if isinstance(parsed, dict) and "tool" in parsed:
                                            tool_calls.append({
                                                "tool": parsed.get("tool"),
                                                "arguments": parsed.get("arguments", parsed.get("parameters", {}))
                                            })
                                    except json.JSONDecodeError:
                                        pass
                                i = j
                                break
                    j += 1
            i += 1
        return tool_calls

    async def _execute_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        context: AgentContext,
    ) -> List[Dict[str, Any]]:
        """
        Execute tool calls and track results.

        Args:
            tool_calls: List of tool calls to execute
            context: Current agent context

        Returns:
            List of tool execution results
        """
        results = []

        if self.tool_executor is None:
            logger.warning("No tool executor configured")
            return results

        for tool_call in tool_calls:
            tool_name = tool_call.get("tool", "")
            arguments = tool_call.get("arguments", {})

            # Display tool execution using modern UI
            # Get file path from various argument names used by different tools
            file_path = (
                arguments.get('TargetFile') or
                arguments.get('AbsolutePath') or
                arguments.get('file_path') or
                arguments.get('path') or
                arguments.get('DirectoryPath') or
                ''
            )
            if file_path:
                self._display(f"  [>] {tool_name}: {file_path}", style="thinking")
            else:
                self._display(f"  [>] {tool_name}", style="thinking")

            try:
                # Execute the tool
                result = await self.tool_executor.execute_tool(tool_name, **arguments)

                # Track in context
                success = result.success if hasattr(result, 'success') else True
                action_record = {
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": success,
                    "output": str(result.output)[:500] if hasattr(result, 'output') else str(result)[:500],
                    "file_path": file_path,
                }
                context.completed_actions.append(action_record)

                # Display result with modern UI
                if success:
                    self._display(f"      [OK]", style="success")
                    # Track file with HcodeDisplay using FileAction enum
                    if self._hcode_display and file_path and FileAction:
                        action_type = FileAction.CREATED if tool_name.lower() in ['write', 'writetool'] else FileAction.EDITED
                        self._hcode_display.track_file(file_path, action_type)

                    # Detect task.md checkbox completions and display them
                    if tool_name.lower() in ['edit', 'edittool'] and 'task.md' in str(file_path):
                        old_text = arguments.get('TargetContent', arguments.get('old_string', ''))
                        new_text = arguments.get('ReplacementContent', arguments.get('new_string', ''))
                        if '- [ ]' in old_text and ('- [x]' in new_text or '- [/]' in new_text):
                            # Extract the task description from the new checkbox line
                            import re as _re
                            completed_tasks = _re.findall(r'-\s*\[x\]\s*(.+?)(?:\s*<!--.*?-->)?$', new_text, _re.MULTILINE)
                            in_progress_tasks = _re.findall(r'-\s*\[/\]\s*(.+?)(?:\s*<!--.*?-->)?$', new_text, _re.MULTILINE)
                            for task_text in completed_tasks:
                                self._display(f"      ✓ {task_text.strip()}", style="success")
                            for task_text in in_progress_tasks:
                                self._display(f"      ⟳ {task_text.strip()}", style="info")
                else:
                    error_msg = result.error if hasattr(result, 'error') else "Unknown error"
                    self._display(f"      [FAIL] {error_msg}", style="error")

                # Track file modifications
                if tool_name.lower() in ['writetool', 'edittool', 'multiedittool', 'write', 'edit']:
                    # Get file path from the action record
                    tracked_path = file_path or arguments.get('TargetFile', '')
                    if tracked_path and tracked_path not in context.modified_files:
                        context.modified_files.append(tracked_path)

                results.append({
                    "tool": tool_name,
                    "success": action_record["success"],
                    "output": action_record["output"],
                    "error": result.error if hasattr(result, 'error') else None,
                    "file_path": file_path,
                })

            except Exception as e:
                logger.error(f"Failed to execute tool {tool_name}: {e}")
                self._display(f"      [ERROR] {e}", style="error")
                results.append({
                    "tool": tool_name,
                    "success": False,
                    "output": None,
                    "error": str(e),
                })

                # Track failed action
                context.completed_actions.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": False,
                    "error": str(e),
                })

        return results

    async def _generate_and_execute(
        self,
        prompt: str,
        context: AgentContext,
        system_prompt: Optional[str] = None,
        max_rounds: int = 8,
        max_tokens: int = 8192,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generate response and execute tool calls in a multi-turn loop.

        Feeds tool execution results back to the AI so it can use the
        output (e.g. file contents from Read) in subsequent responses.
        Loops until the AI produces no more tool calls or max_rounds hit.

        Args:
            prompt: User prompt
            context: Current agent context
            system_prompt: Optional system prompt override
            max_rounds: Maximum generation rounds before stopping
            max_tokens: Maximum tokens per generation call

        Returns:
            Tuple of (last_response_text, all_tool_results)
        """
        all_tool_results = []
        last_response = ""

        # Build initial messages with thinking instructions
        thinking_instructions = self._get_thinking_instructions()
        messages = [Message(role="user", content=thinking_instructions + prompt)]

        for round_num in range(max_rounds):
            logger.info(f"[{self.phase_name}] Generation round {round_num + 1}/{max_rounds}...")

            # Call provider
            try:
                response = await self.provider.generate_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )

                # Extract content from response object
                if hasattr(response, 'content'):
                    last_response = response.content
                elif isinstance(response, dict):
                    last_response = response.get('content', '')
                elif isinstance(response, str):
                    last_response = response
                else:
                    last_response = str(response)

            except Exception as e:
                logger.error(f"Provider call failed on round {round_num + 1}: {e}")
                self._display(f"Generation error: {e}", style="error")
                break

            logger.info(f"[{self.phase_name}] Response length: {len(last_response) if last_response else 0}")

            # Display text portions of this response immediately (Claude Code-style)
            text_portion = self._extract_text_response(last_response)
            if text_portion and len(text_portion.strip()) > 20:
                self._display(text_portion, style="default")

            # Extract tool calls from this response
            tool_calls = self._extract_tool_calls(last_response)
            logger.info(f"[{self.phase_name}] Extracted {len(tool_calls)} tool calls")

            if not tool_calls:
                # No tool calls — AI is done, exit loop
                break

            # Log tool calls for debugging
            for tc in tool_calls:
                logger.debug(f"  Tool: {tc.get('tool')} args: {list(tc.get('arguments', {}).keys())}")

            # Execute extracted tool calls
            tool_results = await self._execute_tools(tool_calls, context)
            all_tool_results.extend(tool_results)

            # Add assistant response to message history
            messages.append(Message(role="assistant", content=last_response))

            # Build context-aware continuation prompt
            continuation = self._build_continuation_prompt(tool_results, all_tool_results, round_num, context)

            # Format results and feed back to AI as user message
            results_feedback = self._format_tool_results(tool_results)
            messages.append(Message(
                role="user",
                content=(
                    f"Tool execution results:\n\n{results_feedback}\n\n"
                    f"{continuation}"
                )
            ))

        return last_response, all_tool_results

    def _build_continuation_prompt(
        self,
        round_results: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]],
        round_num: int,
        context: Any = None,
    ) -> str:
        """
        Build a phase-aware continuation message after each tool round.

        Subclasses override for phase-specific steering (e.g. planning
        pushes the AI to write missing artifacts).

        Default: generic "continue or summarise".
        """
        return (
            "Continue with your task. Output more tool calls if needed, "
            "or provide a summary if you're done."
        )

    def _format_tool_results(
        self, results: List[Dict[str, Any]], preserve_signatures: bool = False
    ) -> str:
        """
        Format tool execution results for feeding back to the AI.

        Args:
            results: List of tool result dicts
            preserve_signatures: If True, preserve class/function signatures
                                 in Read outputs before truncating (useful for planning)

        Returns:
            Formatted string describing each tool's output
        """
        import re

        parts = []
        for r in results:
            tool = r.get('tool', 'unknown')
            success = r.get('success', False)
            output = str(r.get('output', ''))
            error = r.get('error', '')

            if success:
                # Apply signature preservation for Read tool in planning phase
                if preserve_signatures and tool.lower() == 'read':
                    output = self._extract_signatures_and_truncate(output, max_chars=3000)
                else:
                    output = output[:2000]  # Standard truncation

                parts.append(f"[{tool}] Success:\n{output}")
            else:
                parts.append(f"[{tool}] Failed: {error}")

        return "\n\n".join(parts) if parts else "No tool results."

    def _extract_signatures_and_truncate(self, content: str, max_chars: int = 3000) -> str:
        """
        Extract class and function signatures before truncating content.

        Preserves structural information (class/def lines) even when the body
        is truncated, giving the AI context about what's in the file.

        Args:
            content: Full file content
            max_chars: Maximum characters for output

        Returns:
            Content with signatures preserved at the top if needed
        """
        import re

        if len(content) <= max_chars:
            return content

        # Extract signatures
        signatures = []
        # Match class definitions
        for match in re.finditer(r'^(class\s+\w+[^\n]*)', content, re.MULTILINE):
            signatures.append(match.group(1))
        # Match function definitions (including async)
        for match in re.finditer(r'^(\s*(?:async\s+)?def\s+\w+[^\n]*)', content, re.MULTILINE):
            signatures.append(match.group(1).strip())

        if signatures:
            sig_header = "# File signatures (extracted before truncation):\n# " + "\n# ".join(signatures[:15]) + "\n\n"
            remaining = max_chars - len(sig_header)
            return sig_header + content[:remaining] + "\n... [truncated]"
        else:
            return content[:max_chars] + "\n... [truncated]"
