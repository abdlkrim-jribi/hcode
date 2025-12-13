# UI/UX Analysis: Hcode vs Claude Code Display

## Executive Summary

This document provides a comprehensive analysis of your CLI agent's UI/UX compared to Claude Code's actual implementation. The goal is to make your todo list and thinking displays match Claude Code exactly.

---

## 1. TODO LIST DISPLAY

### 1.1 Claude Code's Actual Format

```
✶ Writing integration tests… (esc to interrupt · ctrl+t to hide todos · 3m 21s · ↓ 9.5k tokens)
 ⎿  ☒ Fix Rich markup escaping in Edit tool display
    ☒ Fix long line handling in Edit tool display
    ☐ Write more integration tests for Edit tool
```

**Key Characteristics:**
- Single line header with sparkle icon (✶)
- Active task name + ellipsis (…)
- Meta info in parentheses with dots as separators (·)
- Branch connector (⎿) with specific spacing
- Two checkbox styles only: ☒ (completed), ☐ (pending/in-progress)
- Consistent 4-space indentation for todo items
- No status colors on checkboxes - checkboxes are monochrome
- Active task is indicated ONLY by the header line, not by checkbox style

### 1.2 Your Current Implementation

**File:** `src/hcode/ui/todo_display.py`, class `ClaudeCodeTodoDisplay`

**Current Format:**
```python
# Line 684-732 in todo_display.py
text.append(f"{ICON_SPARKLE} ", style="bold yellow")  # ✶
text.append(f"{active_text}… ", style="bold yellow")

# Branch and todos
text.append(f" {ICON_BRANCH}  ", style="dim")  # ⎿

for i, todo in enumerate(todos):
    if i > 0:
        text.append("\n    ")  # 4 spaces - CORRECT

    if status == "completed":
        text.append(f"{CHECKBOX_CHECKED} ", style="green")  # WRONG: colored
        text.append(content, style="green")  # WRONG: colored text
    elif status == "in_progress":
        text.append(f"{CHECKBOX_UNCHECKED} ", style="bold yellow")  # WRONG: colored
        text.append(content, style="bold yellow")
    else:
        text.append(f"{CHECKBOX_UNCHECKED} ", style="dim")
        text.append(content, style="dim")
```

### 1.3 Problems Identified

| Issue | Current | Should Be |
|-------|---------|-----------|
| **Checkbox colors** | Green for completed, yellow for in-progress | No colors - plain text |
| **Todo text colors** | Colored text (green/yellow/dim) | Plain text, possibly dim for pending |
| **In-progress indicator** | Yellow checkbox + text | Only shown in header, checkbox is ☐ |
| **Spacing before branch** | ` ⎿  ` (1 space before) | ` ⎿  ` (1 space before, 2 after) |

### 1.4 Recommended Fix

```python
def render(
    self,
    todos: List[Dict[str, Any]],
    elapsed_seconds: float = 0,
    token_count: int = 0,
    show_shortcuts: bool = True,
) -> Text:
    """Render Claude Code-style todo display."""
    if not todos:
        return Text("", style="dim")

    text = Text()

    # Find current in-progress task
    current_task = next((t for t in todos if t.get("status") == "in_progress"), None)

    # Header line with sparkle and active task
    if current_task:
        active_text = current_task.get("activeForm") or current_task.get("content", "Working…")
        text.append(f"{ICON_SPARKLE} ", style="")  # NO COLOR
        text.append(f"{active_text}… ", style="")  # NO COLOR
    else:
        completed = sum(1 for t in todos if t.get("status") == "completed")
        if completed == len(todos):
            text.append(f"{ICON_SPARKLE} ", style="")
            text.append("All tasks completed ", style="")
        else:
            text.append(f"{ICON_SPARKLE} ", style="")
            text.append("Ready ", style="")

    # Status info in parentheses
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

    # Todo items with branch connector
    text.append(f" {ICON_BRANCH}  ", style="")  # NO COLOR on branch

    for i, todo in enumerate(todos):
        if i > 0:
            text.append("\n    ")  # 4 spaces indentation

        status = todo.get("status", "pending")
        content = todo.get("content", "")

        # Simple checkbox logic - NO COLORS
        if status == "completed":
            text.append(f"{CHECKBOX_CHECKED} ", style="")  # Plain
            text.append(content, style="")  # Plain
        else:
            # Both pending and in_progress use same unchecked box
            text.append(f"{CHECKBOX_UNCHECKED} ", style="")  # Plain
            text.append(content, style="dim" if status == "pending" else "")

    return text
```

