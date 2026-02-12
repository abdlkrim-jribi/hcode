"""
Confirmation display for Claude Code-style permission prompts.

Shows diff previews before file edits and command confirmations.
"""

import difflib
from pathlib import Path
from typing import Optional, List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.prompt import Confirm
from rich.table import Table


class ConfirmationDisplay:
    """
    Displays confirmation prompts with diff previews for file operations.
    
    Implements Claude Code-style permission system where users must
    approve changes before they are applied.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the confirmation display.
        
        Args:
            console: Rich console for output. Creates new one if not provided.
        """
        self.console = console or Console()
    
    def generate_diff(
        self,
        old_content: str,
        new_content: str,
        file_path: str = "file",
        context_lines: int = 3
    ) -> List[str]:
        """Generate a unified diff between old and new content.
        
        Args:
            old_content: Original file content
            new_content: New file content after edit
            file_path: Path to the file (for diff header)
            context_lines: Number of context lines around changes
            
        Returns:
            List of diff lines
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=context_lines
        )
        
        return list(diff)
    
    def format_diff_for_display(self, diff_lines: List[str]) -> Text:
        """Format diff lines with colors for Rich display.
        
        Args:
            diff_lines: Lines from unified diff
            
        Returns:
            Rich Text object with colored diff
        """
        text = Text()
        
        for line in diff_lines:
            if line.startswith('+++') or line.startswith('---'):
                text.append(line, style="bold white")
            elif line.startswith('@@'):
                text.append(line, style="cyan")
            elif line.startswith('+'):
                text.append(line, style="green")
            elif line.startswith('-'):
                text.append(line, style="red")
            else:
                text.append(line, style="dim")
        
        return text
    
    def count_changes(self, diff_lines: List[str]) -> Tuple[int, int]:
        """Count additions and deletions in diff.
        
        Args:
            diff_lines: Lines from unified diff
            
        Returns:
            Tuple of (additions, deletions)
        """
        additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        return additions, deletions
    
    def show_file_edit_confirmation(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        description: str = ""
    ) -> bool:
        """Show file edit confirmation with diff preview.
        
        Args:
            file_path: Path to file being edited
            old_content: Original content
            new_content: New content after edit
            description: Optional description of the change
            
        Returns:
            True if user approved, False otherwise
        """
        # Generate diff
        diff_lines = self.generate_diff(old_content, new_content, file_path)
        
        if not diff_lines:
            self.console.print("[yellow]No changes detected.[/yellow]")
            return True
        
        # Count changes
        additions, deletions = self.count_changes(diff_lines)
        
        # Create header
        file_name = Path(file_path).name
        header = f"[bold cyan]📝 Edit: {file_name}[/bold cyan]"
        
        # Create stats line
        stats = Text()
        stats.append(f"+{additions}", style="green bold")
        stats.append(" / ", style="dim")
        stats.append(f"-{deletions}", style="red bold")
        stats.append(" lines", style="dim")
        
        # Format diff
        diff_text = self.format_diff_for_display(diff_lines)
        
        # Create panel
        panel_content = Text()
        if description:
            panel_content.append(f"{description}\n\n", style="italic")
        panel_content.append(diff_text)
        
        self.console.print()
        self.console.print(Panel(
            panel_content,
            title=header,
            subtitle=stats,
            border_style="blue",
            padding=(1, 2)
        ))
        
        # Ask for confirmation
        return Confirm.ask(
            "[bold yellow]Apply this change?[/bold yellow]",
            console=self.console,
            default=True
        )
    
    def show_command_confirmation(
        self,
        command: str,
        description: str = "",
        working_dir: str = ""
    ) -> bool:
        """Show command execution confirmation.
        
        Args:
            command: Command to execute
            description: Optional description of what command does
            working_dir: Working directory for command
            
        Returns:
            True if user approved, False otherwise
        """
        # Create content
        content = Text()
        
        if description:
            content.append(f"{description}\n\n", style="italic dim")
        
        content.append("$ ", style="green bold")
        content.append(command, style="white bold")
        
        if working_dir:
            try:
                 from hcode.ui.icons import Icons
                 folder_icon = Icons.FOLDER
            except ImportError:
                 folder_icon = "📁"
            content.append(f"\n\n{folder_icon} ", style="dim grey")
            content.append(f"Directory: ", style="dim white")
            content.append(working_dir, style="dim grey italic")
        
        self.console.print()
        # Import Icons locally to avoid circular import at top level
        try:
            from hcode.ui.icons import Icons
            icon = Icons.LIGHTNING
        except ImportError:
            icon = "⚡"

        # Truncate command for title
        display_cmd = command if len(command) <= 50 else command[:47] + "..."
        
        from rich import box
        
        self.console.print(Panel(
            content,
            title=f"[bold white]{icon} Bash[/bold white] [dim white]{display_cmd}[/]",
            title_align="left",
            border_style="dim white",
            box=box.ROUNDED,
            padding=(1, 2)
        ))
        
        # Ask for confirmation
        return Confirm.ask(
            "[bold yellow]Execute this command?[/bold yellow]",
            console=self.console,
            default=True
        )
    
    def show_file_create_confirmation(
        self,
        file_path: str,
        content: str,
        description: str = ""
    ) -> bool:
        """Show file creation confirmation with content preview.
        
        Args:
            file_path: Path where file will be created
            content: Content to write
            description: Optional description
            
        Returns:
            True if user approved, False otherwise
        """
        file_name = Path(file_path).name
        
        # Create preview (first 20 lines max)
        lines = content.split('\n')
        preview_lines = lines[:20]
        if len(lines) > 20:
            preview_lines.append(f"... ({len(lines) - 20} more lines)")
        preview = '\n'.join(preview_lines)
        
        # Detect language for syntax highlighting
        ext = Path(file_path).suffix.lstrip('.')
        lang_map = {
            'py': 'python', 'js': 'javascript', 'ts': 'typescript',
            'yaml': 'yaml', 'yml': 'yaml', 'json': 'json', 'md': 'markdown'
        }
        lang = lang_map.get(ext, ext)
        
        # Create panel content
        panel_content = Text()
        if description:
            panel_content.append(f"{description}\n\n", style="italic dim")
        panel_content.append(f"📄 {file_path}\n", style="bold")
        panel_content.append(f"📊 {len(lines)} lines\n\n", style="dim")
        
        self.console.print()
        self.console.print(Panel(
            panel_content,
            title=f"[bold green]✨ Create: {file_name}[/bold green]",
            border_style="green",
            padding=(1, 2)
        ))
        
        # Show content preview
        try:
            syntax = Syntax(preview, lang, theme="monokai", line_numbers=True)
            self.console.print(syntax)
        except Exception:
            self.console.print(preview)
        
        # Ask for confirmation
        return Confirm.ask(
            "[bold yellow]Create this file?[/bold yellow]",
            console=self.console,
            default=True
        )
    
    def show_file_delete_confirmation(self, file_path: str) -> bool:
        """Show file deletion confirmation.
        
        Args:
            file_path: Path to file being deleted
            
        Returns:
            True if user approved, False otherwise
        """
        file_name = Path(file_path).name
        
        self.console.print()
        self.console.print(Panel(
            f"[bold red]⚠️  This will permanently delete:[/bold red]\n\n📄 {file_path}",
            title=f"[bold red]🗑️  Delete: {file_name}[/bold red]",
            border_style="red",
            padding=(1, 2)
        ))
        
        return Confirm.ask(
            "[bold red]Delete this file?[/bold red]",
            console=self.console,
            default=False  # Default to NO for deletions
        )


# Global instance for easy access
_confirmation_display: Optional[ConfirmationDisplay] = None


def get_confirmation_display(console: Optional[Console] = None) -> ConfirmationDisplay:
    """Get or create the global confirmation display instance.
    
    Args:
        console: Optional console to use
        
    Returns:
        ConfirmationDisplay instance
    """
    global _confirmation_display
    if _confirmation_display is None:
        _confirmation_display = ConfirmationDisplay(console)
    return _confirmation_display
