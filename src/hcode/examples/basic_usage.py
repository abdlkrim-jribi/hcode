"""
Basic usage examples for Hcode.
"""

import asyncio
from hcode import HcodeAgent, load_config


async def basic_completion():
    """Basic completion example with Anthropic"""
    # Initialize agent
    agent = HcodeAgent(anthropic_key="your-key-here", model="claude-3-5-sonnet-20241022")

    # Execute a simple task
    result = await agent.execute_task("Write a Python function to calculate fibonacci numbers")

    print(result["response"])
    print(f"Cost: ${result['cost']:.4f}")


async def multi_provider_example():
    """Example using both Anthropic and OpenAI"""
    from hcode import ProviderSelector, ProviderPreferences

    # Create provider selector
    preferences = ProviderPreferences(
        primary_provider="auto", cost_optimization="balanced", fallback_enabled=True
    )

    selector = ProviderSelector(
        anthropic_key="your-anthropic-key", openai_key="your-openai-key", preferences=preferences
    )

    # Let it choose the best provider
    provider = selector.select_provider(complexity="moderate")
    print(f"Selected provider: {provider.get_provider_name()}")


async def with_config():
    """Example using configuration file"""
    # Load configuration from .hcoderc
    config = load_config()

    # Initialize with config
    anthropic_key = config["providers"]["anthropic"].get("api_key")
    openai_key = config["providers"]["openai"].get("api_key")

    agent = HcodeAgent(anthropic_key=anthropic_key, openai_key=openai_key)

    result = await agent.execute_task("Analyze this codebase structure")
    print(result)


if __name__ == "__main__":
    # Run basic example
    asyncio.run(basic_completion())
