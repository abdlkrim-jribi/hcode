"""
Layer 1: File-based memory using markdown files.
Mirrors Claude Code's CLAUDE.md approach with hierarchical loading.

Hierarchy (all loaded, in order):
1. ~/.hcode/AGENT.md          - Global preferences (always loaded)
2. /project/AGENT.md          - Project-specific context (version controlled)
3. /project/AGENT.local.md    - Personal project prefs (gitignored)
4. /project/subdir/AGENT.md   - Subdirectory context (loaded when working there)
"""
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
import os

from .config import config


@dataclass
class MemoryFile:
    """Represents a single memory file."""
    path: Path
    content: str
    priority: int  # Lower = loaded first
    scope: str  # "global", "project", "local", "subdirectory"
    size_bytes: int = 0

    def __post_init__(self):
        self.size_bytes = len(self.content.encode('utf-8'))


class FileMemory:
    """
    Manages hierarchical markdown memory files.

    Hierarchy (all loaded, in order):
    1. ~/.hcode/AGENT.md          - Global preferences (always loaded)
    2. /project/AGENT.md          - Project-specific context (version controlled)
    3. /project/AGENT.local.md    - Personal project prefs (gitignored)
    4. /project/subdir/AGENT.md   - Subdirectory context (loaded when working there)
    """

    # Project root markers
    PROJECT_MARKERS = [
        ".git", "package.json", "pyproject.toml", "Cargo.toml",
        "go.mod", "pom.xml", "build.gradle", "Makefile",
        "CMakeLists.txt", ".hcode", "setup.py", "requirements.txt"
    ]

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize file memory.

        Args:
            project_root: Explicit project root, or auto-detect
        """
        self.project_root = project_root or self._detect_project_root()
        self._cache: Dict[Path, MemoryFile] = {}

    def _detect_project_root(self) -> Optional[Path]:
        """Find project root by looking for common project markers."""
        current = Path.cwd()

        while current != current.parent:
            if any((current / marker).exists() for marker in self.PROJECT_MARKERS):
                return current
            current = current.parent

        return Path.cwd()  # Fallback to current directory

    def get_memory_files(self, current_dir: Optional[Path] = None) -> List[MemoryFile]:
        """
        Get all applicable memory files for the current context.
        Returns files in priority order (global first, most specific last).

        Args:
            current_dir: Current working directory for subdirectory context

        Returns:
            List of MemoryFile objects in priority order
        """
        files = []
        current_dir = current_dir or Path.cwd()

        # 1. Global memory (always loaded)
        global_file = config.global_memory_path
        if global_file.exists():
            try:
                content = global_file.read_text(encoding='utf-8')
                files.append(MemoryFile(
                    path=global_file,
                    content=content,
                    priority=0,
                    scope="global"
                ))
            except Exception:
                pass  # Skip if unreadable

        if self.project_root:
            # 2. Project memory
            project_file = config.get_project_memory_path(self.project_root)
            if project_file.exists():
                try:
                    content = project_file.read_text(encoding='utf-8')
                    files.append(MemoryFile(
                        path=project_file,
                        content=content,
                        priority=1,
                        scope="project"
                    ))
                except Exception:
                    pass

            # 3. Local project memory (gitignored)
            local_file = config.get_local_memory_path(self.project_root)
            if local_file.exists():
                try:
                    content = local_file.read_text(encoding='utf-8')
                    files.append(MemoryFile(
                        path=local_file,
                        content=content,
                        priority=2,
                        scope="local"
                    ))
                except Exception:
                    pass

            # 4. Subdirectory memory files (between project root and current dir)
            try:
                if current_dir.is_relative_to(self.project_root):
                    relative = current_dir.relative_to(self.project_root)
                    for i, part in enumerate(relative.parts):
                        subdir = self.project_root / Path(*relative.parts[:i + 1])
                        subdir_file = subdir / config.project_memory_file
                        if subdir_file.exists() and subdir_file != project_file:
                            try:
                                content = subdir_file.read_text(encoding='utf-8')
                                files.append(MemoryFile(
                                    path=subdir_file,
                                    content=content,
                                    priority=3 + i,
                                    scope="subdirectory"
                                ))
                            except Exception:
                                pass
            except ValueError:
                pass  # current_dir not relative to project_root

        return sorted(files, key=lambda f: f.priority)

    def get_combined_context(self, current_dir: Optional[Path] = None) -> str:
        """
        Combine all memory files into a single context string.
        Format suitable for injection into system prompt.

        Args:
            current_dir: Current working directory

        Returns:
            Combined context string with section headers
        """
        files = self.get_memory_files(current_dir)

        if not files:
            return ""

        sections = []
        for f in files:
            # Create header based on scope
            if f.scope == "global":
                header = f"# Global Memory (~/.hcode/AGENT.md)"
            elif f.scope == "project":
                header = f"# Project Memory ({f.path.name})"
            elif f.scope == "local":
                header = f"# Local Memory ({f.path.name}) [gitignored]"
            else:
                header = f"# Subdirectory Memory ({f.path.parent.name}/{f.path.name})"

            sections.append(f"{header}\n\n{f.content}")

        return "\n\n---\n\n".join(sections)

    def update_memory(
        self,
        content: str,
        scope: str = "project",
        append: bool = False,
        section: Optional[str] = None
    ) -> Path:
        """
        Update or create a memory file.

        Args:
            content: The content to write
            scope: "global", "project", or "local"
            append: If True, append to existing content
            section: If provided, update only this section (markdown heading)

        Returns:
            Path to the updated file
        """
        if scope == "global":
            file_path = config.global_memory_path
        elif scope == "local":
            if not self.project_root:
                raise ValueError("No project root found for local memory")
            file_path = config.get_local_memory_path(self.project_root)
            self._ensure_gitignored(file_path)
        else:  # project
            if not self.project_root:
                raise ValueError("No project root found for project memory")
            file_path = config.get_project_memory_path(self.project_root)

        # Handle section update
        if section and file_path.exists():
            existing = file_path.read_text(encoding='utf-8')
            content = self._update_section(existing, section, content)
        elif append and file_path.exists():
            existing = file_path.read_text(encoding='utf-8')
            content = f"{existing}\n\n{content}"

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')

        # Clear cache for this file
        if file_path in self._cache:
            del self._cache[file_path]

        return file_path

    def _update_section(self, existing: str, section: str, new_content: str) -> str:
        """Update a specific section in a markdown file."""
        lines = existing.split('\n')
        result = []
        in_section = False
        section_found = False
        section_level = 0

        for line in lines:
            # Check if this is the target section
            if line.strip().startswith('#'):
                heading_match = line.lstrip('#')
                level = len(line) - len(line.lstrip('#'))

                if section.lower() in line.lower():
                    # Found the section
                    in_section = True
                    section_found = True
                    section_level = level
                    result.append(line)
                    result.append('')
                    result.append(new_content)
                    continue
                elif in_section and level <= section_level:
                    # End of section (found same or higher level heading)
                    in_section = False

            if not in_section:
                result.append(line)

        # If section not found, append it
        if not section_found:
            result.append('')
            result.append(f"## {section}")
            result.append('')
            result.append(new_content)

        return '\n'.join(result)

    def _ensure_gitignored(self, file_path: Path):
        """Ensure local memory files are gitignored."""
        if not self.project_root:
            return

        gitignore = self.project_root / ".gitignore"
        pattern = config.local_memory_file

        if gitignore.exists():
            content = gitignore.read_text(encoding='utf-8')
            if pattern not in content:
                with gitignore.open("a", encoding='utf-8') as f:
                    f.write(f"\n# HCODE agent local memory\n{pattern}\n")
        else:
            gitignore.write_text(f"# HCODE agent local memory\n{pattern}\n", encoding='utf-8')

    def create_template(self, scope: str = "project") -> str:
        """
        Generate a template for a new memory file.

        Args:
            scope: "global" or "project"

        Returns:
            Template string
        """
        if scope == "global":
            return """# Global HCODE Agent Memory

