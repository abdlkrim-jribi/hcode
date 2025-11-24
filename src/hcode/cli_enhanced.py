"""
Enhanced CLI for Hcode with beautiful styling and all advanced features.
"""

import click
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables from .env file
load_dotenv()
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.live import Live
from rich.layout import Layout
from rich.prompt import Prompt, Confirm
from rich.traceback import install as install_rich_traceback
from rich import box
from rich.text import Text

# Install rich traceback for beautiful error messages
install_rich_traceback(show_locals=True)

from .core import EnhancedHcodeAgent
from .providers import ProviderPreferences, TaskComplexity, TaskType
from .utils.config import load_config

console = Console()

# Beautiful banner
BANNER = """
[bold cyan]╦ ╦┌─┐┌─┐┌┬┐┌─┐[/bold cyan]
[bold cyan]╠═╣│  │ │ ││├┤ [/bold cyan]
[bold cyan]╩ ╩└─┘└─┘─┴┘└─┘[/bold cyan]
[dim]Universal AI Coding Assistant[/dim]
[dim]Claude + GPT · Tools · Agents[/dim]
"""

# Emoji shortcuts for status (Windows-safe)
import platform
IS_WINDOWS = platform.system() == "Windows"

def create_progress(**kwargs):
    """Create a Windows-safe Progress object"""
    if IS_WINDOWS:
        # Use simple progress without spinner on Windows
        return Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            **kwargs
        )
    else:
        # Use full progress with spinner on Unix
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            **kwargs
        )

EMOJI = {
    "success": "+" if IS_WINDOWS else "✓",
    "error": "X" if IS_WINDOWS else "✗",
    "warning": "!" if IS_WINDOWS else "⚠",
    "info": "i" if IS_WINDOWS else "ℹ",
    "rocket": ">" if IS_WINDOWS else "🚀",
    "robot": "[AI]" if IS_WINDOWS else "🤖",
    "tool": "[T]" if IS_WINDOWS else "🔧",
    "search": "?" if IS_WINDOWS else "🔍",
    "fire": "*" if IS_WINDOWS else "🔥",
    "sparkles": "*" if IS_WINDOWS else "✨",
    "check": "+" if IS_WINDOWS else "✅",
    "cross": "X" if IS_WINDOWS else "❌",
    "clock": "T" if IS_WINDOWS else "⏱",
    "money": "$" if IS_WINDOWS else "💰"
}


def show_banner():
    """Display beautiful banner"""
    console.print(Panel(BANNER, border_style="cyan", box=box.DOUBLE))


def show_welcome():
    """Show welcome message with tips"""
    tips = [
        "[cyan]💡 Tip:[/cyan] Use [bold]--help[/bold] on any command for details",
        "[cyan]💡 Tip:[/cyan] Press [bold]Ctrl+C[/bold] anytime to safely interrupt",
        "[cyan]💡 Tip:[/cyan] Use [bold]--stream[/bold] for real-time responses",
        "[cyan]💡 Tip:[/cyan] Try [bold]hcode chat[/bold] for interactive mode"
    ]
    console.print("\n".join(tips) + "\n")


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version')
@click.pass_context
def cli(ctx, version):
    """
    Hcode - Universal AI Coding Assistant

    Supports both Anthropic Claude and OpenAI GPT with comprehensive tools.

    \b
    Quick Start:
      hcode run "your task"     Execute a task
      hcode chat               Start interactive session
      hcode -h                 Show this help

    \b
    Examples:
      hcode run "add logging to main.py"
      hcode analyze src/
      hcode debug "NullPointerException in line 42"
    """
    if version:
        console.print(f"[bold cyan]Hcode[/bold cyan] version [green]0.1.0[/green]")
        console.print(f"{EMOJI['robot']} AI Providers: [cyan]Anthropic[/cyan] + [green]OpenAI[/green]")
        sys.exit(0)

    if ctx.invoked_subcommand is None:
        show_banner()
        show_welcome()
        console.print(ctx.get_help())


@cli.command(name='run', short_help='Execute a task')
@click.argument('task', required=False)
@click.option('-p', '--provider', type=click.Choice(['auto', 'anthropic', 'openai', 'claude', 'gpt']),
              default='auto', help='AI provider')
@click.option('-m', '--model', help='Specific model name')
@click.option('--model-size', '--size', type=click.Choice(['small', 'mid', 'big']),
              help='Model size (small/mid/big)')
@click.option('-c', '--complexity', type=click.Choice(['simple', 'moderate', 'complex', 's', 'm', 'c']),
              default='moderate', help='Task complexity')
