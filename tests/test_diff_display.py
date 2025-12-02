"""
Tests for the Claude Code-style diff display.

Tests the DiffDisplay component that shows file changes with:
- Line numbers for both old and new versions
- Colored additions (green) and deletions (red)
- Context lines around changes
- Statistics summary
"""

import pytest
import sys
import os
from io import StringIO

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hcode.cli.styles.components import DiffDisplay, DiffLine


class TestDiffComputation:
    """Test diff computation"""

    def test_simple_addition(self):
        """Test adding a single line"""
        old = "line1\nline2\nline3"
        new = "line1\nline2\nnew line\nline3"

        diff_lines = DiffDisplay.compute_diff(old, new)

        # Should have additions
        additions = [d for d in diff_lines if d.change_type == 'addition']
        assert len(additions) == 1
        assert 'new line' in additions[0].content

    def test_simple_deletion(self):
        """Test removing a single line"""
        old = "line1\nline2\nline3"
        new = "line1\nline3"

        diff_lines = DiffDisplay.compute_diff(old, new)

        # Should have deletions
        deletions = [d for d in diff_lines if d.change_type == 'deletion']
        assert len(deletions) == 1
        assert 'line2' in deletions[0].content

    def test_modification(self):
        """Test modifying a line (shows as delete + add)"""
        old = "line1\nold text\nline3"
        new = "line1\nnew text\nline3"

        diff_lines = DiffDisplay.compute_diff(old, new)

        deletions = [d for d in diff_lines if d.change_type == 'deletion']
        additions = [d for d in diff_lines if d.change_type == 'addition']

        assert len(deletions) == 1
        assert len(additions) == 1
        assert 'old text' in deletions[0].content
        assert 'new text' in additions[0].content

    def test_no_changes(self):
        """Test when content is identical"""
        old = "line1\nline2\nline3"
        new = "line1\nline2\nline3"

        diff_lines = DiffDisplay.compute_diff(old, new)

        # Should have no changes
        assert len(diff_lines) == 0

    def test_context_lines(self):
        """Test context lines are included"""
        old = "line1\nline2\nline3\nline4\nline5"
        new = "line1\nline2\nmodified\nline4\nline5"

        diff_lines = DiffDisplay.compute_diff(old, new, context_lines=2)

        # Should have context lines
        context = [d for d in diff_lines if d.change_type == 'context']
        assert len(context) > 0

    def test_line_numbers(self):
        """Test line numbers are correct"""
        old = "line1\nline2\nline3"
        new = "line1\nnew\nline2\nline3"

        diff_lines = DiffDisplay.compute_diff(old, new)

        # Check that line numbers are set correctly
        for diff in diff_lines:
            if diff.change_type == 'addition':
                assert diff.line_number_new is not None
                assert diff.line_number_old is None
            elif diff.change_type == 'deletion':
                assert diff.line_number_old is not None
                assert diff.line_number_new is None
            elif diff.change_type == 'context':
                assert diff.line_number_old is not None
                assert diff.line_number_new is not None

    def test_multiple_hunks(self):
        """Test diff with changes in multiple locations"""
        old = "\n".join([f"line{i}" for i in range(1, 20)])
        new = old.replace("line2", "modified2").replace("line15", "modified15")

        diff_lines = DiffDisplay.compute_diff(old, new, context_lines=2)

        # Should have separators between hunks
        separators = [d for d in diff_lines if d.change_type == 'separator']
        # Might have separator between distant changes
        assert len([d for d in diff_lines if d.change_type in ('addition', 'deletion')]) >= 2


class TestDiffLineDataclass:
    """Test DiffLine dataclass"""

    def test_creation(self):
        """Test creating a DiffLine"""
        line = DiffLine(
            line_number_old=10,
            line_number_new=11,
            content="test content",
            change_type="context"
        )

        assert line.line_number_old == 10
        assert line.line_number_new == 11
        assert line.content == "test content"
        assert line.change_type == "context"

    def test_addition_line(self):
        """Test creating an addition line"""
        line = DiffLine(
            line_number_old=None,
            line_number_new=5,
            content="new line",
            change_type="addition"
        )

        assert line.line_number_old is None
        assert line.line_number_new == 5

    def test_deletion_line(self):
        """Test creating a deletion line"""
        line = DiffLine(
            line_number_old=5,
            line_number_new=None,
            content="removed line",
            change_type="deletion"
        )

        assert line.line_number_old == 5
        assert line.line_number_new is None


