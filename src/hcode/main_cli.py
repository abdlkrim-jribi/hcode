"""
HCode CLI - Command-line interface with beautiful styling and all features.
"""

import asyncio
import os
import sys

import click
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.traceback import install as install_rich_traceback
from rich import box

# Install rich traceback for beautiful error messages
install_rich_traceback(show_locals=True)

from hcode.core import HcodeAgent
from hcode.providers import ProviderPreferences, TaskComplexity, TaskType
from hcode.utils.config import load_config

# Import UI theme system
from hcode.ui import (
    get_console,
    get_palette,
    set_theme,
    ThemeMode,
    create_banner,
    Icons,
)
from hcode.ui.panels import (
    ErrorPanel,
    InfoPanel,
)
from hcode.cli.autocomplete import (
    create_hcode_prompt,
    get_command_help,
    get_all_commands,
)

from hcode.ui.live_todo_bar import (
    LiveTodoBar,
)

# Import reasoning components for automatic todo extraction
from hcode.core.response.thinking_processor import parse_thinking_block
from hcode.core.reasoning import ReasoningParser, ReasoningToTodoIntegrator

# Get themed console
console = get_console()

# Get icons instance (Windows-safe)
icons = Icons()

# Initialize reasoning components for todo extraction
_reasoning_parser = ReasoningParser()
_todo_integrator = ReasoningToTodoIntegrator()


def extract_todos_from_response(response: str) -> list:
    """
    Extract todos from agent response by parsing thinking blocks.

    Args:
        response: The agent's response text

    Returns:
        List of todo items extracted from reasoning
    """
    todos = []

    # Try to parse thinking block from response
    thinking_block, _ = parse_thinking_block(response)

    if thinking_block and thinking_block.is_valid():
        # Parse structured reasoning from thinking block
        reasoning = _reasoning_parser.parse(thinking_block.raw_content)

        if reasoning:
            # Extract todos from structured reasoning
            todos = _todo_integrator.extract_todos_from_reasoning(reasoning)

    return todos


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
        **kwargs,
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
    "money": "$",  # No icon available
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
        "[cyan]💡 Tip:[/cyan] Try [bold]hcode chat[/bold] for interactive mode",
    ]
    console.print("\n".join(tips) + "\n")


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version")
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
        console.print(
            f"{EMOJI['robot']} AI Providers: [cyan]Anthropic[/cyan] + [green]OpenAI[/green]"
        )
        sys.exit(0)

    if ctx.invoked_subcommand is None:
        show_banner()
        show_welcome()
        console.print(ctx.get_help())


