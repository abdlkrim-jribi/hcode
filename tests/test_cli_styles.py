"""
Tests for CLI styling system.
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hcode.cli.styles import (
    Colors,
    ThemeManager,
    Theme,
    ColorScheme,
    get_rich_theme,
    BoxStyle,
    HCODE_BOX,
    Lines,
    get_default_box,
    Icons,
    Spinners,
    get_status_icon,
    get_file_icon,
    get_tool_icon,
    StyledPanel,
    TodoDisplay,
    TodoItem,
    StyledProgress,
    Header,
    Footer,
    StatusLine,
    Prompt,
    MessageDisplay,
    DiffDisplay,
    FileTree,
    Separator,
    console
)


class TestColors:
    """Test color system"""

    def test_colors_is_color_scheme(self):
        """Colors should be a ColorScheme instance"""
        assert isinstance(Colors, ColorScheme)

    def test_primary_color(self):
        """Primary color should be #08CB00"""
        assert Colors.PRIMARY == "#08CB00"

    def test_color_scheme_has_all_colors(self):
        """ColorScheme should have all required colors"""
        assert hasattr(Colors, 'PRIMARY')
        assert hasattr(Colors, 'SUCCESS')
        assert hasattr(Colors, 'ERROR')
        assert hasattr(Colors, 'WARNING')
        assert hasattr(Colors, 'INFO')
        assert hasattr(Colors, 'TEXT_PRIMARY')
        assert hasattr(Colors, 'TEXT_SECONDARY')
        assert hasattr(Colors, 'BG_PRIMARY')

    def test_semantic_colors(self):
        """Semantic colors should be defined"""
        # Success uses primary green
        assert Colors.SUCCESS == "#08CB00"
        assert Colors.ERROR == "#FF3B3B"
        assert Colors.WARNING == "#FFB800"
        assert Colors.INFO == "#00A8CB"

    def test_todo_colors(self):
        """Todo state colors should be defined"""
        assert hasattr(Colors, 'TODO_PENDING')
        assert hasattr(Colors, 'TODO_IN_PROGRESS')
        assert hasattr(Colors, 'TODO_COMPLETED')
        assert hasattr(Colors, 'TODO_BLOCKED')


class TestThemeManager:
    """Test theme management"""

    def test_get_colors(self):
        """Should return color scheme"""
        colors = ThemeManager.get_colors()
        assert isinstance(colors, ColorScheme)

    def test_default_theme_is_dark(self):
        """Default theme should be dark"""
        assert ThemeManager.get_current_theme() == Theme.DARK

    def test_set_theme(self):
        """Should be able to set theme"""
        original = ThemeManager.get_current_theme()
        ThemeManager.set_theme(Theme.LIGHT)
        assert ThemeManager.get_current_theme() == Theme.LIGHT
        # Restore
        ThemeManager.set_theme(original)

    def test_toggle_theme(self):
        """Should toggle between themes"""
        original = ThemeManager.get_current_theme()
        ThemeManager.toggle_theme()
        assert ThemeManager.get_current_theme() != original
        # Toggle back
        ThemeManager.toggle_theme()
        assert ThemeManager.get_current_theme() == original


class TestRichTheme:
    """Test Rich theme generation"""

    def test_get_rich_theme(self):
        """Should return Rich theme dict"""
        theme = get_rich_theme()
        assert isinstance(theme, dict)

    def test_rich_theme_has_styles(self):
        """Rich theme should have required styles"""
        theme = get_rich_theme()
        assert 'primary' in theme
        assert 'success' in theme
        assert 'error' in theme
        assert 'warning' in theme


class TestBoxStyles:
    """Test box drawing styles"""

    def test_box_styles_exist(self):
        """All box styles should exist"""
        assert BoxStyle.ROUNDED
        assert BoxStyle.SHARP
        assert BoxStyle.DOUBLE
        assert BoxStyle.ASCII

    def test_hcode_box(self):
        """HCODE_BOX should be defined"""
        assert HCODE_BOX is not None

    def test_get_default_box(self):
        """Should return a box"""
        box = get_default_box()
        assert box is not None


class TestLines:
    """Test line drawing utilities"""

    def test_line_chars_exist(self):
        """Line characters should exist"""
        assert Lines.THIN
        assert Lines.THICK
        assert Lines.ARROW_RIGHT

    def test_horizontal_line(self):
        """Should create horizontal line"""
        line = Lines.horizontal(10)
        assert len(line) == 10

    def test_separator_with_label(self):
        """Should create separator with label"""
        sep = Lines.separator(50, label="Test")
        assert "Test" in sep


class TestIcons:
    """Test icon system"""

    def test_icons_instance(self):
        """Should create Icons instance"""
        icons = Icons()
        assert icons is not None

    def test_status_icons(self):
        """Status icons should exist"""
        icons = Icons()
        assert icons.CHECK
        assert icons.CROSS
        assert icons.WARNING
        assert icons.INFO

    def test_todo_icons(self):
        """Todo icons should exist"""
        icons = Icons()
        assert icons.TODO_PENDING
        assert icons.TODO_IN_PROGRESS
        assert icons.TODO_COMPLETED
        assert icons.TODO_BLOCKED

    def test_get_status_icon(self):
        """Should return icon for status"""
        icon = get_status_icon("completed")
        assert icon is not None

    def test_get_file_icon(self):
        """Should return icon for file type"""
        icon = get_file_icon("test.py")
        assert icon is not None

    def test_get_tool_icon(self):
        """Should return icon for tool"""
        icon = get_tool_icon("bash")
        assert icon is not None


