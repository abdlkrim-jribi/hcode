"""
Core Prompts Package.

Provides centralized access to all core prompts used by the agent.
"""

from .loader import CorePromptLoader, get_prompt_loader

__all__ = ["CorePromptLoader", "get_prompt_loader"]
