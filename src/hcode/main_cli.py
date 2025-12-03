"""
HCode CLI - Command-line interface with beautiful styling and all features.
"""

import click
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

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

from hcode.core import HcodeAgent
from hcode.providers import ProviderPreferences, TaskComplexity, TaskType
from hcode.utils.config import load_config

# Import UI theme system
from hcode.ui import (
    get_console,
    get_palette,
    get_theme,
    set_theme,
    ThemeMode,
    create_banner,
    Icons,
)
from hcode.ui.panels import (
    UserMessagePanel,
    AIMessagePanel,
    ToolPanel,
    ErrorPanel,
    SuccessPanel,
    InfoPanel,
)
from hcode.cli.autocomplete import (
    HCodePrompt,
    create_hcode_prompt,
    get_command_help,
    get_all_commands,
)

# Get themed console
console = get_console()

# Get icons instance (Windows-safe)
icons = Icons()

# Create progress with theme
def create_progress(**kwargs):
    """Create a themed Progress object"""
    palette = get_palette()
    return Progress(
        SpinnerColumn(style=palette.primary),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style=palette.primary, finished_style=palette.success),
        TaskProgressColumn(),
        console=console,
        **kwargs
    )

# Emoji shortcuts using Icons (Windows-safe)
EMOJI = {
    "success": icons.SUCCESS,
    "error": icons.ERROR,
    "warning": icons.WARNING,
    "info": icons.INFO,
    "rocket": icons.ROCKET,
    "robot": icons.AI,
    "tool": icons.GEAR,
    "search": icons.SEARCH,
    "fire": icons.LIGHTNING,
    "sparkles": icons.SPARKLE,
    "check": icons.SUCCESS,
    "cross": icons.ERROR,
    "clock": icons.LOADING,
    "money": "$"  # No icon available
}


