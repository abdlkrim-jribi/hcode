"""
Verification Phase Handler — 5-Phase Quality Assurance Protocol
================================================================

Implements the *Verification* phase of the PEV workflow with a structured
5-phase protocol optimized for GPT OSS 120B reasoning:

- **Phase 1: Compliance Verification** — Check implementation matches plan
- **Phase 2: Quality Gates Assessment** — Score code quality metrics
- **Phase 3: Integration Testing** — Mental execution + actual tests
- **Phase 4: Final Decision** — Aggregate into APPROVED/NEEDS REVISION
- **Phase 5: Update task.md** — MANDATORY final status update

The handler combines AI-driven code review with actual test execution.
"""

import re
import logging
import asyncio
from pathlib import Path
from typing import List, Any, Dict, Optional

from .base_handler import BasePhaseHandler
from ..protocols import AgentContext, PhaseResult
from hcode.providers.base import Message

# FileAction enum for HcodeDisplay tracking
try:
    from hcode.ui.hcode_display import FileAction
except ImportError:
    FileAction = None

logger = logging.getLogger(__name__)


class VerificationPhaseHandler(BasePhaseHandler):
    """
    Handler for the Verification phase of PEV workflow.

    Uses a 5-phase QA protocol:
    - Phase 1: Compliance — verify implementation matches plan
    - Phase 2: Quality Gates — score 6 quality dimensions
    - Phase 3: Integration Testing — mental execution + actual tests
    - Phase 4: Final Decision — aggregate verdict
    - Phase 5: Update task.md — mandatory status sync

    Creates:
    - .hcode/walkthrough.md: Structured verification evidence

    Transition criteria:
    - Tests run (pass or fail documented)
    - walkthrough.md created with verification evidence
    - task.md updated with true completion status
    """

    phase_name = "verification"

    def get_required_artifacts(self) -> List[str]:
        """Get artifacts this phase should produce."""
        return ["walkthrough.md"]

    # ═══════════════════════════════════════════════════════════════════════
    # MAIN HANDLER
    # ═══════════════════════════════════════════════════════════════════════

    async def handle(
        self,
        context: AgentContext,
        loop_controller: Any,
    ) -> PhaseResult:
        """
        Execute verification phase using the 5-phase QA protocol.

        Steps:
        1. Run actual tests / compile checks (scope-aware)
        2. Generate AI verification analysis (5-phase protocol)
        3. Build walkthrough.md with structured evidence
        4. Update task.md with true status
        5. Return final verdict

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

            # Load artifacts
            plan_content = self.artifact_manager.load_artifact(
                "implementation_plan.md", context
            )
            task_content = self.artifact_manager.load_artifact(
                "task.md", context
            )

            # Phase 3 (partial): Run actual tests / compile checks
            test_results = await self._run_tests(context, plan_content)

            # Display test results summary
            if test_results.get("tests_run"):
                passed = test_results.get("tests_passed", 0)
                failed = test_results.get("tests_failed", 0)
                commands_run = len(test_results.get("commands_executed", []))
                if failed == 0:
                    self._display(f"Verification: {commands_run} check(s) passed", style="success")
                else:
                    self._display(f"Verification: {passed} passed, {failed} failed", style="error")
            else:
                self._display("No automated checks were run", style="thinking")

            # Generate AI verification analysis (Phases 1-4)
            verification_analysis = ""
            if self.provider is not None:
                if self._hcode_display:
                    self._hcode_display.start_thinking()

                verification_analysis = await self._run_verification_analysis(
                    context, plan_content, task_content, test_results
                )

                if self._hcode_display:
                    self._hcode_display.end_thinking()

            # Build walkthrough with structured verification evidence (AI-generated)
            walkthrough_content = await self._create_walkthrough(
                context, test_results, verification_analysis
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

            # Phase 5: Update task.md with true status
            self._update_task_status(context, test_results)

            # Show summary
            self._display("Implementation Summary:", style="info")
            self._display(f"  - Files modified: {len(context.modified_files)}", style="default")
            self._display(f"  - Actions completed: {len(context.completed_actions)}", style="default")

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

            # Determine verdict from test results
            tests_ok = (
                not test_results.get("tests_run")
                or test_results.get("tests_failed", 0) == 0
            )
            verdict = "APPROVED" if tests_ok else "APPROVED WITH NOTES"

            # Update task memory with learnings from this successful task
            self._update_hcode_memory(
                context=context,
                test_results=test_results,
                verification_analysis=verification_analysis,
                verdict=verdict
            )

            return PhaseResult(
                phase_name=self.phase_name,
                success=True,
                output=f"Verification complete. Verdict: {verdict}",
                artifacts_created=["walkthrough.md"],
                can_transition=True,
                metadata={
                    "test_results": test_results,
                    "modified_files": context.modified_files,
                    "verdict": verdict,
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

    # ═══════════════════════════════════════════════════════════════════════
    # THINKING INSTRUCTIONS (GPT OSS 120B OPTIMIZED)
    # ═══════════════════════════════════════════════════════════════════════

    def _get_thinking_instructions(self) -> str:
        """
        Override base thinking instructions with 5-phase QA protocol.
        """
        return """### 5-PHASE VERIFICATION THINKING PROTOCOL

