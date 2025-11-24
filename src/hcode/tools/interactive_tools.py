"""
Interactive tools for Hcode.
Includes AskUserQuestion, TodoWrite for user interaction.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from .base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


@dataclass
class Question:
    """Question specification"""
    question: str
    header: str
    options: List[Dict[str, str]]
    multi_select: bool = False


@dataclass
class Todo:
    """Todo item"""
    content: str
    status: str  # pending, in_progress, completed
    active_form: str


class AskUserQuestionTool(BaseTool):
    """
    Ask the user questions during execution with multiple choice options.
    """

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.INTERACTIVE
        self.console = Console()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("questions", "array", "List of questions to ask (1-4)", required=True),
        ]

    async def execute(self, questions: List[Dict[str, Any]]) -> ToolResult:
        """Ask user questions and collect responses"""
        try:
            if not questions or len(questions) > 4:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Must provide 1-4 questions"
                )

            answers = {}

            for q_data in questions:
                question_obj = Question(
                    question=q_data["question"],
                    header=q_data["header"],
                    options=q_data["options"],
                    multi_select=q_data.get("multi_select", False)
                )

                # Display question
                self.console.print(f"\n[bold blue]{question_obj.header}[/bold blue]")
                self.console.print(question_obj.question)

                # Display options
                table = Table(show_header=False, box=None)
                for idx, option in enumerate(question_obj.options, 1):
                    table.add_row(
                        f"[cyan]{idx}[/cyan]",
                        f"[bold]{option['label']}[/bold]",
                        option['description']
                    )

                # Add "Other" option
                table.add_row(
                    f"[cyan]{len(question_obj.options) + 1}[/cyan]",
                    "[bold]Other[/bold]",
                    "Enter custom response"
                )

                self.console.print(table)

                # Get user input
                if question_obj.multi_select:
                    self.console.print("[dim]Enter numbers separated by commas (e.g., 1,3)[/dim]")
                    response = Prompt.ask("Your choice(s)")

                    # Parse multi-select
                    selected = []
                    for num in response.split(','):
                        try:
                            idx = int(num.strip()) - 1
                            if 0 <= idx < len(question_obj.options):
                                selected.append(question_obj.options[idx]['label'])
                            elif idx == len(question_obj.options):
                                custom = Prompt.ask("Enter custom response")
                                selected.append(custom)
                        except ValueError:
                            continue

                    answers[question_obj.header] = selected

                else:
                    response = Prompt.ask("Your choice", default="1")

                    try:
                        idx = int(response) - 1
                        if 0 <= idx < len(question_obj.options):
                            answers[question_obj.header] = question_obj.options[idx]['label']
                        elif idx == len(question_obj.options):
                            custom = Prompt.ask("Enter custom response")
                            answers[question_obj.header] = custom
                        else:
                            answers[question_obj.header] = question_obj.options[0]['label']
                    except ValueError:
                        answers[question_obj.header] = question_obj.options[0]['label']

            return ToolResult(
                success=True,
                output=answers,
                metadata={"questions_asked": len(questions)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class TodoWriteTool(BaseTool):
    """
    Manage todo lists for tracking task progress.
    """

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.INTERACTIVE
        self.console = Console()
        self.todos: List[Todo] = []

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("todos", "array", "List of todo items", required=True),
        ]

    async def execute(self, todos: List[Dict[str, str]]) -> ToolResult:
        """Update todo list"""
        try:
            # Parse todos
            self.todos = [
                Todo(
                    content=t["content"],
                    status=t["status"],
                    active_form=t["activeForm"]
                )
                for t in todos
            ]

            # Display updated todo list
            self._display_todos()

            return ToolResult(
                success=True,
                output="Todo list updated",
                metadata={
                    "total_todos": len(self.todos),
                    "completed": sum(1 for t in self.todos if t.status == "completed"),
                    "in_progress": sum(1 for t in self.todos if t.status == "in_progress"),
                    "pending": sum(1 for t in self.todos if t.status == "pending")
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _display_todos(self):
        """Display todo list in formatted table"""
        table = Table(title="[bold]Task Progress[/bold]", show_header=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("Status", width=12)
        table.add_column("Task")

        for idx, todo in enumerate(self.todos, 1):
            # Status icon and color
            if todo.status == "completed":
                status = "[green]✓ Completed[/green]"
            elif todo.status == "in_progress":
                status = "[yellow]⟳ In Progress[/yellow]"
            else:
                status = "[dim]○ Pending[/dim]"

            # Use active form if in progress
            task_text = todo.active_form if todo.status == "in_progress" else todo.content

            table.add_row(str(idx), status, task_text)

        self.console.print(table)

    def get_todos(self) -> List[Todo]:
        """Get current todo list"""
        return self.todos


class ConfirmTool(BaseTool):
    """
    Ask user for confirmation before proceeding.
    """

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.INTERACTIVE
        self.console = Console()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("message", "string", "Confirmation message", required=True),
            ToolParameter("default", "boolean", "Default value", default=True),
        ]

    async def execute(self, message: str, default: bool = True) -> ToolResult:
        """Ask for user confirmation"""
        try:
            result = Confirm.ask(message, default=default)

            return ToolResult(
                success=True,
                output=result,
                metadata={"confirmed": result}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DisplayPanelTool(BaseTool):
    """
    Display formatted information to user in a panel.
    """

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.INTERACTIVE
        self.console = Console()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("content", "string", "Content to display", required=True),
            ToolParameter("title", "string", "Panel title", default=None),
            ToolParameter("style", "string", "Border style (blue, green, red, yellow)", default="blue"),
        ]

    async def execute(
        self,
        content: str,
        title: Optional[str] = None,
        style: str = "blue"
    ) -> ToolResult:
        """Display content in a panel"""
        try:
            panel = Panel(
                content,
                title=f"[bold]{title}[/bold]" if title else None,
                border_style=style
            )

            self.console.print(panel)

            return ToolResult(
                success=True,
                output="Content displayed",
                metadata={"title": title, "style": style}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ProgressTool(BaseTool):
    """
    Show progress indicator for long-running operations.
    """

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.INTERACTIVE

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("message", "string", "Progress message", required=True),
            ToolParameter("total", "integer", "Total steps", default=None),
            ToolParameter("current", "integer", "Current step", default=0),
        ]

    async def execute(
        self,
        message: str,
        total: Optional[int] = None,
        current: int = 0
    ) -> ToolResult:
        """Update progress"""
        try:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%")
            ) as progress:
                task = progress.add_task(message, total=total if total else 100)
                progress.update(task, completed=current)

            return ToolResult(
                success=True,
                output="Progress updated",
                metadata={"message": message, "current": current, "total": total}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
