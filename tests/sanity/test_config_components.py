"""
Sanity Check: Config Components Tests.

Tests the basic functionality of config components.
"""
import pytest


class TestDefaultsComponent:
    """Test defaults config component."""

    def test_defaults_import(self):
        """Test defaults module imports."""
        from hcode.config import defaults
        assert defaults is not None

    def test_defaults_has_values(self):
        """Test defaults has expected configuration values."""
        from hcode.config import defaults
        # Check for common default values
        assert hasattr(defaults, 'DEFAULT_MODEL') or hasattr(defaults, 'MODEL')


class TestSettingsComponent:
    """Test settings config component."""

    def test_settings_import(self):
        """Test settings module imports."""
        from hcode.config.settings import Settings
        assert Settings is not None

    def test_settings_instantiation(self):
        """Test Settings can be instantiated."""
        from hcode.config.settings import Settings
        settings = Settings()
        assert settings is not None


class TestPromptsComponent:
    """Test prompts config component."""

    def test_prompts_import(self):
        """Test prompts module imports."""
        from hcode.config import prompts
        assert prompts is not None

    def test_prompts_has_content(self):
        """Test prompts has expected content."""
        from hcode.config import prompts
        # Check for common prompt attributes
        assert hasattr(prompts, 'SYSTEM_PROMPT') or hasattr(prompts, 'get_system_prompt')


class TestThinkingConfigComponent:
    """Test thinking config component."""

    def test_thinking_config_import(self):
        """Test thinking config module imports."""
        from hcode.config import thinking
        assert thinking is not None


class TestToolsConfigComponent:
    """Test tools config component."""

    def test_tools_config_import(self):
        """Test tools config module imports."""
        from hcode.config import tools
        assert tools is not None

    def test_tools_config_has_definitions(self):
        """Test tools config has tool definitions."""
        from hcode.config import tools
        # Check for tool definitions or configurations
        assert hasattr(tools, 'TOOLS') or hasattr(tools, 'get_tool_definitions')


class TestConfigPackageExports:
    """Test config package exports."""

    def test_config_package_import(self):
        """Test config package imports."""
        from hcode import config
        assert config is not None
