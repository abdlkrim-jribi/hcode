import pytest
import os
import shutil
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Mock anthropic module to avoid ImportError
from unittest.mock import MagicMock
sys.modules["anthropic"] = MagicMock()
sys.modules["openai"] = MagicMock()
sys.modules["tenacity"] = MagicMock()
sys.modules["httpx"] = MagicMock()
sys.modules["tiktoken"] = MagicMock()
sys.modules["html2text"] = MagicMock()
sys.modules["aiofiles"] = MagicMock()

from hcode.tools.git_tools import (
    GitStatusTool,
    GitDiffTool,
    GitAddTool,
    GitCommitTool,
    GitLogTool,
    GitCheckoutTool,
    GitBranchTool,
)

@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo"""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Initialize git repo
    os.system(f"git init {repo_dir}")
    
    # Configure user for commits
    os.system(f"cd {repo_dir} && git config user.email 'test@example.com' && git config user.name 'Test User'")
    
    return str(repo_dir)

@pytest.mark.asyncio
async def test_git_status(git_repo):
    tool = GitStatusTool(root_dir=git_repo)
    result = await tool.execute()
    assert result.success
    assert "On branch" in result.output

@pytest.mark.asyncio
async def test_git_workflow(git_repo):
    # 1. Create a file
    test_file = Path(git_repo) / "test.txt"
    test_file.write_text("Hello World")
    
    # 2. Add file
    add_tool = GitAddTool(root_dir=git_repo)
    result = await add_tool.execute(path="test.txt")
    assert result.success
    
    # 3. Commit
    commit_tool = GitCommitTool(root_dir=git_repo)
    result = await commit_tool.execute(message="Initial commit")
    assert result.success
    
    # 4. Log
    log_tool = GitLogTool(root_dir=git_repo)
    result = await log_tool.execute()
    assert result.success
    assert "Initial commit" in result.output

@pytest.mark.asyncio
async def test_git_branching(git_repo):
    # Setup initial commit
    test_file = Path(git_repo) / "test.txt"
    test_file.write_text("Hello World")
    os.system(f"cd {git_repo} && git add . && git commit -m 'Initial'")
    
    # 1. Create branch
    checkout_tool = GitCheckoutTool(root_dir=git_repo)
    result = await checkout_tool.execute(target="feature-branch", create_branch=True)
    assert result.success
    
    # 2. Verify branch
    branch_tool = GitBranchTool(root_dir=git_repo)
    result = await branch_tool.execute()
    assert result.success
    assert "* feature-branch" in result.output