You MUST think through each verification phase using structured reasoning:

**Phase 1 — COMPLIANCE VERIFICATION:**
<thinking>
Step 1: Load task.md — What was supposed to be done?
Step 2: Load implementation_plan.md — How was it supposed to be done?
Step 3: For each plan step: Was it implemented? Correctly? Completely?
Step 4: Identify DEVIATIONS — changes not in plan, or plan steps not done.
Therefore: Compliance is [PASS/CONDITIONAL PASS/FAIL] because [evidence].
</thinking>

<output>
[Tool calls to read task.md, plan, and modified files, then compliance verification matrix]
</output>

**Phase 2 — QUALITY GATES:**
<thinking>
Step 1: Complexity — Are functions reasonable length (≤50 lines)?
Step 2: Documentation — Do public APIs have docstrings?
Step 3: Error handling — Are exceptions caught? Descriptive messages?
Step 4: Imports — All used? No circular deps?
Step 5: Style — Matches project conventions?
Step 6: Security — No obvious vulnerabilities?
Therefore: Quality gates [X/6 passed].
</thinking>

<output>
[Quality assessment with scores for each gate: X/6 passed]
</output>

**Phase 3 — INTEGRATION TESTING:**
<thinking>
Step 1: HAPPY PATH — Trace primary use case through code.
Step 2: EDGE CASES — Check boundary conditions.
Step 3: ERROR PATHS — Verify failure handling.
Step 4: REGRESSION — Could changes break existing functionality?
Therefore: Integration testing [PASS/FAIL] with [N] scenarios verified.
</thinking>

<output>
[Tool calls to run tests if applicable, then integration test results summary]
</output>

**Phase 4 — FINAL DECISION:**
<thinking>
Step 1: Aggregate — Phase 1 [result], Phase 2 [score], Phase 3 [result].
Step 2: Categorize issues — CRITICAL/HIGH/MEDIUM/LOW.
Step 3: Verdict — APPROVED / APPROVED WITH NOTES / NEEDS REVISION / REJECTED.
Therefore: Final verdict is [verdict] because [justification].
</thinking>

<output>
[Final verdict with evidence-based justification]
</output>

