"""
Bash execution tools for Hcode.
Includes Bash, BashOutput, and KillShell tools for command execution.
"""

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory

# Get logger for this module
logger = logging.getLogger(__name__)


@dataclass
class BackgroundShell:
    """Represents a background shell process"""

    shell_id: str
    process: asyncio.subprocess.Process
    command: str
    started_at: float
    output_buffer: List[str]
    error_buffer: List[str]
    last_read_position: int = 0


class BashShellManager:
    """Manages background bash shells"""

    def __init__(self):
        self.shells: Dict[str, BackgroundShell] = {}

    def create_shell(
        self, shell_id: str, process: asyncio.subprocess.Process, command: str
    ) -> BackgroundShell:
        """Create and register a new background shell"""
        shell = BackgroundShell(
            shell_id=shell_id,
            process=process,
            command=command,
            started_at=time.time(),
            output_buffer=[],
            error_buffer=[],
        )
        self.shells[shell_id] = shell
        return shell

    def get_shell(self, shell_id: str) -> Optional[BackgroundShell]:
        """Get a shell by ID"""
        return self.shells.get(shell_id)


    def remove_shell(self, shell_id: str) -> bool:
        """Remove a shell from registry"""
        if shell_id in self.shells:
            del self.shells[shell_id]
            return True
        return False


# Global shell manager instance
_shell_manager = BashShellManager()


