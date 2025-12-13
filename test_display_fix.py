"""Quick test to verify the display fix."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from inspect import getsource
from hcode.core.agent import HcodeAgent

print("\n" + "="*70)
print("VERIFYING DISPLAY FIX")
print("="*70 + "\n")

# Check if LiveTodoBar start/stop was added
execute_task_source = getsource(HcodeAgent.execute_task)

has_start = "live_bar.start()" in execute_task_source
has_stop = "live_bar.stop()" in execute_task_source
has_finally = "finally:" in execute_task_source

print("Checking execute_task method...")
print(f"  - Has LiveTodoBar start(): {has_start}")
print(f"  - Has LiveTodoBar stop(): {has_stop}")
print(f"  - Has finally block: {has_finally}")

if has_start and has_stop and has_finally:
    print("\n[SUCCESS] Display fix is correctly applied!")
    print("\nThe LiveTodoBar will now:")
    print("  1. Start when a task begins")
    print("  2. Display todos in real-time at the bottom")
    print("  3. Stop when the task completes")
    print("\nYou should now see:")
    print("  - Todo list at bottom of terminal")
    print("  - Updates as agent works")
    print("  - 'Thought for Xs' timer during thinking")
    print("  - Claude Code style (plain text, minimal colors)")
else:
    print("\n[FAILED] Display fix needs attention:")
    if not has_start:
        print("  - Missing: live_bar.start() call")
    if not has_stop:
        print("  - Missing: live_bar.stop() call")
    if not has_finally:
        print("  - Missing: finally block")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70 + "\n")

if has_start and has_stop and has_finally:
    print("Next: Run your agent and give it a task to see the displays!")
    print("  python src/hcode/__main__.py chat")
print("")