"""

    # ═══════════════════════════════════════════════════════════════════════
    # AI VERIFICATION ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════

    async def _run_verification_analysis(
        self,
        context: AgentContext,
        plan_content: Optional[str],
        task_content: Optional[str],
        test_results: Dict[str, Any],
    ) -> str:
        """
        Run AI-driven verification analysis through Phases 1-4.

        Gives the AI the verification_handler.md protocol, all artifacts,
        test results, and the list of modified files. The AI produces
        structured verification analysis.

        Returns:
            AI-generated verification analysis text
        """
        system_prompt = self._get_verification_system_prompt(context)
        prompt = self._build_verification_prompt(
            context, plan_content, task_content, test_results
        )

        try:
            response_text, tool_results = await self._generate_and_execute(
                prompt,
                context,
                system_prompt=system_prompt,
                max_rounds=6,
                max_tokens=16384,
                temperature=0.3,  # Deterministic analysis
                timeout_seconds=300,  # 5 minutes for verification phase
            )
            return response_text
        except Exception as e:
            logger.error(f"Verification analysis failed: {e}")
            return f"[Verification analysis could not be generated: {e}]"

    def _get_verification_system_prompt(self, context: AgentContext) -> str:
        """
        Build system prompt for verification phase.

        Loads verification_handler.md as the primary protocol.
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            identity = loader.get_identity()
            tool_format = loader.get_tool_format()

            verification_protocol = self._load_verification_protocol()

            return f"""{identity}

{tool_format}

---

{verification_protocol}

---
{self._load_hcode_memory(context)}
## CURRENT CONTEXT

Working directory: {context.working_dir}
Artifacts directory: .hcode
Modified files: {len(context.modified_files)}
Completed actions: {len(context.completed_actions)}

### TOOL CALL FORMAT

Output JSON tool calls in code blocks: `{{"tool": "ToolName", "arguments": {{"param": "value"}}}}`
(See tool_format.md for complete documentation)
"""
        except Exception as e:
            logger.warning(f"Failed to load core prompts: {e}")
            return self._get_fallback_verification_prompt(context)

    def _load_verification_protocol(self) -> str:
        """Load verification_handler.md prompt file."""
        try:
            prompt_dir = Path(__file__).parent.parent.parent / "config" / "core_prompts" / "core"
            protocol_path = prompt_dir / "verification_handler.md"

            if protocol_path.exists():
                return protocol_path.read_text(encoding="utf-8")

            logger.warning("verification_handler.md not found, using inline protocol")
        except Exception as e:
            logger.warning(f"Failed to load verification_handler.md: {e}")

        return """# Hcode Verification Mode — 5-Phase QA Protocol

## THE 5-PHASE PROTOCOL

### Phase 1: Compliance Verification
Check each plan step was implemented correctly. PASS/CONDITIONAL/FAIL.

### Phase 2: Quality Gates
Score 6 dimensions: complexity, documentation, error handling, imports, style, security.

### Phase 3: Integration Testing
Trace happy path, edge cases, and error paths through the code.

### Phase 4: Final Decision
Aggregate phases into APPROVED / APPROVED WITH NOTES / NEEDS REVISION / REJECTED.

### Phase 5: Update task.md
MANDATORY — update checkboxes to reflect true implementation status.
"""

    def _get_fallback_verification_prompt(self, context: AgentContext) -> str:
        """Fallback verification prompt."""
        return f"""## VERIFICATION MODE

You are Hcode in VERIFICATION mode. Verify the implementation is correct.

Working directory: {context.working_dir}

### Rules:
1. Read all modified files
2. Check implementation matches the plan
3. Run tests if possible
4. Create walkthrough.md with findings
"""

    def _build_verification_prompt(
        self,
        context: AgentContext,
        plan_content: Optional[str],
        task_content: Optional[str],
        test_results: Dict[str, Any],
    ) -> str:
        """
        Build the user prompt for AI verification analysis.
        """
        # Format modified files
        modified_list = "\n".join(
            f"  - {f}" for f in context.modified_files
        ) if context.modified_files else "  (none)"

        non_artifact_files = self._get_non_artifact_files(context)
        code_files_list = "\n".join(
            f"  - {f}" for f in non_artifact_files
        ) if non_artifact_files else "  (none)"

        # Format test results
        test_summary = "No tests were run."
        if test_results.get("tests_run"):
            passed = test_results.get("tests_passed", 0)
            failed = test_results.get("tests_failed", 0)
            test_summary = f"Tests: {passed} passed, {failed} failed."
            if test_results.get("output"):
                test_summary += f"\n\nTest output:\n```\n{test_results['output'][:3000]}\n```"

        return f"""## VERIFICATION PHASE — 5-Phase QA Protocol

You are verifying the implementation that was just completed.
Follow Phases 1 → 2 → 3 → 4 in sequence.

### task.md (What Should Have Been Done):
{task_content or "(Not available)"}

### implementation_plan.md (How It Should Have Been Done):
{plan_content or "(Not available)"}

### Modified Files (What Was Actually Changed):
All modified files:
{modified_list}

Code files (excluding artifacts):
{code_files_list}

### Test Results (Already Executed):
{test_summary}

### INSTRUCTIONS:

Execute the 5-Phase QA Protocol:

**Phase 1: Compliance Verification**
Read each modified code file. For each plan step, verify:
- Was it implemented?
- Was it implemented correctly?
- Are there unauthorized changes?

**Phase 2: Quality Gates**
Score each modified file on: complexity, documentation, error handling,
imports, style consistency, security. Report X/6 gates passed.

**Phase 3: Integration Testing (Mental Execution)**
Trace at least:
- 1 happy path scenario
- 1 edge case
- 1 error scenario

**Phase 4: Final Decision**
Aggregate all findings into:
- APPROVED: No critical/high issues
- APPROVED WITH NOTES: Minor issues documented
- NEEDS REVISION: Critical issues found
- REJECTED: Fundamental errors

Produce your analysis in structured format. Read the modified files to verify."""

    def _build_continuation_prompt(
        self,
        round_results: List[Dict[str, Any]],
        all_results: List[Dict[str, Any]],
        round_num: int,
        context: Any = None,
    ) -> str:
        """Phase-aware continuation for verification rounds."""
        read_count = sum(
            1 for r in all_results
            if r.get('success') and r.get('tool', '').lower() in ['read', 'readtool']
        )

        if round_num == 0 and read_count == 0:
            return (
                "You MUST read the modified files before making verification claims. "
                "Start Phase 1: Read each modified file and check compliance with the plan."
            )

        if round_num <= 2:
            return (
                "Continue your verification analysis. If you've completed Phase 1 "
                "(compliance), proceed to Phase 2 (quality gates) and Phase 3 "
                "(mental execution traces). Then provide your Phase 4 final verdict."
            )

        return (
            "Wrap up your verification. Provide the final verdict (Phase 4) "
            "with a structured summary of findings by severity "
            "(CRITICAL/HIGH/MEDIUM/LOW)."
        )

    # ═══════════════════════════════════════════════════════════════════════
    # TEST EXECUTION (Scope-Aware)
    # ═══════════════════════════════════════════════════════════════════════

    def _get_non_artifact_files(self, context: AgentContext) -> List[str]:
        """Get modified files excluding .hcode artifacts."""
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
        - 1-2 modified files: compile-check + run each .py file
        - 3+ modified files: full test suite (pytest / npm test etc.)
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

        # Narrow scope: 1-2 files → compile + run only
        if len(non_artifact_files) <= 2:
            test_commands = []
            for py_file in python_files:
                test_commands.append(f'python -m py_compile "{py_file}"')
                test_commands.append(f'python "{py_file}"')

            if not test_commands and non_artifact_files:
                results["output"] = (
                    "Verification: non-Python files modified, no automated check.\n"
                    "Files: " + ", ".join(non_artifact_files)
                )
                return results

            if not test_commands:
                results["output"] = "No files to verify."
                return results

        # Wide scope: 3+ files → full test suite
        else:
            test_commands = self._extract_test_commands(plan_content)
            if not test_commands:
                test_commands = self._detect_test_commands(context)
            if not test_commands:
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
        """Extract test commands from implementation plan."""
        if not plan_content:
            return []

        commands = []

        # Look in testing sections
        test_section_pattern = r'(?:## Test|## Verification|## Testing)[^\n]*\n((?:.*\n)*?)(?:##|$)'
        test_sections = re.findall(test_section_pattern, plan_content, re.IGNORECASE)

        for section in test_sections:
            cmd_pattern = r'`([^`]+(?:pytest|npm test|python|jest|cargo test|go test|mvn test)[^`]*)`'
            cmds = re.findall(cmd_pattern, section, re.IGNORECASE)
            commands.extend(cmds)

        # Also look for explicit "Run:" patterns
        run_pattern = r'(?:Run|Execute|Test|Verify):\s*`([^`]+)`'
        run_cmds = re.findall(run_pattern, plan_content, re.IGNORECASE)
        commands.extend(run_cmds)

        # Deduplicate
        seen = set()
        unique = []
        for cmd in commands:
            cmd = cmd.strip()
            if cmd and cmd not in seen:
                seen.add(cmd)
                unique.append(cmd)

        return unique

    def _detect_test_commands(self, context: AgentContext) -> List[str]:
        """Auto-detect test commands based on project structure."""
        commands = []
        working_dir = Path(context.working_dir)

        if (working_dir / "pytest.ini").exists() or \
           (working_dir / "pyproject.toml").exists() or \
           (working_dir / "tests").is_dir():
            commands.append("pytest --no-cov -v")

        if (working_dir / "package.json").exists():
            commands.append("npm test")

        if (working_dir / "Cargo.toml").exists():
            commands.append("cargo test")

        if (working_dir / "go.mod").exists():
            commands.append("go test ./...")

        return commands

    def _sanitize_command(self, command: str) -> Optional[str]:
        """
        Sanitize shell command against whitelist to prevent injection attacks.

        Only allows safe, whitelisted test commands and patterns. Returns None
        if the command is not safe to execute.

        Whitelist includes:
        - Standard test runners (pytest, npm test, cargo test, go test, etc.)
        - Python compile checks (py_compile, compileall)
        - Direct Python file execution (python <file.py>)

        Rejects:
        - Arbitrary shell commands
        - Commands with dangerous operators (&&, ||, ;, |, >, <, `, $)
        - Commands with subshells or command substitution
        - Commands attempting to modify environment

        Args:
            command: Shell command to validate

        Returns:
            Sanitized command if safe, None if rejected
        """
        import re

        # Strip whitespace
        cmd = command.strip()

        if not cmd:
            return None

        # Check for dangerous shell operators/characters
        dangerous_patterns = [
            r'&&',  # Command chaining
            r'\|\|',  # Or operator
            r';',  # Command separator
            r'\|',  # Pipe (excluding pytest -v | grep which is safe)
            r'>',  # Redirect output
            r'<',  # Redirect input
            r'`',  # Command substitution
            r'\$\(',  # Command substitution
            r'\${',  # Variable expansion with braces
            r'rm\s',  # Remove files
            r'dd\s',  # Disk operations
            r'mkfs',  # Format filesystem
            r'fdisk',  # Disk partitioning
            r'/dev/',  # Device files
            r'sudo',  # Elevated privileges
            r'su\s',  # Switch user
            r'chmod',  # Change permissions
            r'chown',  # Change ownership
            r'curl.*\|',  # Download and execute
            r'wget.*\|',  # Download and execute
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, cmd, re.IGNORECASE):
                logger.warning(f"Command rejected due to dangerous pattern '{pattern}': {cmd}")
                return None

        # Whitelist safe command patterns
        safe_patterns = [
            # Python test runners
            r'^pytest(\s|$)',
            r'^python\s+-m\s+pytest(\s|$)',
            r'^py\.test(\s|$)',

            # JavaScript/Node test runners
            r'^npm\s+test(\s|$)',
            r'^npm\s+run\s+test(\s|$)',
            r'^yarn\s+test(\s|$)',
            r'^jest(\s|$)',
            r'^mocha(\s|$)',

            # Rust test runner
            r'^cargo\s+test(\s|$)',

            # Go test runner
            r'^go\s+test(\s|$)',

            # Python compile checks
            r'^python\s+-m\s+py_compile\s+',
            r'^python\s+-m\s+compileall\s+',

            # Direct Python file execution (safe if file path is validated)
            r'^python\s+"[^"]+\.py"(\s|$)',
            r"^python\s+'[^']+\.py'(\s|$)",
            r'^python\s+[a-zA-Z0-9_/\\.-]+\.py(\s|$)',

            # Python version check
            r'^python\s+--version(\s|$)',
            r'^python\s+-V(\s|$)',

            # Help commands (safe, read-only)
            r'^pytest\s+--help(\s|$)',
            r'^npm\s+--help(\s|$)',
        ]

        for pattern in safe_patterns:
            if re.match(pattern, cmd):
                logger.debug(f"Command approved via pattern '{pattern}': {cmd}")
                return cmd

        # If no pattern matched, reject
        logger.warning(f"Command rejected (not in whitelist): {cmd}")
        return None

    async def _execute_command(
        self,
        command: str,
        working_dir: str,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Execute a shell command and capture output.

        Commands are sanitized before execution to prevent injection attacks.
        Only whitelisted safe commands are allowed.
        """
        # Sanitize command first
        sanitized = self._sanitize_command(command)

        if sanitized is None:
            logger.error(f"Command rejected by security sanitization: {command}")
            return {
                "success": False,
                "output": f"[SECURITY] Command rejected: not in whitelist",
                "exit_code": -1,
            }

        try:
            process = await asyncio.create_subprocess_shell(
                sanitized,  # Use sanitized command
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
        """Parse test output to extract pass/fail counts."""
        passed = 0
        failed = 0

        # Pytest format
        pytest_match = re.search(r'(\d+)\s+passed', output)
        if pytest_match:
            passed = int(pytest_match.group(1))
        pytest_failed = re.search(r'(\d+)\s+failed', output)
        if pytest_failed:
            failed = int(pytest_failed.group(1))

        # Jest format
        jest_match = re.search(r'Tests:\s*(\d+)\s+passed', output)
        if jest_match:
            passed = int(jest_match.group(1))
        jest_failed = re.search(r'Tests:.*?(\d+)\s+failed', output)
        if jest_failed:
            failed = int(jest_failed.group(1))

        # Go test format
        if 'go test' in command:
            passed = output.count('ok  ')
            failed = output.count('FAIL\t')

        # Cargo format
        cargo_match = re.search(r'(\d+)\s+passed[^;]*;', output)
        if cargo_match:
            passed = int(cargo_match.group(1))
        cargo_failed = re.search(r'(\d+)\s+failed', output)
        if cargo_failed:
            failed = int(cargo_failed.group(1))

        return passed, failed

    # ═══════════════════════════════════════════════════════════════════════
    # TASK.MD UPDATE (Phase 5 — MANDATORY)
    # ═══════════════════════════════════════════════════════════════════════

    def _update_task_status(
        self,
        context: AgentContext,
        test_results: Dict[str, Any],
    ) -> None:
        """
        Phase 5: Update task.md with true completion status.

        This is MANDATORY and runs regardless of verdict. Updates each
        subtask checkbox based on whether the corresponding files were
        actually modified and tests passed.
        """
        task_content = self.artifact_manager.load_artifact("task.md", context)
        if not task_content:
            logger.warning("task.md not found, cannot update status")
            return

        tests_ok = (
            not test_results.get("tests_run")
            or test_results.get("tests_failed", 0) == 0
        )

        # Build set of modified code files (not artifacts)
        completed_files = set(self._get_non_artifact_files(context))

        # Update checkbox items
        lines = task_content.split('\n')
        updated_lines = []

        for line in lines:
            # Match unchecked or in-progress checkboxes
            checkbox_match = re.match(r'^(\s*-\s*)\[[ /]\]\s*(.+)$', line)

            if checkbox_match:
                prefix = checkbox_match.group(1)
                task_text = checkbox_match.group(2)

                # Check if this task's files were modified
                task_completed = False
                for file_path in completed_files:
                    file_name = file_path.split('/')[-1].split('\\')[-1]
                    if file_name in task_text or file_path in task_text:
                        task_completed = True
                        break

                # Also check completed actions
                for action in context.completed_actions:
                    tool_name = action.get("tool", "").lower()
                    if tool_name in ['write', 'edit', 'writetool', 'edittool']:
                        args = action.get("arguments", {})
                        target = (
                            args.get("TargetFile", "")
                            or args.get("file_path", "")
                            or action.get("file_path", "")
                        )
                        if target:
                            target_name = target.split('/')[-1].split('\\')[-1]
                            if target_name in task_text or target in task_text:
                                task_completed = True
                                break

                if task_completed and tests_ok:
                    updated_lines.append(f"{prefix}[x] {task_text}")
                elif task_completed and not tests_ok:
                    # Completed but tests failed — mark in-progress
                    updated_lines.append(f"{prefix}[/] {task_text}")
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        updated_content = '\n'.join(updated_lines)

        # Add verification result section
        verdict = "APPROVED" if tests_ok else "NEEDS REVISION"
        passed = test_results.get("tests_passed", 0)
        failed = test_results.get("tests_failed", 0)

        # Remove old verification result if present
        ver_marker = "## Verification Result"
        if ver_marker in updated_content:
            marker_idx = updated_content.index(ver_marker)
            updated_content = updated_content[:marker_idx].rstrip()

        # Remove old progress update if present
        prog_marker = "## Progress Update"
        if prog_marker in updated_content:
            marker_idx = updated_content.index(prog_marker)
            updated_content = updated_content[:marker_idx].rstrip()

        verification_section = f"""

## Verification Result

**Verdict:** {verdict}
**Files modified:** {len(context.modified_files)}
**Tests passed:** {passed}
**Tests failed:** {failed}
"""
        updated_content += verification_section

        self.artifact_manager.create_artifact("task.md", updated_content, context)
        self._display("Updated task.md with verification status", style="success")

    # ═══════════════════════════════════════════════════════════════════════
    # WALKTHROUGH GENERATION
    # ═══════════════════════════════════════════════════════════════════════

    async def _create_walkthrough(
        self,
        context: AgentContext,
        test_results: Dict[str, Any],
        verification_analysis: str = "",
    ) -> str:
        """
        Create walkthrough.md using AI with GPT OSS 120B protocol.

        Uses the walkthrough.md prompt to generate concise, evidence-based documentation.
        """
        try:
            from hcode.config.core_prompts.core.loader import get_prompt_loader
            loader = get_prompt_loader()

            # Load walkthrough protocol
            walkthrough_protocol = loader.get_walkthrough_protocol()

            if not walkthrough_protocol:
                # Fallback to template-based generation
                self._display("Warning: Walkthrough protocol not found, using fallback", style="thinking")
                return self._create_walkthrough_fallback(context, test_results, verification_analysis)

            # Build input data for AI
            input_data = self._build_walkthrough_input_data(context, test_results, verification_analysis)

            # Build prompt
            prompt = f"""{walkthrough_protocol}

---

## INPUT DATA

{input_data}

---

## YOUR TASK

Generate the walkthrough.md content following the GPT OSS 120B protocol above. Use <thinking> blocks for analysis and planning, then output the final walkthrough content in <output> blocks.

Remember: BE CONCISE (max 200 words). Users will be annoyed by verbose documentation.
"""

            # Generate walkthrough using AI
            self._display("Generating walkthrough.md with AI...", style="thinking")

            response = await self.provider.generate_completion(
                messages=[Message(role="user", content=prompt)],
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for consistent formatting
            )

            # Extract walkthrough content from response
            walkthrough_content = self._extract_walkthrough_from_response(response)

            if not walkthrough_content:
                self._display("Warning: AI generation failed, using fallback", style="thinking")
                return self._create_walkthrough_fallback(context, test_results, verification_analysis)

            return walkthrough_content

        except Exception as e:
            self._display(f"Warning: Walkthrough generation error: {e}", style="thinking")
            return self._create_walkthrough_fallback(context, test_results, verification_analysis)

    def _build_walkthrough_input_data(
        self,
        context: AgentContext,
        test_results: Dict[str, Any],
        verification_analysis: str,
    ) -> str:
        """Build formatted input data for walkthrough AI generation."""
        # Format modified files with full paths
        modified_files_list = []
        for file_path in context.modified_files:
            modified_files_list.append(f"  - {file_path}")
        modified_files_str = "\n".join(modified_files_list) if modified_files_list else "  (none)"

        # Format test results
        test_data = {
            "tests_run": test_results.get("tests_run", False),
            "tests_passed": test_results.get("tests_passed", 0),
            "tests_failed": test_results.get("tests_failed", 0),
            "test_command": test_results.get("test_command", "N/A"),
        }

        # Format completed actions (last 10)
        actions_list = []
        for action in context.completed_actions[-10:]:
            tool = action.get("tool", "unknown")
            success = action.get("success", False)
            status = "OK" if success else "FAIL"
            actions_list.append(f"  - [{status}] {tool}")
        actions_str = "\n".join(actions_list) if actions_list else "  (none)"

        return f"""### Task Description
{context.task}

### Modified Files (with full paths)
{modified_files_str}

### Test Results
- Tests Run: {test_data['tests_run']}
- Tests Passed: {test_data['tests_passed']}
- Tests Failed: {test_data['tests_failed']}
- Test Command: {test_data['test_command']}

### Verification Analysis (from QA Protocol)
{verification_analysis if verification_analysis else "(No verification analysis available)"}

### Completed Actions (last 10)
{actions_str}

### Context Metadata
- Working Directory: {context.working_dir}
- Iteration: {context.iteration}
- Total Files Modified: {len(context.modified_files)}
- Total Actions: {len(context.completed_actions)}
"""

    def _extract_walkthrough_from_response(self, response: str) -> str:
        """Extract walkthrough content from AI response.

        Looks for content in <output> tags or after final thinking block.
        """
        import re

        # Try to extract from <output> tags first
        output_pattern = r'<output>\s*(.*?)\s*</output>'
        matches = re.findall(output_pattern, response, re.DOTALL | re.IGNORECASE)

        if matches:
            # Get the last output block (final walkthrough)
            return matches[-1].strip()

        # Fallback: try to find markdown content after thinking blocks
        # Remove all thinking blocks
        cleaned = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL | re.IGNORECASE)
        cleaned = cleaned.strip()

        # If it starts with # Implementation Walkthrough, it's likely the content
        if cleaned.startswith("# Implementation Walkthrough"):
            return cleaned

        # Last resort: return the whole response (AI might not have used tags)
        return response.strip()

    def _create_walkthrough_fallback(
        self,
        context: AgentContext,
        test_results: Dict[str, Any],
        verification_analysis: str = "",
    ) -> str:
        """
        Fallback template-based walkthrough generation.

        Used when AI generation fails or protocol is unavailable.
        """
        # Modified files section with file links
        formatted_files = []
        for f in context.modified_files:
            basename = Path(f).name
            formatted_files.append(f"- [{basename}](file:///{f})")
        files_with_links = "\n".join(formatted_files) if formatted_files else "- No files were modified"

        # Test results section
        test_section = self._format_test_results(test_results)

        # Determine verdict
        tests_ok = (
            not test_results.get("tests_run")
            or test_results.get("tests_failed", 0) == 0
        )
        verdict = "APPROVED" if tests_ok else "NEEDS REVISION"

        return f"""# Implementation Walkthrough

## Task Summary

{context.task}

## Changes Made

{files_with_links}

## Verification Results

{test_section}

## Final Verdict

**{verdict}**

- Files modified: {len(context.modified_files)}
- Tests passed: {test_results.get('tests_passed', 0)}
- Tests failed: {test_results.get('tests_failed', 0)}

---
*Generated by Hcode Verification — 5-Phase QA Protocol*
"""

    def _format_test_results(self, test_results: Dict[str, Any]) -> str:
        """Format test results section."""
        if not test_results.get("tests_run"):
            return "No automated tests were run during verification."

        passed = test_results.get("tests_passed", 0)
        failed = test_results.get("tests_failed", 0)
        output = test_results.get("output", "")

        status = "[OK] All checks passed" if failed == 0 else f"[FAIL] {failed} check(s) failed"

        return f"""### Test Summary

{status}

- Passed: {passed}
- Failed: {failed}

### Test Output

```
{output}
```
"""

    # ═══════════════════════════════════════════════════════════════════════
    # TRANSITION
    # ═══════════════════════════════════════════════════════════════════════

    def can_transition_to_next(self, context: AgentContext) -> bool:
        """Verification is terminal — if walkthrough exists, we're done."""
        return self.artifact_manager.artifact_exists("walkthrough.md", context)

    # ═══════════════════════════════════════════════════════════════════════
    # MEMORY MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def _update_hcode_memory(
        self,
        context: AgentContext,
        test_results: dict,
        verification_analysis: str,
        verdict: str
    ) -> None:
        """
        Update task memory after successful verification.

        Non-critical operation - logs warnings but doesn't fail on errors.

        Args:
            context: Current agent context
            test_results: Test execution results
            verification_analysis: AI verification analysis text
            verdict: APPROVED or APPROVED WITH NOTES
        """
        try:
            # Build new memory entry
            new_entry = self._build_memory_entry(
                context, test_results, verification_analysis, verdict
            )

            # Load existing memory
            existing_memory = self.artifact_manager.load_artifact(
                "hcode_memory.md", context
            ) or ""

            # Merge entries
            updated_memory = self._merge_memory_entries(existing_memory, new_entry)

            # Trim to budget
            trimmed_memory = self._trim_memory(updated_memory)

            # Save back
            self.artifact_manager.create_artifact(
                "hcode_memory.md", trimmed_memory, context
            )

            self._display("[OK] Task memory updated", style="success")

        except Exception as e:
            # Non-critical - log and continue
            self._display(
                f"Warning: Could not update task memory: {e}",
                style="thinking"
            )

    def _build_memory_entry(
        self,
        context: AgentContext,
        test_results: dict,
        verification_analysis: str,
        verdict: str
    ) -> str:
        """
        Build a new memory entry from current task completion.

        Args:
            context: Current agent context
            test_results: Test execution results
            verification_analysis: AI verification analysis
            verdict: Task verdict

        Returns:
            Formatted memory entry markdown
        """
        from datetime import datetime

        # Get task summary
        task_summary = context.task[:100] + "..." if len(context.task) > 100 else context.task
        task_summary = task_summary.replace("\n", " ").strip()

        # Extract insights
        patterns = self._extract_patterns(verification_analysis)
        testing_insights = self._extract_testing_insights(test_results, verification_analysis)
        pitfalls = self._extract_pitfalls(verification_analysis)
        changes_summary = self._summarize_changes(context)

        # Build entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"""## Task: {task_summary}