---

## 2. THINKING DISPLAY

### 2.1 Claude Code's Actual Approach

Claude Code shows thinking in **two ways**:

#### A. Inline Thinking (Default)
```
I'll help you with that task.

<thinking>
Let me break down what needs to be done:
1. First, I need to understand the requirements
2. Then I'll check the existing code
3. Finally, I'll implement the changes
</thinking>

Based on my analysis, here's what I'll do...
```

**Characteristics:**
- Thinking appears inline with regular text
- Uses plain `<thinking>` tags (visible in raw output)
- Simple, monospace text
- No fancy boxes, colors, or icons
- Sometimes collapsed with "Show thinking" toggle
- Uses plain italic/dim style when displayed

#### B. Collapsed Thinking
```
💭 Thinking... (click to expand)
```

When expanded, shows the raw thinking content without decoration.

### 2.2 Your Current Implementation

**Files:**
- `src/hcode/ui/thinking_display.py` - ThinkingDisplayManager
- `src/hcode/ui/antigravity_display.py` - AntigravityDisplay

**Current Approach:**

```python
# thinking_display.py - Lines 109-153
def show_phase_start(self, phase: ReasoningPhase):
    """Display start of a reasoning phase."""
    icon = self.PHASE_ICONS.get(phase, "•")  # 👁️ 🧠 🔍 💭 etc.
    name = self.PHASE_NAMES.get(phase, phase.value)

    self.console.print()
    self.console.print(
        f"┌─ {icon} Phase: {name} " + "─" * (40 - len(name)),
        style="blue"
    )

def show_phase_complete(self, phase, output, show_details=True):
    """Display completion of a reasoning phase."""
    if show_details and output:
        details = self._extract_phase_details(phase, output)
        for detail in details:
            self.console.print(f"│ ✓ {detail}", style="dim")

    self.console.print("└" + "─" * 45, style="blue")
```

**Output Example:**
```
┌─ 👁️ Phase: Perception ──────────────────
│ ✓ Observation: User wants to implement feature X
│ ✓ Identified 2 implicit needs
└─────────────────────────────────────────

┌─ 🧠 Phase: Comprehension ───────────────
│ ✓ Understanding: Need to modify files A and B
│ ✓ 3 assumptions made
└─────────────────────────────────────────
```

### 2.3 Problems Identified

| Issue | Current | Claude Code |
|-------|---------|-------------|
| **Visibility** | Shows phase names (Perception, Comprehension, etc.) | Never shows phase names |
| **Icons** | Heavy use of emojis (👁️ 🧠 🔍 💭 ⚡ ✨ 📋 ✅) | Only 💭 for collapsed state |
| **Boxes** | Box drawing characters (┌─ │ └─) | No boxes |
| **Structure** | Hierarchical phase display | Flat, inline text |
| **Formatting** | Colors and bold styles | Plain dim/italic text |
| **Details** | Shows extracted phase details | Shows raw thinking only |

### 2.4 Recommended Fix

**Option 1: Minimal Inline Thinking (Recommended)**

```python
class SimpleThinkingDisplay:
    """Simple inline thinking display matching Claude Code style."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def show_thinking(self, content: str, collapsed: bool = False):
        """
        Show thinking inline like Claude Code.

        Args:
            content: The thinking content
            collapsed: Whether to show collapsed (not yet implemented)
        """
        if collapsed:
            # Show collapsed state
            self.console.print("💭 Thinking...", style="dim italic")
        else:
            # Show inline thinking
            self.console.print()
            self.console.print(content, style="dim italic")
            self.console.print()

    def show_thinking_block(self, content: str):
        """Show a thinking block without any decoration."""
        # Just print the raw content, dim and italic
        for line in content.split('\n'):
            self.console.print(line, style="dim")
```

**Option 2: Hide Thinking Completely**

