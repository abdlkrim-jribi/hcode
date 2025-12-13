"""Test Claude Code style display."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rich.console import Console
from hcode.ui.todo_display import ClaudeCodeTodoDisplay
from hcode.ui.thinking_display import SimpleThinkingDisplay

console = Console()

# Test todos
todos = [
    {"content": "Analyze requirements", "status": "completed", "activeForm": "Analyzing requirements"},
    {"content": "Design solution", "status": "completed", "activeForm": "Designing solution"},
    {"content": "Implement changes", "status": "in_progress", "activeForm": "Implementing changes"},
    {"content": "Write tests", "status": "pending", "activeForm": "Writing tests"},
    {"content": "Deploy", "status": "pending", "activeForm": "Deploying"},
]

# Test todo display
print("\n" + "="*70)
print("TODO DISPLAY TEST")
print("="*70 + "\n")

print("Expected: Plain text for sparkle, active task, completed items")
print("          Dim text only for pending items")
print("          No yellow, green, or cyan colors\n")

todo_display = ClaudeCodeTodoDisplay(console)
todo_display.print(todos, elapsed_seconds=123, token_count=5432, show_shortcuts=True)

# Test thinking display
print("\n" + "="*70)
print("THINKING DISPLAY TEST")
print("="*70 + "\n")

print("Expected: Plain dim text, no boxes, no phase names, no icons\n")

thinking_display = SimpleThinkingDisplay(console)
thinking_display.show_thinking(
    "I'll help implement this feature. Let me analyze the requirements first.\n"
    "The user wants to add authentication to the application.\n"
    "This will require creating a user model and auth endpoints."
)

# Test collapsed thinking
print("="*70)
print("COLLAPSED THINKING TEST")
print("="*70 + "\n")

thinking_display.show_thinking_collapsed()

print("\n" + "="*70)
print("TESTS COMPLETE")
print("="*70 + "\n")

print("Visual Checklist:")
print("  [ ] Sparkle (✶) is plain text (no yellow)")
print("  [ ] Active task is plain text (no yellow)")
print("  [ ] Branch (⎿) is plain text (no dim)")
print("  [ ] Completed checkbox (☒) is plain text (no green)")
print("  [ ] Completed text is plain text (no green)")
print("  [ ] In-progress checkbox (☐) is plain text")
print("  [ ] In-progress text is plain text")
print("  [ ] Pending checkbox (☐) is dim gray")
print("  [ ] Pending text is dim gray")
print("  [ ] Thinking is plain dim text (no boxes)")
print("")