class BashTool(BaseTool):
    """
    Executes bash commands in a persistent shell session with optional timeout.

    Features:
    - Persistent shell session
    - Optional timeout (default 120000ms, max 600000ms)
    - Background execution support
    - Proper command quoting for paths with spaces
    - Command chaining with && and ||
    """

    def __init__(self, root_dir: str = None):
        super().__init__()
        self.name = "Bash"
        self.category = ToolCategory.EXECUTION
        self.root_dir = Path(root_dir or os.getcwd())
        self.shell_manager = _shell_manager

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="command",
                type="string",
                description="The bash command to execute",
                required=True,
            ),
            ToolParameter(
                name="description",
                type="string",
                description="Clear, concise description of what this command does in 5-10 words",
                required=False,
            ),
            ToolParameter(
                name="timeout",
                type="number",
                description="Optional timeout in milliseconds (max 600000ms / 10 minutes). Default: 120000ms (2 minutes)",
                required=False,
            ),
            ToolParameter(
                name="run_in_background",
                type="boolean",
                description="Set to true to run this command in the background. Allows you to continue working while command runs.",
                required=False,
            ),
            # Legacy
            ToolParameter("CommandLine", "string", "Alias for command", default=None),
        ]

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        # Check required: CommandLine (or command)
        if "CommandLine" not in kwargs and "command" not in kwargs:
             return False, "Missing required parameter: CommandLine (or command)"
        return True, None

    def _translate_command(self, command: str) -> str:
        """Translate Unix commands to Windows equivalents if on Windows"""
        import sys
        if sys.platform != "win32" or not command:
            return command
            
        # Simple tokenization
        parts = command.strip().split()
        if not parts:
            return command
            
        base_cmd = parts[0]
        args = " ".join(parts[1:])
        
        # Helper to replace forward slashes with backslashes in args
        def fix_paths(s):
            return s.replace("/", "\\")
            
        # Command mappings
        if base_cmd == "ls":
            # Handle common flags roughly
            if "-R" in args:
                return f"dir /s {args.replace('-R', '')}"
            elif "-la" in args or "-al" in args:
                return f"dir /a {args.replace('-la', '').replace('-al', '')}"
            return f"dir {args}"
            
        elif base_cmd == "cp":
            return f"copy {fix_paths(args)}"
            
        elif base_cmd == "mv":
            return f"move {fix_paths(args)}"
            
        elif base_cmd == "rm":
            # rm -rf -> rmdir /s /q for dirs, or del for files
            # This is tricky because rm works on both. 
            # safe bet: del for files. rmdir for dirs requires knowing it's a dir.
            # For now, map simple rm to del
            if "-rf" in args:
                 return f"rmdir /s /q {fix_paths(args).replace('-rf', '')}"
            return f"del {fix_paths(args)}"
            
        elif base_cmd == "cat":
            return f"type {fix_paths(args)}"
            
        elif base_cmd == "grep":
            return f"findstr {args}"
            
        elif base_cmd == "touch":
            if args:
                return f"type nul >> {fix_paths(args)}"
                
        return command

    async def execute(self, command: str = None, CommandLine: str = None, **kwargs) -> ToolResult:
        """Execute bash command"""
        raw_command = command or CommandLine
        raw_timeout = kwargs.get("timeout", 120000)
        # Smart unit detection: if value < 1000, assume seconds; otherwise milliseconds
        # This handles both AI sending seconds (30) and milliseconds (30000) correctly
        if raw_timeout < 1000:
            timeout = float(raw_timeout)  # Already in seconds
        else:
            timeout = raw_timeout / 1000  # Convert ms to seconds
        run_in_background = kwargs.get("run_in_background", False)
        description = kwargs.get("description", raw_command[:50] if raw_command else "")

        if not raw_command:
            return ToolResult(success=False, output="", error="command (or CommandLine) is required")

        # Translate command for Windows
        command = self._translate_command(raw_command)

        # If translation changed the command, notify in description/metadata
        if command != raw_command and description == raw_command[:50]:
             description = f"{raw_command} (translated to {command})"

        # Validate timeout - let agent decide, just enforce reasonable bounds
        max_timeout = 600000 / 1000  # 10 minutes max to prevent runaway processes

        if timeout > max_timeout:
            logger.warning(f"[BASH] Timeout {timeout}s exceeds maximum ({max_timeout}s), capping at max")
            timeout = max_timeout

        # DEBUG: Log timeout value
        logger.info(f"[BASH] Executing with timeout={timeout}s: {command[:100]}")

        # Show confirmation before executing command
        try:
            from hcode.ui.confirmation_display import get_confirmation_display
            confirmation = get_confirmation_display()
            
            approved = confirmation.show_command_confirmation(
                command=command,
                description=description,
                working_dir=str(self.root_dir)
            )
            
            if not approved:
                return ToolResult(
                    success=False,
                    output="",
                    error="Command rejected by user"
                )
        except ImportError:
            # If confirmation display not available, proceed without confirmation
            pass

        try:
            if run_in_background:
                return await self._execute_background(command, description)
            else:
                return await self._execute_foreground(command, timeout, description)

        except asyncio.TimeoutError:
            return ToolResult(
                success=False, output="", error=f"Command timed out after {timeout}s: {command}"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Command execution failed: {str(e)}")

    async def _execute_foreground(
        self, command: str, timeout: float, description: str
    ) -> ToolResult:
        """Execute command in foreground with timeout"""

        start_time = time.time()
        logger.info(f"[BASH] _execute_foreground started with timeout={timeout}s at t=0.000s")

        # Platform-specific shell handling

        # Handle simple commands like 'pwd' in a cross‑platform way
        if command.strip() == "pwd":
            cwd = str(self.root_dir)
            return ToolResult(
                success=True,
                output=f"stdout:\n{cwd}",
                error=None,
                metadata={
                    "exit_code": 0,
                    "duration": 0.0,
                    "description": description,
                    "stdout": cwd,
                    "stderr": "",
                },
            )

        # Handle 'true' and 'false' for cross-platform compatibility
        if command.strip() == "true":
            return ToolResult(
                success=True,
                output="",
                error=None,
                metadata={"exit_code": 0, "duration": 0.0, "description": description},
            )

        if command.strip() == "false":
            return ToolResult(
                success=False,
                output="",
                error="Command failed with exit code 1",
                metadata={"exit_code": 1, "duration": 0.0, "description": description},
            )

        try:
            logger.info(f"[BASH] Creating subprocess at t={time.time() - start_time:.3f}s")
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.root_dir),
                shell=True,
            )
            logger.info(f"[BASH] Subprocess created at t={time.time() - start_time:.3f}s, PID={process.pid}")

            # Get output managers
            stream_console = None
            hcode_display = None
            try:
                from hcode.ui import get_console
                from hcode.ui.hcode_display import get_hcode_display
                stream_console = get_console()
                hcode_display = get_hcode_display()
                logger.info(f"[BASH] Display managers loaded at t={time.time() - start_time:.3f}s")
            except ImportError:
                logger.info(f"[BASH] Display managers not available (ImportError)")
                pass

            # Stream stdout line-by-line in real-time
            stdout_lines: list = []
            stderr_lines: list = []

            async def _stream_stdout(live_update=None):
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    decoded = self._decode_output(line)
                    stdout_lines.append(decoded)
                    if live_update:
                        live_update.update(decoded)
                    elif stream_console:
                        stream_console.print(f"    {decoded.rstrip()}", style="dim")

            async def _stream_stderr(live_update=None):
                while True:
                    line = await process.stderr.readline()
                    if not line:
                        break
                    decoded = self._decode_output(line)
                    stderr_lines.append(decoded)
                    if live_update:
                        live_update.update(decoded)

            # Run with live display if available
            if hcode_display:
                # We need to run the async loop inside the sync context manager
                # But context manager is sync.
                logger.info(f"[BASH] Entering live_command_context at t={time.time() - start_time:.3f}s")
                with hcode_display.live_command_context(command) as live:
                    logger.info(f"[BASH] Starting wait_for (timeout={timeout}s) at t={time.time() - start_time:.3f}s")
                    await asyncio.wait_for(
                        asyncio.gather(_stream_stdout(live), _stream_stderr(live)),
                        timeout=timeout,
                    )
                    logger.info(f"[BASH] wait_for completed successfully at t={time.time() - start_time:.3f}s")
            else:
                # Run without live display
                logger.info(f"[BASH] Starting wait_for (no live display, timeout={timeout}s) at t={time.time() - start_time:.3f}s")
                await asyncio.wait_for(
                    asyncio.gather(_stream_stdout(), _stream_stderr()),
                    timeout=timeout,
                )
            await process.wait()

            stdout = "".join(stdout_lines)
            stderr = "".join(stderr_lines)
            exit_code = process.returncode
            duration = time.time() - start_time

            # Store full output for SearchOutput tool
            full_output = stdout + "\n" + stderr if stderr else stdout
            store_last_output(full_output, command)

            # Build output - always include something meaningful
            output_parts = []
            if stdout.strip():
                output_parts.append(f"stdout:\n{stdout.strip()}")
            if stderr.strip():
                output_parts.append(f"stderr:\n{stderr.strip()}")

            # If no output at all, indicate that
            if not output_parts:
                if exit_code == 0:
                    output_parts.append("(command completed with no output)")
                else:
                    output_parts.append(
                        f"(command failed with exit code {exit_code}, no output captured)"
                    )

            output_parts.append(f"\nDuration: {duration:.2f}s")
            output = "\n\n".join(output_parts)

            # Determine error message for failures
            error_msg = None
            if exit_code != 0:
                if stderr.strip():
                    error_msg = stderr.strip()
                else:
                    error_msg = f"Command failed with exit code {exit_code}"

            return ToolResult(
                success=(exit_code == 0),
                output=output,
                error=error_msg,
                metadata={
                    "exit_code": exit_code,
                    "duration": duration,
                    "description": description,
                    "stdout": stdout,
                    "stderr": stderr,
                },
            )

        except asyncio.TimeoutError:
            # Kill process on timeout
            elapsed = time.time() - start_time
            logger.error(f"[BASH] TIMEOUT at t={elapsed:.3f}s (limit was {timeout}s): {command}")
            try:
                process.kill()
                await process.wait()
                logger.info(f"[BASH] Process killed successfully")
            except Exception as kill_error:
                logger.error(f"[BASH] Failed to kill process: {kill_error}")
                pass
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout}s (actual: {elapsed:.2f}s)",
                metadata={"timeout": True, "description": description, "elapsed": elapsed, "limit": timeout},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute command: {str(e)}",
                metadata={"exception": str(e), "description": description},
            )

    def _decode_output(self, data: bytes) -> str:
        """Decode bytes with multiple encoding fallbacks for Windows compatibility"""
        if not data:
            return ""

        # Try multiple encodings
        encodings = ["utf-8", "cp1252", "latin-1", "cp437"]
        for encoding in encodings:
            try:
                return data.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue

        # Last resort: decode with errors replaced
        return data.decode("utf-8", errors="replace")

    async def _execute_background(self, command: str, description: str) -> ToolResult:
        """Execute command in background"""
        shell_id = f"shell_{uuid.uuid4().hex[:8]}"

        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.root_dir),
            shell=True,
        )

        # Register shell
        shell = self.shell_manager.create_shell(shell_id, process, command)

        # Start output collection task
        asyncio.create_task(self._collect_output(shell))

        return ToolResult(
            success=True,
            output=f"Command started in background with shell ID: {shell_id}\nUse BashOutput tool to read output.",
            metadata={"shell_id": shell_id, "command": command, "description": description},
        )

    async def _collect_output(self, shell: BackgroundShell):
        """Collect output from background shell"""
        try:
            while True:
                # Read stdout
                if shell.process.stdout:
                    line = await shell.process.stdout.readline()
                    if line:
                        shell.output_buffer.append(line.decode("utf-8", errors="replace"))

                # Read stderr
                if shell.process.stderr:
                    line = await shell.process.stderr.readline()
                    if line:
                        shell.error_buffer.append(line.decode("utf-8", errors="replace"))

                # Check if process finished
                if shell.process.returncode is not None:
                    break

                await asyncio.sleep(0.1)

        except Exception:
            pass


