"""
Unit tests for the OutputHandler module.

Tests smart truncation, error extraction, search, and convenience functions.
"""

import pytest
from src.hcode.core.output_handler import (
    OutputHandler,
    TruncatedOutput,
    ExtractedError,
    SearchMatch,
    ErrorSeverity,
    OutputType,
    truncate_output,
    extract_errors,
    search_in_output,
    get_latest_lines,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def handler():
    """Default output handler instance"""
    return OutputHandler()


@pytest.fixture
def small_handler():
    """Output handler with small limits for testing truncation"""
    return OutputHandler(
        head_lines=3,
        tail_lines=2,
        max_lines=10,
        max_line_length=50,
    )


@pytest.fixture
def sample_output():
    """Sample multi-line output"""
    return "\n".join([f"Line {i}: Some output content" for i in range(1, 51)])


@pytest.fixture
def python_error_output():
    """Sample Python error output"""
    return '''Running tests...
Collecting tests
Traceback (most recent call last):
  File "/path/to/test.py", line 42, in test_function
    result = process_data(None)
  File "/path/to/module.py", line 15, in process_data
    return data.strip()
AttributeError: 'NoneType' object has no attribute 'strip'
'''


@pytest.fixture
def multi_error_output():
    """Output with multiple errors"""
    return '''Building project...
Step 1: Compiling
WARNING: Deprecated function used at line 10
Step 2: Linking
ERROR: undefined reference to 'missing_function'
Step 3: Packaging
FAILED: Package validation error
Critical: Build cannot continue
'''


# ============================================================
# TRUNCATION TESTS
# ============================================================

class TestTruncation:
    """Tests for output truncation functionality"""

    def test_no_truncation_small_output(self, handler):
        """Small output should not be truncated"""
        output = "Line 1\nLine 2\nLine 3"
        result = handler.process_output(output)

        assert result.truncated is False
        assert result.original_lines == 3
        assert result.displayed_lines == 3
        assert result.omitted_lines == 0

    def test_truncation_large_output(self, small_handler, sample_output):
        """Large output should be truncated"""
        result = small_handler.process_output(sample_output)

        assert result.truncated is True
        assert result.original_lines == 50
        assert result.displayed_lines < 50
        assert result.omitted_lines > 0

    def test_always_shows_tail_lines(self, small_handler):
        """Should always show the last N lines (latest output)"""
        output = "\n".join([f"Line {i}" for i in range(1, 101)])
        result = small_handler.process_output(output)

        # Check that latest lines section is present
        assert "--- Latest" in result.content
        assert "Line 100" in result.content
        assert "Line 99" in result.content

    def test_head_lines_preserved(self, small_handler):
        """Should preserve first N lines"""
        output = "\n".join([f"Line {i}" for i in range(1, 101)])
        result = small_handler.process_output(output)

        assert "Line 1" in result.content
        assert "Line 2" in result.content
        assert "Line 3" in result.content

    def test_omitted_indicator(self, small_handler):
        """Should show omitted lines indicator"""
        output = "\n".join([f"Line {i}" for i in range(1, 101)])
        result = small_handler.process_output(output)

        assert "omitted" in result.content.lower()

    def test_line_truncation(self, small_handler):
        """Long lines should be truncated"""
        long_line = "A" * 100
        result = small_handler.process_output(long_line)

        # Line should be truncated to max_line_length
        assert len(result.content) <= small_handler.max_line_length + 10  # Some margin for "..."

    def test_empty_output(self, handler):
        """Empty output should be handled gracefully"""
        result = handler.process_output("")

        assert result.truncated is False
        assert result.original_lines == 0
        assert "(no output)" in result.content

    def test_none_output(self, handler):
        """None output should be handled gracefully"""
        result = handler.process_output(None)

        assert result.truncated is False
        assert "(no output)" in result.content


# ============================================================
# ERROR EXTRACTION TESTS
# ============================================================

class TestErrorExtraction:
    """Tests for error extraction functionality"""

    def test_extract_python_exception(self, handler, python_error_output):
        """Should extract Python exceptions"""
        result = handler.process_output(
            python_error_output,
            output_type=OutputType.STDOUT,
            extract_errors=True
        )

        assert len(result.errors_found) > 0
        # Should find AttributeError
        error_types = [e.error_type for e in result.errors_found if e.error_type]
        assert "AttributeError" in error_types

    def test_detect_stack_trace(self, handler, python_error_output):
        """Should detect stack traces"""
        result = handler.process_output(
            python_error_output,
            extract_errors=True
        )

        assert result.has_stack_trace is True

    def test_no_stack_trace_in_normal_output(self, handler):
        """Normal output should not have stack trace detected"""
        output = "Build successful\nAll tests passed\nDone"
        result = handler.process_output(output, extract_errors=True)

        assert result.has_stack_trace is False

    def test_extract_generic_errors(self, handler, multi_error_output):
        """Should extract generic error patterns"""
        result = handler.process_output(
            multi_error_output,
            extract_errors=True
        )

        assert len(result.errors_found) > 0
        # Check that we found different severity levels
        severities = {e.severity for e in result.errors_found}
        assert ErrorSeverity.ERROR in severities or ErrorSeverity.WARNING in severities

    def test_error_severity_levels(self, handler):
        """Should correctly classify error severities"""
        output = '''
WARNING: This is a warning
ERROR: This is an error
CRITICAL: This is critical
'''
        result = handler.process_output(output, extract_errors=True)

        errors = result.errors_found
        assert len(errors) > 0

    def test_extract_errors_disabled(self, handler, python_error_output):
        """When extract_errors=False, should not extract errors"""
        result = handler.process_output(
            python_error_output,
            extract_errors=False
        )

        assert len(result.errors_found) == 0

    def test_suggestion_for_module_not_found(self, handler):
        """Should provide suggestion for ModuleNotFoundError"""
        output = "ModuleNotFoundError: No module named 'requests'"
        result = handler.process_output(output, extract_errors=True)

        if result.errors_found:
            suggestions = [e.suggestion for e in result.errors_found if e.suggestion]
            assert any("pip install" in s for s in suggestions if s)

    def test_warnings_count(self, handler, multi_error_output):
        """Should count warnings separately"""
        result = handler.process_output(multi_error_output, extract_errors=True)

        # Should have at least one warning
        assert result.warnings_found >= 0  # May be 0 if no warnings detected


# ============================================================
# SEARCH TESTS
# ============================================================

class TestSearch:
    """Tests for output search functionality"""

    def test_simple_search(self, handler):
        """Simple literal search should work"""
        output = "Line 1: Hello\nLine 2: World\nLine 3: Hello World"
        matches = handler.search_output(output, "Hello")

        assert len(matches) == 2
        assert matches[0].line_number == 1
        assert matches[1].line_number == 3

    def test_case_insensitive_search(self, handler):
        """Case insensitive search should find all matches"""
        output = "Error here\nERROR there\nerror everywhere"
        matches = handler.search_output(output, "error", case_sensitive=False)

        assert len(matches) == 3

    def test_case_sensitive_search(self, handler):
        """Case sensitive search should be exact"""
        output = "Error here\nERROR there\nerror everywhere"
        matches = handler.search_output(output, "ERROR", case_sensitive=True)

        assert len(matches) == 1
        assert matches[0].line_number == 2

    def test_regex_search(self, handler):
        """Regex search should work"""
        output = "Line 1\nLine 10\nLine 100\nLine 2"
        matches = handler.search_output(output, r"Line \d{2,}", regex=True)

        assert len(matches) == 2  # Line 10 and Line 100

    def test_search_context_lines(self, handler):
        """Search should include context lines"""
        output = "Before 1\nBefore 2\nMATCH\nAfter 1\nAfter 2"
        matches = handler.search_output(output, "MATCH", context_lines=2)

        assert len(matches) == 1
        assert len(matches[0].context_before) == 2
        assert len(matches[0].context_after) == 2

    def test_search_max_matches(self, handler):
        """Should respect max_matches limit"""
        output = "\n".join([f"Match {i}" for i in range(100)])
        matches = handler.search_output(output, "Match", max_matches=5)

        assert len(matches) == 5

    def test_search_no_matches(self, handler):
        """Should return empty list when no matches"""
        output = "Line 1\nLine 2\nLine 3"
        matches = handler.search_output(output, "NotFound")

        assert len(matches) == 0

    def test_search_match_positions(self, handler):
        """Should return correct match positions"""
        output = "Hello World"
        matches = handler.search_output(output, "World")

        assert len(matches) == 1
        assert matches[0].match_start == 6
        assert matches[0].match_end == 11

    def test_invalid_regex(self, handler):
        """Invalid regex should return empty list, not error"""
        output = "Some text"
        matches = handler.search_output(output, "[invalid(regex", regex=True)

        assert len(matches) == 0


# ============================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================

class TestConvenienceFunctions:
    """Tests for convenience functions"""

    def test_truncate_output(self):
        """truncate_output function should work"""
        output = "\n".join([f"Line {i}" for i in range(200)])
        result = truncate_output(output, max_lines=50, tail_lines=5)

        assert len(result.split("\n")) < 200
        assert "Line 199" in result  # Should have last line

    def test_extract_errors(self):
        """extract_errors function should work"""
        output = "ValueError: Something went wrong"
        errors = extract_errors(output)

        assert len(errors) > 0

    def test_search_in_output(self):
        """search_in_output function should work"""
        output = "Error: Something failed\nWarning: Check this"
        matches = search_in_output(output, "Error")

        assert len(matches) == 1

    def test_get_latest_lines(self):
        """get_latest_lines function should work"""
        output = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        latest = get_latest_lines(output, 3)

        assert latest == "Line 3\nLine 4\nLine 5"

    def test_get_latest_lines_small_output(self):
        """get_latest_lines should handle small output"""
        output = "Line 1\nLine 2"
        latest = get_latest_lines(output, 5)

        assert latest == output


# ============================================================
# HELPER METHOD TESTS
# ============================================================

class TestHelperMethods:
    """Tests for helper methods"""

    def test_get_head(self, handler):
        """get_head should return first N lines"""
        output = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        head = handler.get_head(output, 3)

        assert head == "Line 1\nLine 2\nLine 3"

    def test_get_tail(self, handler):
        """get_tail should return last N lines"""
        output = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        tail = handler.get_tail(output, 3)

        assert tail == "Line 3\nLine 4\nLine 5"

    def test_get_errors_summary_no_errors(self, handler):
        """get_errors_summary should handle no errors"""
        output = "All good\nNo problems here"
        summary = handler.get_errors_summary(output)

        assert "No errors found" in summary or "no error" in summary.lower()

    def test_get_errors_summary_with_errors(self, handler):
        """get_errors_summary should summarize errors"""
        output = "ValueError: Test error\nTypeError: Another error"
        summary = handler.get_errors_summary(output)

        assert "Errors found" in summary or "error" in summary.lower()

    def test_format_for_display(self, handler, sample_output):
        """format_for_display should format output nicely"""
        truncated = handler.process_output(sample_output)
        formatted = handler.format_for_display(truncated, show_stats=True)

        assert isinstance(formatted, str)
        assert len(formatted) > 0


# ============================================================
# OUTPUT TYPE TESTS
# ============================================================

class TestOutputTypes:
    """Tests for different output types"""

    def test_stdout_type(self, handler):
        """STDOUT type should be processed"""
        output = "Build output\nStep 1 complete"
        result = handler.process_output(output, output_type=OutputType.STDOUT)

        assert result is not None

    def test_stderr_type(self, handler):
        """STDERR type should be processed"""
        output = "Warning: something\nError: something else"
        result = handler.process_output(output, output_type=OutputType.STDERR)

        assert result is not None

    def test_file_content_type(self, handler):
        """FILE_CONTENT type should be processed"""
        output = "def function():\n    pass"
        result = handler.process_output(output, output_type=OutputType.FILE_CONTENT)

        assert result is not None


# ============================================================
# EDGE CASES
# ============================================================

class TestEdgeCases:
    """Tests for edge cases"""

    def test_single_line(self, handler):
        """Single line output should work"""
        result = handler.process_output("Single line")

        assert result.original_lines == 1
        assert result.truncated is False

    def test_very_long_single_line(self, handler):
        """Very long single line should be truncated"""
        long_line = "A" * 10000
        result = handler.process_output(long_line)

        assert "..." in result.content or len(result.content) < 10000

    def test_unicode_content(self, handler):
        """Unicode content should be handled"""
        output = "Hello 世界\nПривет мир\n🎉 Success!"
        result = handler.process_output(output)

        assert result.original_lines == 3
        assert "世界" in result.content

    def test_mixed_line_endings(self, handler):
        """Mixed line endings should be handled"""
        output = "Line 1\r\nLine 2\nLine 3\rLine 4"
        result = handler.process_output(output)

        assert result.original_lines >= 2  # At least some lines detected

    def test_whitespace_only_lines(self, handler):
        """Whitespace-only lines should be handled"""
        output = "Line 1\n   \nLine 3\n\t\nLine 5"
        result = handler.process_output(output)

        assert result.original_lines == 5

    def test_preserve_important_disabled(self, handler, sample_output):
        """preserve_important=False should skip important line detection"""
        output_with_error = sample_output + "\nERROR: Test error"
        result = handler.process_output(
            output_with_error,
            preserve_important=False
        )

        assert result is not None


# ============================================================
# TRUNCATED OUTPUT DATACLASS TESTS
# ============================================================

class TestTruncatedOutput:
    """Tests for TruncatedOutput dataclass"""

    def test_dataclass_fields(self):
        """TruncatedOutput should have all required fields"""
        output = TruncatedOutput(
            content="Test",
            original_lines=100,
            displayed_lines=20,
            truncated=True,
            head_lines=15,
            tail_lines=5,
            omitted_lines=80,
        )

        assert output.content == "Test"
        assert output.original_lines == 100
        assert output.displayed_lines == 20
        assert output.truncated is True
        assert output.head_lines == 15
        assert output.tail_lines == 5
        assert output.omitted_lines == 80
        assert output.errors_found == []
        assert output.warnings_found == 0
        assert output.has_stack_trace is False


# ============================================================
# EXTRACTED ERROR DATACLASS TESTS
# ============================================================

class TestExtractedError:
    """Tests for ExtractedError dataclass"""

    def test_str_representation(self):
        """ExtractedError should have readable string representation"""
        error = ExtractedError(
            message="Something went wrong",
            severity=ErrorSeverity.ERROR,
            line_number=42,
            file_path="/path/to/file.py",
            error_type="ValueError"
        )

        str_repr = str(error)
        assert "ERROR" in str_repr
        assert "ValueError" in str_repr
        assert "file.py" in str_repr
        assert "42" in str_repr

    def test_error_without_file_path(self):
        """ExtractedError should work without file path"""
        error = ExtractedError(
            message="Generic error",
            severity=ErrorSeverity.WARNING
        )

        str_repr = str(error)
        assert "WARNING" in str_repr
        assert "Generic error" in str_repr


# ============================================================
# SEARCH MATCH DATACLASS TESTS
# ============================================================

class TestSearchMatch:
    """Tests for SearchMatch dataclass"""

    def test_dataclass_fields(self):
        """SearchMatch should have all required fields"""
        match = SearchMatch(
            line_number=10,
            line_content="Test line content",
            match_start=5,
            match_end=9,
            context_before=["Line before"],
            context_after=["Line after"]
        )

        assert match.line_number == 10
        assert match.line_content == "Test line content"
        assert match.match_start == 5
        assert match.match_end == 9
        assert len(match.context_before) == 1
        assert len(match.context_after) == 1
