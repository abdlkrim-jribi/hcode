# Quick Reference: Claude Code Style

## TL;DR - The Main Problem

Your todo list uses **too many colors**. Claude Code uses **almost no colors**.

**Fix:** Remove `style="..."` from most places in `todo_display.py`.

---

## What Claude Code Actually Looks Like

```
✶ Writing tests… (esc to interrupt · ctrl+t to hide todos · 1m 23s · ↓ 3.4k tokens)
 ⎿  ☒ Set up test environment
    ☒ Create test fixtures
    ☐ Write unit tests
    ☐ Run test suite
```

**Colors used:**
- Everything is plain white/default
- Only pending items (☐) are dim gray
- That's it. No yellow, no green, no bold.

---

## Your Current Implementation

```
✶ Writing tests… (esc to interrupt · ctrl+t to hide todos · 1m 23s · ↓ 3.4k tokens)
 ⎿  ☒ Set up test environment
    ☒ Create test fixtures
    ☐ Write unit tests
    ☐ Run test suite
```

**Colors used:**
- ✶ is **bold yellow**
- "Writing tests…" is **bold yellow**
- ⎿ is **dim gray**
- ☒ and completed text are **green**
- ☐ pending items are **dim gray**

**Problem:** Too many colors! Claude Code only uses dim for pending items.

---

## The Fix (One Line at a Time)

Open `src/hcode/ui/todo_display.py` and edit the `render()` method:

```python
# Line 684: Remove this parameter
style="bold yellow"

# Line 685: Remove this parameter
style="bold yellow"

# Line 690: Remove this parameter
style="bold green"

# Line 691: Remove this parameter
style="bold green"

# Line 693: Remove this parameter
style="bold cyan"

# Line 694: Remove this parameter
style="bold cyan"

# Line 714: Remove this parameter
style="dim"

# Line 724: Remove this parameter
style="green"

# Line 725: Remove this parameter
style="green"

# Line 727: Remove this parameter
style="bold yellow"

# Line 728: Remove this parameter
style="bold yellow"

# Lines 730-731: KEEP THESE (dim for pending is correct)
```

**Result:** Plain text for everything except pending items.

---

## Thinking Display Fix

### Current (Too Fancy)

```
┌─ 👁️  Phase: Perception ──────────────────
│ ✓ Observation: Analyzing request
│ ✓ Identified 2 implicit needs
└─────────────────────────────────────────

┌─ 🧠 Phase: Comprehension ─────────────────
│ ✓ Understanding: Create auth module
│ ✓ 2 assumptions made
└─────────────────────────────────────────
```

### Claude Code (Simple)

```
I'll help create an auth module. Let me analyze the requirements.
I need to add user authentication with JWT tokens.
This will require creating a user model and auth endpoints.
```

**Fix:** Replace phase boxes with plain text output.

---

## File Change Summary

| File | Lines | Change |
|------|-------|--------|
| `todo_display.py` | 684-728 | Remove style parameters |
| `thinking_display.py` | N/A | Add SimpleThinkingDisplay class |
| `antigravity_display.py` | 424-442 | Simplify display_thinking_block() |

---

## Before/After Comparison

### Before
```python
text.append(f"{ICON_SPARKLE} ", style="bold yellow")
text.append(f"{active_text}… ", style="bold yellow")
text.append(f"{CHECKBOX_CHECKED} ", style="green")
text.append(content, style="green")
```

**Terminal Output:** Yellow sparkle, green checkboxes

### After
```python
text.append(f"{ICON_SPARKLE} ")
text.append(f"{active_text}… ")
text.append(f"{CHECKBOX_CHECKED} ")
text.append(content)
```

**Terminal Output:** Plain text, monochrome

---

## Color Usage Rules

| Element | Your Code | Claude Code | Action |
|---------|-----------|-------------|--------|
| ✶ Sparkle | Bold yellow | Plain | Remove style |
| Active task | Bold yellow | Plain | Remove style |
| ⎿ Branch | Dim | Plain | Remove style |
| ☒ Completed | Green | Plain | Remove style |
| Completed text | Green | Plain | Remove style |
| ☐ In-progress | Bold yellow | Plain | Remove style |
| ☐ Pending | Dim | Dim | **Keep!** |
| Pending text | Dim | Dim | **Keep!** |
| Meta info () | Dim | Dim | **Keep!** |

**Rule:** Only pending items should be dim. Everything else is plain.

---

## Testing Your Changes

```bash
# Run this to test
cd D:\workshops\Hcaude
python test_claude_style.py
```

**Check for:**
- No yellow colors
- No green colors
- No cyan colors
- Only dim gray for pending items
- Plain white/default for everything else

---

## Most Common Mistakes

### ❌ Mistake 1: Keeping colored checkboxes
```python
text.append(f"{CHECKBOX_CHECKED} ", style="green")  # WRONG
```

