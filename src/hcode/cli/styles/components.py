"""
Reusable Rich components for Claude Code-like UI.

Provides styled panels, todos, progress bars, and other UI elements.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.tree import Tree
from rich.columns import Columns
from rich.align import Align
from rich.padding import Padding
from rich.rule import Rule
from rich.live import Live

from .colors import Colors, ThemeManager, get_rich_theme
from .borders import HCODE_BOX, Lines, get_default_box
from .icons import Icons, get_status_icon, get_file_icon, get_tool_icon


# ============================================================
# CONSOLE SETUP
# ============================================================

console = Console()


# ============================================================
# STYLED PANELS
# ============================================================

class StyledPanel:
    """Factory for creating styled panels"""

    @staticmethod
    def success(content: str, title: str = "Success") -> Panel:
        """Create success panel"""
        return Panel(
            Text(content, style=f"bold {Colors.SUCCESS}"),
            title=f"[bold {Colors.SUCCESS}]{Icons().CHECK} {title}[/]",
            border_style=Colors.SUCCESS,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def error(content: str, title: str = "Error") -> Panel:
        """Create error panel"""
        return Panel(
            Text(content, style=Colors.ERROR),
            title=f"[bold {Colors.ERROR}]{Icons().CROSS} {title}[/]",
            border_style=Colors.ERROR,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def warning(content: str, title: str = "Warning") -> Panel:
        """Create warning panel"""
        return Panel(
            Text(content, style=Colors.WARNING),
            title=f"[bold {Colors.WARNING}]{Icons().WARNING} {title}[/]",
            border_style=Colors.WARNING,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def info(content: str, title: str = "Info") -> Panel:
        """Create info panel"""
        return Panel(
            Text(content, style=Colors.INFO),
            title=f"[{Colors.INFO}]{Icons().INFO} {title}[/]",
            border_style=Colors.INFO,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def thinking(content: str, title: str = "Thinking") -> Panel:
        """Create thinking/processing panel"""
        return Panel(
            Text(content, style=Colors.THINKING),
            title=f"[bold {Colors.THINKING}]{Icons().THINKING} {title}[/]",
            border_style=Colors.THINKING,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def code(code: str, language: str = "python", title: str = "Code") -> Panel:
        """Create code panel with syntax highlighting"""
        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            word_wrap=True
        )
        return Panel(
            syntax,
            title=f"[{Colors.TEXT_SECONDARY}]{Icons().CODE} {title}[/]",
            border_style=Colors.BORDER_DEFAULT,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def agent(content: str, title: str = "Agent") -> Panel:
        """Create agent response panel"""
        return Panel(
            Text(content),
            title=f"[bold {Colors.PRIMARY}]{Icons().AGENT} {title}[/]",
            border_style=Colors.PRIMARY,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def user(content: str, title: str = "You") -> Panel:
        """Create user message panel"""
        return Panel(
            Text(content, style=Colors.TEXT_SECONDARY),
            title=f"[{Colors.TEXT_SECONDARY}]{Icons().PROMPT} {title}[/]",
            border_style=Colors.BORDER_DEFAULT,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def tool(content: str, tool_name: str) -> Panel:
        """Create tool execution panel"""
        icon = get_tool_icon(tool_name)
        return Panel(
            Text(content, style=Colors.TEXT_SECONDARY),
            title=f"[{Colors.SECONDARY}]{icon} {tool_name}[/]",
            border_style=Colors.SECONDARY,
            box=get_default_box(),
            padding=(0, 1)
        )


# ============================================================
# TODO DISPLAY
# ============================================================

@dataclass
class TodoItem:
    """Todo item for display"""
    content: str
    status: str  # pending, in_progress, completed, blocked, skipped
    active_form: str = ""


class TodoDisplay:
    """Display for todo list"""

    STATUS_STYLES = {
        "pending": (Icons().TODO_PENDING, Colors.TODO_PENDING),
        "in_progress": (Icons().TODO_IN_PROGRESS, Colors.TODO_IN_PROGRESS),
        "completed": (Icons().TODO_COMPLETED, Colors.TODO_COMPLETED),
        "blocked": (Icons().TODO_BLOCKED, Colors.TODO_BLOCKED),
        "skipped": (Icons().TODO_SKIPPED, Colors.TODO_SKIPPED),
    }

    @classmethod
    def render(cls, todos: List[TodoItem], title: str = "Tasks") -> Panel:
        """Render todo list as panel"""
        if not todos:
            return Panel(
                Text("No tasks", style=Colors.TEXT_MUTED),
                title=f"[{Colors.TEXT_SECONDARY}]{Icons().SQUARE_EMPTY} {title}[/]",
                border_style=Colors.BORDER_DEFAULT,
                box=get_default_box(),
                padding=(0, 1)
            )

        lines = []
        for todo in todos:
            icon, color = cls.STATUS_STYLES.get(
                todo.status,
                (Icons().CIRCLE_EMPTY, Colors.TEXT_MUTED)
            )

            # Use active form for in_progress items
            display_text = todo.active_form if todo.status == "in_progress" and todo.active_form else todo.content

            # Apply strikethrough for completed
            if todo.status == "completed":
                style = f"strike {color}"
            elif todo.status == "in_progress":
                style = f"bold {color}"
            else:
                style = color

            line = Text()
            line.append(f" {icon} ", style=color)
            line.append(display_text, style=style)
            lines.append(line)

        content = Group(*lines)

        return Panel(
            content,
            title=f"[{Colors.PRIMARY}]{Icons().SQUARE_FILLED} {title}[/]",
            border_style=Colors.PRIMARY,
            box=get_default_box(),
            padding=(0, 1)
        )

    @classmethod
    def render_compact(cls, todos: List[TodoItem]) -> Text:
        """Render compact inline todo status"""
        completed = sum(1 for t in todos if t.status == "completed")
        total = len(todos)

        text = Text()
        text.append(f"{Icons().SQUARE_FILLED} ", style=Colors.PRIMARY)
        text.append(f"{completed}/{total}", style=Colors.TEXT_PRIMARY)

        # Show current task
        current = next((t for t in todos if t.status == "in_progress"), None)
        if current:
            text.append(" | ", style=Colors.TEXT_MUTED)
            text.append(current.active_form or current.content, style=Colors.TODO_IN_PROGRESS)

        return text


# ============================================================
# PROGRESS BARS
# ============================================================

class StyledProgress:
    """Factory for styled progress bars"""

    @staticmethod
    def create_spinner(description: str = "Processing") -> Progress:
        """Create spinner progress"""
        return Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn(f"[{Colors.PRIMARY}]{{task.description}}[/]"),
            console=console,
            transient=True
        )

    @staticmethod
    def create_bar(description: str = "Progress") -> Progress:
        """Create progress bar"""
        return Progress(
            TextColumn(f"[{Colors.TEXT_SECONDARY}]{{task.description}}[/]"),
            BarColumn(
                complete_style=Colors.PRIMARY,
                finished_style=Colors.SUCCESS,
                bar_width=40
            ),
            TaskProgressColumn(),
            console=console
        )

    @staticmethod
    def create_download() -> Progress:
        """Create download-style progress"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[filename]}"),
            BarColumn(
                complete_style=Colors.PRIMARY,
                bar_width=30
            ),
            TaskProgressColumn(),
            TextColumn("[{task.fields[status]}]"),
            console=console
        )


