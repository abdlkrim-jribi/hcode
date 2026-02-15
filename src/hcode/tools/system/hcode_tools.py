"""
Hcode workflow tools for Hcode.
Includes TaskBoundaryTool and NotifyUserTool.
"""

from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class TaskBoundaryTool(BaseTool):
    """
    Indicate the start of a task or make an update to the current task.
    This communicates progress to the user via the UI/Console.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.name = "task_boundary"  # Match Hcode name
        self.category = ToolCategory.INTERACTIVE
        self.console = Console()
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()
        # Keep track of current task state
        self.current_task_name = None
        self.current_mode = None
        self._progress_counter = 0

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("TaskName", "string", "Name of the task boundary", required=True),
            ToolParameter("Mode", "string", "The agent focus (PLANNING, EXECUTION, VERIFICATION)", required=True),
            ToolParameter("TaskSummary", "string", "Concise summary of accomplishments", required=True),
            ToolParameter("TaskStatus", "string", "Active status of current action", required=True),
            ToolParameter("PredictedTaskSize", "integer", "Estimation of tool calls needed", required=True),
        ]

    async def execute(
        self,
        TaskName: str,
        Mode: str,
        TaskSummary: str,
        TaskStatus: str,
        PredictedTaskSize: int,
        **kwargs
    ) -> ToolResult:
        """Update task boundary status"""
        try:
            self.current_task_name = TaskName
            self.current_mode = Mode
            
            # Create a rich panel to display the task boundary
            content = f"[bold]Mode:[/bold] {Mode}\n"
            content += f"[bold]Status:[/bold] {TaskStatus}\n"
            content += f"[bold]Summary:[/bold] {TaskSummary}\n"
            content += f"[dim]Predicted Size: {PredictedTaskSize}[/dim]"
            
            style = "blue"
            if Mode == "PLANNING":
                style = "yellow"
            elif Mode == "VERIFICATION":
                style = "green"
            
            panel = Panel(
                content,
                title=f"[bold]{TaskName}[/bold]",
                border_style=style,
                expand=False
            )
            
            self.console.print("\n")
            self.console.print(panel)
            self.console.print("\n")

            # SYNC PROGRESS TO FILE - REMOVED for Antigravity alignment
            # self._sync_progress_to_file(TaskName, Mode, TaskStatus, TaskSummary)

            return ToolResult(
                success=True,
                output=f"Task boundary updated: {TaskName} ({Mode}) - {TaskStatus}",
                metadata={
                    "TaskName": TaskName,
                    "Mode": Mode,
                    "TaskStatus": TaskStatus,
                    "TaskSummary": TaskSummary
                }
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))




class NotifyUserTool(BaseTool):
    """
    Communicate with the user. Used to request review or ask questions.
    """

    def __init__(self):
        super().__init__()
        self.name = "notify_user"  # Match Hcode name
        self.category = ToolCategory.INTERACTIVE
        self.console = Console()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("Message", "string", "Message to notify the user with", required=True),
            ToolParameter("PathsToReview", "array", "List of ABSOLUTE paths to files for review", required=False),
            ToolParameter("BlockedOnUser", "boolean", "Set true if blocked on user approval", required=False),
            ToolParameter("ConfidenceScore", "number", "Agent's confidence from 0.0-1.0", required=True),
            ToolParameter("ConfidenceJustification", "string", "Justification for confidence score", required=True),
        ]

    async def execute(
        self,
        Message: str,
        ConfidenceScore: float,
        ConfidenceJustification: str,
        PathsToReview: Optional[List[str]] = None,
        BlockedOnUser: bool = False,
        **kwargs
    ) -> ToolResult:
        """Notify user and optionally wait for basic acknowledgement if blocked"""
        try:
            from rich.markup import escape
            
            # Enforce blocking if we have files to review, as we need approval
            if PathsToReview and not BlockedOnUser:
                BlockedOnUser = True
            
            # Display the notification - SAFE: Escape user-provided message to avoid markup errors
            safe_message = escape(Message)
            content = f"{safe_message}\n\n"
            
            if PathsToReview:
                content += "[bold]Files to Review:[/bold]\n"
                for path in PathsToReview:
                    content += f"- {escape(path)}\n"
                content += "\n"
                
            content += f"[dim]Confidence: {ConfidenceScore} ({escape(ConfidenceJustification)})[/dim]"
            
            border_style = "red" if BlockedOnUser else "green"
            title = "🛑 User Action Required" if BlockedOnUser else "📢 Notification"
            
            panel = Panel(
                content,
                title=f"[bold]{title}[/bold]",
                border_style=border_style
            )
            
            self.console.print("\n")
            self.console.print(panel)
            self.console.print("\n")
            
            response = None
            if BlockedOnUser:
                # Use a separate print for the instruction to avoid complex markup in Prompt.ask
                # which sometimes causes issues with closing tags in certain environments
                self.console.print("[bold red]Press Enter to continue or type a response[/bold red]")
                response = Prompt.ask(" >")
            
            return ToolResult(
                success=True,
                output=f"User notified. Response: {response}" if response else "User notified.",
                metadata={
                    "response": response,
                    "blocked": BlockedOnUser
                }
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