class BashOutputTool(BaseTool):
    """
    Retrieves output from a running or completed background bash shell.
    Supports filtering and searching for specific patterns.
    """

    def __init__(self):
        super().__init__()
        self.name = "BashOutput"
        self.category = ToolCategory.EXECUTION
        self.shell_manager = _shell_manager

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="bash_id",
                type="string",
                description="The ID of the background shell to retrieve output from",
                required=True,
            ),
            ToolParameter(
                name="filter",
                type="string",
                description="Optional regular expression to filter the output lines. Only matching lines will be included.",
                required=False,
            ),
            ToolParameter(
                name="tail",
                type="number",
                description="Only return the last N lines of output",
                required=False,
            ),
            ToolParameter(
                name="head",
                type="number",
                description="Only return the first N lines of output",
                required=False,
            ),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        """Get output from background shell"""
        bash_id = kwargs.get("bash_id")
        filter_regex = kwargs.get("filter")

        if not bash_id:
            return ToolResult(success=False, output="", error="bash_id is required")

        shell = self.shell_manager.get_shell(bash_id)
        if not shell:
            return ToolResult(success=False, output="", error=f"Shell not found: {bash_id}")

        # Get new output since last read
        new_stdout = shell.output_buffer[shell.last_read_position :]
        new_stderr = shell.error_buffer[shell.last_read_position :]

        # Update read position
        shell.last_read_position = len(shell.output_buffer)

        # Apply filter if provided
        if filter_regex:
            import re

            pattern = re.compile(filter_regex)
            new_stdout = [line for line in new_stdout if pattern.search(line)]
            new_stderr = [line for line in new_stderr if pattern.search(line)]

        # Check if process is still running
        is_running = shell.process.returncode is None
        status = "running" if is_running else f"completed (exit code: {shell.process.returncode})"

        # Build output
        output_parts = [f"Shell {bash_id}: {status}"]

        if new_stdout:
            output_parts.append("\nstdout:")
            output_parts.append("".join(new_stdout))

        if new_stderr:
            output_parts.append("\nstderr:")
            output_parts.append("".join(new_stderr))

        if not new_stdout and not new_stderr:
            output_parts.append("\nNo new output")

        return ToolResult(
            success=True,
            output="\n".join(output_parts),
            metadata={
                "shell_id": bash_id,
                "is_running": is_running,
                "exit_code": shell.process.returncode,
                "duration": time.time() - shell.started_at,
            },
        )


