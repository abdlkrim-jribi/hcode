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

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


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
    Also supports simple open-ended questions for flexibility.
    """

    def __init__(self):
        super().__init__()
        self.category = ToolCategory.INTERACTIVE
        self.console = Console()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("questions", "array", "List of questions to ask (1-4)", required=True),
        ]

    def _normalize_question(self, q_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize question data to handle different formats from different models.

        Supports formats:
        1. Full format: {"question": "...", "header": "...", "options": [...], "multiSelect": bool}
        2. Simple format: {"question": "...", "type": "open"}
        3. Minimal format: {"question": "..."}
        """
        # Extract question text
        question_text = q_data.get("question", q_data.get("text", "Please answer"))

        # Extract or generate header
        header = q_data.get("header", "Question")

        # Check if this is an open-ended question (no options provided or type="open")
        is_open = q_data.get("type") == "open" or "options" not in q_data

        if is_open:
            # Return format for open-ended question
            return {
                "question": question_text,
                "header": header,
                "options": None,  # Signal open-ended
                "multi_select": False,
            }

        # Handle options - support different formats
        raw_options = q_data.get("options", [])
        normalized_options = []

        for opt in raw_options:
            if isinstance(opt, str):
                # Simple string option
                normalized_options.append({"label": opt, "description": ""})
            elif isinstance(opt, dict):
                # Dictionary option - normalize keys
                label = opt.get("label", opt.get("value", opt.get("text", str(opt))))
                desc = opt.get("description", opt.get("desc", ""))
                normalized_options.append({"label": label, "description": desc})

        return {
            "question": question_text,
            "header": header,
            "options": normalized_options if normalized_options else None,
            "multi_select": q_data.get("multiSelect", q_data.get("multi_select", False)),
        }

    async def execute(self, questions: List[Dict[str, Any]], **kwargs) -> ToolResult:
        """Ask user questions and collect responses"""
        try:
            if not questions:
                return ToolResult(
                    success=False, output=None, error="Must provide at least 1 question"
                )

            # Limit to 4 questions
            questions = questions[:4]

            answers = {}

            for q_data in questions:
                # Normalize the question format
                normalized = self._normalize_question(q_data)

                question_text = normalized["question"]
                header = normalized["header"]
                options = normalized["options"]
                multi_select = normalized["multi_select"]

                # Display question
                self.console.print(f"\n[bold blue]{header}[/bold blue]")
                self.console.print(question_text)

                # Open-ended question (no options)
                if not options:
                    response = Prompt.ask("Your answer")
                    answers[header] = response
                    continue

                # Multiple choice question
                table = Table(show_header=False, box=None)
                for idx, option in enumerate(options, 1):
                    table.add_row(
                        f"[cyan]{idx}[/cyan]",
                        f"[bold]{option['label']}[/bold]",
                        option.get("description", ""),
                    )

                # Add "Other" option
                table.add_row(
                    f"[cyan]{len(options) + 1}[/cyan]",
                    "[bold]Other[/bold]",
                    "Enter custom response",
                )

                self.console.print(table)

                # Get user input
                if multi_select:
                    self.console.print("[dim]Enter numbers separated by commas (e.g., 1,3)[/dim]")
                    response = Prompt.ask("Your choice(s)")

                    # Parse multi-select
                    selected = []
                    for num in response.split(","):
                        try:
                            idx = int(num.strip()) - 1
                            if 0 <= idx < len(options):
                                selected.append(options[idx]["label"])
                            elif idx == len(options):
                                custom = Prompt.ask("Enter custom response")
                                selected.append(custom)
                        except ValueError:
                            continue

                    answers[header] = selected

                else:
                    response = Prompt.ask("Your choice", default="1")

                    try:
                        idx = int(response) - 1
                        if 0 <= idx < len(options):
                            answers[header] = options[idx]["label"]
                        elif idx == len(options):
                            custom = Prompt.ask("Enter custom response")
                            answers[header] = custom
                        else:
                            answers[header] = options[0]["label"]
                    except ValueError:
                        # If not a number, treat as direct text input
                        answers[header] = response

            # Convert answers dict to string for downstream processing
            output_str = "\n".join(f"{k}: {v}" for k, v in answers.items())
            return ToolResult(
                success=True, output=output_str, metadata={"questions_asked": len(questions), "answers": answers}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


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

            return ToolResult(success=True, output=result, metadata={"confirmed": result})

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
            ToolParameter(
                "style", "string", "Border style (blue, green, red, yellow)", default="blue"
            ),
        ]

    async def execute(
        self, content: str, title: Optional[str] = None, style: str = "blue"
    ) -> ToolResult:
        """Display content in a panel"""
        try:
            panel = Panel(
                content, title=f"[bold]{title}[/bold]" if title else None, border_style=style
            )

            self.console.print(panel)

            return ToolResult(
                success=True, output="Content displayed", metadata={"title": title, "style": style}
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
        self, message: str, total: Optional[int] = None, current: int = 0
    ) -> ToolResult:
        """Update progress"""
        try:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            ) as progress:
                task = progress.add_task(message, total=total if total else 100)
                progress.update(task, completed=current)

            return ToolResult(
                success=True,
                output="Progress updated",
                metadata={"message": message, "current": current, "total": total},
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
