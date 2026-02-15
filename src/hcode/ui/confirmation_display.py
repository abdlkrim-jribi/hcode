"""
Confirmation display for Claude Code-style permission prompts.

Shows diff previews before file edits and command confirmations.
"""

import difflib
from enum import Enum, auto
from pathlib import Path
from typing import Optional, List, Tuple

from rich.console import Console
from rich.prompt import Confirm
# from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from hcode.ui.components import CyberPanel
from hcode.ui.theme import get_palette


class ConfirmationResult(Enum):
    ALLOW = auto()
    SESSION_ALLOW = auto()
    REJECT = auto()
    COUNTER = auto() # For internal use if we want to distinguish, but user sees [C]ounter

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
    
    def _prompt_loop(self, prompt_text: str = "Select an option") -> Tuple[ConfirmationResult, Optional[str]]:
        """
        Display the 3-option prompt loop and get user choice.
        """
        while True:
            self.console.print()
            palette = get_palette()
            
            self.console.print(f"[{palette.warning} bold]{prompt_text}[/]")
            self.console.print(f"  [{palette.success} bold][A]ccept[/]          - Authorize this action once")
            self.console.print(f"  [{palette.info} bold][S]ession-Accept[/]  - Authorize for this session")
            self.console.print(f"  [{palette.error} bold][C]ounter[/]         - Reject and provide feedback")
            
            response = self.console.input("[bold] > [/bold]").strip().lower()
            
            if response == 'a':
                return ConfirmationResult.ALLOW, None
            elif response == 's':
                return ConfirmationResult.SESSION_ALLOW, None
            elif response == 'c':
                feedback = self.console.input("[bold red]Enter feedback:[/bold red] ")
                return ConfirmationResult.REJECT, feedback
            else:
                self.console.print("[red]Invalid option. Please choose A, S, or C.[/red]")


        # Import Icons locally to avoid circular import at top level
        try:
            from hcode.ui.icons import Icons
        except ImportError:
            pass

    def show_file_edit_confirmation(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        description: str = ""
    ) -> Tuple[ConfirmationResult, Optional[str]]:
        """Show file edit confirmation with diff preview.
        
        Args:
            file_path: Path to file being edited
            old_content: Original content
            new_content: New content after edit
            description: Optional description of the change
            
        Returns:
            Tuple of (ConfirmationResult, optional feedback string)
        """
        # Import icons
        try:
            from hcode.ui.icons import Icons
        except ImportError:
            pass

        # Generate diff
        diff_lines = self.generate_diff(old_content, new_content, file_path)
        
        if not diff_lines:
            self.console.print("[yellow]No changes detected.[/yellow]")
            return ConfirmationResult.ALLOW, None
        
        # Count changes
        additions, deletions = self.count_changes(diff_lines)
        
        # Create header
        file_name = Path(file_path).name
        
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
        
        palette = get_palette()
        panel = CyberPanel(
            panel_content,
            title=f"EDIT: {file_name}",
            subtitle=stats.plain, # CyberPanel expects string for subtitle, we might need to adjust or pass Text if supported 
            # Actually CyberPanel.render takes subtitle as str usually, checking implementation...
            # It takes str. Let's provide a formatted string or modify CyberPanel if needed.
            # Looking at CyberPanel code in previous step: subtitle: Optional[str] = None
            # But line 135: subtitle_text = Text(self.subtitle, style=f"italic {palette.text_muted}")
            # So passing a rich Text object might fail if it expects str.
            # Let's pass a string representation for now or simple string.
            # Stats line was: +5 / -2 lines.
            
            border_color=palette.info,
            glow_color=palette.info,
            status="processing"
        )
        # We can manually inject the stats into the panel content or title if needed, 
        # or just pass the string.
        # Let's verify CyberPanel again. It creates a Text object from the string.
        # So we should pass a string.
        
        panel_obj = panel.render()
        # Override subtitle to support colored stats if possible, or just print stats inside.
        # Actually, let's just append stats to content or print above/below?
        # Better: CyberPanel is flexible.
        
        self.console.print(panel_obj)
        
        # We want the stats to show up nicely. 
        # Let's print stats below the header in the content?
        # Or just use the subtitle string: "+5 / -2 lines"
        
        
        return self._prompt_loop("Apply this change?")

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
        # Icons
        try:
            from hcode.ui.icons import Icons
            icon_folder = Icons.FOLDER
        except ImportError:
            icon_folder = "[DIR]"

        # Create content
        content = Text()
        
        if description:
            content.append(f"{description}\n\n", style="italic dim")
        
        content.append("$ ", style="green bold")
        content.append(command, style="white bold")
        
        if working_dir:
            content.append(f"\n\n{icon_folder} ", style="dim grey")
            content.append(f"Directory: ", style="dim white")
            content.append(working_dir, style="dim grey italic")
        
        self.console.print()

        # Truncate command for title
        command if len(command) <= 50 else command[:47] + "..."
        
        
        self.console.print()
        
        palette = get_palette()
        
        # Use CyberPanel for command
        panel = CyberPanel(
            content,
            title=f"BASH EXECUTION",
            subtitle=working_dir if working_dir else None,
            border_color=palette.warning,
            glow_color=palette.warning,
            status="ready"
        )
        
        self.console.print(panel.render())
        
        # Legacy confirmation for bash
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
    ) -> Tuple[ConfirmationResult, Optional[str]]:
        """Show file creation/write confirmation with content preview.
        
        Args:
            file_path: Path where file will be created
            content: Content to write
            description: Optional description
            
        Returns:
            Tuple of (ConfirmationResult, optional feedback string)
        """
        # Icons
        try:
            from hcode.ui.icons import Icons
            icon_file = Icons.FILE
        except ImportError:
            icon_file = "[F]"

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
        panel_content.append(f"{icon_file} {file_path}\n", style="bold")
        panel_content.append(f"Lines: {len(lines)}\n\n", style="dim")
        
        self.console.print()
        self.console.print()
        
        palette = get_palette()
        
        panel = CyberPanel(
            panel_content,
            title=f"WRITE: {file_name}",
            border_color=palette.success,
            glow_color=palette.success,
            status="processing" 
        )
        
        self.console.print(panel.render())
        
        # Show content preview
        try:
            syntax = Syntax(preview, lang, theme="monokai", line_numbers=True)
            self.console.print(syntax)
        except Exception:
            self.console.print(preview)
        
        return self._prompt_loop("Write this file?")


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
