#!/usr/bin/env python
"""Demo script for the Hcode interface.

This module demonstrates the core capabilities of the Hcode system.

Features:
- Initialization of the HcodeChat and HcodeContextManager.
- Display of available shortcut commands.
- Simulated conversation with automatic todo creation and statistics reporting.
- Detection of task complexity and task type for example tasks.
- Construction and visualization of a parallel execution plan for tool calls.
- Generation of actionable todos from a high‑level task description.

Usage:
    python demo_hcode.py

Prerequisites:
    * Python 3.9+ installed.
    * Required dependencies installed (see requirements.txt).
    * Optional: set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variables for full AI functionality.

The script prints a step‑by‑step log of the demonstration and exits with status 0 on success.
"""


import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()


async def demo():
    """Run a comprehensive demonstration of Hcode features.

    This coroutine performs the following steps:
    1. Prints a header and initializes the ``HcodeChat`` interface.
    2. Lists a subset of available shortcut commands.
    3. Creates a ``HcodeContextManager`` and simulates a short conversation.
    4. Updates and displays todo items and session statistics.
    5. Tests task‑complexity and task‑type detection on example tasks.
    6. Demonstrates the parallel executor by building and visualizing an execution plan.
    7. Generates todos from a sample high‑level task.
    8. Prints a completion banner.

    Args:
        None

    Returns:
        bool: ``True`` if the demonstration completes successfully.
    """

    print("=" * 60)
    print("   HCODE INTERFACE DEMONSTRATION")
    print("=" * 60)

    # Import the Hcode components
    from src.hcode.hcode_chat import HcodeChat
    from src.hcode.core.hcode_context import HcodeContextManager

    print("\n[1] Initializing Hcode Chat Interface...")

    # Create chat instance
    chat = HcodeChat()

    # Show available commands
    print("\n[2] Available Commands:")
    print("-" * 40)
    for cmd, desc in list(chat.shortcuts.items())[:8]:
        print(f"  {cmd:<20} - {desc}")

    print("\n[3] Testing Context Manager...")
    print("-" * 40)

    # Create context manager
    context = HcodeContextManager(auto_save=False)

    # Simulate conversation
    context.add_message("user", "Hello, can you help me write a Python function?")
    context.add_message("assistant", "Of course! I'd be happy to help you write a Python function.")

    # Add todos
    context.update_todos(
        [
            {
                "content": "Understand requirements",
                "status": "completed",
                "activeForm": "Understanding requirements",
            },
            {
                "content": "Write function code",
                "status": "in_progress",
                "activeForm": "Writing function code",
            },
            {
                "content": "Add documentation",
                "status": "pending",
                "activeForm": "Adding documentation",
            },
            {"content": "Write tests", "status": "pending", "activeForm": "Writing tests"},
        ]
    )

    # Get statistics
    stats = context.get_statistics()
    print(f"  Messages: {stats['message_count']}")
    print(f"  Todos: {stats['todo_count']} (Completed: {stats['completed_todos']})")
    print(f"  Session ID: {stats['session_id'][:8]}...")

    print("\n[4] Testing Task Processing...")
    print("-" * 40)

    # Test task complexity detection
    test_tasks = [
        "fix a simple bug",
        "implement a complex authentication system",
        "add a comment to the code",
    ]

    for task in test_tasks:
        complexity = chat.determine_complexity(task)
        task_type = chat.determine_task_type(task)
        print(f"  Task: '{task[:30]}...'")
        print(f"    - Complexity: {complexity.name}")
        print(f"    - Type: {task_type.name}")
        print()

    print("[5] Testing Parallel Executor...")
    print("-" * 40)

    from src.hcode.tools.parallel_executor import ParallelToolExecutor
    from src.hcode.tools.base_tool import ToolRegistry

    registry = ToolRegistry()
    executor = ParallelToolExecutor(registry)

    # Create execution plan
    tool_calls = [
        {"tool": "read_file", "parameters": {"path": "file1.py"}},
        {"tool": "read_file", "parameters": {"path": "file2.py"}},
        {"tool": "write_file", "parameters": {"path": "output.py"}, "dependencies": []},
    ]

    plan = executor._create_execution_plan(tool_calls, auto_detect_dependencies=True)
    print(f"  Execution stages: {len(plan.parallel_groups)}")
    print(f"  Total tools: {len(plan.tool_calls)}")

    # Visualize plan
    viz = executor.visualize_plan(plan)
    for line in viz.split("\n")[:10]:
        print(f"  {line}")

    print("\n[6] Testing Todo Generation...")
    print("-" * 40)

    task = "implement user authentication with JWT tokens"
    todos = chat.generate_todos_from_task(task)

    print(f"  Generated {len(todos)} todos for: '{task}'")
    for i, todo in enumerate(todos[:3], 1):
        print(f"    {i}. {todo['content']}")

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE!")
    print("=" * 60)
    print("\nThe Hcode interface is working correctly!")
    print("\nYou can now run the full chat interface with:")
    print("  python hcode.py")
    print("\nOr use the batch file on Windows:")
    print("  run_hcode.bat")

    return True


def main():
    """
    Entry point for the demo script.

    This function performs environment validation (checking for required API keys), runs the asynchronous ``demo`` coroutine, and exits with appropriate status codes. It also handles import errors and unexpected exceptions, providing helpful messages to the user.
    """
    try:
        # Check for API keys
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            print("\nWARNING: No API keys found!")
            print("The demo will run but the agent won't be able to connect to AI providers.")
            print("\nTo use the full functionality, set one of these environment variables:")
            print("  - ANTHROPIC_API_KEY")
            print("  - OPENAI_API_KEY")
            print()

        # Run the demo
        success = asyncio.run(demo())

        if success:
            sys.exit(0)
        else:
            sys.exit(1)

    except ImportError as e:
        print(f"\nImport Error: {e}")
        print("\nMake sure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
