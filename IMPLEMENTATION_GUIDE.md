# Implementation Guide: Matching Claude Code Style

This guide provides **ready-to-apply** code changes to make your displays match Claude Code exactly.

---

## QUICK START

**Three simple steps:**
1. Apply the todo display fix (5 minutes)
2. Apply the thinking display fix (10 minutes)
3. Test in terminal (5 minutes)

**Total time:** 20 minutes

---

## STEP 1: Fix Todo Display Colors

### File: `src/hcode/ui/todo_display.py`

### Method: `ClaudeCodeTodoDisplay.render()`

**Location:** Lines 654-733

### Option A: Complete Method Replacement

Replace the entire `render()` method with this Claude Code-style version:

```python
def render(
    self,
    todos: List[Dict[str, Any]],
    elapsed_seconds: float = 0,
    token_count: int = 0,
    show_shortcuts: bool = True,
) -> Text:
    """
    Render Claude Code-style todo display.

    Uses minimal styling - plain text for completed/in-progress,
    dim for pending items only.

    Args:
        todos: List of todo dictionaries with content, status, activeForm
        elapsed_seconds: Time elapsed since start
        token_count: Number of tokens used
        show_shortcuts: Whether to show keyboard shortcuts

    Returns:
        Rich Text object for printing
    """
    if not todos:
        return Text("", style="dim")

    text = Text()

    # Find current in-progress task
    current_task = next((t for t in todos if t.get("status") == "in_progress"), None)

    # Header line with sparkle and active task
    if current_task:
        active_text = current_task.get("activeForm") or current_task.get("content", "Working…")
        text.append(f"{ICON_SPARKLE} ")  # Plain text - no color
        text.append(f"{active_text}… ")  # Plain text - no color
    else:
        # All done or no in-progress
        completed = sum(1 for t in todos if t.get("status") == "completed")
        if completed == len(todos):
            text.append(f"{ICON_SPARKLE} ")  # Plain text
            text.append("All tasks completed ")  # Plain text
        else:
            text.append(f"{ICON_SPARKLE} ")  # Plain text
            text.append("Ready ")  # Plain text

    # Status info in parentheses (dim only)
    status_parts = []
    if show_shortcuts:
        status_parts.append("esc to interrupt")
        status_parts.append("ctrl+t to hide todos")
    if elapsed_seconds > 0:
        status_parts.append(self.format_duration(elapsed_seconds))
    if token_count > 0:
        status_parts.append(f"↓ {self.format_tokens(token_count)} tokens")

    if status_parts:
        text.append("(", style="dim")
        text.append(" · ".join(status_parts), style="dim")
        text.append(")", style="dim")

    text.append("\n")

    # Todo items with branch connector (plain - no dim)
    text.append(f" {ICON_BRANCH}  ")  # Plain text - no color

    for i, todo in enumerate(todos):
        if i > 0:
            text.append("\n    ")  # 4 spaces indentation

        status = todo.get("status", "pending")
        content = todo.get("content", "")

        # Claude Code style: plain text for completed/in-progress, dim for pending
        if status == "completed":
            text.append(f"{CHECKBOX_CHECKED} ")  # Plain text
            text.append(content)  # Plain text
        elif status == "in_progress":
            # In-progress shown in header, checkbox is plain
            text.append(f"{CHECKBOX_UNCHECKED} ")  # Plain text
            text.append(content)  # Plain text
        else:  # pending
            text.append(f"{CHECKBOX_UNCHECKED} ", style="dim")  # Dim
            text.append(content, style="dim")  # Dim

    return text
```

### Option B: Line-by-Line Changes

If you prefer to edit line by line:

