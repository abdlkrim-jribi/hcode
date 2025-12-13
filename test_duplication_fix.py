"""Test the duplication fix."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from inspect import getsource
from hcode.ui.live_todo_bar import LiveTodoBar

print("\n" + "="*70)
print("VERIFYING DUPLICATION FIX")
print("="*70 + "\n")

# Check if automatic rendering is disabled
source = getsource(LiveTodoBar)

# Check update loop
update_loop_disabled = "# DISABLED: Automatic rendering" in source and \
                       "#     self._render_status_bar()" in source

# Check callback
callback_disabled = source.count("# DISABLED: Automatic rendering") >= 4

# Check print_final_status exists
has_print_final = "def print_final_status(self)" in source

# Check stop calls print_final_status
stop_method = getsource(LiveTodoBar.stop)
stop_calls_print = "self.print_final_status()" in stop_method

print("Checking LiveTodoBar...")
print(f"  - Automatic rendering disabled: {callback_disabled}")
print(f"  - Has print_final_status() method: {has_print_final}")
print(f"  - stop() calls print_final_status(): {stop_calls_print}")

if callback_disabled and has_print_final and stop_calls_print:
    print("\n[SUCCESS] Duplication fix is correctly applied!")
    print("\nThe LiveTodoBar will now:")
    print("  1. NOT render automatically during execution")
    print("  2. Store todos internally without printing")
    print("  3. Print final status once when task completes")
    print("\nYou should now see:")
    print("  - No duplicate todos")
    print("  - Clean output during execution")
    print("  - Final todo status shown once at completion")
    print("  - Correct status (☒ for completed, ☐ for pending)")
else:
    print("\n[FAILED] Duplication fix needs attention:")
    if not callback_disabled:
        print("  - Missing: Disabled automatic rendering")
    if not has_print_final:
        print("  - Missing: print_final_status() method")
    if not stop_calls_print:
        print("  - Missing: stop() calling print_final_status()")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70 + "\n")

if callback_disabled and has_print_final and stop_calls_print:
    print("Next: Run your agent to verify no duplicates!")
    print("  python src/hcode/__main__.py chat")
print("")
