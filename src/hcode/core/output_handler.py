"""
Smart Output Handler for Hcode.

Handles large outputs from commands and files with:
- Intelligent truncation (keeps first N + last M lines)
- Error extraction and highlighting
- Pattern search within outputs
- Diff detection and formatting
- Memory-efficient streaming for very large outputs

Similar to Claude Code's output handling approach.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class OutputType(Enum):
    """Types of output content"""

    STDOUT = "stdout"
    STDERR = "stderr"
    FILE_CONTENT = "file"
    DIFF = "diff"
    LOG = "log"
    TEST_RESULT = "test"
    BUILD_OUTPUT = "build"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for extracted errors"""

    CRITICAL = "critical"  # Fatal errors, crashes
    ERROR = "error"  # Standard errors
    WARNING = "warning"  # Warnings
    INFO = "info"  # Informational messages


@dataclass
class ExtractedError:
    """Represents an extracted error from output"""

    message: str
    severity: ErrorSeverity
    line_number: Optional[int] = None
    file_path: Optional[str] = None
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    error_type: Optional[str] = None  # e.g., "SyntaxError", "ModuleNotFoundError"
    suggestion: Optional[str] = None  # Suggested fix if detectable

    def __str__(self) -> str:
        parts = [f"[{self.severity.value.upper()}]"]
        if self.file_path:
            parts.append(f"{self.file_path}")
            if self.line_number:
                parts.append(f":{self.line_number}")
        if self.error_type:
            parts.append(f" {self.error_type}:")
        parts.append(f" {self.message}")
        return "".join(parts)


@dataclass
class SearchMatch:
    """Represents a search match in output"""

    line_number: int
    line_content: str
    match_start: int
    match_end: int
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)


@dataclass
class TruncatedOutput:
    """Result of truncating large output"""

    content: str  # The truncated content
    original_lines: int  # Total lines in original
    displayed_lines: int  # Lines shown
    truncated: bool  # Whether truncation occurred
    head_lines: int  # Lines from start
    tail_lines: int  # Lines from end
    omitted_lines: int  # Lines omitted in middle
    errors_found: List[ExtractedError] = field(default_factory=list)
    warnings_found: int = 0
    has_stack_trace: bool = False