@cli.command(name="run", short_help="Execute a task")
@click.argument("task", required=False)
@click.option(
    "-p",
    "--provider",
    type=click.Choice(["auto", "anthropic", "openai", "claude", "gpt"]),
    default="auto",
    help="AI provider",
)
@click.option("-m", "--model", help="Specific model name")
@click.option(
    "-c",
    "--complexity",
    type=click.Choice(["simple", "moderate", "complex", "s", "m", "c"]),
    default="moderate",
    help="Task complexity",
)
@click.option("--cost", "--optimize-cost", is_flag=True, help="Optimize for cost")
@click.option("-s", "--session", help="Session ID")
@click.option("--stream/--no-stream", default=True, help="Stream responses")
@click.option("--agents/--no-agents", default=False, help="Use specialized sub-agents")
@click.option("--autonomous/--no-autonomous", default=False, help="Run in autonomous mode (skip confirmation)")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def run_task(task, provider, model, complexity, cost, session, stream, agents, autonomous, verbose):
    """
    Execute a coding task with AI assistance

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
    provider_map = {"claude": "anthropic", "gpt": "openai"}
    provider = provider_map.get(provider, provider)

    complexity_map = {"s": "simple", "m": "moderate", "c": "complex"}
    complexity = complexity_map.get(complexity, complexity)

    # Show task panel
    task_panel = Panel(
        Markdown(f"**Task:** {task}\n\n**Provider:** {provider} | **Complexity:** {complexity}"),
        title=f"[bold blue]{EMOJI['rocket']} Task Execution[/bold blue]",
        border_style="blue",
    )
    console.print(task_panel)

    config = load_config()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("providers", {}).get(
        "anthropic", {}
    ).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("providers", {}).get("openai", {}).get(
        "api_key"
    )
    openai_base_url = os.getenv("OPENAI_BASE_URL") or config.get("providers", {}).get(
        "openai", {}
    ).get("base_url")

    # Get model configuration
    anthropic_model = os.getenv("ANTHROPIC_MODEL") or config.get("providers", {}).get(
        "anthropic", {}
    ).get("default_model")
    openai_model = os.getenv("OPENAI_MODEL") or config.get("providers", {}).get("openai", {}).get(
        "default_model"
    )

    if not anthropic_key and not openai_key:
        console.print(
            Panel(
                f"[red]{EMOJI['cross']} No API keys found[/red]\n\n"
                "Set environment variables:\n"
                "  [cyan]export ANTHROPIC_API_KEY='your-key'[/cyan]\n"
                "  [cyan]export OPENAI_API_KEY='your-key'[/cyan]\n\n"
                "Or add to .hcoderc configuration file",
                title="[red]Error[/red]",
                border_style="red",
            )
        )
        sys.exit(1)



    # Create agent
    preferences = ProviderPreferences(
        primary_provider=provider,
        cost_optimization="aggressive" if cost else "balanced",
        prefer_streaming=stream,
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
            session_id=session,
            autonomous_mode=autonomous,
        )

        progress.update(init_task, completed=100)

    # Map complexity
    complexity_enum = {
        "simple": TaskComplexity.SIMPLE,
        "moderate": TaskComplexity.MODERATE,
        "complex": TaskComplexity.COMPLEX,
    }[complexity]

    # Execute task
    try:
        if stream:
            console.print("\n[bold cyan]Response:[/bold cyan]\n")

        result = asyncio.run(
            agent.execute_task(
                task=task,
                complexity=complexity_enum,
                task_type=TaskType.CODE_GENERATION,
                stream=stream,
                use_sub_agents=agents,
            )
        )

        if not stream:
            console.print(
                Panel(
                    Markdown(result),
                    title=f"[bold green]{EMOJI['success']} Response[/bold green]",
                    border_style="green",
                )
            )

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
        from rich.markup import escape
        console.print(
            Panel(
                f"[red]{EMOJI['cross']} Error: {escape(str(e))}[/red]\n\n"
                "[dim]Use --verbose for detailed error information[/dim]",
                title="[red]Execution Failed[/red]",
                border_style="red",
            )
        )
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command(name="chat", short_help="Interactive chat")
@click.option(
    "-p",
    "--provider",
    type=click.Choice(["auto", "anthropic", "openai"]),
    default="auto",
    help="AI provider",
)
@click.option("-s", "--session", help="Session ID")
@click.option(
    "--debug", is_flag=True, help="Enable debug mode (show verbose output, thinking panels)"
)
@click.option("--autonomous/--no-autonomous", default=False, help="Run in autonomous mode (skip confirmation)")
def chat_mode(provider, session, debug, autonomous):
    """
    Start an interactive chat session

    \b
    Commands in chat:
      /help     Show available commands
      /clear    Clear conversation
      /stats    Show statistics
      /todos    Toggle todo display
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
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("providers", {}).get(
        "anthropic", {}
    ).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("providers", {}).get("openai", {}).get(
        "api_key"
    )
    openai_base_url = os.getenv("OPENAI_BASE_URL") or config.get("providers", {}).get(
        "openai", {}
    ).get("base_url")

    # Get model configuration
    anthropic_model = os.getenv("ANTHROPIC_MODEL") or config.get("providers", {}).get(
        "anthropic", {}
    ).get("default_model")
    openai_model = os.getenv("OPENAI_MODEL") or config.get("providers", {}).get("openai", {}).get(
        "default_model"
    )

    if not anthropic_key and not openai_key:
        console.print("[red]No API keys found[/red]")
        sys.exit(1)

    # Get provider preference from config if not specified
    if provider == "auto":
        provider = config.get("preferences", {}).get("primary_provider", "auto")

    # Add debug flag to config
    config["debug"] = debug
    if "ui" not in config:
        config["ui"] = {}
    config["ui"]["debug_mode"] = debug

    preferences = ProviderPreferences(primary_provider=provider)
    agent = HcodeAgent(
        anthropic_key=anthropic_key,
        openai_key=openai_key,
        openai_base_url=openai_base_url,
        anthropic_model=anthropic_model,
        openai_model=openai_model,
        preferences=preferences,
        session_id=session,
        config=config,
        autonomous_mode=autonomous,
    )

    palette = get_palette()

    # Show debug mode indicator if enabled
    if debug:
        console.print(
            f"[bold {palette.warning}]{icons.WARNING} Debug mode enabled - showing verbose output[/bold {palette.warning}]"
        )

    # Show modern welcome/help
    from hcode.ui.banners import display_welcome_help
    display_welcome_help(console)

    # Create smart prompt with autocomplete
    hcode_prompt = create_hcode_prompt()
    hcode_prompt.create_session()

    message_count = 0

    # LiveTodoBar handles persistent display via callback system
    live_todo_bar = LiveTodoBar(console=console, height=6)
    chat_todos = []
    
    # Start LIVE todo bar for persistent Claude Code-style display
    live_todo_bar.start()

    pass


    # Helper function to convert Todo objects to dicts (needs to be outside loop)
    def todo_to_dict(todo):
        """Convert a Todo object or dict to a standard dict format."""
        if isinstance(todo, dict):
            return todo
        # Handle dataclass/object with attributes
        return {
            "content": getattr(todo, "content", getattr(todo, "text", "")),
            "status": getattr(todo, "status", "pending"),
            "activeForm": getattr(todo, "active_form", getattr(todo, "activeForm", "")),
        }

    while True:
        try:
            # LiveTodoBar now handles persistent display - no need to show before prompt
            # Just reset the flag

            # Smart prompt with autocomplete (no extra spacing - todo bar already adds separator)
            user_input = hcode_prompt.prompt(message_count=message_count)

            if not user_input.strip():
                continue

            # Handle commands
            if user_input.startswith("/"):
                command = user_input[1:].lower()

                if command in ["exit", "quit", "q"]:
                    if Confirm.ask("Exit chat?", default=True):
                        # Stop LiveTodoBar gracefully
                        if live_todo_bar.is_active:
                            live_todo_bar.stop()
                        console.print("[yellow]👋 Goodbye![/yellow]")
                        break
                    continue

                elif command == "todos":
                    # status = "enabled" if reasoning_runner.show_todos else "disabled" (Removed)
                    console.print(f"[{palette.info}]{icons.SUCCESS} Todo display toggled[/]")
                    continue

                elif command == "todo":
                    # Show full todo panel (Functionality moved to LiveTodoBar/ClaudeCodeTodoDisplay)
                    console.print(f"[{palette.text_muted}]Todo panel display is now automatic[/]")
                    continue

                elif command.startswith("todo add "):
                    # Add a todo item
                    todo_text = command[9:].strip()
                    if todo_text:
                        # reasoning_runner.add_todo(todo_text) (Removed)
                        console.print(f"[{palette.success}]{icons.SUCCESS} Added: {todo_text}[/]")
                    continue

                elif command == "todo done" or command == "done":
                    # Mark current todo as done
                    # reasoning_runner.complete_current() (Removed)
                    console.print(f"[{palette.success}]{icons.SUCCESS} Task completed[/]")
                    continue

                elif command == "prompts" or command == "prompt list":
                    # List all available prompts
                    from hcode.config import get_prompt_loader, get_prompts_settings

                    settings = get_prompts_settings()
                    loader = get_prompt_loader()

                    if settings.directory.exists():
                        loader.prompts_dir = settings.directory

                    prompts_list = loader.list_prompts()
                    if prompts_list:
                        console.print(
                            f"\n[bold {palette.primary}]{icons.GEAR} Available Prompts[/bold {palette.primary}]"
                        )
                        console.print(f"[{palette.text_muted}]Directory: {loader.prompts_dir}[/]")
                        console.print()

                        prompts_table = Table(box=box.ROUNDED, border_style=palette.border_default)
                        prompts_table.add_column("Name", style=palette.info)
                        prompts_table.add_column("Description", style=palette.text_secondary)
                        prompts_table.add_column("Category", style=palette.accent)
                        prompts_table.add_column("Variables", style=palette.text_muted)

                        for p in prompts_list:
                            vars_str = ", ".join([v["name"] for v in p.get("variables", [])])
                            prompts_table.add_row(
                                p["name"],
                                p.get("description", "")[:50],
                                p.get("category", "general"),
                                vars_str or "-",
                            )

                        console.print(prompts_table)
                    else:
                        console.print(
                            f"[{palette.text_muted}]No prompts found in {loader.prompts_dir}[/]"
                        )
                        console.print(
                            f"[{palette.info}]Create .prompt files in that directory to add prompts.[/]"
                        )
                    continue

                elif command.startswith("prompt "):
                    # Use a prompt: /prompt <name> [var1=value1] [var2=value2]
                    from hcode.config import get_prompt_loader, get_prompts_settings

                    settings = get_prompts_settings()
                    loader = get_prompt_loader()

                    if settings.directory.exists():
                        loader.prompts_dir = settings.directory

                    parts = command[7:].strip().split()
                    if not parts:
                        console.print(
                            f"[{palette.warning}]Usage: /prompt <name> [var1=value1] ...[/]"
                        )
                        continue

                    prompt_name = parts[0]
                    variables = {}

                    # Parse variables (var=value format)
                    for part in parts[1:]:
                        if "=" in part:
                            key, value = part.split("=", 1)
                            variables[key] = value

                    try:
                        rendered = loader.render(prompt_name, variables)
                        console.print(
                            f"\n[bold {palette.primary}]{icons.GEAR} Prompt: {prompt_name}[/bold {palette.primary}]"
                        )
                        console.print(Panel(rendered, border_style=palette.border_default))

                        # Send to agent
                        if Confirm.ask("Send this prompt to the agent?", default=True):
                            user_input = rendered
                        else:
                            continue
                    except ValueError as e:
                        console.print(f"[{palette.error}]{icons.ERROR} {e}[/]")
                        continue
                    except Exception as e:
                        console.print(
                            f"[{palette.error}]{icons.ERROR} Error loading prompt: {e}[/]"
                        )
                        continue

                elif command.startswith("help"):
                    # Check if help for specific command
                    parts = command.split(maxsplit=1)
                    if len(parts) > 1:
                        cmd_name = parts[1] if parts[1].startswith("/") else f"/{parts[1]}"
                        help_text = get_command_help(cmd_name)
                        if help_text:
                            console.print(
                                Panel(
                                    help_text,
                                    title=f"[bold]Help: {cmd_name}[/bold]",
                                    border_style=palette.info,
                                )
                            )
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

                    console.print(
                        f"\n[bold {palette.primary}]{icons.INFO} Available Commands[/bold {palette.primary}]\n"
                    )

                    for category, cmds in sorted(categories.items()):
                        console.print(
                            f"[bold {palette.accent}]{category.upper()}[/bold {palette.accent}]"
                        )
                        help_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
                        help_table.add_column("Command", style=f"{palette.info}", min_width=15)
                        help_table.add_column("Description", style=f"{palette.text_secondary}")
                        help_table.add_column("Aliases", style=f"{palette.text_muted}")

                        for cmd in cmds:
                            aliases = ", ".join(cmd.aliases) if cmd.aliases else ""
                            help_table.add_row(cmd.name, cmd.description, aliases)

                        console.print(help_table)
                        console.print()

                    # Add todo commands help
                    console.print(f"[bold {palette.accent}]TASKS[/bold {palette.accent}]")
                    todo_help = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
                    todo_help.add_column("Command", style=f"{palette.info}", min_width=15)
                    todo_help.add_column("Description", style=f"{palette.text_secondary}")
                    todo_help.add_column("Aliases", style=f"{palette.text_muted}")
                    todo_help.add_row("/todos", "Toggle todo progress bar", "")
                    todo_help.add_row("/todo", "Show full todo panel", "")
                    todo_help.add_row("/todo add <task>", "Add a task", "")
                    todo_help.add_row("/done", "Mark current task done", "/todo done")
                    console.print(todo_help)
                    console.print()

                    # Add analytics commands help
                    console.print(f"[bold {palette.accent}]ANALYTICS[/bold {palette.accent}]")
                    analytics_help = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
                    analytics_help.add_column("Command", style=f"{palette.info}", min_width=15)
                    analytics_help.add_column("Description", style=f"{palette.text_secondary}")
                    analytics_help.add_column("Aliases", style=f"{palette.text_muted}")
                    analytics_help.add_row("/analytics", "Show analytics dashboard", "")
                    analytics_help.add_row("/health", "Show provider health status", "")
                    analytics_help.add_row("/stats", "Show session statistics", "")
                    console.print(analytics_help)
                    console.print()

                    # Add prompts commands help
                    console.print(f"[bold {palette.accent}]PROMPTS[/bold {palette.accent}]")
                    prompts_help = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
                    prompts_help.add_column("Command", style=f"{palette.info}", min_width=20)
                    prompts_help.add_column("Description", style=f"{palette.text_secondary}")
                    prompts_help.add_column("Aliases", style=f"{palette.text_muted}")
                    prompts_help.add_row("/prompts", "List all available prompts", "/prompt list")
                    prompts_help.add_row("/prompt <name>", "Load and preview a prompt", "")
                    prompts_help.add_row("/prompt <name> var=val", "Load prompt with variables", "")
                    console.print(prompts_help)
                    console.print()

                    # Add settings/debug commands help
                    console.print(f"[bold {palette.accent}]SETTINGS[/bold {palette.accent}]")
                    settings_help = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
                    settings_help.add_column("Command", style=f"{palette.info}", min_width=15)
                    settings_help.add_column("Description", style=f"{palette.text_secondary}")
                    settings_help.add_column("Aliases", style=f"{palette.text_muted}")
                    settings_help.add_row("/init", "Analyze codebase and generate hcode.md", "")
                    settings_help.add_row("/debug", "Toggle debug mode (verbose output)", "")
                    settings_help.add_row("/theme <name>", "Change color theme", "")
                    settings_help.add_row("/clear", "Clear conversation history", "")
                    settings_help.add_row("/export", "Export session to file", "")
                    console.print(settings_help)
                    console.print()

                    console.print(
                        f"[{palette.text_muted}]Type /help <command> for detailed help on a specific command[/]"
                    )
                    continue

                elif command == "stats":
                    stats = agent.get_session_stats()

                    # Include todo progress in stats
                    todo_progress = ""
                    if chat_todos:
                        total = len(chat_todos)
                        completed = sum(
                            1 for t in chat_todos if t.get("status") == "completed"
                        )
                        todo_progress = (
                            f"\n{icons.GEAR} Tasks: [{palette.info}]{completed}/{total}[/]"
                        )

                    stats_content = (
                        f"$ Cost: [{palette.success}]${stats['total_cost']:.4f}[/]\n"
                        f"{icons.MESSAGE} Messages: [{palette.warning}]{stats['context']['total_messages']}[/]\n"
                        f"{icons.AI} Provider: [{palette.info}]{stats['provider']}[/]\n"
                        f"{icons.FILE} Session: [{palette.text_muted}]{stats['context']['session_id']}[/]"
                        f"{todo_progress}"
                    )
                    stats_panel = InfoPanel(title="Statistics", content=stats_content)
                    console.print(stats_panel.render())
                    continue

                elif command == "analytics":
                    # Show analytics dashboard
                    analytics = agent.get_analytics_summary()
                    health = agent.get_health_report()

                    # Build analytics display
                    console.print(
                        f"\n[bold {palette.primary}]{icons.GEAR} Analytics Dashboard[/bold {palette.primary}]\n"
                    )

                    # Health status
                    status_color = (
                        palette.success if health["status"] == "healthy" else palette.warning
                    )
                    console.print(
                        f"Status: [{status_color}]{health['status'].upper()}[/{status_color}]"
                    )
                    console.print(
                        f"Success Rate: [{palette.info}]{health['overall_success_rate']:.1%}[/]"
                    )
                    console.print(
                        f"Reasoning Quality: [{palette.info}]{health.get('reasoning_quality', 0):.2f}[/]"
                    )
                    console.print(
                        f"Uptime: [{palette.text_muted}]{analytics.get('uptime_formatted', 'N/A')}[/]"
                    )
                    console.print(
                        f"Total Cost: [{palette.success}]${analytics.get('total_cost', 0):.4f}[/]"
                    )
                    console.print()

                    # Issues if any
                    if health.get("issues"):
                        console.print(f"[bold {palette.warning}]Issues:[/bold {palette.warning}]")
                        for issue in health["issues"][:5]:
                            severity_color = (
                                palette.error if issue["severity"] == "high" else palette.warning
                            )
                            console.print(f"  [{severity_color}]•[/] {issue['message']}")
                        console.print()

                    # Top tools
                    tool_stats = analytics.get("tool_stats", {})
                    if tool_stats:
                        console.print(f"[bold {palette.accent}]Top Tools:[/bold {palette.accent}]")
                        for tool_name, stats in list(tool_stats.items())[:5]:
                            calls = stats.get("total_calls", 0)
                            rate = stats.get("success_rate", 0)
                            console.print(f"  {tool_name}: {calls} calls ({rate:.0%} success)")
                    continue

                elif command == "health":
                    # Show provider health
                    provider_health = agent.get_provider_health()
                    console.print(
                        f"\n[bold {palette.primary}]{icons.AI} Provider Health[/bold {palette.primary}]\n"
                    )

                    if provider_health.get("resilient_provider") is False:
                        console.print(
                            f"[{palette.text_muted}]Resilient provider not active (single provider mode)[/]"
                        )
                    else:
                        console.print(
                            f"Current Provider: [{palette.info}]{provider_health.get('current_provider', 'N/A')}[/]"
                        )
                        for name, info in provider_health.get("providers", {}).items():
                            health_color = (
                                palette.success
                                if info["health"] == "healthy"
                                else (
                                    palette.warning
                                    if info["health"] == "degraded"
                                    else palette.error
                                )
                            )
                            console.print(f"\n  [{palette.accent}]{name}[/]:")
                            console.print(f"    Health: [{health_color}]{info['health']}[/]")
                            console.print(f"    Success Rate: {info['success_rate']:.1%}")
                            console.print(f"    Avg Latency: {info['avg_latency']:.2f}s")
                            console.print(f"    Total Requests: {info['total_requests']}")
                    continue

                elif command.startswith("theme"):
                    parts = command.split(maxsplit=1)
                    if len(parts) > 1:
                        theme_name = parts[1].lower()
                        theme_map = {
                            "cyberpunk": ThemeMode.CYBERPUNK,
                            "neon": ThemeMode.NEON_NIGHTS,
                            "matrix": ThemeMode.MATRIX,
                            "synthwave": ThemeMode.SYNTHWAVE,
                            "frost": ThemeMode.FROST,
                            "minimal": ThemeMode.MINIMAL,
                            "hacker": ThemeMode.HACKER,
                        }
                        if theme_name in theme_map:
                            set_theme(theme_map[theme_name])
                            palette = get_palette()  # Refresh palette
                            console.print(
                                f"[{palette.success}]{icons.SUCCESS} Theme changed to {theme_name}[/]"
                            )
                        else:
                            console.print(
                                f"[{palette.warning}]Available themes: {', '.join(theme_map.keys())}[/]"
                            )
                    else:
                        console.print(
                            f"[{palette.info}]Current theme. Available: cyberpunk, neon, matrix, synthwave, frost, minimal, hacker[/]"
                        )
                    continue

                elif command == "debug":
                    # Toggle debug mode
                    debug = not debug
                    config["debug"] = debug
                    config["ui"]["debug_mode"] = debug
                    status = "enabled" if debug else "disabled"
                    color = palette.warning if debug else palette.success
                    console.print(f"[{color}]{icons.SUCCESS} Debug mode {status}[/]")
                    if debug:
                        console.print(
                            f"[{palette.text_muted}]Showing verbose output, thinking panels, and detailed messages[/]"
                        )
                    else:
                        console.print(f"[{palette.text_muted}]Claude Code-style minimal output[/]")
                    continue

                elif command == "clear":
                    agent.context_manager.clear_context(keep_system=True)
                    chat_todos = []  # Clear todos too
                    console.print(f"[{palette.success}]{icons.SUCCESS} Conversation cleared[/]")
                    message_count = 0
                    continue

                elif command == "export":
                    filename = f"session_{agent.context_manager.session_id}.json"
                    agent.export_session(filename)
                    console.print(f"[green]{EMOJI['success']} Exported to {filename}[/green]")
                    continue

                elif command == "init":
                    # Codebase initialization - agent-driven analysis
                    console.print(
                        Panel(
                            f"[bold {palette.primary}]🚀 Initializing codebase analysis...[/bold {palette.primary}]\n\n"
                            f"The agent will now comprehensively analyze your codebase using its tools:\n"
                            f"  • Glob to discover structure\n"
                            f"  • Read to understand code\n"
                            f"  • Grep to find patterns\n\n"
                            f"This will generate detailed documentation in [cyan].hcode/hcode.md[/cyan]\n"
                            f"that will guide all future implementations.",
                            title=f"[bold {palette.primary}]/init Command[/bold {palette.primary}]",
                            border_style=palette.primary,
                        )
                    )
                    
                    try:
                        from pathlib import Path as PathlibPath
                        from hcode.core.phases.init_handler import InitHandler
                        from hcode.core.protocols import AgentContext
                        
                        # Create InitHandler with agent's components
                        # Note: agent.current_provider may be None if not yet selected
                        # We need to select a provider first
                        if not agent.current_provider:
                            from hcode.providers import TaskComplexity, TaskType
                            agent.current_provider = agent.provider_selector.select_provider(
                                complexity=TaskComplexity.MODERATE,
                                task_type=TaskType.CODE_GENERATION
                            )
                        
                        init_handler = InitHandler(
                            provider=agent.current_provider,
                            tool_executor=agent._tool_executor,
                            context_manager=agent.context_manager,
                            console=console,
                        )
                        
                        # Create AgentContext
                        context = AgentContext(
                            task="/init codebase analysis",
                            session_id=agent.context_manager.session_id,
                            working_dir=str(PathlibPath.cwd()),
                            iteration=1,
                        )
                        
                        # Execute analysis
                        result = asyncio.run(init_handler.analyze(context))
                        
                        # Display results
                        if result.success:
                            console.print(
                                Panel(
                                    f"[bold {palette.success}]✅ Codebase initialization complete![/bold {palette.success}]\n\n"
                                    f"📁 Documentation created: [cyan]{result.hcode_path}[/cyan]\n\n"
                                    f"[{palette.text_muted}]The agent has analyzed your codebase and generated\n"
                                    f"comprehensive documentation that will guide all future\n"
                                    f"implementations. Use this as a reference for understanding\n"
                                    f"the project structure, patterns, and conventions.[/]\n\n"
                                    f"🎯 Ready for implementation tasks!",
                                    title=f"[bold {palette.success}]Analysis Complete[/bold {palette.success}]",
                                    border_style=palette.success,
                                )
                            )
                        else:
                            console.print(
                                Panel(
                                    f"[bold {palette.warning}]⚠️ Analysis completed with issues[/bold {palette.warning}]\n\n"
                                    f"Error: {result.error}\n\n"
                                    f"The agent completed its analysis but did not generate hcode.md.\n"
                                    f"Try running /init again or check the error above.",
                                    title=f"[bold {palette.warning}]Incomplete Analysis[/bold {palette.warning}]",
                                    border_style=palette.warning,
                                )
                            )
                        
                    except Exception as e:
                        from rich.markup import escape
                        error_panel = ErrorPanel(
                            message=f"An error occurred during codebase analysis:",
                            details=(
                                f"{escape(str(e))}\n\n"
                                f"Make sure you're in a valid project directory."
                            ),
                            error_type="Initialization Failed"
                        )
                        console.print(error_panel.render())
                        if debug:
                            console.print_exception()
                    
                    continue

            # Execute task with modern assistant indicator
            console.print(
                f"\n[bold {palette.success}]{icons.AI} Assistant [{message_count}]:[/bold {palette.success}]\n"
            )

            # Start LIVE todo bar - it will update automatically via callbacks
            # when the agent calls TodoWrite during execution
            if chat_todos:
                live_todo_bar.update_todos(chat_todos)
            live_todo_bar.start()

            # Import Hcode display for Claude Code style output
            from hcode.ui.hcode_display import (
                get_hcode_display,
            )
            
            # Get Hcode display instance
            hcode_display = get_hcode_display(console)
            
            # Extract task name from user input
            task_name = user_input.split('\n')[0].strip()[:50]
            if len(user_input) > 50:
                task_name = task_name[:47] + "..."
            
            # Wrapper for agent execution
            # The agent handles task boundary display internally
            
            # Pause todo bar during streaming to prevent ANSI interference
            live_todo_bar.pause()
            
            try:
                result = asyncio.run(agent.execute_task(task=user_input, stream=True))
            finally:
                # End thinking timer if it was running (safety)
                hcode_display.end_thinking()
                
                # Resume todo bar after streaming
                live_todo_bar.resume()

            # Stop live todo bar after task
            if live_todo_bar.is_active:
                live_todo_bar.stop()

            # Sync todos from live bar (which received callback updates)
            callback_todos = live_todo_bar.get_todos()
            if callback_todos:
                chat_todos = callback_todos

            # SYNC TODOS FROM AGENT'S TODOWRITE TOOL
            # The agent's tool manager has the authoritative todo list
            synced = False
            try:
                # Access the todo_write_tool directly (it's stored as an attribute)
                todowrite_tool = None

                # First try direct attribute access (preferred)
                if hasattr(agent.tool_manager, "todo_write_tool"):
                    todowrite_tool = agent.tool_manager.todo_write_tool

                # Fallback: try registry lookup
                if not todowrite_tool:
                    for tool_name in ["TodoWrite", "todowrite", "TodoWriteTool", "todo_write"]:
                        todowrite_tool = agent.tool_manager.get_tool(tool_name)
                        if todowrite_tool:
                            break

                if todowrite_tool:
                    # The todos property returns to_dict_list() - use it directly
                    if hasattr(todowrite_tool, "todos"):
                        agent_todos = todowrite_tool.todos  # Now a property
                        if agent_todos:
                            chat_todos = [todo_to_dict(t) for t in agent_todos]
                            synced = True
                            if debug:
                                console.print(
                                    f"[dim]Synced {len(agent_todos)} todos from agent[/dim]"
                                )
                    # Fallback: try todo_manager directly
                    elif hasattr(todowrite_tool, "todo_manager") and todowrite_tool.todo_manager:
                        agent_todos = todowrite_tool.todo_manager.to_dict_list()
                        if agent_todos:
                            chat_todos = [todo_to_dict(t) for t in agent_todos]
                            synced = True
                            if debug:
                                console.print(
                                    f"[dim]Synced {len(agent_todos)} todos via manager[/dim]"
                                )
            except Exception as e:
                if debug:
                    console.print(f"[dim red]Todo sync error: {e}[/dim red]")

            # If no todos from agent, try extracting from response
            if not chat_todos and not synced:
                extracted_todos = extract_todos_from_response(result)
                if extracted_todos:
                    chat_todos = [todo_to_dict(t) for t in extracted_todos]

            # Ensure at least one is in_progress if todos exist and none completed
            if chat_todos:
                has_in_progress = any(
                    t.get("status") == "in_progress" for t in chat_todos
                )
                all_completed = all(t.get("status") == "completed" for t in chat_todos)
                if not has_in_progress and not all_completed:
                    for todo in chat_todos:
                        if todo.get("status") == "pending":
                            todo["status"] = "in_progress"
                            break

            # Update LiveTodoBar with latest todos (it will display persistently)
            if chat_todos:
                live_todo_bar.update_todos(chat_todos)

            message_count += 1

        except KeyboardInterrupt:
            # Stop live todo bar on interrupt
            if live_todo_bar.is_active:
                live_todo_bar.stop()

            console.print(
                f"\n[{palette.warning}]{icons.WARNING} Interrupted. Type /exit to quit or continue chatting.[/{palette.warning}]"
            )

            # Sync todos from live bar first (it may have received callback updates)
            callback_todos = live_todo_bar.get_todos()
            if callback_todos:
                chat_todos = callback_todos

            # Also sync from agent's TodoWrite tool
            try:
                todowrite_tool = None
                # Direct access preferred
                if hasattr(agent.tool_manager, "todo_write_tool"):
                    todowrite_tool = agent.tool_manager.todo_write_tool
                if not todowrite_tool:
                    for tool_name in ["TodoWrite", "todowrite", "TodoWriteTool", "todo_write"]:
                        todowrite_tool = agent.tool_manager.get_tool(tool_name)
                        if todowrite_tool:
                            break
                if todowrite_tool:
                    # Use todos property (returns to_dict_list())
                    if hasattr(todowrite_tool, "todos"):
                        agent_todos = todowrite_tool.todos
                        if agent_todos:
                            chat_todos = [todo_to_dict(t) for t in agent_todos]
                    elif hasattr(todowrite_tool, "todo_manager") and todowrite_tool.todo_manager:
                        agent_todos = todowrite_tool.todo_manager.to_dict_list()
                        if agent_todos:
                            chat_todos = [todo_to_dict(t) for t in agent_todos]
                # Update LiveTodoBar after interrupt (it shows persistently)
                if chat_todos:
                    live_todo_bar.update_todos(chat_todos)
            except Exception:
                pass
            continue
        except EOFError:
            break
        except Exception as e:
            error_panel = ErrorPanel(message=str(e), error_type="Error")
            console.print(error_panel.render())


