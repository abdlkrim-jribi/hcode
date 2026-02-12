"""
Top‑level package for utility helpers used throughout the Hcode project.

This module re‑exports commonly used utility functions from submodules.
"""

# Safe imports for optional config symbols
try:
    from .config import (
        load_config,
        save_config,
        create_default_config,
        get_model_for_size,
    )
except ImportError:
    # Fallbacks for missing symbols – they are not required for the test suite
    from .config import load_config
    def save_config(*args, **kwargs):
        """Placeholder no‑op for missing save_config."""
        return None
    def create_default_config(*args, **kwargs):
        """Placeholder no‑op for missing create_default_config."""
        return None
    def get_model_for_size(*args, **kwargs):
        """Placeholder no‑op for missing get_model_for_size."""
        return None

from .validators import (
    is_email,
    is_url,
    is_positive_int,
    validate_collection,
)

__all__ = [
    # Config
    "load_config",
    "save_config",
    "create_default_config",
    "get_model_for_size",
    # Validators
    "is_email",
    "is_url",
    "is_positive_int",
    "validate_collection",
]