def show_banner():
    """Display beautiful themed banner"""
    banner = create_banner()
    console.print(banner)


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

        agent = HcodeAgent(
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
    openai_base_url = os.getenv("OPENAI_BASE_URL") or config.get("providers", {}).get("openai", {}).get("base_url")

    # Get model configuration
    anthropic_model = os.getenv("ANTHROPIC_MODEL") or config.get("providers", {}).get("anthropic", {}).get("default_model")
    openai_model = os.getenv("OPENAI_MODEL") or config.get("providers", {}).get("openai", {}).get("default_model")

    if not anthropic_key and not openai_key:
        console.print("[red]No API keys found[/red]")
        sys.exit(1)

    # Get provider preference from config if not specified
    if provider == 'auto':
        provider = config.get("preferences", {}).get("primary_provider", "auto")

    preferences = ProviderPreferences(primary_provider=provider)
    agent = HcodeAgent(
        anthropic_key=anthropic_key,
        openai_key=openai_key,
        openai_base_url=openai_base_url,
        anthropic_model=anthropic_model,
        openai_model=openai_model,
        preferences=preferences,
        session_id=session,
        config=config
    )

    palette = get_palette()

    # Show modern info panel for chat tips
    info_panel = InfoPanel(
        title="Interactive Chat Mode",
        content=(
            f"{icons.INFO} Tips:\n"
            "  • Type naturally, Hcode understands context\n"
            "  • Use /commands for special actions (Tab to autocomplete)\n"
            "  • Press Ctrl+C to interrupt, /exit to quit\n"
            "  • Responses stream in real-time\n\n"
            f"{icons.LIGHTNING} Shortcuts:\n"
            "  • Tab: Autocomplete commands & suggestions\n"
            "  • Ctrl+Space: Show all suggestions\n"
            "  • ↑/↓: Navigate history & suggestions"
        )
    )
    console.print(info_panel.render())

    # Create smart prompt with autocomplete
    hcode_prompt = create_hcode_prompt()
    hcode_prompt.create_session()

    message_count = 0

    while True:
        try:
            # Smart prompt with autocomplete
            console.print()  # Add spacing
            user_input = hcode_prompt.prompt(message_count=message_count)

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

                elif command.startswith('help'):
                    # Check if help for specific command
                    parts = command.split(maxsplit=1)
                    if len(parts) > 1:
                        cmd_name = parts[1] if parts[1].startswith('/') else f'/{parts[1]}'
                        help_text = get_command_help(cmd_name)
                        if help_text:
                            console.print(Panel(help_text, title=f"[bold]Help: {cmd_name}[/bold]", border_style=palette.info))
                        else:
                            console.print(f"[{palette.warning}]Unknown command: {cmd_name}[/]")
                        continue

                    # Show all commands grouped by category
                    all_commands = get_all_commands()
                    categories = {}
                    for cmd in all_commands:
                        if cmd.category not in categories:
                            categories[cmd.category] = []
                        categories[cmd.category].append(cmd)

                    console.print(f"\n[bold {palette.primary}]{icons.INFO} Available Commands[/bold {palette.primary}]\n")

                    for category, cmds in sorted(categories.items()):
                        console.print(f"[bold {palette.accent}]{category.upper()}[/bold {palette.accent}]")
                        help_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
                        help_table.add_column("Command", style=f"{palette.info}", min_width=15)
                        help_table.add_column("Description", style=f"{palette.text_secondary}")
                        help_table.add_column("Aliases", style=f"{palette.text_muted}")

                        for cmd in cmds:
                            aliases = ", ".join(cmd.aliases) if cmd.aliases else ""
                            help_table.add_row(cmd.name, cmd.description, aliases)

                        console.print(help_table)
                        console.print()

                    console.print(f"[{palette.text_muted}]Type /help <command> for detailed help on a specific command[/]")
                    continue

                elif command == 'stats':
                    stats = agent.get_session_stats()
                    stats_content = (
                        f"$ Cost: [{palette.success}]${stats['total_cost']:.4f}[/]\n"
                        f"{icons.MESSAGE} Messages: [{palette.warning}]{stats['context']['total_messages']}[/]\n"
                        f"{icons.AI} Provider: [{palette.info}]{stats['provider']}[/]\n"
                        f"{icons.FILE} Session: [{palette.text_muted}]{stats['context']['session_id']}[/]"
                    )
                    stats_panel = InfoPanel(
                        title="Statistics",
                        content=stats_content
                    )
                    console.print(stats_panel.render())
                    continue

                elif command.startswith('theme'):
                    parts = command.split(maxsplit=1)
                    if len(parts) > 1:
                        theme_name = parts[1].lower()
                        theme_map = {
                            'cyberpunk': ThemeMode.CYBERPUNK,
                            'neon': ThemeMode.NEON_NIGHTS,
                            'matrix': ThemeMode.MATRIX,
                            'synthwave': ThemeMode.SYNTHWAVE,
                            'frost': ThemeMode.FROST,
                            'minimal': ThemeMode.MINIMAL,
                            'hacker': ThemeMode.HACKER,
                        }
                        if theme_name in theme_map:
                            set_theme(theme_map[theme_name])
                            palette = get_palette()  # Refresh palette
                            console.print(f"[{palette.success}]{icons.SUCCESS} Theme changed to {theme_name}[/]")
                        else:
                            console.print(f"[{palette.warning}]Available themes: {', '.join(theme_map.keys())}[/]")
                    else:
                        console.print(f"[{palette.info}]Current theme. Available: cyberpunk, neon, matrix, synthwave, frost, minimal, hacker[/]")
                    continue

                elif command == 'clear':
                    agent.context_manager.clear_context(keep_system=True)
                    console.print(f"[{palette.success}]{icons.SUCCESS} Conversation cleared[/]")
                    message_count = 0
                    continue

                elif command == 'export':
                    filename = f"session_{agent.context_manager.session_id}.json"
                    agent.export_session(filename)
                    console.print(f"[green]{EMOJI['success']} Exported to {filename}[/green]")
                    continue

            # Execute task with modern assistant indicator
            console.print(f"\n[bold {palette.success}]{icons.AI} Assistant [{message_count}]:[/bold {palette.success}]\n")

            result = asyncio.run(agent.execute_task(
                task=user_input,
                stream=True
            ))

            message_count += 1

        except KeyboardInterrupt:
            console.print(f"\n[{palette.warning}]{icons.WARNING} Interrupted. Type /exit to quit or continue chatting.[/{palette.warning}]")
            continue
        except EOFError:
            break
        except Exception as e:
            error_panel = ErrorPanel(
                message=str(e),
                error_type="Error"
            )
            console.print(error_panel.render())


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
    agent = HcodeAgent(
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

    agent = HcodeAgent(
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


@cli.command(name='init', short_help='Initialize project config')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing config')
def init_project(force):
    """
    Initialize HCode configuration in current directory.

    Creates a .hcode/ directory with default configuration files.

    \b
    Examples:
      hcode init           Initialize with defaults
      hcode init --force   Overwrite existing config
    """
    from pathlib import Path
    from .config.defaults import DEFAULT_CONFIG_YAML

    project_dir = Path.cwd()
    hcode_dir = project_dir / ".hcode"
    config_file = hcode_dir / "config.yaml"

    if config_file.exists() and not force:
        console.print(Panel(
            f"[yellow]{EMOJI['warning']} Configuration already exists[/yellow]\n\n"
            f"Location: {config_file}\n\n"
            "Use [bold]--force[/bold] to overwrite",
            title="[yellow]Already Initialized[/yellow]",
            border_style="yellow"
        ))
        return

    try:
        # Create .hcode directory
        hcode_dir.mkdir(exist_ok=True)

        # Create config file
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_CONFIG_YAML)

        # Create logs directory
        (hcode_dir / "logs").mkdir(exist_ok=True)

        # Create .gitignore for .hcode
        gitignore_file = hcode_dir / ".gitignore"
        with open(gitignore_file, 'w', encoding='utf-8') as f:
            f.write("# HCode local files\nlogs/\nmemory.db\n*.log\n")

        console.print(Panel(
            f"[green]{EMOJI['success']} HCode initialized successfully![/green]\n\n"
            f"[dim]Created:[/dim]\n"
            f"  {EMOJI['check']} .hcode/config.yaml\n"
            f"  {EMOJI['check']} .hcode/logs/\n"
            f"  {EMOJI['check']} .hcode/.gitignore\n\n"
            "[dim]Next steps:[/dim]\n"
            "  1. Edit .hcode/config.yaml to customize settings\n"
            "  2. Set API keys in environment or config\n"
            "  3. Run [bold]hcode chat[/bold] to start",
            title=f"[green]{EMOJI['rocket']} Project Initialized[/green]",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[red]{EMOJI['cross']} Error: {e}[/red]")
        sys.exit(1)


@cli.group(name='config', short_help='Manage configuration')
def config_group():
    """
    Manage HCode configuration settings.

    \b
    Commands:
      hcode config set KEY VALUE   Set a configuration value
      hcode config get KEY         Get a configuration value
      hcode config list            List all configurations
      hcode config path            Show config file locations
    """
    pass


@config_group.command(name='set')
@click.argument('key')
@click.argument('value')
@click.option('--global', '-g', 'is_global', is_flag=True, help='Set in global config')
def config_set(key, value, is_global):
    """
    Set a configuration value.

    \b
    Examples:
      hcode config set llm.provider anthropic
      hcode config set llm.temperature 0.5
      hcode config set ui.theme dark
      hcode config set -g llm.anthropic_api_key sk-ant-...
    """
    from pathlib import Path
    import yaml

    # Determine config file location
    if is_global:
        config_dir = Path.home() / ".hcode"
    else:
        config_dir = Path.cwd() / ".hcode"

    config_file = config_dir / "config.yaml"

    # Load existing config or create empty
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    else:
        config_dir.mkdir(parents=True, exist_ok=True)
        config = {}

    # Parse key path (e.g., "llm.provider" -> ["llm", "provider"])
    keys = key.split('.')
    current = config

    # Navigate/create nested structure
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    # Convert value to appropriate type
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif value.isdigit():
        value = int(value)
    else:
        try:
            value = float(value)
        except ValueError:
            pass  # Keep as string

    # Set the value
    current[keys[-1]] = value

    # Save config
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print(f"[green]{EMOJI['success']} Set {key} = {value}[/green]")
    console.print(f"[dim]Config file: {config_file}[/dim]")


@config_group.command(name='get')
@click.argument('key', required=False)
def config_get(key):
    """
    Get a configuration value.

    \b
    Examples:
      hcode config get llm.provider
      hcode config get llm
      hcode config get              # Show all
    """
    from pathlib import Path
    import yaml

    # Check both local and global configs
    local_config = Path.cwd() / ".hcode" / "config.yaml"
    global_config = Path.home() / ".hcode" / "config.yaml"

    config = {}

    # Load global config first
    if global_config.exists():
        with open(global_config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

    # Override with local config
    if local_config.exists():
        with open(local_config, 'r', encoding='utf-8') as f:
            local = yaml.safe_load(f) or {}
            # Deep merge
            def merge(base, override):
                for k, v in override.items():
                    if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                        merge(base[k], v)
                    else:
                        base[k] = v
            merge(config, local)

    if not key:
        # Show all config
        console.print(Panel(
            Syntax(yaml.dump(config, default_flow_style=False), "yaml", theme="monokai"),
            title="[bold]Configuration[/bold]",
            border_style="blue"
        ))
        return

    # Navigate to key
    keys = key.split('.')
    current = config

    try:
        for k in keys:
            current = current[k]

        if isinstance(current, dict):
            console.print(Panel(
                Syntax(yaml.dump(current, default_flow_style=False), "yaml", theme="monokai"),
                title=f"[bold]{key}[/bold]",
                border_style="blue"
            ))
        else:
            console.print(f"[cyan]{key}[/cyan] = [green]{current}[/green]")

    except (KeyError, TypeError):
        console.print(f"[yellow]{EMOJI['warning']} Key not found: {key}[/yellow]")


@config_group.command(name='list')
def config_list():
    """List all configuration values."""
    from pathlib import Path
    import yaml

    table = Table(title="Configuration", box=box.ROUNDED)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="dim")

    # Check configs
    local_config = Path.cwd() / ".hcode" / "config.yaml"
    global_config = Path.home() / ".hcode" / "config.yaml"

    def flatten_dict(d, prefix=''):
        items = []
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, key))
            else:
                items.append((key, v))
        return items

    # Load and display global config
    if global_config.exists():
        with open(global_config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            for key, value in flatten_dict(config):
                table.add_row(key, str(value), "global")

    # Load and display local config
    if local_config.exists():
        with open(local_config, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            for key, value in flatten_dict(config):
                table.add_row(key, str(value), "local")

    console.print(table)


@config_group.command(name='path')
def config_path():
    """Show configuration file locations."""
    from pathlib import Path

    local_config = Path.cwd() / ".hcode" / "config.yaml"
    global_config = Path.home() / ".hcode" / "config.yaml"

    table = Table(title="Config Locations", box=box.ROUNDED)
    table.add_column("Type", style="cyan")
    table.add_column("Path")
    table.add_column("Exists", style="green")

    table.add_row(
        "Global",
        str(global_config),
        EMOJI['check'] if global_config.exists() else EMOJI['cross']
    )
    table.add_row(
        "Local",
        str(local_config),
        EMOJI['check'] if local_config.exists() else EMOJI['cross']
    )

    console.print(table)


@cli.command(name='history', short_help='Show conversation history')
@click.option('-n', '--limit', default=10, help='Number of entries to show')
@click.option('--session', '-s', help='Filter by session ID')
def show_history(limit, session):
    """
    Show conversation history.

    \b
    Examples:
      hcode history             Show last 10 entries
      hcode history -n 20       Show last 20 entries
      hcode history -s abc123   Show history for session
    """
    from pathlib import Path
    import sqlite3
    import json

    db_path = Path.home() / ".hcode" / "memory.db"

    if not db_path.exists():
        console.print(f"[yellow]{EMOJI['warning']} No history found[/yellow]")
        console.print("[dim]Start a chat session to create history[/dim]")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
        )
        if not cursor.fetchone():
            console.print(f"[yellow]{EMOJI['warning']} No conversations found[/yellow]")
            conn.close()
            return

        # Query history
        if session:
            cursor.execute(
                "SELECT session_id, role, content, timestamp FROM conversations "
                "WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session, limit)
            )
        else:
            cursor.execute(
                "SELECT session_id, role, content, timestamp FROM conversations "
                "ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            console.print(f"[yellow]{EMOJI['warning']} No history found[/yellow]")
            return

        table = Table(title="Conversation History", box=box.ROUNDED)
        table.add_column("Session", style="dim", max_width=12)
        table.add_column("Role", style="cyan", max_width=10)
        table.add_column("Content", max_width=60)
        table.add_column("Time", style="dim")

        for session_id, role, content, timestamp in rows:
            # Truncate content
            content_preview = content[:100] + "..." if len(content) > 100 else content
            content_preview = content_preview.replace('\n', ' ')

            table.add_row(
                session_id[:10] + "...",
                role,
                content_preview,
                timestamp
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]{EMOJI['cross']} Error reading history: {e}[/red]")


@cli.command(name='clear', short_help='Clear conversation history')
@click.option('--session', '-s', help='Clear specific session')
@click.option('--all', '-a', 'clear_all', is_flag=True, help='Clear all history')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def clear_history(session, clear_all, force):
    """
    Clear conversation history.

    \b
    Examples:
      hcode clear                 Clear current context
      hcode clear -s abc123       Clear specific session
      hcode clear --all           Clear all history
      hcode clear --all --force   Clear all without confirmation
    """
    from pathlib import Path
    import sqlite3

    db_path = Path.home() / ".hcode" / "memory.db"

    if not db_path.exists():
        console.print(f"[green]{EMOJI['success']} No history to clear[/green]")
        return

    # Confirmation
    if clear_all and not force:
        if not Confirm.ask("[yellow]Clear ALL conversation history?[/yellow]", default=False):
            console.print("[dim]Cancelled[/dim]")
            return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
        )
        if not cursor.fetchone():
            console.print(f"[green]{EMOJI['success']} No history to clear[/green]")
            conn.close()
            return

        if clear_all:
            cursor.execute("DELETE FROM conversations")
            deleted = cursor.rowcount
        elif session:
            cursor.execute(
                "DELETE FROM conversations WHERE session_id = ?",
                (session,)
            )
            deleted = cursor.rowcount
        else:
            # Clear most recent session
            cursor.execute(
                "SELECT session_id FROM conversations ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "DELETE FROM conversations WHERE session_id = ?",
                    (row[0],)
                )
                deleted = cursor.rowcount
            else:
                deleted = 0

        conn.commit()
        conn.close()

        console.print(f"[green]{EMOJI['success']} Cleared {deleted} entries[/green]")

    except Exception as e:
        console.print(f"[red]{EMOJI['cross']} Error clearing history: {e}[/red]")


@cli.command(name='debug', short_help='Debug an issue')
@click.argument('error_description')
@click.option('-p', '--provider', type=click.Choice(['auto', 'anthropic', 'openai']), default='auto')
def debug_issue(error_description, provider):
    """
    Debug an issue with AI assistance.

    \b
    Examples:
      hcode debug "TypeError: NoneType has no attribute 'get'"
      hcode debug "Tests failing on line 42"
    """
    config = load_config()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("providers", {}).get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("providers", {}).get("openai", {}).get("api_key")

    if not anthropic_key and not openai_key:
        console.print("[red]No API keys found[/red]")
        sys.exit(1)

    preferences = ProviderPreferences(primary_provider=provider)
    agent = HcodeAgent(
        anthropic_key=anthropic_key,
        openai_key=openai_key,
        preferences=preferences
    )

    console.print(Panel(
        f"[bold blue]Debugging:[/bold blue] {error_description}",
        border_style="blue"
    ))

    console.print("\n[bold cyan]Analysis:[/bold cyan]\n")

    result = asyncio.run(agent.execute_task(
        f"Debug this issue: {error_description}\n\n"
        "Please:\n"
        "1. Identify the root cause\n"
        "2. Explain why it's happening\n"
        "3. Propose a fix\n"
        "4. Suggest how to prevent similar issues",
        stream=True
    ))


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
