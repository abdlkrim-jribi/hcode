"""
HcodeAgent - Main orchestrator for Hcode.
Coordinates AI providers, file system, tools, and safety mechanisms.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, AsyncIterator
from rich.console import Console
from rich.markdown import Markdown

from ..providers import (
    ProviderSelector,
    ProviderPreferences,
    TaskComplexity,
    TaskType,
    Message,
    AIProvider
)
from .filesystem import FileSystemManager
from .safety import SafetyGuard
from .context import ContextManager
from ..tools.executor import ToolExecutor, ExecutionResult


class HcodeAgent:
    """Main agent orchestrator for Hcode"""

    def __init__(
        self,
        anthropic_key: Optional[str] = None,
        openai_key: Optional[str] = None,
        root_dir: Optional[str] = None,
        preferences: Optional[ProviderPreferences] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize Hcode agent.

        Args:
            anthropic_key: Anthropic API key
            openai_key: OpenAI API key
            root_dir: Root directory for operations
            preferences: Provider preferences
            session_id: Session ID to resume
        """
        self.root_dir = Path(root_dir or Path.cwd())
        self.console = Console()

        # Initialize components
        self.provider_selector = ProviderSelector(
            anthropic_key=anthropic_key,
            openai_key=openai_key,
            preferences=preferences or ProviderPreferences()
        )

        self.file_manager = FileSystemManager(root_dir=str(self.root_dir))
        self.safety_guard = SafetyGuard(root_dir=str(self.root_dir))
        self.context_manager = ContextManager(root_dir=str(self.root_dir), session_id=session_id)
        self.tool_executor = ToolExecutor(root_dir=str(self.root_dir))

        self.current_provider: Optional[AIProvider] = None

    async def execute_task(
        self,
        task_description: str,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        task_type: TaskType = TaskType.CODE_GENERATION,
        stream: bool = True
    ) -> str:
        """
        Execute a coding task autonomously.

        Args:
            task_description: Natural language task description
            complexity: Task complexity level
            task_type: Type of task
            stream: Stream the response

        Returns:
            Final response from the agent
        """
        # Select appropriate provider
        self.current_provider = self.provider_selector.select_provider(
            complexity=complexity,
            task_type=task_type
        )

        self.console.print(f"[bold green]Using {self.current_provider}[/bold green]")

        # Set system prompt
        system_prompt = self.current_provider.get_system_prompt_for_coding()
        self.context_manager.set_system_prompt(system_prompt)

        # Add user task to context
        self.context_manager.add_message(
            role="user",
            content=task_description,
            importance=1.0,
            provider=self.current_provider
        )

        try:
            # Generate response
            if stream:
                response = await self._stream_response()
            else:
                response = await self._generate_response()

            # Add assistant response to context
            self.context_manager.add_message(
                role="assistant",
                content=response,
                importance=0.8,
                provider=self.current_provider
            )

            return response

        except Exception as e:
            # Try fallback provider if available
            fallback_provider = self.provider_selector.get_fallback_provider(self.current_provider)

            if fallback_provider:
                self.console.print(f"[yellow]Switching to fallback: {fallback_provider}[/yellow]")
                self.current_provider = fallback_provider

                # Retry with fallback
                if stream:
                    response = await self._stream_response()
                else:
                    response = await self._generate_response()

                self.context_manager.add_message(
                    role="assistant",
                    content=response,
                    importance=0.8,
                    provider=self.current_provider
                )

                return response
            else:
                raise e

    async def _generate_response(self) -> str:
        """Generate a non-streaming response"""
        messages = self.context_manager.get_messages(
            max_tokens=self.current_provider.get_context_window() - self.current_provider.max_tokens
        )

        result = await self.current_provider.generate_completion(
            messages=messages,
            stream=False
        )

        return result.content

    async def _stream_response(self) -> str:
        """Generate a streaming response"""
        messages = self.context_manager.get_messages(
            max_tokens=self.current_provider.get_context_window() - self.current_provider.max_tokens
        )

        stream = await self.current_provider.generate_completion(
            messages=messages,
            stream=True
        )

        response_parts = []

        self.console.print("[bold blue]Assistant:[/bold blue]")

        async for chunk in stream:
            response_parts.append(chunk)
            print(chunk, end="", flush=True)

        print()  # New line after streaming

        return "".join(response_parts)

    async def plan_approach(self, task: str) -> Dict[str, Any]:
        """
        Plan an approach for a complex task.

        Args:
            task: Task description

        Returns:
            Plan dictionary with steps
        """
        planning_prompt = f"""Analyze this task and create a detailed implementation plan:

Task: {task}

Please provide:
1. High-level approach
2. Step-by-step breakdown
3. Potential challenges
4. Required files/resources
5. Testing strategy

Format as a structured plan."""

        self.context_manager.add_message(
            role="user",
            content=planning_prompt,
            importance=1.0,
            provider=self.current_provider
        )

        response = await self._generate_response()

        self.context_manager.add_message(
            role="assistant",
            content=response,
            importance=1.0,
            provider=self.current_provider
        )

        return {
            "task": task,
            "plan": response,
            "complexity": TaskComplexity.COMPLEX,
        }

    async def implement_solution(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement a solution based on a plan.

        Args:
            plan: Plan dictionary

        Returns:
            Implementation results
        """
        # Start safety transaction
        tx_id = self.safety_guard.start_transaction(
            description=f"Implementing: {plan['task']}"
        )

        results = {
            "transaction_id": tx_id,
            "files_modified": [],
            "files_created": [],
            "tests_passed": False,
            "success": False
        }

        try:
            # Execute implementation (this would contain the actual implementation logic)
            implementation_prompt = f"""Based on this plan, implement the solution:

{plan['plan']}

Provide the complete implementation with all necessary code."""

            self.context_manager.add_message(
                role="user",
                content=implementation_prompt,
                importance=1.0,
                provider=self.current_provider
            )

            response = await self._generate_response()

            self.context_manager.add_message(
                role="assistant",
                content=response,
                importance=0.9,
                provider=self.current_provider
            )

            results["implementation"] = response
            results["success"] = True

            # Commit transaction
            self.safety_guard.commit_transaction()

        except Exception as e:
            # Rollback on failure
            self.safety_guard.rollback_transaction()
            results["error"] = str(e)
            results["success"] = False

        return results

    async def verify_solution(self, implementation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify an implementation by running tests.

        Args:
            implementation: Implementation results

        Returns:
            Verification results
        """
        results = {
            "tests_run": False,
            "tests_passed": False,
            "linter_passed": False,
            "errors": []
        }

        try:
            # Run tests
            test_result = await self.tool_executor.run_tests()
            results["tests_run"] = True
            results["tests_passed"] = test_result.success
            results["test_output"] = str(test_result)

            if not test_result.success:
                interpretation = self.tool_executor.interpret_output(test_result)
                results["errors"].extend(interpretation["errors"])

            # Run linter
            lint_result = await self.tool_executor.run_linter()
            results["linter_passed"] = lint_result.success
            results["lint_output"] = str(lint_result)

            if not lint_result.success:
                interpretation = self.tool_executor.interpret_output(lint_result)
                results["errors"].extend(interpretation["errors"])

        except Exception as e:
            results["errors"].append(str(e))

        return results

    async def analyze_code(self, file_path: Optional[str] = None) -> str:
        """
        Analyze code for issues and improvements.

        Args:
            file_path: Specific file to analyze (or entire project)

        Returns:
            Analysis results
        """
        if file_path:
            code = await self.file_manager.read_file(file_path)
            analysis_prompt = f"""Analyze this code for:
- Potential bugs
- Security vulnerabilities
- Performance issues
- Code quality improvements
- Best practice violations

File: {file_path}

```
{code}
```"""
        else:
            structure = self.file_manager.get_project_structure()
            analysis_prompt = f"""Analyze this project for:
- Architecture issues
- Code organization
- Dependency problems
- Testing coverage
- Documentation needs

Project structure:
{structure}"""

        self.context_manager.add_message(
            role="user",
            content=analysis_prompt,
            importance=0.8,
            provider=self.current_provider
        )

        response = await self._generate_response()

        self.context_manager.add_message(
            role="assistant",
            content=response,
            importance=0.7,
            provider=self.current_provider
        )

        return response

    async def debug_issue(self, error_description: str) -> str:
        """
        Debug an issue autonomously.

        Args:
            error_description: Description of the error

        Returns:
            Debug analysis and potential fixes
        """
        debug_prompt = f"""Debug this issue:

{error_description}

Please:
1. Identify the root cause
2. Explain why it's happening
3. Propose a fix
4. Suggest how to prevent similar issues"""

        self.context_manager.add_message(
            role="user",
            content=debug_prompt,
            importance=1.0,
            provider=self.current_provider
        )

        response = await self._generate_response()

        self.context_manager.add_message(
            role="assistant",
            content=response,
            importance=0.9,
            provider=self.current_provider
        )

        return response

    def get_session_stats(self) -> Dict:
        """Get statistics about the current session"""
        return {
            "context": self.context_manager.get_context_stats(),
            "provider": str(self.current_provider) if self.current_provider else "None",
            "total_cost": self.current_provider.total_cost if self.current_provider else 0,
            "available_providers": self.provider_selector.get_available_providers(),
        }

    def export_session(self, output_path: str):
        """Export current session to file"""
        self.context_manager.export_session(output_path)
        self.console.print(f"[green]Session exported to {output_path}[/green]")

    def switch_provider(self, provider_name: str):
        """
        Manually switch to a different provider.

        Args:
            provider_name: Provider name (anthropic or openai)
        """
        new_provider = self.provider_selector.get_provider_by_name(provider_name)

        if new_provider:
            self.current_provider = new_provider
            self.console.print(f"[green]Switched to {self.current_provider}[/green]")
        else:
            self.console.print(f"[red]Provider {provider_name} not available[/red]")
