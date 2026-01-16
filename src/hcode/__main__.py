#!/usr/bin/env python3
"""
HCode - AI Coding Agent CLI

Entry point for running hcode as a module:
    python -m hcode

This module serves as the main entry point when the package is run as a script.
"""

import sys
import os

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