### ✅ Correct:
```python
text.append(f"{CHECKBOX_CHECKED} ")  # RIGHT
```

---

### ❌ Mistake 2: Bold yellow sparkle
```python
text.append(f"{ICON_SPARKLE} ", style="bold yellow")  # WRONG
```

### ✅ Correct:
```python
text.append(f"{ICON_SPARKLE} ")  # RIGHT
```

---

### ❌ Mistake 3: Showing phase boxes
```python
self.console.print(f"┌─ {icon} Phase: {name}")  # WRONG
```

### ✅ Correct:
```python
self.console.print(content, style="dim")  # RIGHT
```

---

## 5-Minute Quick Fix

1. Open `src/hcode/ui/todo_display.py`
2. Find the `render()` method (line 654)
3. Do a find/replace:
   - Find: `style="bold yellow"`
   - Replace: (empty)
4. Do another find/replace:
   - Find: `style="green"`
   - Replace: (empty)
5. Do another find/replace:
   - Find: `style="bold cyan"`
   - Replace: (empty)
6. Manually remove `style="dim"` from line 714 (branch connector)
7. Save and test

**Done!** Your todos now match Claude Code.

---

## Visual Reference

### What Colors You Should See

**Claude Code Style:**
```
✶ Writing tests…                 ← White/default
 ⎿  ☒ Completed task             ← White/default
    ☐ Pending task               ← Gray (dim)
```

**NOT This (Your Current):**
```
✶ Writing tests…                 ← Yellow
 ⎿  ☒ Completed task             ← Green
    ☐ Pending task               ← Gray (dim)
```

---

## Regex for Find/Replace

If your editor supports regex:

```regex
# Remove all styles except dim
Find:    style="bold (yellow|green|cyan)"
Replace: (empty)

# Remove green styles
Find:    style="green"
Replace: (empty)
```

**Don't replace:**
- `style="dim"` for pending items
- `style="dim"` for meta info

---

## Complete Todo Display Code (Ready to Copy)

```python
def render(self, todos, elapsed_seconds=0, token_count=0, show_shortcuts=True):
    """Render Claude Code-style todo display."""
    if not todos:
        return Text("", style="dim")

    text = Text()
    current_task = next((t for t in todos if t.get("status") == "in_progress"), None)

    # Header - plain text only
    if current_task:
        active_text = current_task.get("activeForm") or current_task.get("content", "Working…")
        text.append(f"{ICON_SPARKLE} ")
        text.append(f"{active_text}… ")
    else:
        text.append(f"{ICON_SPARKLE} ")
        text.append("Ready ")

    # Meta info - dim only
    status_parts = []
    if show_shortcuts:
        status_parts.extend(["esc to interrupt", "ctrl+t to hide todos"])
    if elapsed_seconds > 0:
        status_parts.append(self.format_duration(elapsed_seconds))
    if token_count > 0:
        status_parts.append(f"↓ {self.format_tokens(token_count)} tokens")

    if status_parts:
        text.append("(", style="dim")
        text.append(" · ".join(status_parts), style="dim")
        text.append(")", style="dim")

    text.append("\n")
    text.append(f" {ICON_BRANCH}  ")  # Plain, no dim

    # Todo items
    for i, todo in enumerate(todos):
        if i > 0:
            text.append("\n    ")

        status = todo.get("status", "pending")
        content = todo.get("content", "")

        if status == "completed":
            text.append(f"{CHECKBOX_CHECKED} ")  # Plain
            text.append(content)  # Plain
        elif status == "in_progress":
            text.append(f"{CHECKBOX_UNCHECKED} ")  # Plain
            text.append(content)  # Plain
        else:  # pending
            text.append(f"{CHECKBOX_UNCHECKED} ", style="dim")  # Dim
            text.append(content, style="dim")  # Dim

    return text
```

---

## Documents Reference

1. **UI_UX_ANALYSIS.md** - Full analysis of differences
2. **VISUAL_COMPARISON.md** - Side-by-side examples
3. **IMPLEMENTATION_GUIDE.md** - Step-by-step fixes
4. **QUICK_REFERENCE.md** - This document

---

## Bottom Line

**Problem:** Too many colors in todo display

**Solution:** Remove colors, keep only dim for pending

**Time:** 5-20 minutes depending on approach

**Result:** Matches Claude Code exactly

---

## Need Help?

Check these files in order:

1. This file (QUICK_REFERENCE.md) - Quick overview
2. IMPLEMENTATION_GUIDE.md - Step-by-step instructions
3. VISUAL_COMPARISON.md - Exact visual examples
4. UI_UX_ANALYSIS.md - Deep dive analysis

**Or just copy the code from IMPLEMENTATION_GUIDE.md and paste it in!**