@click.option('--cost', '--optimize-cost', is_flag=True, help='Optimize for cost')
@click.option('-s', '--session', help='Session ID')
@click.option('--stream/--no-stream', default=True, help='Stream responses')
@click.option('--agents/--no-agents', default=False, help='Use specialized sub-agents')
@click.option('-v', '--verbose', is_flag=True, help='Verbose output')
def run_task(task, provider, model, model_size, complexity, cost, session, stream, agents, verbose):
    """
    🚀 Execute a coding task with AI assistance

    \b
    Examples:
      hcode run "create REST API for users"
      hcode run "add tests" --provider=anthropic
      hcode run "refactor" --model-size=small
      hcode run "complex task" --size=big
      hcode run "implement feature" --agents

    \b
    Shortcuts:
      -p     Provider (auto/anthropic/openai/claude/gpt)
      -m     Model name (e.g., gpt-4o, claude-3-5-sonnet)
      --size Model size (small/mid/big)
      -c     Complexity (s/m/c)
      --cost Optimize for cost
      -s     Session ID
      -v     Verbose output
    """
    if not task:
        task = Prompt.ask("[bold cyan]Enter your task[/bold cyan]")
        if not task:
            console.print("[red]No task provided[/red]")
            sys.exit(1)

    # Map shortcuts
    provider_map = {'claude': 'anthropic', 'gpt': 'openai'}
    provider = provider_map.get(provider, provider)

    complexity_map = {'s': 'simple', 'm': 'moderate', 'c': 'complex'}
    complexity = complexity_map.get(complexity, complexity)

    # Show task panel
    task_panel = Panel(
        Markdown(f"**Task:** {task}\n\n**Provider:** {provider} | **Complexity:** {complexity}"),
        title=f"[bold blue]{EMOJI['rocket']} Task Execution[/bold blue]",
        border_style="blue"
    )
    console.print(task_panel)

    # Load config
    config = load_config()

    # Get API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("providers", {}).get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("providers", {}).get("openai", {}).get("api_key")
    openai_base_url = config.get("providers", {}).get("openai", {}).get("base_url")

    if not anthropic_key and not openai_key:
        console.print(Panel(
            f"[red]{EMOJI['cross']} No API keys found[/red]\n\n"
            "Set environment variables:\n"
            "  [cyan]export ANTHROPIC_API_KEY='your-key'[/cyan]\n"
            "  [cyan]export OPENAI_API_KEY='your-key'[/cyan]\n\n"
            "Or add to .hcoderc configuration file",
            title="[red]Error[/red]",
            border_style="red"
        ))
        sys.exit(1)

    # Determine model selection
    from hcode.utils import get_model_for_size

    anthropic_model = None
    openai_model = None

    # Priority: CLI arg > env var (handled in config) > config default
    if model:
        # Specific model provided via CLI
        if provider in ['anthropic', 'claude']:
            anthropic_model = model
        elif provider in ['openai', 'gpt']:
            openai_model = model
        else:
            # Auto provider, use for both (will be selected by provider selector)
            anthropic_model = model if 'claude' in model.lower() else None
            openai_model = model if 'gpt' in model.lower() or 'llama' in model.lower() else None
    elif model_size:
        # Model size provided via CLI
        anthropic_model = get_model_for_size("anthropic", model_size)
        openai_model = get_model_for_size("openai", model_size, openai_base_url)
    else:
        # Use from config (already loaded with env overrides)
        anthropic_model = config.get("providers", {}).get("anthropic", {}).get("default_model")
        openai_model = config.get("providers", {}).get("openai", {}).get("default_model")

    # Create agent
    preferences = ProviderPreferences(
        primary_provider=provider,
        cost_optimization="aggressive" if cost else "balanced",
        prefer_streaming=stream
    )

    with create_progress() as progress:
        init_task = progress.add_task("[cyan]Initializing agent...", total=100)

        agent = EnhancedHcodeAgent(
            anthropic_key=anthropic_key,
            openai_key=openai_key,
            openai_base_url=openai_base_url,
            anthropic_model=anthropic_model,
            openai_model=openai_model,
            preferences=preferences,
            session_id=session
        )

        progress.update(init_task, completed=100)

    # Map complexity
    complexity_enum = {
        "simple": TaskComplexity.SIMPLE,
        "moderate": TaskComplexity.MODERATE,
        "complex": TaskComplexity.COMPLEX
    }[complexity]

    # Execute task
    try:
        if stream:
            console.print("\n[bold cyan]Response:[/bold cyan]\n")

        result = asyncio.run(agent.execute_task(
            task=task,
            complexity=complexity_enum,
            task_type=TaskType.CODE_GENERATION,
            stream=stream,
            use_sub_agents=agents
        ))

        if not stream:
            console.print(Panel(
                Markdown(result),
                title=f"[bold green]{EMOJI['success']} Response[/bold green]",
                border_style="green"
            ))

        # Show stats
        stats = agent.get_session_stats()

        stats_table = Table(show_header=False, box=box.SIMPLE)
        stats_table.add_row(f"{EMOJI['money']} Cost", f"[green]${stats['total_cost']:.4f}[/green]")
        stats_table.add_row(f"{EMOJI['robot']} Provider", f"[cyan]{stats['provider']}[/cyan]")
        stats_table.add_row("Messages", f"[yellow]{stats['context']['total_messages']}[/yellow]")
        stats_table.add_row("Session", f"[dim]{stats['context']['session_id']}[/dim]")

        console.print("\n")
        console.print(Panel(stats_table, title="[bold]Statistics[/bold]", border_style="dim"))

    except KeyboardInterrupt:
        console.print(f"\n[yellow]{EMOJI['warning']} Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(Panel(
            f"[red]{EMOJI['cross']} Error: {str(e)}[/red]\n\n"
            "[dim]Use --verbose for detailed error information[/dim]",
            title="[red]Execution Failed[/red]",
            border_style="red"
        ))
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command(name='chat', short_help='Interactive chat')
@click.option('-p', '--provider', type=click.Choice(['auto', 'anthropic', 'openai']),
              default='auto', help='AI provider')
