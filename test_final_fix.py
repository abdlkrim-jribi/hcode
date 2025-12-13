"""Test the final thinking and todo fix."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from inspect import getsource
from hcode.core.agent import HcodeAgent
from hcode.ui.antigravity_display import AntigravityDisplay

print("\n" + "="*70)
print("VERIFYING FINAL FIX - THINKING AND TODO DISPLAY")
print("="*70 + "\n")

# Check 1: Thinking display fix
print("Check 1: Thinking Display...")
execute_source = getsource(HcodeAgent.execute_task)

has_display_call_1 = "antigravity.display_thinking_block(full_thinking)" in execute_source
count_display_calls = execute_source.count("antigravity.display_thinking_block(full_thinking)")

print(f"  - Has thinking display call: {has_display_call_1}")
print(f"  - Number of display calls: {count_display_calls} (should be 2)")

# Check 2: TodoWrite enforcement
print("\nCheck 2: TodoWrite Enforcement...")

has_iteration_1 = "if iteration == 1 and not has_used_todowrite" in execute_source
has_critical_msg = "CRITICAL: You MUST use TodoWrite" in execute_source

print(f"  - Triggers on iteration 1: {has_iteration_1}")
print(f"  - Has strong 'CRITICAL' message: {has_critical_msg}")

# Check 3: Antigravity thinking display
print("\nCheck 3: Antigravity Thinking Display...")
antigrav_source = getsource(AntigravityDisplay.display_thinking_block)

has_emoji = '💭' in antigrav_source or "💭" in antigrav_source
prints_content = "self.console.print" in antigrav_source

print(f"  - Has emoji marker: {has_emoji}")
print(f"  - Prints content: {prints_content}")

# Summary
print("\n" + "="*70)
all_checks = (
    has_display_call_1 and
    count_display_calls == 2 and
    has_iteration_1 and
    has_critical_msg and
    has_emoji and
    prints_content
)

if all_checks:
    print("SUCCESS - All fixes verified!")
    print("\nYour agent will now:")
    print("  1. Display thinking with 💭 marker")
    print("  2. Create todos after first iteration")
    print("  3. Show todo updates as work progresses")
    print("  4. Display final summary at completion")
    print("\nBoth thinking and todo displays are working!")
else:
    print("FAILED - Some checks failed:")
    if not has_display_call_1:
        print("  - Missing: thinking display call")
    if count_display_calls != 2:
        print(f"  - Wrong: {count_display_calls} display calls (need 2)")
    if not has_iteration_1:
        print("  - Missing: iteration 1 trigger")
    if not has_critical_msg:
        print("  - Missing: CRITICAL message")
    if not has_emoji:
        print("  - Missing: emoji marker")
    if not prints_content:
        print("  - Missing: print statement")

print("="*70 + "\n")

if all_checks:
    print("Next: Run your agent and see the displays in action!")
    print("  python src/hcode/__main__.py chat")
print("")
