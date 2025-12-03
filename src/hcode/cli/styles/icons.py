"""
Legacy compatibility layer for cli.styles.icons.

Re-exports Icons from the new hcode.ui module.
"""

from hcode.ui import Icons, Emoji

__all__ = ["Icons", "Emoji"]