@click.option('-s', '--session', help='Session ID')
def chat_mode(provider, session):
    """
    💬 Start an interactive chat session

    \b
    Commands in chat:
      /help     Show available commands
      /clear    Clear conversation
      /stats    Show statistics
      /export   Export session
      /exit     Exit chat

    \b
    Examples:
      hcode chat
      hcode chat --provider=anthropic
      hcode chat --session=my-session
    """
    show_banner()

    config = load_config()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("providers", {}).get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("providers", {}).get("openai", {}).get("api_key")

    if not anthropic_key and not openai_key:
        console.print("[red]No API keys found[/red]")
        sys.exit(1)

    preferences = ProviderPreferences(primary_provider=provider)
    agent = EnhancedHcodeAgent(
        anthropic_key=anthropic_key,
        openai_key=openai_key,
        preferences=preferences,
        session_id=session
    )

    console.print(Panel(
        "[bold green]Interactive Chat Mode[/bold green]\n\n"
        "💡 Tips:\n"
        "  • Type naturally, Hcode understands context\n"
        "  • Use /commands for special actions\n"
        "  • Press Ctrl+C to interrupt, /exit to quit\n"
        "  • Responses stream in real-time",
        border_style="green"
    ))

    message_count = 0

    while True:
        try:
            # Beautiful prompt
            user_input = console.input(f"\n[bold cyan]You [{message_count}]:[/bold cyan] ")

            if not user_input.strip():
                continue

            # Handle commands
            if user_input.startswith('/'):
                command = user_input[1:].lower()

                if command in ['exit', 'quit', 'q']:
                    if Confirm.ask("Exit chat?", default=True):
                        console.print("[yellow]👋 Goodbye![/yellow]")
                        break
                    continue

                elif command == 'help':
                    help_table = Table(title="Chat Commands", box=box.ROUNDED)
                    help_table.add_column("Command", style="cyan")
                    help_table.add_column("Description")
                    help_table.add_row("/help", "Show this help")
                    help_table.add_row("/clear", "Clear conversation")
                    help_table.add_row("/stats", "Show statistics")
                    help_table.add_row("/export", "Export session")
                    help_table.add_row("/exit", "Exit chat")
                    console.print(help_table)
                    continue

                elif command == 'stats':
                    stats = agent.get_session_stats()
                    stats_panel = Panel(
                        f"💰 Cost: [green]${stats['total_cost']:.4f}[/green]\n"
                        f"💬 Messages: [yellow]{stats['context']['total_messages']}[/yellow]\n"
                        f"{EMOJI['robot']} Provider: [cyan]{stats['provider']}[/cyan]\n"
                        f"📝 Session: [dim]{stats['context']['session_id']}[/dim]",
                        title="Statistics",
                        border_style="blue"
                    )
                    console.print(stats_panel)
                    continue

                elif command == 'clear':
                    agent.context_manager.clear_context(keep_system=True)
                    console.print(f"[green]{EMOJI['success']} Conversation cleared[/green]")
                    message_count = 0
                    continue

                elif command == 'export':
                    filename = f"session_{agent.context_manager.session_id}.json"
                    agent.export_session(filename)
                    console.print(f"[green]{EMOJI['success']} Exported to {filename}[/green]")
                    continue

            # Execute task
            console.print(f"\n[bold green]Assistant [{message_count}]:[/bold green]\n")

            result = asyncio.run(agent.execute_task(
                task=user_input,
                stream=True
            ))

            message_count += 1

        except KeyboardInterrupt:
            console.print(f"\n[yellow]{EMOJI['warning']} Interrupted. Type /exit to quit or continue chatting.[/yellow]")
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]{EMOJI['cross']} Error: {str(e)}[/red]")