@cli.command(name="analyze", short_help="Analyze code")
@click.argument("path", required=False)
@click.option(
    "-p", "--provider", type=click.Choice(["auto", "anthropic", "openai"]), default="auto"
)
@click.option("--deep", is_flag=True, help="Deep analysis")
def analyze_code(path, provider, deep):
    """
    Analyze code for issues and improvements

    \b
    Examples:
      hcode analyze src/main.py
      hcode analyze .
      hcode analyze --deep
    """
    if not path:
        path = "."

    console.print(
        Panel(
            f"[bold blue]Analyzing:[/bold blue] {path}\n"
            f"[dim]Mode: {'Deep' if deep else 'Standard'}[/dim]",
            border_style="blue",
        )
    )

    config = load_config()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("providers", {}).get(
        "anthropic", {}
    ).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("providers", {}).get("openai", {}).get(
        "api_key"
    )

    preferences = ProviderPreferences(primary_provider=provider)
    agent = HcodeAgent(anthropic_key=anthropic_key, openai_key=openai_key, preferences=preferences)

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
    ) as progress:
        task = progress.add_task("Analyzing code...", total=None)

        result = asyncio.run(
            agent.execute_task(
                f"Analyze code in {path} for bugs, security issues, and improvements. "
                f"{'Provide deep analysis with detailed recommendations.' if deep else ''}",
                stream=False,
            )
        )

        progress.remove_task(task)

    console.print(
        Panel(
            Markdown(result),
            title="[bold green]✓ Analysis Complete[/bold green]",
            border_style="green",
        )
    )


