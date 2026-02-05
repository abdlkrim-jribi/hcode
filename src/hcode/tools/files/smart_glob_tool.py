"""
Smart Glob tool with Claude Code-style safeguards.

Prevents context overflow by:
1. Limiting number of results
2. Excluding common bloat directories
3. Providing helpful guidance
4. Smart truncation and previews
"""

import os
from pathlib import Path
from typing import List, Optional

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory
from hcode.core.context.budget_manager import ContextBudgetManager


class SmartGlobTool(BaseTool):
    """
    Find files matching glob patterns with context protection.

    Similar to Claude Code's Glob tool:
    - Automatically excludes .git, .venv, node_modules, etc.
    - Limits results to prevent context overflow
    - Provides helpful guidance for large result sets
    - Shows smart previews with "... and N more" truncation
    """

    # Tool name must match GlobTool for alias compatibility
    name = "GlobTool"

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.root_dir = Path(root_dir or os.getcwd())
        self.budget_manager = ContextBudgetManager()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                "Pattern",
                "string",
                """Glob pattern to match files.

Examples:
  **/*.py          - All Python files recursively
  src/**/*.py      - Python files in src/
  tests/test_*.py  - Test files
  *.md             - Markdown in current dir

Note: Automatically excludes .git, .venv, node_modules, __pycache__, etc.
""",
                required=True
            ),
            ToolParameter(
                "SearchDirectory",
                "string",
                "Directory to search in (default: project root)",
                default=None
            ),
        ]

    async def execute(
        self,
        Pattern: str,
        SearchDirectory: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """Find files matching pattern with context protection."""

        try:
            search_dir = Path(SearchDirectory) if SearchDirectory else self.root_dir

            if not search_dir.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Directory not found: {search_dir}"
                )

            # Find matching files
            matches = list(search_dir.glob(Pattern))

            # Sort by modification time (most recent first)
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Filter and limit results (Claude Code approach)
            filtered, was_truncated, guidance = self.budget_manager.filter_glob_results(
                matches, Pattern
            )

            # Format output with smart truncation
            output = self.budget_manager.format_glob_output(
                filtered, self.root_dir, was_truncated
            )

            # Add guidance if results were filtered
            if guidance:
                output = guidance + "\n" + output

            # Check context budget
            can_add, warning = self.budget_manager.check_context_budget(output)
            if not can_add:
                return ToolResult(
                    success=False,
                    output=None,
                    error=warning
                )

            if warning:
                output = warning + "\n" + output

            # Provide helpful message if no matches
            if not filtered:
                help_msg = self._generate_no_match_help(Pattern, search_dir)
                output = help_msg

            # Display with Hcode UI
            try:
                from hcode.ui.hcode_display import get_hcode_display
                display = get_hcode_display()
                display.display_tool_result("SmartGlob", output, "success")
            except ImportError:
                pass

            return ToolResult(
                success=True,
                output=output,
                error=None,
                metadata={
                    "total_matches": len(matches),
                    "filtered_matches": len(filtered),
                    "was_truncated": was_truncated,
                    "excluded_count": len(matches) - len(filtered),
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Glob failed: {str(e)}"
            )

    def _generate_no_match_help(self, pattern: str, search_dir: Path) -> str:
        """
        Generate helpful message when no files match.

        Args:
            pattern: The glob pattern that didn't match
            search_dir: Directory that was searched

        Returns:
            Helpful message string
        """
        # Find subdirectories that might be relevant
        subdirs = []
        try:
            for item in search_dir.iterdir():
                if item.is_dir() and not self.budget_manager.should_exclude_path(item):
                    subdirs.append(item.name)
        except (PermissionError, OSError):
            pass

        help_msg = f"No files found matching '{pattern}' in {search_dir}\n"

        if subdirs:
            help_msg += f"\nAvailable directories:\n"
            for subdir in subdirs[:10]:  # Show first 10
                help_msg += f"  - {subdir}/\n"

            help_msg += "\nTry patterns like:\n"
            if subdirs:
                help_msg += f"  - {subdirs[0]}/**/*.py  (all Python files in {subdirs[0]}/)\n"
            help_msg += "  - **/*.md              (all Markdown files)\n"
            help_msg += "  - src/**/*.py          (Python files in src/)\n"

        return help_msg

    def get_description(self) -> str:
        return """Find files matching glob patterns.

This tool automatically:
- Excludes .git, .venv, node_modules, __pycache__, and other cache directories
- Limits results to prevent context overflow
- Sorts by modification time (most recent first)
- Shows smart previews for large result sets

For large result sets, use more specific patterns:
  ✓ GOOD: src/**/*.py          (specific directory and extension)
  ✓ GOOD: tests/test_*.py      (specific pattern)
  ✗ BAD:  **/*                 (matches everything, will be truncated)

Maximum results: 1000 files
Display limit: 100 files (others shown as "... and N more")
"""