@cli.command(name='analyze', short_help='Analyze code')
@click.argument('path', required=False)
@click.option('-p', '--provider', type=click.Choice(['auto', 'anthropic', 'openai']), default='auto')
@click.option('--deep', is_flag=True, help='Deep analysis')
def analyze_code(path, provider, deep):
    """
    🔍 Analyze code for issues and improvements

    \b
    Examples:
      hcode analyze src/main.py
      hcode analyze .
      hcode analyze --deep
    """
    if not path:
        path = "."

    console.print(Panel(
        f"[bold blue]Analyzing:[/bold blue] {path}\n"
        f"[dim]Mode: {'Deep' if deep else 'Standard'}[/dim]",
        border_style="blue"
    ))

    config = load_config()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("providers", {}).get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("providers", {}).get("openai", {}).get("api_key")

    preferences = ProviderPreferences(primary_provider=provider)
    agent = EnhancedHcodeAgent(
        anthropic_key=anthropic_key,
        openai_key=openai_key,
        preferences=preferences
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing code...", total=None)

        result = asyncio.run(agent.execute_task(
            f"Analyze code in {path} for bugs, security issues, and improvements. "
            f"{'Provide deep analysis with detailed recommendations.' if deep else ''}",
            stream=False
        ))

        progress.remove_task(task)

    console.print(Panel(Markdown(result), title="[bold green]✓ Analysis Complete[/bold green]", border_style="green"))


@cli.command(name='explore', short_help='Explore codebase')
@click.argument('query')
@click.option('-t', '--thoroughness', type=click.Choice(['quick', 'medium', 'thorough', 'q', 'm', 't']),
              default='medium', help='Search thoroughness')
def explore_codebase(query, thoroughness):
    """
    🔍 Explore and search codebase

    \b
    Examples:
      hcode explore "API endpoints"
      hcode explore "authentication logic" --thoroughness=thorough
      hcode explore "database queries" -t q
    """
    thoroughness_map = {'q': 'quick', 'm': 'medium', 't': 'thorough'}
    thoroughness = thoroughness_map.get(thoroughness, thoroughness)

    config = load_config()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("providers", {}).get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("providers", {}).get("openai", {}).get("api_key")

    agent = EnhancedHcodeAgent(
        anthropic_key=anthropic_key,
        openai_key=openai_key
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Exploring ({thoroughness})...", total=None)

        result = asyncio.run(agent.explore_codebase(query, thoroughness=thoroughness))

        progress.remove_task(task)

    console.print(Panel(Markdown(result), title="[bold cyan]🔍 Exploration Results[/bold cyan]", border_style="cyan"))


# Aliases for convenience
@cli.command(name='r', hidden=True)
@click.pass_context
def run_alias(ctx):
    """Alias for 'run' command"""
    ctx.forward(run_task)


@cli.command(name='c', hidden=True)
@click.pass_context
def chat_alias(ctx):
    """Alias for 'chat' command"""
    ctx.forward(chat_mode)


@cli.command(name='a', hidden=True)
@click.pass_context
def analyze_alias(ctx):
    """Alias for 'analyze' command"""
    ctx.forward(analyze_code)


@cli.command(name='quick', short_help='Quick shortcuts')
def quick_reference():
    """
    ⚡ Quick reference for shortcuts and commands
    """
    show_banner()

    # Shortcuts table
    shortcuts = Table(title="⚡ Keyboard Shortcuts & Aliases", box=box.ROUNDED)
    shortcuts.add_column("Shortcut", style="cyan", no_wrap=True)
    shortcuts.add_column("Command", style="green")
    shortcuts.add_column("Description")

    shortcuts.add_row("hcode r", "hcode run", "Execute task")
    shortcuts.add_row("hcode c", "hcode chat", "Start chat")
    shortcuts.add_row("hcode a", "hcode analyze", "Analyze code")
    shortcuts.add_row("-p", "--provider", "Choose provider")
    shortcuts.add_row("-c s/m/c", "--complexity", "Set complexity")
    shortcuts.add_row("--cost", "--optimize-cost", "Optimize cost")
    shortcuts.add_row("-v", "--verbose", "Verbose output")

    console.print(shortcuts)

    # Common patterns
    patterns = Table(title="🎯 Common Patterns", box=box.ROUNDED)
    patterns.add_column("Pattern", style="cyan")
    patterns.add_column("Example")

    patterns.add_row("Quick task", "hcode r 'add logging'")
    patterns.add_row("With Claude", "hcode r 'refactor' -p claude")
    patterns.add_row("Cost optimized", "hcode r 'fix tests' --cost")
    patterns.add_row("Complex task", "hcode r 'redesign' -c c")
    patterns.add_row("Interactive", "hcode c")
    patterns.add_row("Deep analysis", "hcode a . --deep")

    console.print("\n", patterns)


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
