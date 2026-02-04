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

        This helps display the conversational parts of the AI response
        while tool calls are processed separately.

        Args:
            response: Full AI response text

        Returns:
            Text portions without JSON code blocks
        """
        if not response:
            return ""

        # Remove JSON code blocks
        text = re.sub(r'```(?:json)?\s*\{[^`]*\}\s*```', '', response, flags=re.DOTALL)

        # Remove inline JSON objects
        text = re.sub(r'\{[^{}]*"tool"\s*:[^{}]*\}', '', text, flags=re.DOTALL)

        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Strip and return
        return text.strip()

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from response.

        Parses both native tool calls and JSON-formatted tool calls from text.

        Args:
            response: AI response text

        Returns:
            List of parsed tool calls as dicts with 'tool' and 'arguments' keys
        """
        tool_calls = []

        # Pattern 1: JSON code blocks with tool calls
        json_block_pattern = r'```(?:json)?\s*(\{[^`]*?"tool"[^`]*?\})\s*```'
        json_blocks = re.findall(json_block_pattern, response, re.DOTALL | re.IGNORECASE)

        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if "tool" in parsed:
                    tool_calls.append({
                        "tool": parsed.get("tool"),
                        "arguments": parsed.get("arguments", parsed.get("parameters", {}))
                    })
            except json.JSONDecodeError:
                continue

        # Pattern 2: Inline JSON objects (not in code blocks)
        if not tool_calls:
            inline_pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"(?:arguments|parameters)"\s*:\s*\{[^{}]*\}[^{}]*\}'
            inline_matches = re.findall(inline_pattern, response, re.DOTALL)

            for match in inline_matches:
                try:
                    parsed = json.loads(match)
                    if "tool" in parsed:
                        tool_calls.append({
                            "tool": parsed.get("tool"),
                            "arguments": parsed.get("arguments", parsed.get("parameters", {}))
                        })
                except json.JSONDecodeError:
                    continue

        # Pattern 3: Look for Write/Edit/Read tool patterns
        write_pattern = r'(?:Write|Edit|Read)(?:Tool)?\s*\(\s*["\']?([^"\')\s]+)["\']?\s*(?:,|\))'
        file_matches = re.findall(write_pattern, response)

        # Log extracted tool calls
        if tool_calls:
            logger.debug(f"Extracted {len(tool_calls)} tool calls from response")

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
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generate response and execute any tool calls.

        Combines generation, extraction, and execution in one method.

        Args:
            prompt: User prompt
            context: Current agent context
            system_prompt: Optional system prompt override

        Returns:
            Tuple of (response_text, tool_results)
        """
        # Generate response
        logger.info(f"Generating response for {self.phase_name} phase...")
        response = await self._generate_response(prompt, context, system_prompt)
        logger.info(f"Generated response length: {len(response) if response else 0}")

        # Extract tool calls
        tool_calls = self._extract_tool_calls(response)
        logger.info(f"Extracted {len(tool_calls)} tool calls from response")
        if tool_calls:
            for tc in tool_calls:
                logger.debug(f"  Tool call: {tc.get('tool')} with args: {list(tc.get('arguments', {}).keys())}")

        # Execute tools
        tool_results = []
        if tool_calls:
            logger.info(f"Executing {len(tool_calls)} tool calls...")
            tool_results = await self._execute_tools(tool_calls, context)
            logger.info(f"Tool execution complete, {len(tool_results)} results")
        else:
            logger.info("No tool calls to execute")

        return response, tool_results