@cli.command(name="explore", short_help="Explore codebase")
@click.argument("query")
@click.option(
    "-t",
    "--thoroughness",
    type=click.Choice(["quick", "medium", "thorough", "q", "m", "t"]),
    default="medium",
    help="Search thoroughness",
)
def explore_codebase(query, thoroughness):
    """
    Explore and search codebase

    \b
    Examples:
      hcode explore "API endpoints"
      hcode explore "authentication logic" --thoroughness=thorough
      hcode explore "database queries" -t q
    """
    thoroughness_map = {"q": "quick", "m": "medium", "t": "thorough"}
    thoroughness = thoroughness_map.get(thoroughness, thoroughness)

    config = load_config()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("providers", {}).get(
        "anthropic", {}
    ).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("providers", {}).get("openai", {}).get(
        "api_key"
    )

    agent = HcodeAgent(anthropic_key=anthropic_key, openai_key=openai_key)

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
    ) as progress:
        task = progress.add_task(f"Exploring ({thoroughness})...", total=None)

        result = asyncio.run(agent.explore_codebase(query, thoroughness=thoroughness))

        progress.remove_task(task)

    console.print(
        Panel(
            Markdown(result),
            title="[bold cyan]🔍 Exploration Results[/bold cyan]",
            border_style="cyan",
        )
    )





