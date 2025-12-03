"""
Legacy compatibility layer for cli.styles.colors.

Re-exports Colors from the new hcode.ui module.
"""

from hcode.ui import Colors

__all__ = ["Colors"]
