"""
FileSystemManager for Hcode.
Handles all file system operations including read, write, search, and Git integration.
"""

import os
import shutil
import glob
import re
from pathlib import Path
from typing import List, Dict, Optional, Set
import aiofiles
import asyncio
from git import Repo, InvalidGitRepositoryError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pathspec


class FileSystemManager:
    """Manages file system operations for Hcode"""

    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize FileSystemManager.

        Args:
            root_dir: Root directory to work in (defaults to current directory)
        """
        self.root_dir = Path(root_dir or os.getcwd()).resolve()
        self.git_repo: Optional[Repo] = None
        self._load_gitignore()
        self._try_init_git()

    def _load_gitignore(self):
        """Load .gitignore patterns"""
        gitignore_path = self.root_dir / ".gitignore"
        self.gitignore_spec = None

        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                patterns = f.read().splitlines()
                self.gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def _try_init_git(self):
        """Try to initialize Git repository"""
        try:
            self.git_repo = Repo(self.root_dir)
        except InvalidGitRepositoryError:
            self.git_repo = None

    def is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored"""
        if self.gitignore_spec:
            rel_path = path.relative_to(self.root_dir)
            return self.gitignore_spec.match_file(str(rel_path))
        return False

    async def read_file(self, file_path: str) -> str:
        """
        Read file contents asynchronously.

        Args:
            file_path: Path to file

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self._resolve_path(file_path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            return await f.read()

    async def write_file(self, file_path: str, content: str, create_dirs: bool = True) -> bool:
        """
        Write content to file asynchronously.

        Args:
            file_path: Path to file
            content: Content to write
            create_dirs: Create parent directories if needed

        Returns:
            True if successful

        Raises:
            IOError: If write fails
        """
        full_path = self._resolve_path(file_path)

        if create_dirs:
            full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
            await f.write(content)

        return True

    async def append_to_file(self, file_path: str, content: str) -> bool:
        """
        Append content to file.

        Args:
            file_path: Path to file
            content: Content to append

        Returns:
            True if successful
        """
        full_path = self._resolve_path(file_path)

        async with aiofiles.open(full_path, "a", encoding="utf-8") as f:
            await f.write(content)

        return True

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to file

        Returns:
            True if successful
        """
        full_path = self._resolve_path(file_path)

        if full_path.exists():
            full_path.unlink()
            return True

        return False

    def list_files(
        self, pattern: str = "*", recursive: bool = True, include_hidden: bool = False
    ) -> List[str]:
        """
        List files matching pattern.

        Args:
            pattern: Glob pattern
            recursive: Search recursively
            include_hidden: Include hidden files

        Returns:
            List of file paths
        """
        if recursive:
            pattern = f"**/{pattern}"

        files = []
        for file_path in self.root_dir.glob(pattern):
            if file_path.is_file():
                # Skip hidden files if needed
                if not include_hidden and any(p.startswith(".") for p in file_path.parts):
                    continue

                # Skip ignored files
                if self.is_ignored(file_path):
                    continue

                rel_path = file_path.relative_to(self.root_dir)
                files.append(str(rel_path))

        return sorted(files)

    def search_in_files(
        self,
        pattern: str,
        file_pattern: str = "*.py",
        regex: bool = False,
        case_sensitive: bool = False,
    ) -> Dict[str, List[tuple]]:
        """
        Search for pattern in files.

        Args:
            pattern: Search pattern
            file_pattern: File glob pattern
            regex: Use regex matching
            case_sensitive: Case sensitive search

        Returns:
            Dict mapping file paths to list of (line_number, line_content) tuples
        """
        results = {}
        files = self.list_files(file_pattern, recursive=True)

        if regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            compiled_pattern = re.compile(pattern, flags)
        else:
            if not case_sensitive:
                pattern = pattern.lower()

        for file_path in files:
            try:
                full_path = self.root_dir / file_path
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    matches = []
                    for line_num, line in enumerate(f, 1):
                        search_line = line if case_sensitive else line.lower()

                        if regex:
                            if compiled_pattern.search(line):
                                matches.append((line_num, line.rstrip()))
                        else:
                            if pattern in search_line:
                                matches.append((line_num, line.rstrip()))

                    if matches:
                        results[file_path] = matches
            except Exception:
                # Skip files that can't be read
                pass

        return results

    def get_file_info(self, file_path: str) -> Dict:
        """
        Get file information.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file info
        """
        full_path = self._resolve_path(file_path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = full_path.stat()

        return {
            "path": str(file_path),
            "absolute_path": str(full_path),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "is_file": full_path.is_file(),
            "is_dir": full_path.is_dir(),
            "extension": full_path.suffix,
        }

    def create_directory(self, dir_path: str) -> bool:
        """
        Create a directory.

        Args:
            dir_path: Path to directory

        Returns:
            True if successful
        """
        full_path = self._resolve_path(dir_path)
        full_path.mkdir(parents=True, exist_ok=True)
        return True

    def copy_file(self, src: str, dest: str) -> bool:
        """
        Copy a file.

        Args:
            src: Source file path
            dest: Destination file path

        Returns:
            True if successful
        """
        src_path = self._resolve_path(src)
        dest_path = self._resolve_path(dest)

        shutil.copy2(src_path, dest_path)
        return True

    def move_file(self, src: str, dest: str) -> bool:
        """
        Move a file.

        Args:
            src: Source file path
            dest: Destination file path

        Returns:
            True if successful
        """
        src_path = self._resolve_path(src)
        dest_path = self._resolve_path(dest)

        shutil.move(str(src_path), str(dest_path))
        return True

    # Git operations

    def git_status(self) -> Optional[Dict]:
        """
        Get Git repository status.

        Returns:
            Status dictionary or None if not a Git repo
        """
        if not self.git_repo:
            return None

        return {
            "branch": self.git_repo.active_branch.name,
            "untracked": [item.a_path for item in self.git_repo.untracked_files],
            "modified": [item.a_path for item in self.git_repo.index.diff(None)],
            "staged": [item.a_path for item in self.git_repo.index.diff("HEAD")],
        }

    def git_diff(self, file_path: Optional[str] = None) -> str:
        """
        Get Git diff.

        Args:
            file_path: Specific file to diff (or all changes if None)

        Returns:
            Diff string
        """
        if not self.git_repo:
            return ""

        if file_path:
            return self.git_repo.git.diff(file_path)
        else:
            return self.git_repo.git.diff()

    def git_add(self, files: List[str]) -> bool:
        """
        Stage files for commit.

        Args:
            files: List of file paths to stage

        Returns:
            True if successful
        """
        if not self.git_repo:
            return False

        self.git_repo.index.add(files)
        return True

    def git_commit(self, message: str) -> bool:
        """
        Create a Git commit.

        Args:
            message: Commit message

        Returns:
            True if successful
        """
        if not self.git_repo:
            return False

        self.git_repo.index.commit(message)
        return True

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a path relative to root directory.

        Args:
            path: Path to resolve

        Returns:
            Absolute Path object
        """
        path_obj = Path(path)

        if path_obj.is_absolute():
            return path_obj
        else:
            return (self.root_dir / path_obj).resolve()

    def get_project_structure(self, max_depth: int = 3) -> Dict:
        """
        Get project directory structure.

        Args:
            max_depth: Maximum depth to traverse

        Returns:
            Directory structure as nested dict
        """

        def build_tree(path: Path, current_depth: int = 0) -> Dict:
            if current_depth >= max_depth:
                return {}

            tree = {}

            try:
                for item in sorted(path.iterdir()):
                    # Skip ignored items
                    if self.is_ignored(item):
                        continue

                    # Skip hidden items
                    if item.name.startswith("."):
                        continue

                    if item.is_dir():
                        tree[item.name + "/"] = build_tree(item, current_depth + 1)
                    else:
                        tree[item.name] = None
            except PermissionError:
                pass

            return tree

        return build_tree(self.root_dir)


class FileWatcher(FileSystemEventHandler):
    """Watch file system for changes"""

    def __init__(self, callback):
        """
        Initialize file watcher.

        Args:
            callback: Function to call on file changes
        """
        self.callback = callback

    def on_modified(self, event):
        """Handle file modification"""
        if not event.is_directory:
            self.callback("modified", event.src_path)

    def on_created(self, event):
        """Handle file creation"""
        if not event.is_directory:
            self.callback("created", event.src_path)

    def on_deleted(self, event):
        """Handle file deletion"""
        if not event.is_directory:
            self.callback("deleted", event.src_path)