class KillShellTool(BaseTool):
    """
    Kills a running background bash shell by its ID.
    """

    def __init__(self):
        super().__init__()
        self.name = "KillShell"
        self.category = ToolCategory.EXECUTION
        self.shell_manager = _shell_manager

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="shell_id",
                type="string",
                description="The ID of the background shell to kill",
                required=True,
            ),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        """Kill background shell"""
        shell_id = kwargs.get("shell_id")

        if not shell_id:
            return ToolResult(success=False, output="", error="shell_id is required")

        shell = self.shell_manager.get_shell(shell_id)
        if not shell:
            return ToolResult(success=False, output="", error=f"Shell not found: {shell_id}")

        try:
            # Try graceful termination first
            shell.process.terminate()
            try:
                await asyncio.wait_for(shell.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Force kill if graceful termination failed
                shell.process.kill()
                await shell.process.wait()

            # Remove from registry
            self.shell_manager.remove_shell(shell_id)

            return ToolResult(
                success=True,
                output=f"Shell {shell_id} terminated successfully",
                metadata={
                    "shell_id": shell_id,
                    "command": shell.command,
                    "duration": time.time() - shell.started_at,
                },
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to kill shell: {str(e)}")


class LSTool(BaseTool):
    """
    Lists files and directories at a specified path with optional ignore patterns.
    """

    def __init__(self, root_dir: str = None):
        super().__init__()
        self.name = "LS"
        self.category = ToolCategory.FILE_OPERATIONS
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="path",
                type="string",
                description="Absolute directory path to list",
                required=True,
            ),
            ToolParameter(
                name="ignore",
                type="string",
                description="Optional glob patterns to exclude (comma-separated)",
                required=False,
            ),
            # Legacy
            ToolParameter("DirectoryPath", "string", "Alias for path", default=None),
        ]

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        # Check required: DirectoryPath (or path)
        if "DirectoryPath" not in kwargs and "path" not in kwargs:
             return False, "Missing required parameter: DirectoryPath"
        return True, None


    async def execute(self, path: str = None, DirectoryPath: str = None, **kwargs) -> ToolResult:
        """List directory contents"""
        import sys

        path_str = path or DirectoryPath
        ignore_patterns = kwargs.get("ignore", "")

        if not path_str:
            return ToolResult(success=False, output="", error="path (or DirectoryPath) is required")

        # Handle "/" on Windows - convert to current working directory
        if sys.platform == "win32" and path_str == "/":
            path_str = str(self.root_dir)

        # Handle "." as current directory
        if path_str == ".":
            path_str = str(self.root_dir)

        path = Path(path_str)

        # If path is relative, resolve it against root_dir
        if not path.is_absolute():
            path = self.root_dir / path

        if not path.exists():
            return ToolResult(success=False, output="", error=f"Path does not exist: {path}")

        if not path.is_dir():
            return ToolResult(success=False, output="", error=f"Path is not a directory: {path}")

        try:
            # Parse ignore patterns
            ignore_list = [p.strip() for p in ignore_patterns.split(",") if p.strip()]

            # List directory contents
            entries = []
            for item in sorted(path.iterdir()):
                # Check ignore patterns
                should_ignore = False
                for pattern in ignore_list:
                    if item.match(pattern):
                        should_ignore = True
                        break

                if should_ignore:
                    continue

                # Get item info
                is_dir = item.is_dir()
                size = item.stat().st_size if item.is_file() else 0

                entry = {
                    "name": item.name,
                    "type": "directory" if is_dir else "file",
                    "size": size,
                    "path": str(item),
                }
                entries.append(entry)

            # Format output
            output_lines = [f"Contents of {path}:"]
            output_lines.append("")

            for entry in entries:
                type_indicator = "📁" if entry["type"] == "directory" else "📄"
                size_str = f"{entry['size']:,} bytes" if entry["type"] == "file" else ""
                output_lines.append(f"{type_indicator} {entry['name']:<40} {size_str}")

            output_lines.append("")
            output_lines.append(f"Total: {len(entries)} items")

            output_text = "\n".join(output_lines)



            return ToolResult(
                success=True,
                output=output_text,
                metadata={"path": str(path), "count": len(entries), "entries": entries},
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to list directory: {str(e)}")


# Global storage for last command output (for search capability)
_last_command_output: Dict[str, str] = {}


def store_last_output(output: str, command: str = ""):
    """Store the last command output for search capability"""
    global _last_command_output
    _last_command_output["output"] = output
    _last_command_output["command"] = command


def get_last_output() -> str:
    """Get the last command output"""
    return _last_command_output.get("output", "")


class SearchOutputTool(BaseTool):
    """
    Search within the last command output for specific patterns.

    This is useful when a long command output was truncated and you need
    to find specific lines (like "TOTAL" in coverage reports).
    """

    def __init__(self):
        super().__init__()
        self.name = "SearchOutput"
        self.category = ToolCategory.EXECUTION

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="pattern",
                type="string",
                description="Pattern to search for (regex supported)",
                required=True,
            ),
            ToolParameter(
                name="context_lines",
                type="number",
                description="Number of lines to show before and after each match (default: 2)",
                required=False,
            ),
            ToolParameter(
                name="case_sensitive",
                type="boolean",
                description="Whether search is case-sensitive (default: false)",
                required=False,
            ),
        ]

    async def execute(self, **kwargs) -> ToolResult:
        """Search in the last command output"""
        import re

        pattern = kwargs.get("pattern", "")
        context_lines = kwargs.get("context_lines", 2)
        case_sensitive = kwargs.get("case_sensitive", False)

        if not pattern:
            return ToolResult(success=False, output="", error="pattern is required")

        output = get_last_output()
        if not output:
            return ToolResult(
                success=False,
                output="",
                error="No previous command output available. Run a Bash command first.",
            )

        # Compile pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ToolResult(success=False, output="", error=f"Invalid regex pattern: {e}")

        # Search through lines
        lines = output.split("\n")
        matches = []

        for i, line in enumerate(lines):
            if regex.search(line):
                # Collect context
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)

                match_block = []
                for j in range(start, end):
                    prefix = ">>> " if j == i else "    "
                    match_block.append(f"{j + 1:4}: {prefix}{lines[j]}")

                matches.append(
                    {"line_number": i + 1, "line": line, "context": "\n".join(match_block)}
                )

        if not matches:
            return ToolResult(
                success=True,
                output=f"No matches found for pattern: {pattern}\n(Searched {len(lines)} lines)",
                metadata={"matches": 0, "total_lines": len(lines)},
            )

        # Format output
        output_parts = [f"Found {len(matches)} match(es) for pattern: {pattern}\n"]

        for i, match in enumerate(matches[:20]):  # Limit to first 20 matches
            output_parts.append(f"--- Match {i + 1} (line {match['line_number']}) ---")
            output_parts.append(match["context"])
            output_parts.append("")

        if len(matches) > 20:
            output_parts.append(f"... and {len(matches) - 20} more matches")

        return ToolResult(
            success=True,
            output="\n".join(output_parts),
            metadata={"matches": len(matches), "total_lines": len(lines), "pattern": pattern},
        )
