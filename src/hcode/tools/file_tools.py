"""
File operation tools for Hcode.
Includes Read, Write, Edit, Glob tools similar to Hcode.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import glob as glob_module

from .base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class ReadTool(BaseTool):
    """
    Read files from the filesystem with support for line ranges and offsets.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("file_path", "string", "Absolute path to the file to read", required=True),
            ToolParameter("offset", "integer", "Line number to start reading from (1-indexed)", default=1),
            ToolParameter("limit", "integer", "Number of lines to read", default=None),
        ]

    async def execute(self, file_path: str, offset: int = 1, limit: Optional[int] = None) -> ToolResult:
        """Read file contents with line numbers"""
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {file_path}"
                )

            if not path.is_file():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Not a file: {file_path}"
                )

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Apply offset and limit
            start_idx = max(0, offset - 1)
            end_idx = start_idx + limit if limit else len(lines)
            selected_lines = lines[start_idx:end_idx]

            # Format with line numbers (using cat -n format)
            output = ""
            for idx, line in enumerate(selected_lines, start=offset):
                output += f"{idx:6d}\t{line}"

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "file_path": str(path),
                    "total_lines": len(lines),
                    "lines_read": len(selected_lines),
                    "offset": offset
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class WriteTool(BaseTool):
    """
    Write content to files, creating them if they don't exist.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("file_path", "string", "Absolute path to write to", required=True),
            ToolParameter("content", "string", "Content to write", required=True),
        ]

    async def execute(self, file_path: str, content: str) -> ToolResult:
        """Write content to file"""
        try:
            path = Path(file_path)

            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"File written successfully: {path}",
                metadata={
                    "file_path": str(path),
                    "bytes_written": len(content.encode('utf-8'))
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class EditTool(BaseTool):
    """
    Edit files by replacing exact string matches.
    Uses old_string/new_string replacement for precise editing.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())
        self._file_read_cache = {}

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("file_path", "string", "Absolute path to file", required=True),
            ToolParameter("old_string", "string", "Exact string to replace", required=True),
            ToolParameter("new_string", "string", "Replacement string", required=True),
            ToolParameter("replace_all", "boolean", "Replace all occurrences", default=False),
        ]

    async def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False
    ) -> ToolResult:
        """Edit file by replacing old_string with new_string"""
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {file_path}"
                )

            # Read file
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if old_string exists
            if old_string not in content:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"String not found in file: {old_string[:100]}..."
                )

            # Check if replacement would be ambiguous
            if not replace_all and content.count(old_string) > 1:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"String appears {content.count(old_string)} times. Use replace_all=True or provide more context."
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Write back
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return ToolResult(
                success=True,
                output=f"File edited successfully. Replaced {replacements} occurrence(s).",
                metadata={
                    "file_path": str(path),
                    "replacements": replacements,
                    "old_length": len(old_string),
                    "new_length": len(new_string)
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class MultiEditTool(BaseTool):
    """
    Makes multiple sequential edits to a single file.
    More efficient than multiple Edit tool calls.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.name = "MultiEdit"
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="Absolute path to file",
                required=True
            ),
            ToolParameter(
                name="edits",
                type="array",
                description="Array of edit objects with old_string, new_string, and optional replace_all",
                required=True
            ),
        ]

    async def execute(self, file_path: str, edits: List[Dict[str, Any]]) -> ToolResult:
        """Apply multiple edits to a file"""
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {file_path}"
                )

            # Read file once
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            total_replacements = 0
            edit_results = []

            # Apply each edit sequentially
            for i, edit in enumerate(edits):
                old_string = edit.get("old_string")
                new_string = edit.get("new_string")
                replace_all = edit.get("replace_all", False)

                if not old_string or new_string is None:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Edit {i+1}: old_string and new_string are required"
                    )

                # Check if old_string exists
                if old_string not in content:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Edit {i+1}: String not found in file: {old_string[:100]}..."
                    )

                # Check if replacement would be ambiguous
                count = content.count(old_string)
                if not replace_all and count > 1:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Edit {i+1}: String appears {count} times. Use replace_all=true or provide more context."
                    )

                # Perform replacement
                if replace_all:
                    content = content.replace(old_string, new_string)
                    replacements = count
                else:
                    content = content.replace(old_string, new_string, 1)
                    replacements = 1

                total_replacements += replacements
                edit_results.append({
                    "edit_number": i + 1,
                    "replacements": replacements,
                    "old_length": len(old_string),
                    "new_length": len(new_string)
                })

            # Write back only if changes were made
            if content != original_content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)

                return ToolResult(
                    success=True,
                    output=f"File edited successfully. Applied {len(edits)} edits with {total_replacements} total replacements.",
                    metadata={
                        "file_path": str(path),
                        "total_edits": len(edits),
                        "total_replacements": total_replacements,
                        "edit_results": edit_results
                    }
                )
            else:
                return ToolResult(
                    success=True,
                    output="No changes were needed.",
                    metadata={
                        "file_path": str(path),
                        "total_edits": 0,
                        "total_replacements": 0
                    }
                )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class GlobTool(BaseTool):
    """
    Find files matching glob patterns.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("pattern", "string", "Glob pattern (e.g., '**/*.py')", required=True),
            ToolParameter("path", "string", "Directory to search in", default=None),
        ]

    async def execute(self, pattern: str, path: Optional[str] = None) -> ToolResult:
        """Find files matching pattern"""
        try:
            search_dir = Path(path) if path else self.root_dir

            if not search_dir.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Directory not found: {search_dir}"
                )

            # Find matching files
            matches = list(search_dir.glob(pattern))

            # Sort by modification time (most recent first)
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Convert to relative paths
            relative_matches = []
            for match in matches:
                try:
                    rel = match.relative_to(self.root_dir)
                    relative_matches.append(str(rel))
                except ValueError:
                    relative_matches.append(str(match))

            output = "\n".join(relative_matches) if relative_matches else "No matches found"

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "pattern": pattern,
                    "search_dir": str(search_dir),
                    "matches": len(relative_matches)
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class GrepTool(BaseTool):
    """
    Search for patterns in files using ripgrep-style interface.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("pattern", "string", "Search pattern (regex)", required=True),
            ToolParameter("path", "string", "File or directory to search", default=None),
            ToolParameter("glob", "string", "Glob pattern to filter files", default=None),
            ToolParameter("case_insensitive", "boolean", "Case insensitive search", default=False),
            ToolParameter("output_mode", "string", "Output mode: content, files_with_matches, count", default="files_with_matches"),
            ToolParameter("context_before", "integer", "Lines of context before match", default=0),
            ToolParameter("context_after", "integer", "Lines of context after match", default=0),
        ]

    async def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        case_insensitive: bool = False,
        output_mode: str = "files_with_matches",
        context_before: int = 0,
        context_after: int = 0
    ) -> ToolResult:
        """Search for pattern in files"""
        import re

        try:
            search_path = Path(path) if path else self.root_dir

            # Compile regex pattern
            flags = re.IGNORECASE if case_insensitive else 0
            regex = re.compile(pattern, flags)

            results = []

            # Determine files to search
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                # Use glob pattern or search all files
                if glob:
                    files_to_search = list(search_path.glob(glob))
                else:
                    files_to_search = [f for f in search_path.rglob("*") if f.is_file()]

            # Search in files
            for file_path in files_to_search:
                # Skip binary files and common ignore patterns
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                if 'node_modules' in file_path.parts or '__pycache__' in file_path.parts:
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                    matches_in_file = []
                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            matches_in_file.append((line_num, line.rstrip()))

                    if matches_in_file:
                        rel_path = file_path.relative_to(self.root_dir) if file_path.is_relative_to(self.root_dir) else file_path

                        if output_mode == "files_with_matches":
                            results.append(str(rel_path))
                        elif output_mode == "count":
                            results.append(f"{rel_path}:{len(matches_in_file)}")
                        elif output_mode == "content":
                            for line_num, line in matches_in_file:
                                results.append(f"{rel_path}:{line_num}:{line}")

                except Exception:
                    continue

            output = "\n".join(results) if results else "No matches found"

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "pattern": pattern,
                    "matches": len(results),
                    "output_mode": output_mode
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