class TestSpinners:
    """Test spinner animations"""

    def test_spinners_exist(self):
        """Spinner types should exist"""
        assert Spinners.SIMPLE
        assert Spinners.DOTS
        assert Spinners.LINE
        assert Spinners.DEFAULT


class TestStyledPanel:
    """Test styled panel factory"""

    def test_success_panel(self):
        """Should create success panel"""
        panel = StyledPanel.success("Test message")
        assert panel is not None

    def test_error_panel(self):
        """Should create error panel"""
        panel = StyledPanel.error("Test error")
        assert panel is not None

    def test_warning_panel(self):
        """Should create warning panel"""
        panel = StyledPanel.warning("Test warning")
        assert panel is not None

    def test_info_panel(self):
        """Should create info panel"""
        panel = StyledPanel.info("Test info")
        assert panel is not None

    def test_thinking_panel(self):
        """Should create thinking panel"""
        panel = StyledPanel.thinking("Thinking...")
        assert panel is not None

    def test_code_panel(self):
        """Should create code panel"""
        panel = StyledPanel.code("print('hello')", "python")
        assert panel is not None


class TestTodoDisplay:
    """Test todo display component"""

    def test_render_empty(self):
        """Should render empty todos"""
        panel = TodoDisplay.render([])
        assert panel is not None

    def test_render_todos(self):
        """Should render todo list"""
        todos = [
            TodoItem("Task 1", "completed"),
            TodoItem("Task 2", "in_progress", "Working on Task 2"),
            TodoItem("Task 3", "pending"),
        ]
        panel = TodoDisplay.render(todos)
        assert panel is not None

    def test_render_compact(self):
        """Should render compact view"""
        todos = [
            TodoItem("Task 1", "completed"),
            TodoItem("Task 2", "in_progress", "Working on Task 2"),
        ]
        text = TodoDisplay.render_compact(todos)
        assert text is not None


class TestHeader:
    """Test header component"""

    def test_render_header(self):
        """Should render header"""
        header = Header.render("Hcode", version="1.0")
        assert header is not None

    def test_render_minimal(self):
        """Should render minimal header"""
        header = Header.render_minimal("Hcode")
        assert header is not None


class TestFooter:
    """Test footer component"""

    def test_render_footer(self):
        """Should render footer"""
        footer = Footer.render("Status text")
        assert footer is not None

    def test_render_with_shortcuts(self):
        """Should render footer with shortcuts"""
        footer = Footer.render(shortcuts={"^C": "Exit", "^R": "Refresh"})
        assert footer is not None


class TestStatusLine:
    """Test status line component"""

    def test_render_status(self):
        """Should render status line"""
        status = StatusLine.render("ready", "All systems go")
        assert status is not None

    def test_render_thinking_status(self):
        """Should render thinking status"""
        status = StatusLine.render("thinking", "Processing request")
        assert status is not None


class TestPrompt:
    """Test prompt components"""

    def test_input_prompt(self):
        """Should render input prompt"""
        prompt = Prompt.render_input()
        assert prompt is not None

    def test_continuation_prompt(self):
        """Should render continuation prompt"""
        prompt = Prompt.render_continuation()
        assert prompt is not None

    def test_confirm_prompt(self):
        """Should render confirm prompt"""
        prompt = Prompt.render_confirm("Continue?")
        assert prompt is not None


class TestMessageDisplay:
    """Test message display component"""

    def test_render_user(self):
        """Should render user message"""
        msg = MessageDisplay.render_user("Hello")
        assert msg is not None

    def test_render_assistant(self):
        """Should render assistant message"""
        msg = MessageDisplay.render_assistant("Hello back!")
        assert msg is not None

    def test_render_with_thinking(self):
        """Should render message with thinking"""
        msg = MessageDisplay.render_assistant("Response", thinking="Analyzing...")
        assert msg is not None


class TestDiffDisplay:
    """Test diff display component"""

    def test_render_diff(self):
        """Should render diff"""
        # Use new Claude Code-style diff display
        diff = DiffDisplay.render(
            filename="test.py",
            old_content="old line\n",
            new_content="new line\n"
        )
        assert diff is not None

    def test_render_simple_diff(self):
        """Should render simple diff with lists"""
        diff = DiffDisplay.render_simple(
            "test.py",
            additions=["+ new line"],
            deletions=["- old line"]
        )
        assert diff is not None

    def test_render_inline_diff(self):
        """Should render inline diff"""
        diff = DiffDisplay.render_inline("old", "new")
        assert diff is not None


class TestFileTree:
    """Test file tree component"""

    def test_render_tree(self):
        """Should render file tree"""
        tree = FileTree.render("src", [
            "src/main.py",
            "src/utils/helper.py",
        ])
        assert tree is not None


class TestSeparator:
    """Test separator component"""

    def test_thin_separator(self):
        """Should create thin separator"""
        sep = Separator.thin()
        assert sep is not None

    def test_separator_with_label(self):
        """Should create labeled separator"""
        sep = Separator.with_label("Section")
        assert sep is not None


class TestConsole:
    """Test console instance"""

    def test_console_exists(self):
        """Console should be available"""
        assert console is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
