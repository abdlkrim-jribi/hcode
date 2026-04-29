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

from hcode.ui.theme import get_palette
from hcode.ui.icons import Icons
from hcode.ui.interactive_selector import select_option_async
from rich.table import Table


class ConfirmationResult(Enum):
    ALLOW = auto()
    SESSION_ALLOW = auto()
    REJECT = auto()


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

    async def _prompt_loop(self, prompt_text: str = "Select an option") -> Tuple[ConfirmationResult, Optional[str]]:
        """
        Display the interactive option selection and get user choice.
        """
        options = [
            ("allow", "Accept", "Authorize this action once"),
            ("session", "Session-Accept", "Authorize for this session"),
            ("counter", "Counter", "Reject and provide feedback")
        ]
        
        choice = await select_option_async(options, title=prompt_text)
        
        if choice == "allow":
            return ConfirmationResult.ALLOW, None
        elif choice == "session":
            return ConfirmationResult.SESSION_ALLOW, None
        elif choice == "counter":
            feedback = self.console.input("[bold red]Enter feedback:[/bold red] ")
            return ConfirmationResult.REJECT, feedback
        else:
            # If aborted (Esc/Ctrl+C)
            return ConfirmationResult.REJECT, "Operation aborted by user"

        # Import Icons locally to avoid circular import at top level
        try:
            from hcode.ui.icons import Icons
        except ImportError:
            pass

    async def show_file_edit_confirmation(
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
        
        # Create Thinking-Style Header
        header_title = Text()
        header_title.append("EDIT: ", style="bold")
        header_title.append(file_name, style=f"bold {palette.info}")
        header_title.append(f" ({stats.plain})", style="dim")

        # Create Grid Layout (Borderless with Gutter like Thinking block)
        grid = Table.grid(padding=(0, 1))
        grid.add_column(style=f"{palette.info}", width=2, justify="center") # Gutter column
        grid.add_column() # Content column

        # Header Row
        grid.add_row("▍", header_title)
        
        # Spacer
        grid.add_row("▍", "")

        # Content Row
        if description:
            grid.add_row("▍", Text(description, style="italic dim"))
            grid.add_row("▍", "")

        grid.add_row("▍", diff_text)

        self.console.print()
        self.console.print(grid)

        return await self._prompt_loop("Apply this change?")

    async def show_command_confirmation(
            self,
            command: str,
            description: str = "",
            working_dir: str = ""
    ) -> Tuple[ConfirmationResult, Optional[str]]:
        """Show command execution confirmation with session support.
        
        Args:
            command: Command to execute
            description: Optional description
            working_dir: Working directory
            
        Returns:
            Tuple of (ConfirmationResult, optional feedback)
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

        # Create Thinking-Style Header
        header_title = Text()
        header_title.append("BASH EXECUTION", style=f"bold {palette.warning}")

        # Grid with gutter
        grid = Table.grid(padding=(0, 1))
        grid.add_column(style=f"{palette.warning}", width=2, justify="center")
        grid.add_column()

        grid.add_row("▍", header_title)
        grid.add_row("▍", "")
        grid.add_row("▍", content)

        self.console.print()
        self.console.print(grid)

        # Use select_option_async with Session support
        options = [
            ("allow", "Execute", "Run this command once"),
            ("session", "Session-Accept", "Authorize all commands for this session"),
            ("counter", "Counter", "Reject and provide feedback")
        ]
        
        choice = await select_option_async(options, title="Execute this command?")
        
        if choice == "allow":
            return ConfirmationResult.ALLOW, None
        elif choice == "session":
            return ConfirmationResult.SESSION_ALLOW, None
        elif choice == "counter":
            feedback = self.console.input("[bold red]Enter feedback:[/bold red] ")
            return ConfirmationResult.REJECT, feedback
        else:
            return ConfirmationResult.REJECT, "Operation aborted"

    async def show_file_create_confirmation(
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

        # Create Thinking-Style Header
        header_title = Text()
        header_title.append("WRITE: ", style="bold")
        header_title.append(file_name, style=f"bold {palette.success}")

        # Grid with gutter
        grid = Table.grid(padding=(0, 1))
        grid.add_column(style=f"{palette.success}", width=2, justify="center")
        grid.add_column()

        grid.add_row("▍", header_title)
        grid.add_row("▍", "")
        grid.add_row("▍", panel_content)

        # Show content preview within the grid? 
        # Actually Syntax might be better outside or also indented.
        # Let's indent it too.
        try:
            syntax = Syntax(preview, lang, theme="monokai", line_numbers=True)
            grid.add_row("▍", syntax)
        except Exception:
            grid.add_row("▍", preview)

        self.console.print()
        self.console.print(grid)

        return await self._prompt_loop("Write this file?")


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
