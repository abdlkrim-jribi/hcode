"""
Prompt construction package for Hcode agent.

This package handles building prompts for the LLM:
- System prompt construction with tool documentation
- Context injection (task.md, implementation_plan.md)
- User task formatting
- Continuation prompts
"""

from .context_injector import ContextInjector
from .user_task_formatter import UserTaskFormatter

__all__ = [
    "ContextInjector",
    "UserTaskFormatter",
]