class OutputHandler:
    """
    Smart output handler for large console outputs and file contents.

    Features:
    - Intelligent truncation preserving important content
    - Error/warning extraction with context
    - Pattern search with highlighting
    - Stack trace detection and preservation
    - Memory-efficient processing
    """

    # Default configuration
    DEFAULT_HEAD_LINES = 20  # Lines to show from start
    DEFAULT_TAIL_LINES = 5  # Lines to show from end (always show latest)
    DEFAULT_MAX_LINES = 100  # Max total lines before truncation
    DEFAULT_MAX_LINE_LENGTH = 500  # Max characters per line
    DEFAULT_CONTEXT_LINES = 3  # Context lines around errors

    # Error patterns for different languages/tools
    ERROR_PATTERNS = {
        # Python errors
        "python_error": re.compile(
            r'^(\s*File "([^"]+)", line (\d+).*$|'
            r"^\s*((?:Traceback|.*Error|.*Exception|.*Warning)[^\n]*$))",
            re.MULTILINE | re.IGNORECASE,
        ),
        "python_traceback": re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE),
        "python_exception": re.compile(
            r"^(\w+Error|\w+Exception|\w+Warning):\s*(.+)$", re.MULTILINE
        ),
        # JavaScript/Node errors
        "js_error": re.compile(
            r"^(\s*at\s+.+\(.*:\d+:\d+\)|"
            r"^\s*((?:TypeError|ReferenceError|SyntaxError|Error)[^\n]*$))",
            re.MULTILINE,
        ),
        # Rust errors
        "rust_error": re.compile(
            r"^error(\[E\d+\])?:\s*(.+)$|" r"^\s*-->\s*([^:]+):(\d+):(\d+)", re.MULTILINE
        ),
        # Go errors
        "go_error": re.compile(
            r"^([^:]+):(\d+):(\d+):\s*(.*(?:error|undefined|cannot).*)$",
            re.MULTILINE | re.IGNORECASE,
        ),
        # Generic error patterns
        "generic_error": re.compile(
            r"^.*(?:error|failed|failure|exception|fatal|critical|panic).*$",
            re.MULTILINE | re.IGNORECASE,
        ),
        "generic_warning": re.compile(
            r"^.*(?:warning|warn|deprecated|caution).*$", re.MULTILINE | re.IGNORECASE
        ),
        # Test failures
        "test_failure": re.compile(
            r"^(?:FAILED|FAIL|ERROR|BROKEN|✗|✘|×)[\s:].*$|"
            r"^\s*(?:assert|expect).*(?:failed|error).*$",
            re.MULTILINE | re.IGNORECASE,
        ),
        # Build errors
        "build_error": re.compile(
            r"^(?:ERROR|error):\s*.*$|" r"^\s*(?:compilation|build)\s+(?:failed|error).*$",
            re.MULTILINE | re.IGNORECASE,
        ),
    }

    # Patterns that indicate important content to preserve
    IMPORTANT_PATTERNS = [
        re.compile(r"Traceback", re.IGNORECASE),
        re.compile(r"Error:|Exception:", re.IGNORECASE),
        re.compile(r"FAILED|FAIL:", re.IGNORECASE),
        re.compile(r"assert.*failed", re.IGNORECASE),
        re.compile(r"^\s*>\s+", re.MULTILINE),  # pytest error indicator
        re.compile(r"^E\s+", re.MULTILINE),  # pytest assertion error
    ]

    def __init__(
        self,
        head_lines: int = DEFAULT_HEAD_LINES,
        tail_lines: int = DEFAULT_TAIL_LINES,
        max_lines: int = DEFAULT_MAX_LINES,
        max_line_length: int = DEFAULT_MAX_LINE_LENGTH,
        context_lines: int = DEFAULT_CONTEXT_LINES,
    ):
        self.head_lines = head_lines
        self.tail_lines = tail_lines
        self.max_lines = max_lines
        self.max_line_length = max_line_length
        self.context_lines = context_lines

    def process_output(
        self,
        output: str,
        output_type: OutputType = OutputType.UNKNOWN,
        extract_errors: bool = True,
        preserve_important: bool = True,
    ) -> TruncatedOutput:
        """
        Process and intelligently truncate output.

        Args:
            output: The raw output string
            output_type: Type of output for specialized processing
            extract_errors: Whether to extract error information
            preserve_important: Whether to preserve important lines (errors, etc.)

        Returns:
            TruncatedOutput with processed content and metadata
        """
        if not output:
            return TruncatedOutput(
                content="(no output)",
                original_lines=0,
                displayed_lines=0,
                truncated=False,
                head_lines=0,
                tail_lines=0,
                omitted_lines=0,
            )

        lines = output.splitlines()
        original_line_count = len(lines)

        # Extract errors first (before truncation)
        errors = []
        warnings_count = 0
        has_stack_trace = False

        if extract_errors:
            errors = self._extract_errors(lines, output_type)
            warnings_count = sum(1 for e in errors if e.severity == ErrorSeverity.WARNING)
            has_stack_trace = self._has_stack_trace(output)

        # Find important lines to preserve
        important_line_indices = set()
        if preserve_important:
            important_line_indices = self._find_important_lines(lines)

        # Truncate if necessary
        if original_line_count <= self.max_lines:
            # No truncation needed
            processed_lines = [self._truncate_line(line) for line in lines]
            return TruncatedOutput(
                content="\n".join(processed_lines),
                original_lines=original_line_count,
                displayed_lines=original_line_count,
                truncated=False,
                head_lines=original_line_count,
                tail_lines=0,
                omitted_lines=0,
                errors_found=errors,
                warnings_found=warnings_count,
                has_stack_trace=has_stack_trace,
            )

        # Smart truncation
        truncated_content, head_count, tail_count = self._smart_truncate(
            lines, important_line_indices
        )

        return TruncatedOutput(
            content=truncated_content,
            original_lines=original_line_count,
            displayed_lines=head_count + tail_count,
            truncated=True,
            head_lines=head_count,
            tail_lines=tail_count,
            omitted_lines=original_line_count - head_count - tail_count,
            errors_found=errors,
            warnings_found=warnings_count,
            has_stack_trace=has_stack_trace,
        )

    def _smart_truncate(
        self,
        lines: List[str],
        important_indices: set,
    ) -> Tuple[str, int, int]:
        """
        Intelligently truncate lines while preserving important content.

        Strategy:
        1. Always show first N lines (head)
        2. Always show last M lines (tail) - MOST IMPORTANT for seeing latest output
        3. Preserve lines with errors/important content
        4. Show truncation indicator in middle
        """
        total = len(lines)

        # Calculate head and tail sizes
        # Prioritize tail (latest output) when space is limited
        available = self.max_lines - 3  # Reserve 3 lines for truncation message

        # Ensure we always show at least tail_lines at the end
        actual_tail = min(self.tail_lines, available // 2, total)
        actual_head = min(self.head_lines, available - actual_tail, total - actual_tail)

        # Adjust if overlap would occur
        if actual_head + actual_tail >= total:
            # No truncation needed after adjustment
            processed = [self._truncate_line(line) for line in lines]
            return "\n".join(processed), total, 0

        # Build output
        result_lines = []

        # Add head lines
        for i in range(actual_head):
            result_lines.append(self._truncate_line(lines[i]))

        # Add truncation indicator
        omitted = total - actual_head - actual_tail

        # Check if there are important lines in the omitted section
        important_in_middle = [
            i for i in important_indices if actual_head <= i < total - actual_tail
        ]

        if important_in_middle and len(important_in_middle) <= 10:
            # Show important lines from middle section
            result_lines.append("")
            result_lines.append(
                f"... [{omitted} lines omitted, showing {len(important_in_middle)} important lines] ..."
            )
            result_lines.append("")

            for idx in sorted(important_in_middle)[:10]:
                result_lines.append(f"  [{idx + 1}] {self._truncate_line(lines[idx])}")

            result_lines.append("")
        else:
            result_lines.append("")
            result_lines.append(f"... [{omitted} lines omitted] ...")
            result_lines.append("")

        # Add tail lines (latest output - most important!)
        result_lines.append(f"--- Latest {actual_tail} lines ---")
        for i in range(total - actual_tail, total):
            result_lines.append(self._truncate_line(lines[i]))

        return "\n".join(result_lines), actual_head, actual_tail

    def _truncate_line(self, line: str) -> str:
        """Truncate a single line if too long"""
        if len(line) <= self.max_line_length:
            return line
        return line[: self.max_line_length - 3] + "..."

    def _find_important_lines(self, lines: List[str]) -> set:
        """Find line indices that contain important content"""
        important = set()

        for i, line in enumerate(lines):
            for pattern in self.IMPORTANT_PATTERNS:
                if pattern.search(line):
                    # Add this line and context
                    for j in range(
                        max(0, i - self.context_lines), min(len(lines), i + self.context_lines + 1)
                    ):
                        important.add(j)
                    break

        return important

    def _has_stack_trace(self, output: str) -> bool:
        """Check if output contains a stack trace"""
        return bool(self.ERROR_PATTERNS["python_traceback"].search(output))

    def _extract_errors(
        self,
        lines: List[str],
        output_type: OutputType,
    ) -> List[ExtractedError]:
        """Extract error information from output lines"""
        errors = []
        full_text = "\n".join(lines)

        # Try Python errors first (most common in this context)
        errors.extend(self._extract_python_errors(lines, full_text))

        # Try generic patterns if no specific errors found
        if not errors:
            errors.extend(self._extract_generic_errors(lines))

        return errors

    def _extract_python_errors(
        self,
        lines: List[str],
        full_text: str,
    ) -> List[ExtractedError]:
        """Extract Python-specific errors"""
        errors = []

        # Find exception lines
        for match in self.ERROR_PATTERNS["python_exception"].finditer(full_text):
            error_type = match.group(1)
            message = match.group(2)

            # Determine severity
            if "Warning" in error_type:
                severity = ErrorSeverity.WARNING
            elif error_type in ("SyntaxError", "IndentationError", "TabError"):
                severity = ErrorSeverity.CRITICAL
            else:
                severity = ErrorSeverity.ERROR

            # Find line number in output
            line_num = None
            file_path = None
            for i, line in enumerate(lines):
                if match.group(0) in line:
                    line_num = i + 1
                    # Look for file reference above
                    for j in range(max(0, i - 5), i):
                        file_match = re.search(r'File "([^"]+)", line (\d+)', lines[j])
                        if file_match:
                            file_path = file_match.group(1)
                            break
                    break

            # Generate suggestion for common errors
            suggestion = self._suggest_fix(error_type, message)

            errors.append(
                ExtractedError(
                    message=message,
                    severity=severity,
                    line_number=line_num,
                    file_path=file_path,
                    error_type=error_type,
                    suggestion=suggestion,
                )
            )

        return errors

    def _extract_generic_errors(self, lines: List[str]) -> List[ExtractedError]:
        """Extract generic error patterns"""
        errors = []

        for i, line in enumerate(lines):
            # Check for error patterns
            if self.ERROR_PATTERNS["generic_error"].search(line):
                errors.append(
                    ExtractedError(
                        message=line.strip(),
                        severity=ErrorSeverity.ERROR,
                        line_number=i + 1,
                        context_before=lines[max(0, i - 2) : i],
                        context_after=lines[i + 1 : min(len(lines), i + 3)],
                    )
                )
            elif self.ERROR_PATTERNS["generic_warning"].search(line):
                errors.append(
                    ExtractedError(
                        message=line.strip(),
                        severity=ErrorSeverity.WARNING,
                        line_number=i + 1,
                    )
                )

        # Limit to most important errors
        return errors[:20]

    def _suggest_fix(self, error_type: str, message: str) -> Optional[str]:
        """Generate fix suggestions for common errors"""

        # Helper to extract module name from message
        def get_module_name(m: str) -> str:
            if "'" in m:
                parts = m.split("'")
                return parts[1] if len(parts) > 1 else "package"
            return "package"

        suggestions = {
            "ModuleNotFoundError": lambda m: f"Install missing module: pip install {get_module_name(m)}",
            "ImportError": lambda m: "Check module path and ensure it exists",
            "FileNotFoundError": lambda m: "Verify the file path exists",
            "SyntaxError": lambda m: "Check for missing colons, brackets, or quotes",
            "IndentationError": lambda m: "Fix indentation - use consistent spaces or tabs",
            "NameError": lambda m: "Variable or function is not defined - check spelling",
            "TypeError": lambda m: "Check argument types and function signatures",
            "AttributeError": lambda m: "Object doesn't have this attribute - check spelling",
            "KeyError": lambda m: "Key doesn't exist in dictionary - check key name",
            "IndexError": lambda m: "Index out of range - check list/array length",
            "ValueError": lambda m: "Invalid value - check data format",
            "ZeroDivisionError": lambda m: "Add check for zero before division",
            "PermissionError": lambda m: "Check file permissions or run with elevated privileges",
            "ConnectionError": lambda m: "Check network connection and endpoint availability",
            "TimeoutError": lambda m: "Increase timeout or check if service is responding",
        }

        if error_type in suggestions:
            return suggestions[error_type](message)
        return None

    def search_output(
        self,
        output: str,
        pattern: str,
        regex: bool = False,
        case_sensitive: bool = False,
        context_lines: int = 2,
        max_matches: int = 50,
    ) -> List[SearchMatch]:
        """
        Search for pattern in output.

        Args:
            output: The output to search
            pattern: Pattern to search for
            regex: Whether pattern is a regex
            case_sensitive: Case-sensitive search
            context_lines: Lines of context around matches
            max_matches: Maximum matches to return

        Returns:
            List of SearchMatch objects
        """
        lines = output.splitlines()
        matches = []

        # Compile pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        if regex:
            try:
                compiled = re.compile(pattern, flags)
            except re.error:
                return []
        else:
            # Escape special regex characters for literal search
            compiled = re.compile(re.escape(pattern), flags)

        for i, line in enumerate(lines):
            match = compiled.search(line)
            if match:
                matches.append(
                    SearchMatch(
                        line_number=i + 1,
                        line_content=line,
                        match_start=match.start(),
                        match_end=match.end(),
                        context_before=lines[max(0, i - context_lines) : i],
                        context_after=lines[i + 1 : min(len(lines), i + context_lines + 1)],
                    )
                )

                if len(matches) >= max_matches:
                    break

        return matches

    def format_for_display(
        self,
        truncated: TruncatedOutput,
        show_stats: bool = True,
        show_errors: bool = True,
        max_error_display: int = 5,
    ) -> str:
        """
        Format truncated output for console display.

        Args:
            truncated: TruncatedOutput object
            show_stats: Whether to show statistics header
            show_errors: Whether to show extracted errors
            max_error_display: Maximum errors to show

        Returns:
            Formatted string for display
        """
        parts = []

        # Stats header
        if show_stats and truncated.truncated:
            stats = (
                f"[Output: {truncated.original_lines} lines, showing {truncated.displayed_lines}]"
            )
            if truncated.errors_found:
                error_count = len(
                    [e for e in truncated.errors_found if e.severity != ErrorSeverity.WARNING]
                )
                stats += f" [{error_count} errors, {truncated.warnings_found} warnings]"
            parts.append(stats)
            parts.append("")

        # Error summary (if any)
        if show_errors and truncated.errors_found:
            critical_errors = [
                e
                for e in truncated.errors_found
                if e.severity in (ErrorSeverity.CRITICAL, ErrorSeverity.ERROR)
            ]
            if critical_errors:
                parts.append("=== ERRORS DETECTED ===")
                for error in critical_errors[:max_error_display]:
                    parts.append(str(error))
                    if error.suggestion:
                        parts.append(f"    Suggestion: {error.suggestion}")
                if len(critical_errors) > max_error_display:
                    parts.append(
                        f"    ... and {len(critical_errors) - max_error_display} more errors"
                    )
                parts.append("=" * 23)
                parts.append("")

        # Main content
        parts.append(truncated.content)

        return "\n".join(parts)

    def get_tail(self, output: str, lines: int = 5) -> str:
        """
        Get the last N lines of output.

        Args:
            output: The output string
            lines: Number of lines to get

        Returns:
            Last N lines
        """
        all_lines = output.splitlines()
        if len(all_lines) <= lines:
            return output
        return "\n".join(all_lines[-lines:])

    def get_head(self, output: str, lines: int = 20) -> str:
        """
        Get the first N lines of output.

        Args:
            output: The output string
            lines: Number of lines to get

        Returns:
            First N lines
        """
        all_lines = output.splitlines()
        if len(all_lines) <= lines:
            return output
        return "\n".join(all_lines[:lines])

    def get_errors_summary(self, output: str) -> str:
        """
        Extract just the errors from output.

        Args:
            output: The output string

        Returns:
            Summary of errors found
        """
        result = self.process_output(output, extract_errors=True)
        if not result.errors_found:
            return "No errors found."

        lines = ["Errors found:"]
        for error in result.errors_found:
            lines.append(f"  - {error}")
            if error.suggestion:
                lines.append(f"    Fix: {error.suggestion}")

        return "\n".join(lines)


# Convenience functions
def truncate_output(
    output: str,
    max_lines: int = 100,
    tail_lines: int = 5,
) -> str:
    """
    Quick truncation of output.

    Args:
        output: Output to truncate
        max_lines: Maximum total lines
        tail_lines: Lines to keep from end

    Returns:
        Truncated output string
    """
    handler = OutputHandler(max_lines=max_lines, tail_lines=tail_lines)
    result = handler.process_output(output)
    return result.content


def extract_errors(output: str) -> List[ExtractedError]:
    """
    Extract errors from output.

    Args:
        output: Output to analyze

    Returns:
        List of extracted errors
    """
    handler = OutputHandler()
    result = handler.process_output(output, extract_errors=True)
    return result.errors_found


def search_in_output(output: str, pattern: str) -> List[SearchMatch]:
    """
    Search for pattern in output.

    Args:
        output: Output to search
        pattern: Pattern to find

    Returns:
        List of matches
    """
    handler = OutputHandler()
    return handler.search_output(output, pattern)


def get_latest_lines(output: str, count: int = 5) -> str:
    """
    Get the latest N lines from output.

    Args:
        output: The output
        count: Number of lines

    Returns:
        Latest lines
    """
    handler = OutputHandler()
    return handler.get_tail(output, count)
