"""Verify code changes (Windows-safe)."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from inspect import getsource
from rich.console import Console
from hcode.ui.todo_display import ClaudeCodeTodoDisplay
from hcode.ui.thinking_display import SimpleThinkingDisplay
from hcode.ui.antigravity_display import AntigravityDisplay

console = Console()

print("\n" + "="*70)
print("VERIFYING CODE CHANGES")
print("="*70 + "\n")

# Test 1: Check render method source
print("Test 1: Checking ClaudeCodeTodoDisplay.render() method...")
render_source = getsource(ClaudeCodeTodoDisplay.render)

# Check for removed colors
has_bold_yellow = 'style="bold yellow"' in render_source
has_green = 'style="green"' in render_source
has_bold_cyan = 'style="bold cyan"' in render_source

print(f"  - Has 'style=\"bold yellow\"': {has_bold_yellow} (should be False)")
print(f"  - Has 'style=\"green\"': {has_green} (should be False)")
print(f"  - Has 'style=\"bold cyan\"': {has_bold_cyan} (should be False)")

# Check for kept dim style
has_dim = 'style="dim"' in render_source
print(f"  - Has 'style=\"dim\"': {has_dim} (should be True for pending items)")

if not has_bold_yellow and not has_green and not has_bold_cyan and has_dim:
    print("  [PASS] Todo display colors FIXED!")
else:
    print("  [FAIL] Todo display colors need more work")

# Test 2: Check SimpleThinkingDisplay exists
print("\nTest 2: Checking SimpleThinkingDisplay class...")
try:
    display = SimpleThinkingDisplay(console)
    has_show_thinking = hasattr(display, 'show_thinking')
    has_show_collapsed = hasattr(display, 'show_thinking_collapsed')
    has_show_block = hasattr(display, 'show_thinking_block')

    print(f"  - Has show_thinking method: {has_show_thinking}")
    print(f"  - Has show_thinking_collapsed method: {has_show_collapsed}")
    print(f"  - Has show_thinking_block method: {has_show_block}")

    if has_show_thinking and has_show_collapsed and has_show_block:
        print("  [PASS] SimpleThinkingDisplay class ADDED!")
    else:
        print("  [FAIL] SimpleThinkingDisplay class needs more work")

    test2_pass = has_show_thinking and has_show_collapsed and has_show_block
except Exception as e:
    print(f"  [FAIL] SimpleThinkingDisplay error: {e}")
    test2_pass = False

# Test 3: Check AntigravityDisplay
print("\nTest 3: Checking AntigravityDisplay.display_thinking_block()...")
antigrav_source = getsource(AntigravityDisplay.display_thinking_block)
uses_dim_style = 'style="dim"' in antigrav_source
has_text_muted = 'text_muted' in antigrav_source

print(f"  - Uses 'style=\"dim\"': {uses_dim_style} (should be True)")
print(f"  - Uses 'text_muted': {has_text_muted} (should be False)")

if uses_dim_style and not has_text_muted:
    print("  [PASS] AntigravityDisplay SIMPLIFIED!")
else:
    print("  [FAIL] AntigravityDisplay needs more work")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

test1_pass = not has_bold_yellow and not has_green and not has_bold_cyan and has_dim
test3_pass = uses_dim_style and not has_text_muted

all_tests_passed = test1_pass and test2_pass and test3_pass

if all_tests_passed:
    print("\n[SUCCESS] All changes successfully applied!\n")
    print("Your displays now match Claude Code style:")
    print("  - Todo list uses plain text (no colors except dim for pending)")
    print("  - Thinking display is simple and minimal")
    print("  - No fancy boxes or decorations")
    print("\nNext steps:")
    print("  1. Test in your actual application")
    print("  2. Verify terminal rendering")
    print("  3. Check both Windows and Unix terminals if possible")
else:
    print("\n[FAILED] Some changes need attention (see details above)")

print("")
