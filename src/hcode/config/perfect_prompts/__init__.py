"""
Perfect Prompts Loader.

Loads and provides access to perfect prompt templates from the perfect_prompts directory.
"""

from .loader import PerfectPromptLoader, get_perfect_prompt_loader

__all__ = [
    "PerfectPromptLoader",
    "get_perfect_prompt_loader",
]