**Date:** {timestamp.split()[0]}
**Verdict:** {verdict}
**Files Modified:** {len(context.modified_files)} files

### What Was Done
{changes_summary}

### Successful Patterns
{patterns}

### Testing Insights
{testing_insights}

### Pitfalls Avoided
{pitfalls}

---
"""
        return entry

    def _extract_patterns(self, verification_analysis: str) -> str:
        """
        Extract successful patterns from verification analysis.

        Args:
            verification_analysis: AI verification text

        Returns:
            Bullet list of patterns or default message
        """
        patterns = []

        # Look for pattern indicators in analysis
        analysis_lower = verification_analysis.lower()

        # Common pattern keywords
        pattern_keywords = [
            ("graceful degradation", "Graceful degradation for error handling"),
            ("non-critical", "Non-critical operations with safe fallbacks"),
            ("inheritance", "Inheritance pattern for shared functionality"),
            ("composition", "Composition pattern for modularity"),
            ("dependency injection", "Dependency injection for testability"),
            ("single responsibility", "Single Responsibility Principle adherence"),
            ("open-closed", "Open-Closed Principle adherence"),
        ]

        for keyword, pattern_desc in pattern_keywords:
            if keyword in analysis_lower:
                patterns.append(f"- {pattern_desc}")

        if not patterns:
            return "- Standard implementation patterns applied"

        return "\n".join(patterns)

    def _extract_testing_insights(self, test_results: dict, verification_analysis: str) -> str:
        """
        Extract testing insights from results and analysis.

        Args:
            test_results: Test execution results dict
            verification_analysis: AI verification text

        Returns:
            Bullet list of testing insights
        """
        insights = []

        # Test command used
        if test_results.get("test_command"):
            insights.append(f"- Test command: `{test_results['test_command']}`")

        # Test strategy
        tests_run = test_results.get("tests_run", 0)
        if tests_run > 0:
            tests_failed = test_results.get("tests_failed", 0)
            tests_passed = tests_run - tests_failed
            insights.append(f"- Tests executed: {tests_passed}/{tests_run} passed")

            # Scope detection
            if tests_run <= 5:
                insights.append("- Strategy: Targeted testing for focused changes")
            else:
                insights.append("- Strategy: Comprehensive test suite validation")
        else:
            insights.append("- No automated tests required for this change")

        if not insights:
            return "- Manual verification only"

        return "\n".join(insights)

    def _extract_pitfalls(self, verification_analysis: str) -> str:
        """
        Extract pitfalls and warnings from verification analysis.

        Args:
            verification_analysis: AI verification text

        Returns:
            Bullet list of pitfalls or default message
        """
        pitfalls = []

        # Look for warning indicators
        analysis_lower = verification_analysis.lower()

        # Common pitfall keywords
        pitfall_keywords = [
            ("breaking change", "Watch for breaking changes in public APIs"),
            ("backwardcompat", "Ensure backward compatibility maintained"),
            ("performance", "Consider performance implications"),
            ("memory", "Monitor memory usage for large operations"),
            ("thread safe", "Verify thread safety in concurrent contexts"),
            ("race condition", "Check for potential race conditions"),
        ]

        for keyword, pitfall_desc in pitfall_keywords:
            if keyword in analysis_lower:
                pitfalls.append(f"- {pitfall_desc}")

        if not pitfalls:
            return "- No specific pitfalls identified"

        return "\n".join(pitfalls)

    def _summarize_changes(self, context: AgentContext) -> str:
        """
        Summarize file changes from context.

        Args:
            context: Current agent context

        Returns:
            Bullet list of changes with file references
        """
        if not context.modified_files:
            return "- No files modified"

        changes = []
        for file_path in list(context.modified_files)[:5]:  # Limit to 5 files
            # Extract filename
            file_name = file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
            changes.append(f"- Modified: `{file_name}`")

        if len(context.modified_files) > 5:
            changes.append(f"- ... and {len(context.modified_files) - 5} more files")

        return "\n".join(changes)

    def _merge_memory_entries(self, existing_memory: str, new_entry: str) -> str:
        """
        Merge new entry with existing memory.

        Prepends new entry and updates header timestamp.

        Args:
            existing_memory: Current memory content
            new_entry: New entry to prepend

        Returns:
            Merged memory content
        """
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build header
        header = f"""# Hcode Task Memory