# ============================================================
# HEADER & FOOTER
# ============================================================

class Header:
    """Application header"""

    @staticmethod
    def render(title: str = "Hcode", subtitle: str = "", version: str = "") -> Panel:
        """Render header"""
        icons = Icons()

        header_text = Text()
        header_text.append(f" {icons.LOGO} ", style=f"bold {Colors.PRIMARY}")
        header_text.append(title, style=f"bold {Colors.TEXT_PRIMARY}")

        if version:
            header_text.append(f" v{version}", style=Colors.TEXT_MUTED)

        if subtitle:
            header_text.append(f" {icons.BULLET} ", style=Colors.TEXT_MUTED)
            header_text.append(subtitle, style=Colors.TEXT_SECONDARY)

        return Panel(
            Align.center(header_text),
            border_style=Colors.PRIMARY,
            box=get_default_box(),
            padding=(0, 2)
        )

    @staticmethod
    def render_minimal(title: str = "Hcode") -> Text:
        """Render minimal header line"""
        icons = Icons()
        text = Text()
        text.append(f"{icons.LOGO} ", style=f"bold {Colors.PRIMARY}")
        text.append(title, style=f"bold {Colors.TEXT_PRIMARY}")
        return text


class Footer:
    """Application footer"""

    @staticmethod
    def render(text: str = "", shortcuts: Dict[str, str] = None) -> Panel:
        """Render footer with optional shortcuts"""
        content = Text()

        if shortcuts:
            for key, desc in shortcuts.items():
                content.append(f" {key} ", style=f"bold {Colors.BG_ELEVATED} {Colors.TEXT_PRIMARY}")
                content.append(f" {desc}  ", style=Colors.TEXT_MUTED)

        if text:
            if shortcuts:
                content.append(" | ", style=Colors.TEXT_MUTED)
            content.append(text, style=Colors.TEXT_MUTED)

        return Panel(
            Align.center(content),
            border_style=Colors.BORDER_DEFAULT,
            box=get_default_box(),
            padding=(0, 1)
        )


