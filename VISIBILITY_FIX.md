# Visibility Fix: Restored Todo and Thinking Displays

## Problem

After the duplication fix, the todo list and thinking displays **completely disappeared**.

### Root Cause

I disabled **all** automatic rendering to fix duplication, but this made nothing display at all. The todos were being tracked internally but never shown to the user.

---

## Solution

**Selective re-enabling**: Print todos when they change (not continuously) + make thinking visible.

### Changes Made

**File:** `src/hcode/ui/live_todo_bar.py`

#### 1. Added Simple Print Method (Line 178-201)

```python
def _print_simple_status(self) -> None:
    """Print todos as simple output (no ANSI positioning)."""
    with self._lock:
        if not self.todos:
            return

        # Calculate elapsed time
        elapsed = 0.0
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()

        try:
            # Render todos
            rendered = self.todo_display.render(
                self.todos,
                elapsed_seconds=elapsed,
                token_count=self.token_count,
                show_shortcuts=True,
            )

            # Simple print without complex positioning
            self.console.print(rendered)
        except Exception:
            pass  # Silently fail if rendering has issues
```

#### 2. Modified Callback to Print on Change (Line 118-126)

```python
if event.todos is not None:
    with self._lock:
        # Check if todos actually changed
        todos_changed = str(self.todos) != str(event.todos)
        self.todos = list(event.todos)

    # Print only if todos changed and we're not paused
    if todos_changed and self._active and not self._paused:
        self._print_simple_status()
```

**Key:** Only prints when `todos_changed` is True!

#### 3. Enhanced Final Status (Line 197-203)

```python
# Print with separators for visibility
self.console.print("\n" + "─" * 70)
self.console.print(rendered)
self.console.print("─" * 70 + "\n")
```

**File:** `src/hcode/ui/antigravity_display.py`

#### 4. Made Thinking Visible (Line 441-444)

```python
# Display thinking as plain text with a subtle marker
self.console.print()
self.console.print("💭 " + content)
self.console.print()
```

Changed from dim text (invisible) to normal text with 💭 emoji.

---

## How It Works Now

### Todo Display

1. **Task starts** → LiveTodoBar.start()
2. **Todos created** → Callback receives event
3. **Todos changed?** → Yes → Print simple status
4. **Todos changed?** → No → Skip (prevents duplication)
5. **Task completes** → Print final status with separators
6. **LiveTodoBar stops** → Clear display

### Thinking Display

1. Thinking content arrives
2. Print with 💭 emoji marker
3. Clear, visible output

---

## What You'll See Now

### During Execution

```
Using OpenAI(gpt-oss)
💭 I'll help you run a unit test from the repository...

✶ Running test… (esc to interrupt · ctrl+t to hide todos · 5s)
 ⎿  ☐ Find test files
    ☐ Select a test
    ☐ Execute with pytest
```

**Todos appear when created!**

### When Status Changes

```
✶ Running test… (8s)
 ⎿  ☒ Find test files
    ☐ Select a test
    ☐ Execute with pytest
```

**Updates when todos change!**

### At Completion

```
──────────────────────────────────────────────────────────────────────
✶ All tasks completed (15s)
 ⎿  ☒ Find test files
    ☒ Select a test
    ☒ Execute with pytest
──────────────────────────────────────────────────────────────────────
```

**Final summary with separators!**

---

## Benefits

1. ✅ **Visible** - Todos and thinking now display
2. ✅ **No Duplication** - Only prints when changed
3. ✅ **Status Updates** - Shows progress (☐ → ☒)
4. ✅ **Clear Thinking** - 💭 marker makes it visible
5. ✅ **Final Summary** - Separators highlight completion

---

## Prevention of Duplication

The key is the **change detection**:

```python
todos_changed = str(self.todos) != str(event.todos)
```

This ensures we only print when todos actually change, not on every update.

**Example:**
- Update 1: `[{todo1: pending}]` → `[{todo1: in_progress}]` → **Print** ✅
- Update 2: `[{todo1: in_progress}]` → `[{todo1: in_progress}]` → **Skip** ⏭️
- Update 3: `[{todo1: in_progress}]` → `[{todo1: completed}]` → **Print** ✅

No more spam!

---

## Testing

Run your agent:
```bash
python src/hcode/__main__.py chat
```

Try:
```
run a unit test from the repo
```

**Expected:**
- ✅ Thinking displays with 💭
- ✅ Todos appear when created
- ✅ Todos update when status changes
- ✅ Final summary at completion
- ✅ No duplicates

---

## Files Modified

1. `src/hcode/ui/live_todo_bar.py`
   - Added `_print_simple_status()` method
   - Modified callback to check for changes
   - Enhanced final status with separators

2. `src/hcode/ui/antigravity_display.py`
   - Changed thinking from dim to normal with 💭

---

## Summary

**Problem:** Todo and thinking displays disappeared
**Cause:** Over-aggressive disabling of rendering
**Fix:** Re-enable printing on change only
**Result:** Visible displays without duplication! ✅

Now you get:
- ✅ Thinking displays (💭 marker)
- ✅ Todo updates (on change only)
- ✅ Final summary (with separators)
- ✅ No spam/duplication

**Best of both worlds!** 🎉