```python
# Line 684: Remove bold yellow from sparkle
# BEFORE:
text.append(f"{ICON_SPARKLE} ", style="bold yellow")
# AFTER:
text.append(f"{ICON_SPARKLE} ")

# Line 685: Remove bold yellow from active task
# BEFORE:
text.append(f"{active_text}… ", style="bold yellow")
# AFTER:
text.append(f"{active_text}… ")

# Line 690: Remove bold green
# BEFORE:
text.append(f"{ICON_SPARKLE} ", style="bold green")
# AFTER:
text.append(f"{ICON_SPARKLE} ")

# Line 691: Remove bold green
# BEFORE:
text.append("All tasks completed ", style="bold green")
# AFTER:
text.append("All tasks completed ")

# Line 693: Remove bold cyan
# BEFORE:
text.append(f"{ICON_SPARKLE} ", style="bold cyan")
# AFTER:
text.append(f"{ICON_SPARKLE} ")

# Line 694: Remove bold cyan
# BEFORE:
text.append("Ready ", style="bold cyan")
# AFTER:
text.append("Ready ")

# Line 714: Remove dim from branch
# BEFORE:
text.append(f" {ICON_BRANCH}  ", style="dim")
# AFTER:
text.append(f" {ICON_BRANCH}  ")

# Line 724: Remove green from completed checkbox
# BEFORE:
text.append(f"{CHECKBOX_CHECKED} ", style="green")
# AFTER:
text.append(f"{CHECKBOX_CHECKED} ")

# Line 725: Remove green from completed text
# BEFORE:
text.append(content, style="green")
# AFTER:
text.append(content)

# Line 727: Remove bold yellow from in-progress checkbox
# BEFORE:
text.append(f"{CHECKBOX_UNCHECKED} ", style="bold yellow")
# AFTER:
text.append(f"{CHECKBOX_UNCHECKED} ")

# Line 728: Remove bold yellow from in-progress text
# BEFORE:
text.append(content, style="bold yellow")
# AFTER:
text.append(content)

# Lines 730-731: KEEP AS IS - dim for pending is correct
```

---

## STEP 2: Fix Thinking Display

### File: `src/hcode/ui/thinking_display.py`

### Option A: Add Simple Thinking Method

Add this new method to `ThinkingDisplayManager` class:

```python
def show_thinking_simple(self, content: str):
    """
    Display thinking inline like Claude Code.

    No boxes, no phase names, just plain text.

    Args:
        content: The thinking content to display
    """
    if not content:
        return

    self.console.print()
    self.console.print(content, style="dim")
    self.console.print()

def show_thinking_collapsed(self):
    """Show collapsed thinking indicator."""
    self.console.print("💭 Thinking...", style="dim italic")
```

Then update existing methods to be no-ops:

```python
def show_phase_start(self, phase: ReasoningPhase) -> None:
    """Phase start - no visual output in Claude Code style."""
    pass  # Don't show phase boxes

def show_phase_complete(
    self,
    phase: ReasoningPhase,
    output: Any,
    show_details: bool = True
) -> None:
    """Phase complete - no visual output in Claude Code style."""
    pass  # Don't show phase completion boxes

def show_phase_summary(self) -> None:
    """Phase summary - not shown in Claude Code style."""
    pass  # Don't show phase summary
```

### Option B: Create New Simple Display Class

Add this new class to `src/hcode/ui/thinking_display.py`:

```python
class SimpleThinkingDisplay:
    """
    Minimal thinking display matching Claude Code style.

    Shows thinking as plain inline text without decoration.
    No boxes, no phase names, no colors, no icons.
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize simple thinking display.

        Args:
            console: Rich console for output (creates if None)
        """
        self.console = console or Console()

    def show_thinking(self, content: str):
        """
        Display thinking inline as plain text.

        Args:
            content: The thinking content
        """
        if not content:
            return

        self.console.print()
        # Just print plain text, slightly dimmed
        for line in content.split('\n'):
            if line.strip():
                self.console.print(line, style="dim")
        self.console.print()

    def show_thinking_collapsed(self):
        """Display collapsed thinking indicator."""
        self.console.print("💭 Thinking...", style="dim italic")

    def show_thinking_block(self, content: str):
        """
        Display a block of thinking without any formatting.

        Args:
            content: The thinking content block
        """
        self.show_thinking(content)
```