# ============================================================
# STATUS LINE
# ============================================================

class StatusLine:
    """Status line component"""

    @staticmethod
    def render(
        status: str = "ready",
        message: str = "",
        model: str = "",
        tokens: int = 0
    ) -> Text:
        """Render status line"""
        icons = Icons()
        text = Text()

        # Status indicator
        status_config = {
            "ready": (icons.CHECK, Colors.SUCCESS, "Ready"),
            "thinking": (icons.THINKING, Colors.THINKING, "Thinking"),
            "executing": (icons.EXECUTING, Colors.EXECUTING, "Executing"),
            "waiting": (icons.WAITING, Colors.WAITING, "Waiting"),
            "error": (icons.ERROR, Colors.ERROR, "Error"),
        }

        icon, color, label = status_config.get(
            status,
            (icons.CIRCLE_EMPTY, Colors.TEXT_MUTED, status.title())
        )

        text.append(f" {icon} ", style=f"bold {color}")
        text.append(label, style=color)

        # Message
        if message:
            text.append(f" {icons.BULLET} ", style=Colors.TEXT_MUTED)
            text.append(message, style=Colors.TEXT_SECONDARY)

        # Model info
        if model:
            text.append(f" {icons.BULLET} ", style=Colors.TEXT_MUTED)
            text.append(model, style=Colors.INFO)

        # Token count
        if tokens > 0:
            text.append(f" {icons.BULLET} ", style=Colors.TEXT_MUTED)
            text.append(f"{tokens:,} tokens", style=Colors.TEXT_MUTED)

        return text


# ============================================================
# PROMPT COMPONENTS
# ============================================================

class Prompt:
    """Styled prompt components"""

    @staticmethod
    def render_input(label: str = "You") -> Text:
        """Render input prompt"""
        icons = Icons()
        text = Text()
        text.append(f" {icons.PROMPT} ", style=f"bold {Colors.PRIMARY}")
        text.append(f"{label} ", style=Colors.TEXT_SECONDARY)
        text.append(f"{icons.ARROW_RIGHT_FANCY} ", style=Colors.PRIMARY)
        return text

    @staticmethod
    def render_continuation() -> Text:
        """Render continuation prompt"""
        icons = Icons()
        text = Text()
        text.append(f"   {icons.PROMPT_CONTINUE} ", style=Colors.TEXT_MUTED)
        return text

    @staticmethod
    def render_confirm(message: str, default_yes: bool = True) -> Text:
        """Render confirmation prompt with default option highlighted"""
        icons = Icons()
        text = Text()
        text.append(f" {icons.WARNING} ", style=f"bold {Colors.WARNING}")
        text.append(message, style=Colors.TEXT_PRIMARY)
        if default_yes:
            # Default is Yes - [Ok/n]
            text.append(" [", style=Colors.TEXT_MUTED)
            text.append("Ok", style=f"bold {Colors.SUCCESS}")
            text.append("/n] ", style=Colors.TEXT_MUTED)
        else:
            # Default is No - [y/N]
            text.append(" [y/", style=Colors.TEXT_MUTED)
            text.append("N", style=f"bold {Colors.ERROR}")
            text.append("] ", style=Colors.TEXT_MUTED)
        return text