## User Preferences
<!-- Your preferences that apply across all projects -->
- Preferred programming language:
- Code style preferences:
- Communication style:
- Timezone:

## Common Patterns
<!-- Patterns and conventions you use across projects -->

## Shortcuts & Aliases
<!-- Custom shortcuts or command preferences -->

## Notes
<!-- Persistent notes for the agent -->
"""
        else:
            return """# Project HCODE Agent Memory

## Project Overview
<!-- Brief description of this project -->

## Tech Stack
- Language:
- Framework:
- Key dependencies:
- Build system:

## Architecture
<!-- Key architectural decisions and patterns -->

## Code Conventions
<!-- Project-specific coding conventions -->
- Naming conventions:
- File organization:
- Testing approach:

## Important Files
<!-- Key files the agent should know about -->

## Current Focus
<!-- What you're currently working on -->

## Known Issues
<!-- Current bugs or technical debt -->

## Notes
<!-- Important context for the agent -->
"""

    def get_memory_stats(self) -> Dict[str, any]:
        """Get statistics about loaded memory files."""
        files = self.get_memory_files()
        return {
            "file_count": len(files),
            "total_bytes": sum(f.size_bytes for f in files),
            "files": [
                {
                    "path": str(f.path),
                    "scope": f.scope,
                    "size_bytes": f.size_bytes
                }
                for f in files
            ]
        }

    def search_memory(self, query: str, current_dir: Optional[Path] = None) -> List[Dict]:
        """
        Search memory files for a query string.

        Args:
            query: Search string
            current_dir: Current directory for context

        Returns:
            List of matches with file, line number, and content
        """
        files = self.get_memory_files(current_dir)
        results = []
        query_lower = query.lower()

        for f in files:
            lines = f.content.split('\n')
            for i, line in enumerate(lines, 1):
                if query_lower in line.lower():
                    results.append({
                        "file": str(f.path),
                        "scope": f.scope,
                        "line": i,
                        "content": line.strip(),
                        "context": self._get_line_context(lines, i - 1)
                    })

        return results

    def _get_line_context(self, lines: List[str], index: int, context_lines: int = 2) -> str:
        """Get surrounding lines for context."""
        start = max(0, index - context_lines)
        end = min(len(lines), index + context_lines + 1)
        return '\n'.join(lines[start:end])
