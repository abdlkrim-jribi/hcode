"""
ToolExecutor for Hcode.
Executes external tools and commands with timeout and output handling.
"""

import asyncio
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


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


# Import os at module level
import os