# ============================================================
# MESSAGE DISPLAY
# ============================================================

class MessageDisplay:
    """Display for chat messages"""

    @staticmethod
    def render_user(content: str) -> Panel:
        """Render user message"""
        return StyledPanel.user(content)

    @staticmethod
    def render_assistant(content: str, thinking: str = None) -> Group:
        """Render assistant message with optional thinking"""
        elements = []

        if thinking:
            elements.append(StyledPanel.thinking(thinking, "Thinking"))

        elements.append(StyledPanel.agent(content, "Assistant"))

        return Group(*elements)

    @staticmethod
    def render_tool_use(tool_name: str, input_data: str, output: str = None) -> Group:
        """Render tool use display"""
        elements = []

        # Input panel
        elements.append(StyledPanel.tool(input_data, tool_name))

        # Output panel if available
        if output:
            elements.append(Panel(
                Text(output, style=Colors.TEXT_SECONDARY),
                title=f"[{Colors.TEXT_MUTED}]Output[/]",
                border_style=Colors.BORDER_DEFAULT,
                box=get_default_box(),
                padding=(0, 1)
            ))

        return Group(*elements)


# ============================================================
# DIFF DISPLAY - Claude Code Style
# ============================================================

@dataclass
class DiffLine:
    """A single line in a diff"""
    line_number_old: Optional[int]  # Line number in old file (None for additions)
    line_number_new: Optional[int]  # Line number in new file (None for deletions)
    content: str
    change_type: str  # 'context', 'addition', 'deletion', 'modification'


