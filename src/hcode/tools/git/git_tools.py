"""
Git integration tools for Hcode.
"""

import asyncio
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class BaseGitTool(BaseTool):
    """Base class for Git tools"""

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.VERSION_CONTROL
        self.root_dir = Path(root_dir or os.getcwd())

    async def _run_git(self, args: List[str]) -> ToolResult:
        """Run a git command"""
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.root_dir),
            )
            stdout, stderr = await process.communicate()
            
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()
            
            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    output=stdout_str,
                    error=stderr_str or f"Git command failed with exit code {process.returncode}",
                    metadata={"exit_code": process.returncode}
                )
            
            return ToolResult(
                success=True,
                output=stdout_str,
                metadata={"exit_code": 0}
            )
        except FileNotFoundError:
             return ToolResult(
                success=False,
                output=None,
                error="Git executable not found. Please ensure git is installed and in your PATH."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to execute git command: {str(e)}"
            )


class GitStatusTool(BaseGitTool):
    """Check the status of the git repository"""

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__(root_dir)
        self.name = "GitStatus"

    def get_parameters(self) -> List[ToolParameter]:
        return []

    async def execute(self, **kwargs) -> ToolResult:
        return await self._run_git(["status"])


class GitDiffTool(BaseGitTool):
    """Show changes between commits, commit and working tree, etc"""

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__(root_dir)
        self.name = "GitDiff"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("target", "string", "File or branch to diff (optional)", default=None),
            ToolParameter("staged", "boolean", "Show staged changes", default=False),
        ]

    async def execute(self, target: Optional[str] = None, staged: bool = False, **kwargs) -> ToolResult:
        args = ["diff"]
        if staged:
            args.append("--staged")
        if target:
            args.append(target)
        return await self._run_git(args)


class GitAddTool(BaseGitTool):
    """Add file contents to the index"""

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__(root_dir)
        self.name = "GitAdd"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("path", "string", "Path to file(s) to add", required=True),
        ]

    async def execute(self, path: str, **kwargs) -> ToolResult:
        return await self._run_git(["add", path])


class GitCommitTool(BaseGitTool):
    """Record changes to the repository"""

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__(root_dir)
        self.name = "GitCommit"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("message", "string", "Commit message", required=True),
        ]

    async def execute(self, message: str, **kwargs) -> ToolResult:
        return await self._run_git(["commit", "-m", message])


class GitLogTool(BaseGitTool):
    """Show commit logs"""

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__(root_dir)
        self.name = "GitLog"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("max_count", "integer", "Limit the number of commits to output", default=10),
        ]

    async def execute(self, max_count: int = 10, **kwargs) -> ToolResult:
        return await self._run_git(["log", f"-n {max_count}", "--oneline", "--graph", "--decorate"])


class GitCheckoutTool(BaseGitTool):
    """Switch branches or restore working tree files"""

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__(root_dir)
        self.name = "GitCheckout"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("target", "string", "Branch or file to checkout", required=True),
            ToolParameter("create_branch", "boolean", "Create a new branch", default=False),
        ]

    async def execute(self, target: str, create_branch: bool = False, **kwargs) -> ToolResult:
        args = ["checkout"]
        if create_branch:
            args.append("-b")
        args.append(target)
        return await self._run_git(args)


class GitBranchTool(BaseGitTool):
    """List, create, or delete branches"""

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__(root_dir)
        self.name = "GitBranch"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("list_branches", "boolean", "List all branches", default=True),
            ToolParameter("delete_branch", "string", "Branch to delete (optional)", default=None),
        ]

    async def execute(self, list_branches: bool = True, delete_branch: Optional[str] = None, **kwargs) -> ToolResult:
        if delete_branch:
            return await self._run_git(["branch", "-d", delete_branch])
        return await self._run_git(["branch", "-a"])
