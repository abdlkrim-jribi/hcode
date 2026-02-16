"""
Context budget manager - prevents context overflow like Claude Code.

Implements safeguards:
1. Tool result truncation (max size limits)
2. Glob result limits (max files returned)
3. Context budget tracking
4. Proactive warnings and guidance
"""

from pathlib import Path
from typing import Optional, Tuple, List


class ContextBudgetManager:
    """
    Manages context budget to prevent overflow.

    Similar to Claude Code's approach:
    - Limits tool result sizes
    - Truncates large outputs
    - Provides helpful guidance
    - Prevents context explosion
    """

    # Claude Code-style limits
    MAX_GLOB_RESULTS = 1000  # Maximum files to return from Glob
    MAX_GLOB_DISPLAY = 100  # Maximum files to display in full
    MAX_TOOL_OUTPUT_CHARS = 30000  # Maximum characters per tool output
    MAX_FILE_LINES = 2000  # Maximum lines to read from a file

    # Directories to exclude from glob (like .gitignore)
    EXCLUDED_DIRS = {
        '.git', '.hg', '.svn',  # Version control
        '.venv', 'venv', 'env', 'virtualenv',  # Python virtual environments
        'node_modules', 'bower_components',  # JavaScript
        '__pycache__', '.pytest_cache', '.mypy_cache',  # Python cache
        'build', 'dist', 'target',  # Build outputs
        '.idea', '.vscode', '.vs',  # IDEs
        'coverage', '.coverage', 'htmlcov',  # Coverage
        '.tox', '.nox',  # Testing
    }

    # File patterns to exclude
    EXCLUDED_PATTERNS = {
        '*.pyc', '*.pyo', '*.pyd',  # Python bytecode
        '*.so', '*.dll', '*.dylib', '*.exe',  # Compiled libraries/executables
        '*.o', '*.a', '*.lib',  # Object files
        '*.class', '*.jar',  # Java
        '*.log', '*.tmp',  # Temp files
        '.DS_Store', 'Thumbs.db',  # OS files
    }

    def __init__(self, context_window: int = 128000):
        """
        Initialize budget manager.

        Args:
            context_window: Total context window size in tokens
        """
        self.context_window = context_window
        self.current_usage = 0
        self.warning_threshold = 0.8  # Warn at 80%

    def should_exclude_path(self, path: Path) -> bool:
        """
        Check if path should be excluded (like Claude Code's filtering).

        Args:
            path: Path to check

        Returns:
            True if should exclude
        """
        # Check if any parent directory is in excluded dirs
        for parent in path.parents:
            if parent.name in self.EXCLUDED_DIRS:
                return True

        # Check if the path itself is an excluded dir
        if path.is_dir() and path.name in self.EXCLUDED_DIRS:
            return True

        # Check file patterns
        for pattern in self.EXCLUDED_PATTERNS:
            if path.match(pattern):
                return True

        return False

    def filter_glob_results(
            self,
            matches: List[Path],
            pattern: str,
    ) -> Tuple[List[Path], bool, str]:
        """
        Filter and limit glob results like Claude Code.

        Args:
            matches: List of matched paths
            pattern: Original glob pattern

        Returns:
            Tuple of (filtered_paths, was_truncated, guidance_message)
        """
        # Filter out excluded paths
        filtered = [p for p in matches if not self.should_exclude_path(p)]

        was_truncated = False
        guidance = ""

        # Check if we have too many results
        if len(filtered) > self.MAX_GLOB_RESULTS:
            was_truncated = True
            filtered = filtered[:self.MAX_GLOB_RESULTS]

            guidance = f"""
[WARNING] Glob returned {len(matches)} files (showing first {self.MAX_GLOB_RESULTS})

To get more specific results, try:
- Use more specific patterns (e.g., 'src/**/*.py' instead of '**/*')
- Search in a specific directory
- Exclude large directories explicitly
- Use more specific file extensions

Example patterns:
  src/**/*.py        - Python files in src/
  tests/**/test_*.py - Test files
  *.md               - Markdown files in current directory
"""
        elif len(filtered) > self.MAX_GLOB_DISPLAY:
            # Many results but not over limit - just truncate display
            guidance = f"""
[INFO] Found {len(filtered)} files. Showing preview (first 50 and last 50).
Use a more specific pattern to see all results.
"""

        return filtered, was_truncated, guidance

    def format_glob_output(
            self,
            paths: List[Path],
            root_dir: Path,
            was_truncated: bool = False,
    ) -> str:
        """
        Format glob output with smart truncation.

        Args:
            paths: List of paths to format
            root_dir: Root directory for relative paths
            was_truncated: Whether results were truncated

        Returns:
            Formatted output string
        """
        if not paths:
            # This means all files were filtered out or no files matched
            # The caller should handle this distinction
            return "No files to display (all filtered or no matches)"

        # Convert to relative paths
        relative_paths = []
        for path in paths:
            try:
                rel = path.relative_to(root_dir)
                relative_paths.append(str(rel))
            except ValueError:
                relative_paths.append(str(path))

        # If we have many results, show preview
        if len(relative_paths) > self.MAX_GLOB_DISPLAY:
            # Show first 50 and last 50
            preview_count = 50
            first_part = relative_paths[:preview_count]
            last_part = relative_paths[-preview_count:]

            output_lines = first_part
            output_lines.append(f"... and {len(relative_paths) - 2 * preview_count} more")
            output_lines.extend(last_part)

            result = "\n".join(output_lines)
        else:
            result = "\n".join(relative_paths)

        # Add summary
        summary = f"\nFound {len(paths)} file(s)"
        if was_truncated:
            summary += f" (truncated from more)"

        return result + summary

    def truncate_tool_output(
            self,
            output: str,
            tool_name: str,
    ) -> Tuple[str, bool]:
        """
        Truncate tool output if too large.

        Args:
            output: Tool output string
            tool_name: Name of the tool

        Returns:
            Tuple of (truncated_output, was_truncated)
        """
        if len(output) <= self.MAX_TOOL_OUTPUT_CHARS:
            return output, False

        # Truncate in the middle to show both start and end
        half = self.MAX_TOOL_OUTPUT_CHARS // 2
        truncated = (
                output[:half] +
                f"\n\n... [Output truncated - {len(output)} chars total, showing {self.MAX_TOOL_OUTPUT_CHARS}] ...\n\n" +
                output[-half:]
        )

        return truncated, True

    def estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation (4 chars per token).

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        # Claude Code uses ~4 chars per token as rough estimate
        return len(text) // 4

    def check_context_budget(
            self,
            new_content: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if adding new content would exceed budget.

        Args:
            new_content: Content to add

        Returns:
            Tuple of (can_add, warning_message)
        """
        estimated_tokens = self.estimate_tokens(new_content)
        new_usage = self.current_usage + estimated_tokens

        # Check if we'd exceed the window
        if new_usage > self.context_window:
            return False, f"""
[ERROR] Context budget exceeded!

Current usage: {self.current_usage:,} tokens
New content: {estimated_tokens:,} tokens
Total: {new_usage:,} tokens
Limit: {self.context_window:,} tokens

The result is too large to fit in context. Please:
- Use more specific queries
- Search in smaller directories
- Read files in chunks (use StartLine/EndLine)
- Use Grep instead of Glob for finding specific content
"""

        # Warn if approaching limit
        usage_ratio = new_usage / self.context_window
        if usage_ratio >= self.warning_threshold:
            warning = f"""
[WARNING] Context budget at {usage_ratio * 100:.0f}%

Current: {self.current_usage:,} tokens
After this: {new_usage:,} tokens
Limit: {self.context_window:,} tokens

Consider:
- Being more specific in your queries
- Reading files in chunks
- Using Grep for specific searches
"""
            return True, warning

        return True, None

    def update_usage(self, text: str):
        """
        Update current context usage.

        Args:
            text: Text that was added to context
        """
        self.current_usage += self.estimate_tokens(text)

    def get_usage_stats(self) -> dict:
        """
        Get current usage statistics.

        Returns:
            Dict with usage stats
        """
        usage_ratio = self.current_usage / self.context_window

        return {
            "current_tokens": self.current_usage,
            "total_tokens": self.context_window,
            "usage_percent": usage_ratio * 100,
            "remaining_tokens": self.context_window - self.current_usage,
            "status": "healthy" if usage_ratio < 0.7 else "warning" if usage_ratio < 0.9 else "critical"
        }