Then update `__all__` at the end of the file:

```python
__all__ = [
    "ThinkingDisplayManager",
    "SimpleThinkingDisplay",  # Add this
    "display_task_boundary",
    "display_reasoning_summary",
]
```

---

## STEP 3: Update AntigravityDisplay

### File: `src/hcode/ui/antigravity_display.py`

### Method: `display_thinking_block()`

**Location:** Lines 424-442

Replace with:

```python
def display_thinking_block(
    self,
    content: str,
    phase: Optional[str] = None,
    collapsed: bool = False,
) -> None:
    """
    Display a thinking block inline like Claude Code.

    Args:
        content: The thinking content
        phase: Optional phase name (ignored - not shown in Claude Code)
        collapsed: Whether to show collapsed (not implemented yet)
    """
    if not content:
        return

    # Display thinking as plain text, Claude Code style
    self.console.print()
    self.console.print(content, style="dim")
    self.console.print()
```

---

## STEP 4: Test Your Changes

### Test Script

Create a test file `test_claude_style.py`:

```python
"""Test Claude Code style display."""

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
print("\n=== TODO DISPLAY TEST ===\n")
todo_display = ClaudeCodeTodoDisplay(console)
todo_display.print(todos, elapsed_seconds=123, token_count=5432, show_shortcuts=True)

# Test thinking display
print("\n\n=== THINKING DISPLAY TEST ===\n")
thinking_display = SimpleThinkingDisplay(console)
thinking_display.show_thinking(
    "I'll help implement this feature. Let me analyze the requirements first.\n"
    "The user wants to add authentication to the application.\n"
    "This will require creating a user model and auth endpoints."
)

print("\n=== TESTS COMPLETE ===\n")
```

Run the test:

```bash
cd D:\workshops\Hcaude
python test_claude_style.py
```

### Expected Output

```
=== TODO DISPLAY TEST ===

✶ Implementing changes… (esc to interrupt · ctrl+t to hide todos · 2m 3s · ↓ 5.4k tokens)
 ⎿  ☒ Analyze requirements
    ☒ Design solution
    ☐ Implement changes
    ☐ Write tests
    ☐ Deploy


=== THINKING DISPLAY TEST ===

I'll help implement this feature. Let me analyze the requirements first.
The user wants to add authentication to the application.
This will require creating a user model and auth endpoints.

=== TESTS COMPLETE ===
```

**Visual Check:**
- ✶ should be plain text (no yellow)
- "Implementing changes…" should be plain text (no yellow)
- ⎿ should be plain text (no dim)
- ☒ for completed should be plain text (no green)
- "Analyze requirements" should be plain text (no green)
- ☐ for pending should be dim gray
- "Write tests" should be dim gray
- Thinking should be plain dim text (no boxes, no icons)

---

## STEP 5: Integration with Agent

### Update Agent to Use Simple Display

**File:** `src/hcode/core/agent.py`

Find where thinking is displayed and update:

```python
# BEFORE:
from hcode.ui.thinking_display import ThinkingDisplayManager

thinking_mgr = ThinkingDisplayManager(console)
thinking_mgr.show_phase_start(phase)
# ... do work ...
thinking_mgr.show_phase_complete(phase, output)

# AFTER:
from hcode.ui.thinking_display import SimpleThinkingDisplay

thinking_display = SimpleThinkingDisplay(console)
# Just show the thinking content directly
thinking_display.show_thinking(thinking_content)
```

### Update Chat Interface

**File:** `src/hcode/hcode_chat.py`

The todo display is already integrated via `execute_with_tools()`. Make sure it uses the fixed version:

```python
# Line 591-665 in hcode_chat.py
# No changes needed - it already uses ClaudeCodeTodoDisplay
# Just ensure the imports are correct
from hcode.ui.antigravity_display import (
    AntigravityDisplay,
    TaskMode,
    FileAction,
    get_antigravity_display,
)
```

---

## COMMON ISSUES & FIXES

### Issue 1: Colors Still Showing