class DiffDisplay:
    """
    Claude Code-style diff display.

    Shows file changes with:
    - Line numbers for both old and new versions
    - Colored additions (green) and deletions (red)
    - Context lines around changes
    - Syntax highlighting for code
    - Statistics summary (lines added/removed)
    """

    CONTEXT_LINES = 3  # Lines of context around changes

    @staticmethod
    def compute_diff(
        old_content: str,
        new_content: str,
        context_lines: int = 3
    ) -> List[DiffLine]:
        """
        Compute diff between old and new content.

        Returns list of DiffLine objects representing the changes.
        """
        import difflib

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        # Use unified diff for better output
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm='',
            n=context_lines
        ))

        result = []
        old_line_num = 0
        new_line_num = 0

        # Skip the header lines (---, +++, @@)
        i = 0
        while i < len(diff):
            line = diff[i]

            # Parse hunk header @@ -start,count +start,count @@
            if line.startswith('@@'):
                import re
                match = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
                if match:
                    old_line_num = int(match.group(1)) - 1
                    new_line_num = int(match.group(2)) - 1

                # Add separator for hunks (except first)
                if result:
                    result.append(DiffLine(None, None, "...", "separator"))

            elif line.startswith('---') or line.startswith('+++'):
                # Skip file headers
                pass
            elif line.startswith('-'):
                old_line_num += 1
                result.append(DiffLine(
                    old_line_num, None,
                    line[1:].rstrip('\n\r'),
                    'deletion'
                ))
            elif line.startswith('+'):
                new_line_num += 1
                result.append(DiffLine(
                    None, new_line_num,
                    line[1:].rstrip('\n\r'),
                    'addition'
                ))
            elif line.startswith(' '):
                old_line_num += 1
                new_line_num += 1
                result.append(DiffLine(
                    old_line_num, new_line_num,
                    line[1:].rstrip('\n\r'),
                    'context'
                ))

            i += 1

        return result

    @staticmethod
    def render(
        filename: str,
        old_content: str,
        new_content: str,
        context_lines: int = 3,
        show_stats: bool = True,
        language: str = None
    ) -> Panel:
        """
        Render a Claude Code-style diff panel.

        Args:
            filename: Name of the file being edited
            old_content: Original file content
            new_content: New file content after edit
            context_lines: Number of context lines to show
            show_stats: Whether to show addition/deletion statistics
            language: Language for syntax highlighting (auto-detected from filename if None)
        """
        icons = Icons()

        # Auto-detect language from filename
        if language is None:
            ext_map = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                '.jsx': 'jsx', '.tsx': 'tsx', '.html': 'html', '.css': 'css',
                '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.md': 'markdown',
                '.rs': 'rust', '.go': 'go', '.java': 'java', '.c': 'c',
                '.cpp': 'cpp', '.h': 'c', '.hpp': 'cpp', '.rb': 'ruby',
                '.php': 'php', '.sh': 'bash', '.sql': 'sql', '.xml': 'xml',
            }
            import os
            ext = os.path.splitext(filename)[1].lower()
            language = ext_map.get(ext, 'text')

        # Compute diff
        diff_lines = DiffDisplay.compute_diff(old_content, new_content, context_lines)

        if not diff_lines:
            return Panel(
                Text("No changes", style=Colors.TEXT_MUTED),
                title=f"[{Colors.TEXT_SECONDARY}]{get_file_icon(filename)} {filename}[/]",
                border_style=Colors.BORDER_DEFAULT,
                box=get_default_box(),
                padding=(0, 1)
            )

        # Calculate statistics
        additions = sum(1 for d in diff_lines if d.change_type == 'addition')
        deletions = sum(1 for d in diff_lines if d.change_type == 'deletion')

        # Build the diff display
        lines = []

        # Stats header
        if show_stats:
            stats_text = Text()
            stats_text.append(f" {icons.DIFF_ADDED if hasattr(icons, 'DIFF_ADDED') else '+'}", style=Colors.DIFF_ADDED)
            stats_text.append(f" {additions} ", style=Colors.DIFF_ADDED)
            stats_text.append(f" {icons.DIFF_REMOVED if hasattr(icons, 'DIFF_REMOVED') else '-'}", style=Colors.DIFF_REMOVED)
            stats_text.append(f" {deletions} ", style=Colors.DIFF_REMOVED)
            lines.append(stats_text)
            lines.append(Text(""))  # Empty line after stats

        # Calculate max line number width for alignment
        max_old = max((d.line_number_old or 0) for d in diff_lines)
        max_new = max((d.line_number_new or 0) for d in diff_lines)
        ln_width = max(len(str(max_old)), len(str(max_new)), 3)

        # Render each diff line
        for diff_line in diff_lines:
            line_text = Text()

            if diff_line.change_type == 'separator':
                # Separator between hunks
                line_text.append(f"{'─' * (ln_width * 2 + 5)}", style=Colors.TEXT_MUTED)
            elif diff_line.change_type == 'deletion':
                # Deleted line - red background
                old_ln = str(diff_line.line_number_old).rjust(ln_width)
                new_ln = ' ' * ln_width
                line_text.append(f" {old_ln} ", style=f"{Colors.TEXT_MUTED}")
                line_text.append(f" {new_ln} ", style=f"dim {Colors.TEXT_MUTED}")
                line_text.append(" - ", style=f"bold {Colors.DIFF_REMOVED}")
                line_text.append(diff_line.content, style=Colors.DIFF_REMOVED)
            elif diff_line.change_type == 'addition':
                # Added line - green background
                old_ln = ' ' * ln_width
                new_ln = str(diff_line.line_number_new).rjust(ln_width)
                line_text.append(f" {old_ln} ", style=f"dim {Colors.TEXT_MUTED}")
                line_text.append(f" {new_ln} ", style=f"{Colors.TEXT_MUTED}")
                line_text.append(" + ", style=f"bold {Colors.DIFF_ADDED}")
                line_text.append(diff_line.content, style=Colors.DIFF_ADDED)
            else:
                # Context line
                old_ln = str(diff_line.line_number_old).rjust(ln_width) if diff_line.line_number_old else ' ' * ln_width
                new_ln = str(diff_line.line_number_new).rjust(ln_width) if diff_line.line_number_new else ' ' * ln_width
                line_text.append(f" {old_ln} ", style=Colors.TEXT_MUTED)
                line_text.append(f" {new_ln} ", style=Colors.TEXT_MUTED)
                line_text.append("   ", style=Colors.TEXT_MUTED)
                line_text.append(diff_line.content, style=Colors.TEXT_SECONDARY)

            lines.append(line_text)

        content = Group(*lines)

        # Build title with file icon and stats
        file_icon = get_file_icon(filename)
        title_text = f"[{Colors.TEXT_SECONDARY}]{file_icon} {filename}[/]"

        return Panel(
            content,
            title=title_text,
            border_style=Colors.BORDER_DEFAULT,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def render_simple(
        filename: str,
        additions: List[str] = None,
        deletions: List[str] = None,
        context: List[str] = None
    ) -> Panel:
        """
        Render simple diff display (legacy format).

        For simple cases where you just have lists of added/deleted lines.
        """
        icons = Icons()
        lines = []

        if context:
            for line in context:
                text = Text(f"  {line}")
                text.stylize(Colors.TEXT_MUTED)
                lines.append(text)

        if deletions:
            for line in deletions:
                text = Text(f"- {line}")
                text.stylize(Colors.DIFF_REMOVED)
                lines.append(text)

        if additions:
            for line in additions:
                text = Text(f"+ {line}")
                text.stylize(Colors.DIFF_ADDED)
                lines.append(text)

        content = Group(*lines) if lines else Text("No changes", style=Colors.TEXT_MUTED)

        file_icon = get_file_icon(filename)
        return Panel(
            content,
            title=f"[{Colors.TEXT_SECONDARY}]{file_icon} {filename}[/]",
            border_style=Colors.BORDER_DEFAULT,
            box=get_default_box(),
            padding=(0, 1)
        )

    @staticmethod
    def render_inline(
        old_string: str,
        new_string: str
    ) -> Text:
        """
        Render inline diff for small changes.

        Shows old text struck through and new text highlighted.
        """
        text = Text()
        text.append(old_string, style=f"strike {Colors.DIFF_REMOVED}")
        text.append(" → ", style=Colors.TEXT_MUTED)
        text.append(new_string, style=f"bold {Colors.DIFF_ADDED}")
        return text


# ============================================================
# FILE TREE
# ============================================================

class FileTree:
    """File tree display"""

    @staticmethod
    def render(
        root_name: str,
        files: List[str],
        show_icons: bool = True
    ) -> Tree:
        """Render file tree"""
        icons = Icons()
        tree = Tree(
            f"[{Colors.PRIMARY}]{icons.FOLDER} {root_name}[/]",
            guide_style=Colors.BORDER_DEFAULT
        )

        # Group by directories
        dirs: Dict[str, Any] = {}

        for filepath in sorted(files):
            parts = filepath.replace("\\", "/").split("/")
            current = dirs

            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Add file
            filename = parts[-1]
            current[filename] = None

        def add_nodes(parent_tree: Tree, structure: Dict, path: str = ""):
            for name, children in sorted(structure.items()):
                if children is None:
                    # File
                    icon = get_file_icon(name) if show_icons else ""
                    parent_tree.add(f"[{Colors.TEXT_SECONDARY}]{icon} {name}[/]")
                else:
                    # Directory
                    icon = icons.FOLDER if show_icons else ""
                    branch = parent_tree.add(f"[{Colors.PRIMARY}]{icon} {name}[/]")
                    add_nodes(branch, children, f"{path}/{name}")

        add_nodes(tree, dirs)
        return tree


# ============================================================
# SEPARATOR
# ============================================================

class Separator:
    """Line separators - Windows compatible"""

    @staticmethod
    def thin(width: int = None) -> Rule:
        """Thin separator line"""
        # Use ASCII dash for Windows compatibility
        return Rule(style=Colors.BORDER_DEFAULT, characters="-")

    @staticmethod
    def thick(width: int = None) -> Rule:
        """Thick separator line"""
        # Use ASCII equals for Windows compatibility
        return Rule(style=Colors.BORDER_LIGHT, characters="=")

    @staticmethod
    def with_label(label: str) -> Rule:
        """Separator with label"""
        return Rule(
            label,
            style=Colors.BORDER_DEFAULT,
            align="center",
            characters="-"
        )


# ============================================================
# LIVE DISPLAY MANAGER
# ============================================================

class LiveDisplay:
    """Manager for live-updating displays"""

    def __init__(self):
        self.live: Optional[Live] = None

    def start(self, initial_content: Any = None):
        """Start live display"""
        self.live = Live(
            initial_content or Text(""),
            console=console,
            refresh_per_second=10,
            transient=True
        )
        self.live.start()

    def update(self, content: Any):
        """Update live content"""
        if self.live:
            self.live.update(content)

    def stop(self):
        """Stop live display"""
        if self.live:
            self.live.stop()
            self.live = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
