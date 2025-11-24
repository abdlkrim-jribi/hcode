#!/usr/bin/env python
"""
Hcode AI Assistant
Run your AI agent with advanced chat interface and features.
"""

import sys
import os
import asyncio
import click
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.hcode.hcode_chat import HcodeChat


@click.command()
@click.option('--model', '-m', help='AI model to use (e.g., claude-3-opus, gpt-4)')
@click.option('--provider', '-p',
              type=click.Choice(['auto', 'anthropic', 'openai']),
              default='auto',
              help='AI provider to use')
@click.option('--session', '-s', help='Resume a previous session by ID')
@click.option('--api-key', help='API key (can also use environment variables)')
@click.option('--debug', is_flag=True, help='Enable debug mode for verbose output')
@click.option('--no-stream', is_flag=True, help='Disable streaming responses')
@click.option('--config', '-c', type=click.Path(), help='Path to configuration file')
@click.option('--export', '-e', help='Export session on exit to specified file')
@click.version_option(version='1.0.0', prog_name='Hcode')
def main(model, provider, session, api_key, debug, no_stream, config, export):
    """
    Launch Hcode AI Assistant.

    This provides an advanced chat experience with your AI agent,
    including all the features you expect:

    \b
    Commands:
      /help     - Show available commands
      /clear    - Clear conversation
      /tasks    - Show todo list
      /exit     - Exit chat

    \b
    Shortcuts:
      @workspace - Reference workspace context
      @file      - Reference specific file
      @web       - Search the web
      @docs      - Search documentation

    \b
    Examples:
      hcode                       # Start default chat
      hcode --model gpt-4         # Use specific model
      hcode --session abc123      # Resume session
      hcode --debug               # Debug mode
    """
    # Initialize chat interface
    chat = HcodeChat()

    # Apply configuration
    if config:
        config_path = Path(config)
        if config_path.exists():
            import json
            with open(config_path, 'r') as f:
                chat.config.update(json.load(f))

    # Apply command-line options
    if model:
        chat.config['model'] = model
    if provider:
        chat.config['provider'] = provider
    if session:
        chat.config['session'] = session
    if api_key:
        os.environ['ANTHROPIC_API_KEY'] = api_key
        os.environ['OPENAI_API_KEY'] = api_key
    if debug:
        chat.config['debug'] = True
    if no_stream:
        chat.stream_responses = False
    if export:
        chat.config['export_on_exit'] = export

    # Run the chat interface
    try:
        asyncio.run(chat.run())
    except KeyboardInterrupt:
        print("\n\nGoodbye! Your session has been saved.")
        if export:
            chat.export_conversation(export)
            print(f"Session exported to: {export}")
    except Exception as e:
        print(f"\nError: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()