**Problem:** After changes, colors still appear

**Solution:**
1. Restart your Python session
2. Clear any cached `.pyc` files:
   ```bash
   find . -type d -name __pycache__ -exec rm -r {} +
   ```
3. Verify you edited the correct file (check `src/` not `build/`)

### Issue 2: Import Errors

**Problem:** `SimpleThinkingDisplay` not found

**Solution:**
1. Make sure you added it to `__all__` in `thinking_display.py`
2. Restart Python to reload modules

### Issue 3: Still See Phase Boxes

**Problem:** Phase boxes still appearing

**Solution:**
1. Update the methods to be no-ops (return early or `pass`)
2. Or switch to using `SimpleThinkingDisplay` instead

### Issue 4: Terminal Not Updating

**Problem:** Changes don't appear in terminal

**Solution:**
1. Make sure you're running from `src/` directory
2. Check if there's a `build/` directory with old code
3. Reinstall: `pip install -e .`

---

## VERIFICATION CHECKLIST

After implementing changes, verify:

- [ ] Todo sparkle (✶) is plain white/default color
- [ ] Active task name is plain white/default color
- [ ] Branch connector (⎿) is plain white/default color
- [ ] Completed checkboxes (☒) are plain white/default color
- [ ] Completed task text is plain white/default color
- [ ] In-progress checkboxes (☐) are plain white/default color
- [ ] In-progress task text is plain white/default color
- [ ] Pending checkboxes (☐) are dim gray
- [ ] Pending task text is dim gray
- [ ] Meta info in parentheses is dim gray
- [ ] No phase boxes appear
- [ ] No phase names appear
- [ ] Thinking is plain dim text
- [ ] No thinking icons (except 💭 for collapsed)
- [ ] No colors in thinking output

---

## ROLLBACK PROCEDURE

If you need to revert changes:

### Git Rollback

```bash
cd D:\workshops\Hcaude
git checkout src/hcode/ui/todo_display.py
git checkout src/hcode/ui/thinking_display.py
git checkout src/hcode/ui/antigravity_display.py
```

### Manual Rollback

1. Open the file
2. Use Ctrl+Z (undo) repeatedly
3. Or restore from your backup

### Backup Before Starting

```bash
# Create backups
cp src/hcode/ui/todo_display.py src/hcode/ui/todo_display.py.backup
cp src/hcode/ui/thinking_display.py src/hcode/ui/thinking_display.py.backup
cp src/hcode/ui/antigravity_display.py src/hcode/ui/antigravity_display.py.backup
```

---

## ADVANCED: REGEX FIND/REPLACE

If you want to use find/replace in your editor:

### Remove Bold Yellow

```regex
Find:    style="bold yellow"
Replace: (leave empty or replace with "")
```

### Remove Green

```regex
Find:    style="green"
Replace: (leave empty or replace with "")
```

### Remove Bold Cyan

```regex
Find:    style="bold cyan"
Replace: (leave empty or replace with "")
```

### Keep Dim (Don't Replace)

Don't replace lines with:
- `style="dim"` when it's for pending items
- `style="dim"` when it's for meta info

---

## SUMMARY

**Three key changes:**

1. **Todo Display:** Remove all colors except dim for pending
2. **Thinking Display:** Remove boxes and phase names, show plain text
3. **Integration:** Use simple displays instead of complex ones

**Files to edit:**
1. `src/hcode/ui/todo_display.py` - Remove colors from render()
2. `src/hcode/ui/thinking_display.py` - Add SimpleThinkingDisplay
3. `src/hcode/ui/antigravity_display.py` - Simplify display_thinking_block()

**Time required:** 20-30 minutes

**Result:** Your CLI will match Claude Code's minimalist aesthetic exactly.

---

## NEXT STEPS

After completing these changes:

1. Test thoroughly in your terminal
2. Try different todo states
3. Verify thinking display
4. Check on Windows and Unix if possible
5. Update documentation
6. Commit your changes

**Then you'll have a Claude Code-style display!** 🎉
