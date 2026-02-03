"""
Verification phase handler.

Responsible for:
- Running tests to verify implementation
- Creating walkthrough.md documentation
- Validating implementation correctness
- Marking task as complete
"""

import re
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import List, Any, Dict, Optional
from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult
from hcode.config.core_prompts.core import CorePromptLoader

logger = logging.getLogger(__name__)


class VerificationPhaseHandler(BasePhaseHandler):
    """
    Handler for the Verification phase of PEV workflow.

    Creates:
    - .hcode/walkthrough.md: Documentation of what was implemented

    Actions:
    - Runs tests (pytest, npm test, etc.)
    - Validates implementation
    - Documents results

    Transition criteria:
    - Tests run (pass or fail documented)
    - walkthrough.md created with implementation summary
    - Agent confirms task is complete
    """

    phase_name = "verification"

    def get_required_artifacts(self) -> List[str]:
        """Get artifacts this phase should produce."""
        return ["walkthrough.md"]

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute verification phase.

        Steps:
        1. Run tests specified in implementation plan
        2. Collect test results
        3. Create walkthrough.md with:
           - What was implemented
           - Files modified
           - Test results
           - How to verify
        4. Mark task as complete

        Args:
            context: Current agent context
            loop_controller: Loop controller

        Returns:
            PhaseResult with verification outcome
        """
        try:
            # Load implementation plan to find test strategy
            plan_content = self.artifact_manager.load_artifact(
                "implementation_plan.md", context
            )

            # Run tests (if specified)
            test_results = await self._run_tests(context, plan_content)

            # Create walkthrough
            walkthrough_content = self._create_walkthrough(
                context, test_results
            )

            # Save walkthrough.md
            self.artifact_manager.create_artifact(
                "walkthrough.md",
                walkthrough_content,
                context
            )

            # Validate artifact
            valid, error = self.validate_artifacts(context)

            if not valid:
                return PhaseResult(
                    phase_name=self.phase_name,
                    success=False,
                    output=f"Verification validation failed: {error}",
                    artifacts_created=["walkthrough.md"],
                    can_transition=False,
                    error=error,
                )

            # Verification phase is terminal (can_transition = workflow complete)
            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output="Verification phase complete. Task is done.",
                artifacts_created=["walkthrough.md"],
                can_transition=True,  # True means workflow is complete
                metadata={
                    "test_results": test_results,
                    "modified_files": context.modified_files,
                }
            )

        except Exception as e:
            return PhaseResult(
                phase_name=self.phase_name,
                success=False,
                output=f"Verification phase failed: {str(e)}",
                can_transition=False,
                error=str(e),
            )

    async def _run_tests(
        self,
        context: AgentContext,
        plan_content: Optional[str]
    ) -> Dict[str, Any]:
        """
        Run tests specified in implementation plan.

        Parses the plan for test commands and executes them.

        Args:
            context: Current agent context
            plan_content: Implementation plan content

        Returns:
            Dict with test results including:
            - tests_run: bool
            - tests_passed: int
            - tests_failed: int
            - output: str
            - commands_executed: List[str]
        """
        results = {
            "tests_run": False,
            "tests_passed": 0,
            "tests_failed": 0,
            "output": "",
            "commands_executed": [],
        }

        # Extract test commands from plan
        test_commands = self._extract_test_commands(plan_content)

        if not test_commands:
            # Try to auto-detect test commands based on project structure
            test_commands = self._detect_test_commands(context)

        if not test_commands:
            results["output"] = "No test commands found in plan or project."
            return results

        # Execute each test command
        all_output = []
        total_passed = 0
        total_failed = 0

        for command in test_commands:
            logger.info(f"Running test command: {command}")
            results["commands_executed"].append(command)

            try:
                # Execute test command
                cmd_result = await self._execute_command(command, context.working_dir)
                all_output.append(f"$ {command}")
                all_output.append(cmd_result["output"])
                all_output.append("")

                # Parse test results from output
                passed, failed = self._parse_test_output(cmd_result["output"], command)
                total_passed += passed
                total_failed += failed

                if not cmd_result["success"]:
                    all_output.append(f"[Command exited with code {cmd_result['exit_code']}]")

            except Exception as e:
                logger.error(f"Failed to run test command '{command}': {e}")
                all_output.append(f"$ {command}")
                all_output.append(f"[Error: {e}]")
                all_output.append("")

        results["tests_run"] = len(results["commands_executed"]) > 0
        results["tests_passed"] = total_passed
        results["tests_failed"] = total_failed
        results["output"] = "\n".join(all_output)

        return results

    def _extract_test_commands(self, plan_content: Optional[str]) -> List[str]:
        """
        Extract test commands from implementation plan.

        Looks for patterns like:
        - Run tests: `pytest tests/`
        - Test with: `npm test`
        - Verify: `python -m pytest`

        Args:
            plan_content: Implementation plan content

        Returns:
            List of test commands
        """
        if not plan_content:
            return []

        commands = []

        # Pattern for backtick commands in testing sections
        test_section_pattern = r'(?:## Test|## Verification|## Testing)[^\n]*\n((?:.*\n)*?)(?:##|$)'
        test_sections = re.findall(test_section_pattern, plan_content, re.IGNORECASE)

        for section in test_sections:
            # Extract commands from backticks
            cmd_pattern = r'`([^`]+(?:pytest|npm test|python|jest|cargo test|go test|mvn test)[^`]*)`'
            cmds = re.findall(cmd_pattern, section, re.IGNORECASE)
            commands.extend(cmds)

        # Also look for explicit "Run:" or "Execute:" patterns
        run_pattern = r'(?:Run|Execute|Test|Verify):\s*`([^`]+)`'
        run_cmds = re.findall(run_pattern, plan_content, re.IGNORECASE)
        commands.extend(run_cmds)

        # Deduplicate while preserving order
        seen = set()
        unique_commands = []
        for cmd in commands:
            cmd = cmd.strip()
            if cmd and cmd not in seen:
                seen.add(cmd)
                unique_commands.append(cmd)

        return unique_commands

    def _detect_test_commands(self, context: AgentContext) -> List[str]:
        """
        Auto-detect test commands based on project structure.

        Args:
            context: Current agent context

        Returns:
            List of detected test commands
        """
        commands = []
        working_dir = Path(context.working_dir)

        # Python: pytest or unittest
        if (working_dir / "pytest.ini").exists() or \
           (working_dir / "pyproject.toml").exists() or \
           (working_dir / "tests").is_dir():
            commands.append("pytest --no-cov -v")

        # JavaScript/Node: npm test
        if (working_dir / "package.json").exists():
            commands.append("npm test")

        # Rust: cargo test
        if (working_dir / "Cargo.toml").exists():
            commands.append("cargo test")

        # Go: go test
        if (working_dir / "go.mod").exists():
            commands.append("go test ./...")

        return commands

    async def _execute_command(
        self,
        command: str,
        working_dir: str,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Execute a shell command and capture output.

        Args:
            command: Command to execute
            working_dir: Working directory
            timeout: Timeout in seconds

        Returns:
            Dict with success, exit_code, output
        """
        try:
            # Use asyncio subprocess for non-blocking execution
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                shell=True,
            )

            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                output = stdout.decode('utf-8', errors='replace')
                exit_code = process.returncode

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                output = f"[Command timed out after {timeout} seconds]"
                exit_code = -1

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "output": output,
            }

        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "output": f"[Failed to execute: {e}]",
            }

    def _parse_test_output(self, output: str, command: str) -> tuple:
        """
        Parse test output to extract pass/fail counts.

        Supports pytest, npm test, jest, and other common formats.

        Args:
            output: Test command output
            command: Original command (to determine parser)

        Returns:
            Tuple of (passed_count, failed_count)
        """
        passed = 0
        failed = 0

        # Pytest format: "5 passed, 2 failed"
        pytest_match = re.search(r'(\d+)\s+passed', output)
        if pytest_match:
            passed = int(pytest_match.group(1))

        pytest_failed = re.search(r'(\d+)\s+failed', output)
        if pytest_failed:
            failed = int(pytest_failed.group(1))

        # Jest format: "Tests: 5 passed, 2 failed"
        jest_match = re.search(r'Tests:\s*(\d+)\s+passed', output)
        if jest_match:
            passed = int(jest_match.group(1))

        jest_failed = re.search(r'Tests:.*?(\d+)\s+failed', output)
        if jest_failed:
            failed = int(jest_failed.group(1))

        # Go test format: "ok" or "FAIL"
        if 'go test' in command:
            passed = output.count('ok  ')
            failed = output.count('FAIL\t')

        # Rust/Cargo format: "test result: ok. 5 passed"
        cargo_match = re.search(r'(\d+)\s+passed[^;]*;', output)
        if cargo_match:
            passed = int(cargo_match.group(1))

        cargo_failed = re.search(r'(\d+)\s+failed', output)
        if cargo_failed:
            failed = int(cargo_failed.group(1))

        return passed, failed

    def _create_walkthrough(
        self,
        context: AgentContext,
        test_results: dict
    ) -> str:
        """
        Create walkthrough documentation.

        Args:
            context: Current agent context
            test_results: Results from test execution

        Returns:
            Walkthrough content
        """
        modified_files_section = "\n".join(
            f"- `{file}`" for file in context.modified_files
        ) if context.modified_files else "- No files were modified"

        test_section = self._format_test_results(test_results)
        changes_details = self._format_changes_details(context)

        loader = CorePromptLoader()
        return loader.build_walkthrough_md(
            task=context.task,
            modified_files_section=modified_files_section,
            changes_details=changes_details,
            test_section=test_section,
        )

    def _format_changes_details(self, context: AgentContext) -> str:
        """
        Format details about changes made.

        Args:
            context: Current agent context

        Returns:
            Formatted changes section
        """
        if not context.completed_actions:
            return "No detailed action history available."

        details = []
        for action in context.completed_actions[-10:]:  # Last 10 actions
            tool = action.get("tool", "unknown")
            success = action.get("success", False)
            status = "[OK]" if success else "[FAIL]"
            details.append(f"- {status} {tool}")

        return "\n".join(details)

    def _format_test_results(self, test_results: dict) -> str:
        """
        Format test results section.

        Args:
            test_results: Test execution results

        Returns:
            Formatted test results
        """
        if not test_results.get("tests_run"):
            return "Tests were not run during this implementation."

        passed = test_results.get("tests_passed", 0)
        failed = test_results.get("tests_failed", 0)
        output = test_results.get("output", "")

        status = "[OK] All tests passed" if failed == 0 else f"[FAIL] {failed} test(s) failed"

        return f"""### Test Summary

{status}

- Passed: {passed}
- Failed: {failed}

### Test Output

```
{output}
```
"""

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """
        Check if verification is complete.

        For verification phase, this means the workflow is complete.

        Args:
            context: Current agent context

        Returns:
            True if verification is done (task complete)
        """
        # Verification is terminal - if artifact exists, we're done
        return self.artifact_manager.artifact_exists("walkthrough.md", context)
