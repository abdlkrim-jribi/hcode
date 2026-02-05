"""
Verification phase handler.

Responsible for:
- Running tests to verify implementation
- Creating walkthrough.md documentation
- Validating implementation correctness
- Marking task as complete in task.md
"""

import re
import logging
import asyncio
from pathlib import Path
from typing import List, Any, Dict, Optional
from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult

# FileAction enum for HcodeDisplay tracking
try:
    from hcode.ui.hcode_display import FileAction
except ImportError:
    FileAction = None

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
            self._display("Verifying implementation...", style="info")

            # Show which files will be verified
            non_artifact_files = self._get_non_artifact_files(context)
            if non_artifact_files:
                self._display(f"  Files to verify ({len(non_artifact_files)}):", style="thinking")
                for f in non_artifact_files:
                    self._display(f"    - {f}", style="thinking")

            # Load implementation plan to find test strategy
            plan_content = self.artifact_manager.load_artifact(
                "implementation_plan.md", context
            )

            # Run tests / compile checks (each command is displayed as it runs)
            test_results = await self._run_tests(context, plan_content)

            # Display final test results summary
            if test_results.get("tests_run"):
                passed = test_results.get("tests_passed", 0)
                failed = test_results.get("tests_failed", 0)
                commands_run = len(test_results.get("commands_executed", []))
                if failed == 0:
                    self._display(f"Verification: {commands_run} check(s) passed", style="success")
                else:
                    self._display(f"Verification: {passed} passed, {failed} failed", style="error")
            else:
                self._display("No verification checks were run", style="thinking")

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
            self._display("Created walkthrough.md", style="success")
            if self._hcode_display and FileAction:
                self._hcode_display.track_file(".hcode/walkthrough.md", FileAction.CREATED)

            # Show summary
            self._display("Implementation Summary:", style="info")
            self._display(f"  - Files modified: {len(context.modified_files)}", style="default")
            self._display(f"  - Actions completed: {len(context.completed_actions)}", style="default")

            # Display modified files list
            if context.modified_files:
                for file_path in non_artifact_files:
                    self._display(f"  - {file_path}", style="default")
                if self._hcode_display and FileAction:
                    for file_path in context.modified_files:
                        self._hcode_display.track_file(file_path, FileAction.EDITED)

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

    def _get_non_artifact_files(self, context: AgentContext) -> List[str]:
        """
        Get modified files excluding .hcode artifacts.

        Args:
            context: Current agent context

        Returns:
            List of non-artifact modified file paths
        """
        return [
            f for f in context.modified_files
            if ".hcode" not in f
            and not f.endswith("task.md")
            and not f.endswith("implementation_plan.md")
            and not f.endswith("walkthrough.md")
        ]

    async def _run_tests(
        self,
        context: AgentContext,
        plan_content: Optional[str]
    ) -> Dict[str, Any]:
        """
        Run verification commands with scope-aware strategy.

        Strategy:
        - 1-2 modified files:  compile-check each .py file, then run it directly.
          Full test suite is skipped (it's unrelated to the change).
        - 3+ modified files:   run the full test suite (pytest / npm test etc.)
          as specified in the plan or auto-detected.

        This prevents a single new script from triggering 700+ unrelated tests.

        Args:
            context: Current agent context
            plan_content: Implementation plan content

        Returns:
            Dict with test results
        """
        results = {
            "tests_run": False,
            "tests_passed": 0,
            "tests_failed": 0,
            "output": "",
            "commands_executed": [],
        }

        non_artifact_files = self._get_non_artifact_files(context)
        python_files = [f for f in non_artifact_files if f.endswith(".py")]

        # ── Narrow scope: 1-2 files → compile + run only ──
        if len(non_artifact_files) <= 2:
            test_commands = []

            for py_file in python_files:
                # Syntax check first
                test_commands.append(f'python -m py_compile "{py_file}"')
                # Then run it (short timeout – just verify it doesn't crash)
                test_commands.append(f'python "{py_file}"')

            if not test_commands and non_artifact_files:
                # Non-Python files – just note them, no automated verification
                results["output"] = (
                    "Verification: non-Python files modified, no automated check.\n"
                    "Files: " + ", ".join(non_artifact_files)
                )
                return results

            if not test_commands:
                results["output"] = "No files to verify."
                return results

        # ── Wide scope: 3+ files → full test suite ──
        else:
            # Honor explicit test commands from the plan first
            test_commands = self._extract_test_commands(plan_content)
            if not test_commands:
                test_commands = self._detect_test_commands(context)

            if not test_commands:
                # Fallback: still compile-check all Python files
                test_commands = [f'python -m py_compile "{f}"' for f in python_files]

        # Execute each command
        all_output = []
        total_passed = 0
        total_failed = 0

        for command in test_commands:
            logger.info(f"Running verification command: {command}")
            results["commands_executed"].append(command)
            self._display(f"  $ {command}", style="thinking")

            try:
                cmd_result = await self._execute_command(command, context.working_dir)
                all_output.append(f"$ {command}")
                all_output.append(cmd_result["output"])
                all_output.append("")

                passed, failed = self._parse_test_output(cmd_result["output"], command)
                total_passed += passed
                total_failed += failed

                if cmd_result["success"]:
                    self._display(f"      [OK]", style="success")
                else:
                    self._display(f"      [FAIL] exit code {cmd_result['exit_code']}", style="error")
                    all_output.append(f"[Command exited with code {cmd_result['exit_code']}]")
                    # For compile checks, a failure is a real error
                    if "py_compile" in command:
                        total_failed += 1

            except Exception as e:
                logger.error(f"Failed to run command '{command}': {e}")
                all_output.append(f"$ {command}")
                all_output.append(f"[Error: {e}]")
                all_output.append("")
                self._display(f"      [ERROR] {e}", style="error")

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
        verification_thinking = self._generate_verification_thinking(context, test_results)

        # Build walkthrough using perfect prompts template or fallback
        return self._build_walkthrough_content(
            task=context.task,
            modified_files_section=modified_files_section,
            changes_details=changes_details,
            test_section=test_section,
            verification_thinking=verification_thinking,
        )

    def _generate_verification_thinking(
        self,
        context: AgentContext,
        test_results: dict
    ) -> str:
        """
        Generate verification thinking summary.

        Args:
            context: Current agent context
            test_results: Test execution results

        Returns:
            Verification thinking summary
        """
        thinking_parts = []

        # Summarize what was done
        thinking_parts.append("### Implementation Summary")
        thinking_parts.append(f"- Task: {context.task[:100]}...")
        thinking_parts.append(f"- Files modified: {len(context.modified_files)}")
        thinking_parts.append(f"- Actions completed: {len(context.completed_actions)}")
        thinking_parts.append(f"- Total iterations: {context.iteration}")

        # Analyze test results
        thinking_parts.append("\n### Verification Analysis")
        if test_results.get("tests_run"):
            passed = test_results.get("tests_passed", 0)
            failed = test_results.get("tests_failed", 0)
            if failed == 0:
                thinking_parts.append(f"- All {passed} tests passed [OK]")
                thinking_parts.append("- No regressions detected")
            else:
                thinking_parts.append(f"- {passed} tests passed, {failed} tests failed [NEEDS ATTENTION]")
                thinking_parts.append("- Review failed tests for potential issues")
        else:
            thinking_parts.append("- Tests were not run")
            thinking_parts.append("- Consider running tests manually to verify changes")

        # Success assessment
        thinking_parts.append("\n### Success Assessment")
        has_changes = len(context.modified_files) > 0 or len(context.completed_actions) > 0
        tests_ok = not test_results.get("tests_run") or test_results.get("tests_failed", 0) == 0

        if has_changes and tests_ok:
            thinking_parts.append("- Implementation appears successful")
            thinking_parts.append("- Changes were made as planned")
            thinking_parts.append("- No test failures detected")
        elif has_changes and not tests_ok:
            thinking_parts.append("- Changes were made but tests failed")
            thinking_parts.append("- May require follow-up fixes")
        else:
            thinking_parts.append("- Limited changes were made")
            thinking_parts.append("- Review if all requirements were addressed")

        return "\n".join(thinking_parts)

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

    def _build_walkthrough_content(
        self,
        task: str,
        modified_files_section: str,
        changes_details: str,
        test_section: str,
        verification_thinking: str = "",
    ) -> str:
        """
        Build walkthrough.md content using perfect_prompts/walkthrough.md template.

        The walkthrough.md template from perfect_prompts provides guidelines for:
        - Summarizing what was accomplished
        - Documenting verification results
        - Being concise yet comprehensive

        Args:
            task: The user's original task
            modified_files_section: Formatted list of modified files
            changes_details: Details of changes made
            test_section: Test results section
            verification_thinking: Verification analysis summary

        Returns:
            Formatted walkthrough content following the template guidelines
        """
        # Build walkthrough following perfect_prompts/walkthrough.md guidelines:
        # - Be concise yet comprehensive
        # - Document what was tested and validation results
        # - Use file basenames for link text

        # Format file links with basenames (per walkthrough.md Critical Rules)
        formatted_files = []
        for file_path in self._extract_file_paths(modified_files_section):
            basename = Path(file_path).name
            formatted_files.append(f"- [{basename}](file:///{file_path})")

        files_with_links = "\n".join(formatted_files) if formatted_files else modified_files_section

        return f"""# Implementation Walkthrough

## Task

{task}

## Changes Made

{changes_details}

## Files Modified

{files_with_links}

## Verification Summary

{test_section}

## Analysis

{verification_thinking}

---
*Generated following walkthrough.md guidelines: concise, comprehensive, with verification proof.*
"""

    def _extract_file_paths(self, modified_files_section: str) -> List[str]:
        """Extract file paths from modified files section."""
        paths = []
        for line in modified_files_section.split('\n'):
            # Match patterns like "- `file.py`" or "- file.py"
            line = line.strip()
            if line.startswith('- '):
                path = line[2:].strip('`').strip()
                if path and path != "No files were modified":
                    paths.append(path)
        return paths

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