```python
# Don't show thinking at all - just work silently
# This matches Claude Code's behavior when thinking is auto-collapsed
```

---

## 3. DETAILED COMPARISON TABLE

### 3.1 Todo List Elements

| Element | Claude Code | Your Implementation | Status |
|---------|-------------|---------------------|--------|
| Sparkle icon | ✶ (plain) | ✶ (bold yellow) | ⚠️ Fix color |
| Active task | Plain text + … | Bold yellow | ⚠️ Remove color |
| Separator | · (dot) | · (dot) | ✅ Correct |
| Branch | ⎿ (plain) | ⎿ (dim) | ⚠️ Remove dim |
| Completed checkbox | ☒ (plain) | ☒ (green) | ⚠️ Remove color |
| Pending checkbox | ☐ (dim) | ☐ (dim) | ✅ Correct |
| Todo text | Plain/dim | Colored | ⚠️ Remove colors |
| Indentation | 4 spaces | 4 spaces | ✅ Correct |
| Time format | 3m 21s | Same | ✅ Correct |
| Token format | ↓ 9.5k tokens | Same | ✅ Correct |

### 3.2 Thinking Elements

| Element | Claude Code | Your Implementation | Status |
|---------|-------------|---------------------|--------|
| Thinking tags | `<thinking>` visible | Hidden | ⚠️ Different approach |
| Phase names | Hidden from user | Shown with boxes | ❌ Remove |
| Icons | Only 💭 | 👁️ 🧠 🔍 💭 ⚡ ✨ 📋 ✅ | ❌ Remove extra icons |
| Boxes | None | ┌─ │ └─ | ❌ Remove boxes |
| Colors | None (dim/italic only) | Blue, green, colors | ❌ Remove colors |
| Format | Inline, plain text | Structured phases | ❌ Simplify |

---

## 4. IMPLEMENTATION RECOMMENDATIONS

### 4.1 Priority 1: Fix Todo Colors

**File:** `src/hcode/ui/todo_display.py`

Remove all colors from the todo display. Claude Code uses plain text with minimal styling.

### 4.2 Priority 2: Simplify Thinking Display

**File:** `src/hcode/ui/thinking_display.py`

Replace the elaborate phase system with simple inline text:
- Remove all phase names
- Remove all boxes
- Remove all icons except 💭
- Show thinking as plain dim/italic text
- Or hide thinking completely

### 4.3 Priority 3: Adjust Spacing and Formatting

Ensure exact spacing matches Claude Code:
- Branch connector: ` ⎿  ` (1 space before, 2 after)
- Todo indentation: 4 spaces
- No extra blank lines

### 4.4 Priority 4: Test Terminal Rendering

Claude Code is designed for terminal rendering. Ensure:
- ANSI codes work properly
- No color bleeding
- Proper cursor positioning
- Clean on Windows/Unix terminals

---

## 5. SPECIFIC CODE CHANGES NEEDED

### 5.1 ClaudeCodeTodoDisplay.render()

**Location:** `src/hcode/ui/todo_display.py:654-733`

**Changes:**
1. Remove `style="bold yellow"` from line 684
2. Remove `style="bold yellow"` from line 685
3. Remove `style="green"` from lines 724-725
4. Remove `style="bold yellow"` from lines 727-728
5. Keep `style="dim"` for pending items only (lines 730-731)
6. Remove `style="dim"` from branch connector (line 714)

### 5.2 ThinkingDisplayManager

**Location:** `src/hcode/ui/thinking_display.py`

**Changes:**
1. Remove `show_phase_start()` method or make it a no-op
2. Remove `show_phase_complete()` method or make it a no-op
3. Remove `_extract_phase_details()` method
4. Replace with simple `show_thinking(content: str)` that prints dim/italic
5. Remove all PHASE_NAMES and PHASE_ICONS dictionaries

### 5.3 AntigravityDisplay

**Location:** `src/hcode/ui/antigravity_display.py`

**Changes:**
1. Simplify `display_thinking_block()` method (lines 424-442)
2. Remove fancy formatting, just print plain text
3. Remove task boundary display boxes (lines 126-204)
4. Use simple text output instead

---