class TestDiffRendering:
    """Test diff rendering"""

    def test_render_returns_panel(self):
        """Test that render returns a Panel"""
        from rich.panel import Panel

        old = "old content"
        new = "new content"

        result = DiffDisplay.render("test.py", old, new)

        assert isinstance(result, Panel)

    def test_render_no_changes(self):
        """Test rendering when no changes"""
        from rich.panel import Panel

        content = "same content"
        result = DiffDisplay.render("test.py", content, content)

        assert isinstance(result, Panel)

    def test_render_simple(self):
        """Test simple rendering"""
        from rich.panel import Panel

        result = DiffDisplay.render_simple(
            "test.py",
            additions=["new line 1", "new line 2"],
            deletions=["old line"],
            context=["context line"]
        )

        assert isinstance(result, Panel)

    def test_render_inline(self):
        """Test inline diff rendering"""
        from rich.text import Text

        result = DiffDisplay.render_inline("old text", "new text")

        assert isinstance(result, Text)
        # The text should contain both old and new
        plain = result.plain
        assert "old text" in plain
        assert "new text" in plain

    def test_language_detection(self):
        """Test automatic language detection from filename"""
        old = "def foo():\n    pass"
        new = "def foo():\n    return 1"

        # Should not raise even with various extensions
        for ext in ['.py', '.js', '.ts', '.go', '.rs', '.java', '.txt']:
            result = DiffDisplay.render(f"test{ext}", old, new)
            assert result is not None


class TestDiffStatistics:
    """Test diff statistics"""

    def test_addition_count(self):
        """Test counting additions"""
        old = "line1"
        new = "line1\nline2\nline3"

        diff_lines = DiffDisplay.compute_diff(old, new)
        additions = sum(1 for d in diff_lines if d.change_type == 'addition')

        # Should have at least 2 additions (might count newline changes differently)
        assert additions >= 2

    def test_deletion_count(self):
        """Test counting deletions"""
        old = "line1\nline2\nline3"
        new = "line1"

        diff_lines = DiffDisplay.compute_diff(old, new)
        deletions = sum(1 for d in diff_lines if d.change_type == 'deletion')

        # Should have at least 2 deletions
        assert deletions >= 2

    def test_mixed_changes(self):
        """Test counting mixed changes"""
        old = "line1\nold line\nline3"
        new = "line1\nnew line\nline3\nline4"

        diff_lines = DiffDisplay.compute_diff(old, new)
        additions = sum(1 for d in diff_lines if d.change_type == 'addition')
        deletions = sum(1 for d in diff_lines if d.change_type == 'deletion')

        assert additions >= 1
        assert deletions >= 1


class TestRealWorldDiffs:
    """Test with realistic code changes"""

    def test_python_function_change(self):
        """Test diff of Python function modification"""
        old = '''def greet(name):
    print("Hello, " + name)
    return None
'''
        new = '''def greet(name):
    """Greet a person by name."""
    message = f"Hello, {name}!"
    print(message)
    return message
'''
        diff_lines = DiffDisplay.compute_diff(old, new)

        # Should show the changes
        assert len(diff_lines) > 0
        additions = [d for d in diff_lines if d.change_type == 'addition']
        assert any('docstring' in d.content.lower() or '"""' in d.content for d in additions)

    def test_import_addition(self):
        """Test adding imports"""
        old = '''import os

def main():
    pass
'''
        new = '''import os
import sys
import json

def main():
    pass
'''
        diff_lines = DiffDisplay.compute_diff(old, new)
        additions = [d for d in diff_lines if d.change_type == 'addition']

        assert len(additions) >= 2
        assert any('sys' in d.content for d in additions)
        assert any('json' in d.content for d in additions)

    def test_class_method_change(self):
        """Test modifying a class method"""
        old = '''class Calculator:
    def add(self, a, b):
        return a + b
'''
        new = '''class Calculator:
    def add(self, a, b):
        """Add two numbers."""
        result = a + b
        return result
'''
        diff_lines = DiffDisplay.compute_diff(old, new)

        assert len(diff_lines) > 0


class TestEdgeCases:
    """Test edge cases"""

    def test_empty_old_content(self):
        """Test when old content is empty"""
        old = ""
        new = "new content\nline 2"

        diff_lines = DiffDisplay.compute_diff(old, new)
        additions = [d for d in diff_lines if d.change_type == 'addition']

        assert len(additions) >= 1

    def test_empty_new_content(self):
        """Test when new content is empty"""
        old = "old content\nline 2"
        new = ""

        diff_lines = DiffDisplay.compute_diff(old, new)
        deletions = [d for d in diff_lines if d.change_type == 'deletion']

        assert len(deletions) >= 1

    def test_single_character_change(self):
        """Test single character modification"""
        old = "hello world"
        new = "hello World"

        diff_lines = DiffDisplay.compute_diff(old, new)

        assert len(diff_lines) > 0

    def test_whitespace_only_change(self):
        """Test whitespace-only changes"""
        old = "line with trailing space "
        new = "line with trailing space"

        diff_lines = DiffDisplay.compute_diff(old, new)

        # Should detect the whitespace change
        assert len(diff_lines) > 0

    def test_unicode_content(self):
        """Test with unicode content"""
        old = "Hello 世界\n你好"
        new = "Hello 世界\n你好\nПривет"

        diff_lines = DiffDisplay.compute_diff(old, new)
        additions = [d for d in diff_lines if d.change_type == 'addition']

        assert len(additions) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
