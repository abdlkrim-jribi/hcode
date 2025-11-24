"""
Hcode CLI - Command-line interface for Hcode.
"""

import click
import asyncio
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from .core import HcodeAgent
from .providers import ProviderPreferences, TaskComplexity, TaskType
from .utils.config import load_config


console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="Hcode")
def cli():
    """
    Hcode - Universal AI Coding Assistant

    Supports both Anthropic Claude and OpenAI GPT models.
    """
    pass


@cli.command()
@click.argument("task", required=False)
@click.option("--provider", type=click.Choice(["auto", "anthropic", "openai"]), default="auto",
              help="AI provider to use")
@click.option("--model", help="Specific model to use")
@click.option("--complexity", type=click.Choice(["simple", "moderate", "complex"]), default="moderate",
              help="Task complexity")
@click.option("--optimize-cost", is_flag=True, help="Optimize for cost")
@click.option("--session", help="Session ID to resume")
@click.option("--stream/--no-stream", default=True, help="Stream responses")
def run(task, provider, model, complexity, optimize_cost, session, stream):
    """
    Execute a coding task.

    Example: hcode run "Create a REST API for user management"
    """
    if not task:
        console.print("[yellow]Enter your task (Ctrl+D when done):[/yellow]")
        task = click.get_text_stream('stdin').read()

    # Load configuration
    config = load_config()

    # Get API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("openai", {}).get("api_key")

    if not anthropic_key and not openai_key:
        console.print("[red]Error: No API keys found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.[/red]")
        return

    # Set up preferences
    preferences = ProviderPreferences(
        primary_provider=provider,
        cost_optimization="aggressive" if optimize_cost else "balanced",
        prefer_streaming=stream
    )

    # Create agent
    agent = HcodeAgent(
        anthropic_key=anthropic_key,
        openai_key=openai_key,
        preferences=preferences,
        session_id=session
    )

    # Map complexity
    complexity_map = {
        "simple": TaskComplexity.SIMPLE,
        "moderate": TaskComplexity.MODERATE,
        "complex": TaskComplexity.COMPLEX
    }

    # Show task panel
    console.print(Panel(task, title="[bold blue]Task[/bold blue]", border_style="blue"))

    # Execute task
    try:
        response = asyncio.run(agent.execute_task(
            task_description=task,
            complexity=complexity_map[complexity],
            task_type=TaskType.CODE_GENERATION,
            stream=stream
        ))

        if not stream:
            console.print(Panel(Markdown(response), title="[bold green]Response[/bold green]"))

        # Show stats
        stats = agent.get_session_stats()
        console.print(f"\n[dim]Session: {stats['context']['session_id']}[/dim]")
        console.print(f"[dim]Cost: ${stats['total_cost']:.4f}[/dim]")
        console.print(f"[dim]Messages: {stats['context']['total_messages']}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise


@cli.command()
@click.option("--provider", type=click.Choice(["auto", "anthropic", "openai"]), default="auto")
@click.option("--session", help="Session ID to resume")
def chat(provider, session):
    """
    Start an interactive chat session.
    """
    config = load_config()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("openai", {}).get("api_key")

    if not anthropic_key and not openai_key:
        console.print("[red]Error: No API keys found.[/red]")
        return

    preferences = ProviderPreferences(primary_provider=provider)

    agent = HcodeAgent(
        anthropic_key=anthropic_key,
        openai_key=openai_key,
        preferences=preferences,
        session_id=session
    )

    console.print(Panel(
        "[bold green]Hcode Interactive Chat[/bold green]\n"
        "Type your requests and press Enter. Type 'exit' to quit.",
        border_style="green"
    ))

    while True:
        try:
            user_input = console.input("\n[bold blue]You:[/bold blue] ")

            if user_input.lower() in ['exit', 'quit', 'q']:
                console.print("[yellow]Goodbye![/yellow]")
                break

            if not user_input.strip():
                continue

            response = asyncio.run(agent.execute_task(
                task_description=user_input,
                stream=True
            ))

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.argument("file_path", required=False)
@click.option("--provider", type=click.Choice(["auto", "anthropic", "openai"]), default="auto")
def analyze(file_path, provider):
    """
    Analyze code for issues and improvements.

    Example: hcode analyze src/main.py
    """
    config = load_config()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("openai", {}).get("api_key")

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

        result = asyncio.run(agent.analyze_code(file_path))

        progress.remove_task(task)

    console.print(Panel(Markdown(result), title="[bold green]Code Analysis[/bold green]"))


@cli.command()
@click.argument("error_description")
@click.option("--provider", type=click.Choice(["auto", "anthropic", "openai"]), default="auto")
def debug(error_description, provider):
    """
    Debug an issue autonomously.

    Example: hcode debug "TypeError in user authentication"
    """
    config = load_config()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("openai", {}).get("api_key")

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
        task = progress.add_task("Debugging...", total=None)

        result = asyncio.run(agent.debug_issue(error_description))

        progress.remove_task(task)

    console.print(Panel(Markdown(result), title="[bold green]Debug Analysis[/bold green]"))


@cli.command()
@click.option("--status", type=click.Choice(["all", "in_progress", "committed", "rolled_back"]),
              default="all")
def backups(status):
    """
    List and manage backups.
    """
    from .core import SafetyGuard

    safety = SafetyGuard()

    filter_status = None if status == "all" else status
    transactions = safety.list_transactions(status=filter_status)

    table = Table(title="Backups")
    table.add_column("ID", style="cyan")
    table.add_column("Description")
    table.add_column("Status", style="green")
    table.add_column("Timestamp", style="dim")
    table.add_column("Files", justify="right")

    for tx in transactions:
        table.add_row(
            tx["id"][:12],
            tx["description"][:50],
            tx["status"],
            tx["timestamp"][:19],
            str(len(tx["files_backed_up"]))
        )

    console.print(table)


@cli.command()
@click.argument("session_id", required=False)
@click.option("--output", "-o", help="Output file path")
def export(session_id, output):
    """
    Export a session to file.
    """
    from .core import ContextManager

    if not session_id:
        # List available sessions
        sessions = ContextManager.list_sessions()
        console.print("[bold]Available sessions:[/bold]")
        for s in sessions:
            console.print(f"  - {s}")
        return

    context = ContextManager(session_id=session_id)

    output_path = output or f"{session_id}.json"
    context.export_session(output_path)

    console.print(f"[green]Session exported to {output_path}[/green]")


@cli.command()
def stats():
    """
    Show statistics about usage and costs.
    """
    # This would show aggregated stats across all sessions
    console.print("[yellow]Stats functionality coming soon![/yellow]")


@cli.command()
@click.option("--provider", type=click.Choice(["anthropic", "openai", "both"]), default="both")
@click.argument("query")
def compare(provider, query):
    """
    Compare responses from different providers.

    Example: hcode compare "Implement a binary search tree"
    """
    config = load_config()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or config.get("anthropic", {}).get("api_key")
    openai_key = os.getenv("OPENAI_API_KEY") or config.get("openai", {}).get("api_key")

    responses = {}

    if provider in ["anthropic", "both"] and anthropic_key:
        console.print("\n[bold cyan]Anthropic Claude:[/bold cyan]")
        prefs = ProviderPreferences(primary_provider="anthropic")
        agent = HcodeAgent(anthropic_key=anthropic_key, openai_key=None, preferences=prefs)
        responses["anthropic"] = asyncio.run(agent.execute_task(query, stream=False))
        console.print(Panel(Markdown(responses["anthropic"]), title="Claude", border_style="cyan"))

    if provider in ["openai", "both"] and openai_key:
        console.print("\n[bold green]OpenAI GPT:[/bold green]")
        prefs = ProviderPreferences(primary_provider="openai")
        agent = HcodeAgent(anthropic_key=None, openai_key=openai_key, preferences=prefs)
        responses["openai"] = asyncio.run(agent.execute_task(query, stream=False))
        console.print(Panel(Markdown(responses["openai"]), title="GPT", border_style="green"))


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()