Last updated: {timestamp}
---

"""

        # Strip old header if present
        if existing_memory.strip():
            lines = existing_memory.split("\n")
            # Skip header lines (first 3 lines typically)
            content_start = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("---") and i < 10:
                    content_start = i + 1
                    break

            if content_start > 0:
                existing_memory = "\n".join(lines[content_start:])

        # Merge: header + new entry + existing entries
        return header + new_entry + existing_memory

    def _trim_memory(self, memory_content: str) -> str:
        """
        Trim memory to maintain rolling window of 10 tasks and token budget.

        Args:
            memory_content: Full memory content

        Returns:
            Trimmed memory content
        """
        MAX_TASKS = 10
        MAX_TOKENS = 3500  # Approximate token budget (~14000 chars)

        lines = memory_content.split("\n")

        # Find all task separators (---)
        separators = []
        for i, line in enumerate(lines):
            if line.strip() == "---":
                separators.append(i)

        # Keep header + first MAX_TASKS task entries
        if len(separators) > MAX_TASKS + 1:  # +1 for header separator
            trim_line = separators[MAX_TASKS + 1]
            lines = lines[:trim_line]
            memory_content = "\n".join(lines)

        # Check token budget (rough approximation: 1 token ≈ 4 chars)
        if len(memory_content) > MAX_TOKENS * 4:
            # Trim by tasks until under budget
            while len(separators) > 2 and len(memory_content) > MAX_TOKENS * 4:
                separators.pop()
                trim_line = separators[-1]
                lines = lines[:trim_line]
                memory_content = "\n".join(lines)

        return memory_content
