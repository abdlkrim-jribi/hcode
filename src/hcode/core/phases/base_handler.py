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
    ):
        """
        Initialize base phase handler.

        Args:
            artifact_manager: Manager for phase artifacts
            provider: AI provider for generating responses
            tool_executor: Executor for tool calls
            context_manager: Manager for conversation context
        """
        self.artifact_manager = artifact_manager
        self.provider = provider
        self.tool_executor = tool_executor
        self.context_manager = context_manager

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

    async def _generate_response(
        self,
        prompt: str,
        context: AgentContext,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate AI response for this phase.

        Args:
            prompt: User prompt
            context: Current agent context
            system_prompt: Optional system prompt override

        Returns:
            Generated response text
        """
        if self.provider is None:
            logger.warning("No AI provider configured, returning empty response")
            return ""

        try:
            # Build messages list
            messages = [Message(role="user", content=prompt)]

            # Generate completion from provider
            response = await self.provider.generate_completion(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=4000,
            )

            # Extract content from response
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, dict):
                return response.get('content', '')
            elif isinstance(response, str):
                return response
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                return str(response)

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return f"[Error generating response: {e}]"

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

            try:
                # Execute the tool
                result = await self.tool_executor.execute_tool(tool_name, **arguments)

                # Track in context
                action_record = {
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": result.success if hasattr(result, 'success') else True,
                    "output": str(result.output)[:500] if hasattr(result, 'output') else str(result)[:500],
                }
                context.completed_actions.append(action_record)

                # Track file modifications
                if tool_name.lower() in ['writetool', 'edittool', 'multiedittool', 'write', 'edit']:
                    file_path = arguments.get('file_path', arguments.get('path', ''))
                    if file_path and file_path not in context.modified_files:
                        context.modified_files.append(file_path)

                results.append({
                    "tool": tool_name,
                    "success": action_record["success"],
                    "output": action_record["output"],
                    "error": result.error if hasattr(result, 'error') else None,
                })

            except Exception as e:
                logger.error(f"Failed to execute tool {tool_name}: {e}")
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
        response = await self._generate_response(prompt, context, system_prompt)

        # Extract tool calls
        tool_calls = self._extract_tool_calls(response)

        # Execute tools
        tool_results = []
        if tool_calls:
            tool_results = await self._execute_tools(tool_calls, context)

        return response, tool_results
