"""
User task formatting for Hcode agent.

This module handles formatting user tasks with output format instructions
and proper structure for the LLM.
"""

from typing import Optional


class UserTaskFormatter:
    """
    Format user tasks for LLM consumption.
    
    Wraps user tasks with appropriate instructions for output format,
    tool usage hints, and task completion expectations.
    """
    
    # Default output format instructions
    OUTPUT_FORMAT = """<output_format>
When executing tasks:
1. Think through the task step by step
2. Use tools to interact with files and the codebase
3. Provide clear explanations of your actions
4. When done, explicitly state that the task is completed

For tool calls, use the following JSON format:
{"tool": "ToolName", "parameters": {"param1": "value1"}}

Available tools include:
- Read: Read file contents
- Write: Create or overwrite files
- Edit: Modify existing file content
- LS: List directory contents
- Glob: Find files by pattern
- Grep: Search file contents
- Bash: Run shell commands
- TodoWrite: Manage task lists
</output_format>"""
    
    def __init__(self, include_output_format: bool = True):
        """
        Initialize the user task formatter.
        
        Args:
            include_output_format: Whether to include output format instructions
        """
        self.include_output_format = include_output_format
    
    def format(self, task: str, context: Optional[str] = None) -> str:
        """
        Format a user task for the LLM.
        
        Args:
            task: The raw user task
            context: Optional additional context
            
        Returns:
            Formatted task string
        """
        formatted = f"<user_task>\n{task}\n</user_task>"
        
        if context:
            formatted = f"<context>\n{context}\n</context>\n\n{formatted}"
        
        if self.include_output_format:
            formatted = formatted + "\n\n" + self.OUTPUT_FORMAT
        
        return formatted
    
    def format_continuation(self, iteration: int, previous_summary: Optional[str] = None) -> str:
        """
        Format a continuation prompt when the model's response was truncated.
        
        Args:
            iteration: Current iteration number
            previous_summary: Optional summary of what was done so far
            
        Returns:
            Continuation prompt string
        """
        base_prompt = "Please continue with the task. "
        
        if previous_summary:
            base_prompt += f"So far: {previous_summary}. "
        
        base_prompt += "Complete the remaining work and provide final output."
        
        return base_prompt
    
    def format_clarification_request(self, questions: list) -> str:
        """
        Format a request for clarification from the user.
        
        Args:
            questions: List of questions to ask
            
        Returns:
            Formatted clarification request
        """
        if not questions:
            return "I need some clarification before proceeding. What would you like me to focus on?"
        
        formatted = "Before I proceed, I have some questions:\n\n"
        for i, question in enumerate(questions, 1):
            formatted += f"{i}. {question}\n"
        
        formatted += "\nPlease provide your answers so I can proceed appropriately."
        
        return formatted
    
    def format_error_recovery(self, error: str, suggestion: Optional[str] = None) -> str:
        """
        Format an error recovery prompt.
        
        Args:
            error: The error that occurred
            suggestion: Optional suggested recovery action
            
        Returns:
            Error recovery prompt
        """
        prompt = f"An error occurred: {error}\n\n"
        
        if suggestion:
            prompt += f"Suggested action: {suggestion}\n\n"
        
        prompt += "Please analyze this error and either fix the issue or take an alternative approach."
        
        return prompt
