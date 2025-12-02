"""
Sanity Check: CLI Components Tests.

Tests the basic functionality of CLI components.
"""
import pytest


class TestDisplayComponent:
    """Test display component basic functionality."""

    def test_display_module_import(self):
        """Test display module imports."""
        from hcode.cli import display
        assert display is not None

    def test_agent_display_instantiation(self):
        """Test AgentDisplay can be instantiated."""
        from hcode.cli.display import AgentDisplay
        display = AgentDisplay()
        assert display is not None


class TestToolDisplayComponent:
    """Test tool display component basic functionality."""

    def test_tool_display_module_import(self):
        """Test tool_display module imports."""
        from hcode.cli import tool_display
        assert tool_display is not None

    def test_hcode_style_import(self):
        """Test HcodeStyle can be imported."""
        from hcode.cli.tool_display import HcodeStyle
        assert HcodeStyle is not None


class TestColorsComponent:
    """Test colors component basic functionality."""

    def test_colors_import(self):
        """Test colors module imports."""
        from hcode.cli.styles.colors import Colors
        assert Colors is not None

    def test_colors_attributes(self):
        """Test Colors has expected color attributes."""
        from hcode.cli.styles.colors import Colors
        # Check for common color attributes
        assert hasattr(Colors, 'PRIMARY')
        assert hasattr(Colors, 'SUCCESS')
        assert hasattr(Colors, 'ERROR')
        assert hasattr(Colors, 'WARNING')


class TestBordersComponent:
    """Test borders component basic functionality."""

    def test_borders_module_import(self):
        """Test borders module imports."""
        from hcode.cli.styles import borders
        assert borders is not None

    def test_box_style_import(self):
        """Test BoxStyle can be imported."""
        from hcode.cli.styles.borders import BoxStyle
        assert BoxStyle is not None

    def test_box_chars_import(self):
        """Test BoxChars can be imported."""
        from hcode.cli.styles.borders import BoxChars
        assert BoxChars is not None


class TestIconsComponent:
    """Test icons component basic functionality."""

    def test_icons_import(self):
        """Test icons module imports."""
        from hcode.cli.styles.icons import Icons
        assert Icons is not None

    def test_icons_instantiation(self):
        """Test Icons can be instantiated."""
        from hcode.cli.styles.icons import Icons
        icons = Icons()
        assert icons is not None

    def test_icons_attributes(self):
        """Test Icons has expected icon attributes."""
        from hcode.cli.styles.icons import Icons
        icons = Icons()
        # Check for common icon attributes
        assert hasattr(icons, 'CHECK')
        assert hasattr(icons, 'ERROR')
        assert hasattr(icons, 'WARNING')


class TestComponentsComponent:
    """Test components component basic functionality."""

    def test_components_import(self):
        """Test components module imports."""
        from hcode.cli.styles import components
        assert components is not None


class TestAnimationsComponent:
    """Test animations component basic functionality."""

    def test_animations_import(self):
        """Test animations module imports."""
        from hcode.cli.styles.animations import AnimatedSpinner
        assert AnimatedSpinner is not None

    def test_spinner_instantiation(self):
        """Test AnimatedSpinner can be instantiated."""
        from hcode.cli.styles.animations import AnimatedSpinner
        spinner = AnimatedSpinner(message="Testing")
        assert spinner is not None

    def test_typing_animation_import(self):
        """Test TypingAnimation imports."""
        from hcode.cli.styles.animations import TypingAnimation
        assert TypingAnimation is not None

    def test_progress_animation_import(self):
        """Test ProgressAnimation imports."""
        from hcode.cli.styles.animations import ProgressAnimation
        assert ProgressAnimation is not None

    def test_thinking_animation_import(self):
        """Test ThinkingAnimation imports."""
        from hcode.cli.styles.animations import ThinkingAnimation
        assert ThinkingAnimation is not None


class TestShortcutsComponent:
    """Test shortcuts component basic functionality."""

    def test_shortcuts_import(self):
        """Test shortcuts module imports."""
        from hcode.cli import shortcuts
        assert shortcuts is not None


class TestAutonomousCLIComponent:
    """Test autonomous CLI component basic functionality."""

    def test_autonomous_cli_import(self):
        """Test autonomous_cli module imports."""
        from hcode.cli import autonomous_cli
        assert autonomous_cli is not None
