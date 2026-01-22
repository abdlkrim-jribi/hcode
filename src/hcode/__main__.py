#!/usr/bin/env python3
"""
HCode - AI Coding Agent CLI

Entry point for running hcode as a module:
    python -m hcode

This module serves as the main entry point when the package is run as a script.
"""

import os
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# WINDOWS UNICODE FIX
# ═══════════════════════════════════════════════════════════════════════════════
# Fix Unicode encoding issues on Windows with legacy cp1252 codepage.
# This MUST be done before any Rich imports to prevent UnicodeEncodeError.
if sys.platform == "win32":
    # Force UTF-8 encoding for stdout/stderr
    import io

    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Also set environment variable for child processes and Rich
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# DEVELOPMENT FIX: Ensure we use the local package when running from source
# This handles the case where user runs 'python hcode' and sys.path[0] is 'src/hcode'
# preventing 'import hcode' from finding the local package.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def main() -> int:
    """Main entry point for the hcode CLI."""
    try:
        from hcode.main_cli import main as cli_main

        cli_main()
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