@cli.command(name="init", short_help="Initialize project config")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing config")
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
        console.print(
            Panel(
                f"[yellow]{EMOJI['warning']} Configuration already exists[/yellow]\n\n"
                f"Location: {config_file}\n\n"
                "Use [bold]--force[/bold] to overwrite",
                title="[yellow]Already Initialized[/yellow]",
                border_style="yellow",
            )
        )
        return

    try:
        # Create .hcode directory
        hcode_dir.mkdir(exist_ok=True)

        # Create config file
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(DEFAULT_CONFIG_YAML)

        # Create logs directory
        (hcode_dir / "logs").mkdir(exist_ok=True)

        # Create .gitignore for .hcode
        gitignore_file = hcode_dir / ".gitignore"
        with open(gitignore_file, "w", encoding="utf-8") as f:
            f.write("# HCode local files\nlogs/\nmemory.db\n*.log\n")

        console.print(
            Panel(
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
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]{EMOJI['cross']} Error: {e}[/red]")
        sys.exit(1)


@cli.group(name="config", short_help="Manage configuration")
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


@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
@click.option("--global", "-g", "is_global", is_flag=True, help="Set in global config")
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
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config_dir.mkdir(parents=True, exist_ok=True)
        config = {}

    # Parse key path (e.g., "llm.provider" -> ["llm", "provider"])
    keys = key.split(".")
    current = config

    # Navigate/create nested structure
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    # Convert value to appropriate type
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
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
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print(f"[green]{EMOJI['success']} Set {key} = {value}[/green]")
    console.print(f"[dim]Config file: {config_file}[/dim]")


@config_group.command(name="get")
@click.argument("key", required=False)
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
        with open(global_config, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Override with local config
    if local_config.exists():
        with open(local_config, "r", encoding="utf-8") as f:
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
        console.print(
            Panel(
                Syntax(yaml.dump(config, default_flow_style=False), "yaml", theme="monokai"),
                title="[bold]Configuration[/bold]",
                border_style="blue",
            )
        )
        return

    # Navigate to key
    keys = key.split(".")
    current = config

    try:
        for k in keys:
            current = current[k]

        if isinstance(current, dict):
            console.print(
                Panel(
                    Syntax(yaml.dump(current, default_flow_style=False), "yaml", theme="monokai"),
                    title=f"[bold]{key}[/bold]",
                    border_style="blue",
                )
            )
        else:
            console.print(f"[cyan]{key}[/cyan] = [green]{current}[/green]")

    except (KeyError, TypeError):
        console.print(f"[yellow]{EMOJI['warning']} Key not found: {key}[/yellow]")


@config_group.command(name="list")
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

    def flatten_dict(d, prefix=""):
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
        with open(global_config, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            for key, value in flatten_dict(config):
                table.add_row(key, str(value), "global")

    # Load and display local config
    if local_config.exists():
        with open(local_config, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            for key, value in flatten_dict(config):
                table.add_row(key, str(value), "local")

    console.print(table)


@config_group.command(name="path")
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
        "Global", str(global_config), EMOJI["check"] if global_config.exists() else EMOJI["cross"]
    )
    table.add_row(
        "Local", str(local_config), EMOJI["check"] if local_config.exists() else EMOJI["cross"]
    )

    console.print(table)




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
