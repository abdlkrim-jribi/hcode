"""
ToolExecutor for Hcode.
Executes external tools and commands with timeout and output handling.
"""

import asyncio
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List


@dataclass
class ExecutionResult:
    """Result from command execution"""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float  # seconds
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Check if command succeeded"""
        return self.exit_code == 0 and not self.timed_out

    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"{status} {self.command} (exit: {self.exit_code}, {self.duration:.2f}s)"


class ToolExecutor:
    """Executes external tools and commands"""

    # Common tool configurations
    TOOL_CONFIGS = {
        # Python tools
        "pytest": {
            "command": "pytest",
            "timeout": 300,
            "env": {},
        },
        "pylint": {
            "command": "pylint",
            "timeout": 60,
        },
        "black": {
            "command": "black",
            "timeout": 60,
        },
        "mypy": {
            "command": "mypy",
            "timeout": 120,
        },
        # JavaScript tools
        "npm": {
            "command": "npm",
            "timeout": 300,
        },
        "jest": {
            "command": "jest",
            "timeout": 300,
        },
        "eslint": {
            "command": "eslint",
            "timeout": 60,
        },
        "prettier": {
            "command": "prettier",
            "timeout": 60,
        },
        # Build tools
        "make": {
            "command": "make",
            "timeout": 600,
        },
        "cargo": {
            "command": "cargo",
            "timeout": 600,
        },
        "gradle": {
            "command": "gradle",
            "timeout": 600,
        },
        # Version control
        "git": {
            "command": "git",
            "timeout": 60,
        },
    }

    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize ToolExecutor.

        Args:
            root_dir: Root directory for command execution
        """
        self.root_dir = Path(root_dir or Path.cwd())
        self.env = dict(os.environ)  # Copy environment variables

    async def execute(
        self,
        command: str,
        timeout: float = 120,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        shell: bool = False,
    ) -> ExecutionResult:
        """
        Execute a command asynchronously.

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            cwd: Working directory
            env: Environment variables
            shell: Use shell execution

        Returns:
            ExecutionResult
        """
        import time

        start_time = time.time()
        work_dir = Path(cwd) if cwd else self.root_dir

        # Prepare environment
        exec_env = self.env.copy()
        if env:
            exec_env.update(env)

        # Parse command
        if not shell:
            cmd_parts = shlex.split(command)
        else:
            cmd_parts = command

        try:
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd_parts if not shell else [command],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
                env=exec_env,
                shell=shell,
            )

            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

                exit_code = process.returncode
                timed_out = False

            except asyncio.TimeoutError:
                # Kill process on timeout
                process.kill()
                await process.communicate()

                stdout = b""
                stderr = b"Command timed out"
                exit_code = -1
                timed_out = True

            duration = time.time() - start_time

            return ExecutionResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout.decode("utf-8", errors="ignore"),
                stderr=stderr.decode("utf-8", errors="ignore"),
                duration=duration,
                timed_out=timed_out,
            )

        except Exception as e:
            duration = time.time() - start_time

            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration=duration,
                timed_out=False,
            )

    async def run_tool(self, tool_name: str, args: List[str], **kwargs) -> ExecutionResult:
        """
        Run a configured tool.

        Args:
            tool_name: Tool name from TOOL_CONFIGS
            args: Tool arguments
            **kwargs: Additional execution parameters

        Returns:
            ExecutionResult
        """
        if tool_name not in self.TOOL_CONFIGS:
            raise ValueError(f"Unknown tool: {tool_name}")

        config = self.TOOL_CONFIGS[tool_name]
        command = f"{config['command']} {' '.join(args)}"

        # Merge config with kwargs
        exec_params = {
            "timeout": config.get("timeout", 120),
            "env": config.get("env", {}),
        }
        exec_params.update(kwargs)

        return await self.execute(command, **exec_params)





    def _detect_test_framework(self) -> str:
        """Detect test framework from project"""
        # Check for Python
        if (self.root_dir / "pytest.ini").exists() or (self.root_dir / "setup.cfg").exists():
            return "pytest"

        # Check for JavaScript
        package_json = self.root_dir / "package.json"
        if package_json.exists():
            try:
                import json

                with open(package_json) as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    if "jest" in deps:
                        return "jest"
                    if "mocha" in deps:
                        return "mocha"
            except:
                pass

        return "pytest"  # Default

    def _detect_linter(self) -> str:
        """Detect linter from project"""
        # Check for Python
        if (self.root_dir / ".pylintrc").exists():
            return "pylint"

        # Check for JavaScript
        if (self.root_dir / ".eslintrc.js").exists() or (self.root_dir / ".eslintrc.json").exists():
            return "eslint"

        # Default based on files
        if list(self.root_dir.glob("**/*.py")):
            return "pylint"

        if list(self.root_dir.glob("**/*.js")) or list(self.root_dir.glob("**/*.ts")):
            return "eslint"

        return "pylint"

    def _detect_formatter(self) -> str:
        """Detect formatter from project"""
        # Check for Python
        if (self.root_dir / "pyproject.toml").exists():
            return "black"

        # Check for JavaScript
        if (self.root_dir / ".prettierrc").exists():
            return "prettier"

        # Default based on files
        if list(self.root_dir.glob("**/*.py")):
            return "black"

        return "prettier"

    def _detect_build_tool(self) -> str:
        """Detect build tool from project"""
        if (self.root_dir / "Makefile").exists():
            return "make"

        if (self.root_dir / "package.json").exists():
            return "npm"

        if (self.root_dir / "Cargo.toml").exists():
            return "cargo"

        if (self.root_dir / "build.gradle").exists():
            return "gradle"

        return "make"



# Import os at module level
import os