## 6. VISUAL EXAMPLES

### 6.1 Before (Current)

```
┌─ 🧠 Phase: Comprehension ───────────────
│ ✓ Understanding: Need to modify config.py
│ ✓ 2 assumptions made
└─────────────────────────────────────────

✶ Implementing feature… (esc to interrupt · ctrl+t to hide todos · 45s · ↓ 2.3k tokens)
 ⎿  ☒ Read configuration file
    ☒ Parse settings
    ☐ Update values
```
**Issues:** Phase boxes, colored checkboxes, green text for completed

### 6.2 After (Recommended)

```
Let me analyze the configuration structure...
I need to modify the config.py file to add the new settings.
This will require updating the schema validation as well.

✶ Implementing feature… (esc to interrupt · ctrl+t to hide todos · 45s · ↓ 2.3k tokens)
 ⎿  ☒ Read configuration file
    ☒ Parse settings
    ☐ Update values
```
**Fixed:** No phase boxes, plain text thinking, monochrome checkboxes

---

## 7. TESTING CHECKLIST

After implementing changes, verify:

- [ ] Todo list has no colored checkboxes
- [ ] Todo list has no colored text (except dim for pending)
- [ ] Branch connector has no color styling
- [ ] Sparkle icon is plain text
- [ ] Active task is plain text
- [ ] Meta info in parentheses is dim
- [ ] 4-space indentation is correct
- [ ] Thinking displays as plain dim/italic text
- [ ] No phase names visible
- [ ] No thinking boxes
- [ ] No extra icons (except 💭 if collapsed)
- [ ] Renders correctly on Windows terminal
- [ ] Renders correctly on Unix terminal
- [ ] ANSI codes don't bleed into output
- [ ] Cursor positioning works correctly

---

## 8. ADDITIONAL NOTES

### 8.1 Why Claude Code Uses Minimal Styling

1. **Terminal Compatibility:** Plain text works everywhere
2. **Readability:** Less visual noise = easier to scan
3. **Professional Look:** Clean, monochrome aesthetic
4. **Performance:** Less ANSI overhead
5. **Accessibility:** Works with screen readers

### 8.2 Why Your Current Implementation Is "Too Much"

Your implementation is actually very well-engineered, but it's **over-designed** compared to Claude Code:

- Phase tracking is sophisticated but invisible to users in Claude Code
- The reasoning system is powerful but shouldn't be displayed
- Colors and icons are nice but Claude Code intentionally avoids them
- Box drawing is beautiful but not part of Claude Code's aesthetic

### 8.3 What To Keep From Your Implementation

Keep the **logic** but change the **presentation**:

- ✅ Keep the reasoning phases internally
- ✅ Keep the structured thinking system
- ✅ Keep the todo tracking logic
- ✅ Keep the callback system
- ✅ Keep the animation thread
- ❌ Remove the visual display of phases
- ❌ Remove colors from todos
- ❌ Remove boxes and borders
- ❌ Simplify thinking output

---

## 9. FINAL RECOMMENDATIONS

### Quick Wins (30 minutes)
1. Remove colors from `ClaudeCodeTodoDisplay.render()`
2. Remove `style=` arguments from checkboxes and text
3. Test the output

### Medium Effort (2 hours)
1. Simplify `ThinkingDisplayManager` to plain text output
2. Remove phase display boxes
3. Create new `SimpleThinkingDisplay` class
4. Update references in `agent.py`

### Long-term Improvements (4+ hours)
1. Add thinking collapse/expand feature
2. Implement "Show thinking" toggle
3. Add keyboard shortcuts (ctrl+t, etc.)
4. Improve ANSI positioning for status bar
5. Add animation for active task

---

## 10. CONCLUSION

Your implementation is well-architected and feature-rich. The issue is that it's **visually different** from Claude Code's minimalist aesthetic.

**Key Principle:** Claude Code prefers **information density** over **visual decoration**.

**Action Items:**
1. Strip colors from todo display
2. Simplify thinking display
3. Remove boxes and decorative elements
4. Keep functionality, change presentation
5. Test on real terminals

The good news: Your underlying architecture is solid. You just need to adjust the display layer to match Claude Code's minimalist style.
