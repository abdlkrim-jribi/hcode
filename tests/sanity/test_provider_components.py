"""
Sanity Check: Provider Components Tests.

Tests the basic functionality of AI provider components.
"""
import pytest


class TestBaseProviderComponent:
    """Test base provider component."""

    def test_base_provider_import(self):
        """Test base provider module imports."""
        from hcode.providers.base import BaseProvider
        assert BaseProvider is not None


class TestAnthropicProviderComponent:
    """Test Anthropic provider component."""

    def test_anthropic_provider_import(self):
        """Test anthropic_provider module imports."""
        from hcode.providers.anthropic_provider import AnthropicProvider
        assert AnthropicProvider is not None

    def test_anthropic_provider_attributes(self):
        """Test AnthropicProvider has required attributes."""
        from hcode.providers.anthropic_provider import AnthropicProvider
        # Check class has required methods
        assert hasattr(AnthropicProvider, 'generate')
        assert hasattr(AnthropicProvider, 'stream')


class TestOpenAIProviderComponent:
    """Test OpenAI provider component."""

    def test_openai_provider_import(self):
        """Test openai_provider module imports."""
        from hcode.providers.openai_provider import OpenAIProvider
        assert OpenAIProvider is not None

    def test_openai_provider_attributes(self):
        """Test OpenAIProvider has required attributes."""
        from hcode.providers.openai_provider import OpenAIProvider
        # Check class has required methods
        assert hasattr(OpenAIProvider, 'generate')
        assert hasattr(OpenAIProvider, 'stream')


class TestProviderSelectorComponent:
    """Test provider selector component."""

    def test_provider_selector_import(self):
        """Test provider_selector module imports."""
        from hcode.providers.provider_selector import ProviderSelector
        assert ProviderSelector is not None

    def test_provider_selector_instantiation(self):
        """Test ProviderSelector can be instantiated."""
        from hcode.providers.provider_selector import ProviderSelector
        selector = ProviderSelector()
        assert selector is not None

    def test_provider_selector_get_provider(self):
        """Test ProviderSelector can get provider names."""
        from hcode.providers.provider_selector import ProviderSelector
        selector = ProviderSelector()
        # Check it has methods to get providers
        assert hasattr(selector, 'get_provider')


class TestProvidersPackageExports:
    """Test providers package exports."""

    def test_providers_package_import(self):
        """Test providers package imports."""
        from hcode import providers
        assert providers is not None

    def test_providers_exports(self):
        """Test providers package exports expected classes."""
        from hcode.providers import BaseProvider
        assert BaseProvider is not None
