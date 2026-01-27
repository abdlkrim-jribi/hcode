"""
CLI commands for HCODE memory system.
Provides commands for managing all three memory layers.
"""

import argparse
import sys
from pathlib import Path

from hcode.memory.config import config
from hcode.memory.file_memory import FileMemory
from hcode.memory.memory_manager import MemoryManager
from hcode.memory.semantic_memory import SemanticMemory, MemoryType
from hcode.memory.session_memory import SessionMemory


def cmd_init(args):
    """Initialize memory files for a project."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    file_memory = FileMemory(project_root)

    # Create project memory template
    if args.scope in ("project", "all"):
        template = file_memory.create_template("project")
        path = file_memory.update_memory(template, scope="project")
        print(f"Created project memory: {path}")

    # Create global memory template
    if args.scope in ("global", "all"):
        if not config.global_memory_path.exists():
            template = file_memory.create_template("global")
            path = file_memory.update_memory(template, scope="global")
            print(f"Created global memory: {path}")
        else:
            print(f"Global memory already exists: {config.global_memory_path}")

    # Create local memory (gitignored)
    if args.scope in ("local", "all"):
        template = "# Local Memory (gitignored)\n\n## Personal Notes\n\n"
        path = file_memory.update_memory(template, scope="local")
        print(f"Created local memory: {path}")


def cmd_status(args):
    """Show memory system status."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    manager = MemoryManager(project_root)
    stats = manager.get_stats()

    print("=" * 50)
    print("HCODE Memory System Status")
    print("=" * 50)

    print(f"\nProject: {stats['project']['root']}")
    print(f"Project ID: {stats['project']['id']}")

    print("\n--- File Memory (Layer 1) ---")
    file_stats = stats["file_memory"]
    print(f"Memory files: {file_stats['file_count']}")
    print(f"Total size: {file_stats['total_bytes']} bytes")
    for f in file_stats["files"]:
        print(f"  - [{f['scope']}] {f['path']} ({f['size_bytes']} bytes)")

    print("\n--- Session Memory (Layer 2) ---")
    session_stats = stats["session"]
    print(f"Session ID: {session_stats['id']}")
    print(f"Messages: {session_stats['message_count']}")
    print(f"Summaries: {session_stats['summary_count']}")
    print(f"Anchors: {session_stats['anchor_count']}")

    print("\n--- Semantic Memory (Layer 3) ---")
    semantic_stats = stats["semantic_memory"]
    print(f"Total memories: {semantic_stats['total_memories']}")
    print(f"Average importance: {semantic_stats['average_importance']}")
    print(f"Total accesses: {semantic_stats['total_accesses']}")
    if semantic_stats["by_type"]:
        print("By type:")
        for mem_type, count in semantic_stats["by_type"].items():
            print(f"  - {mem_type}: {count}")


def cmd_search(args):
    """Search semantic memory."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    manager = MemoryManager(project_root)

    memory_types = None
    if args.type:
        try:
            memory_types = [MemoryType(args.type)]
        except ValueError:
            print(f"Invalid memory type: {args.type}")
            print(f"Valid types: {[t.value for t in MemoryType]}")
            return

    results = manager.recall(query=args.query, top_k=args.limit, memory_types=memory_types)

    if not results:
        print("No matching memories found.")
        return

    print(f"Found {len(results)} results:\n")
    for i, (memory, score) in enumerate(results, 1):
        print(f"{i}. [{memory.memory_type.value}] (score: {score:.3f})")
        print(f"   {memory.content}")
        print(f"   Source: {memory.source} | Importance: {memory.importance:.2f}")
        print()


def cmd_remember(args):
    """Add a memory to semantic storage."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    manager = MemoryManager(project_root)

    try:
        memory_type = MemoryType(args.type) if args.type else MemoryType.CONTEXT
    except ValueError:
        print(f"Invalid memory type: {args.type}")
        print(f"Valid types: {[t.value for t in MemoryType]}")
        return

    memory = manager.remember(
        content=args.content, memory_type=memory_type, importance=args.importance, source="cli"
    )

    print(f"Memory added (ID: {memory.id})")
    print(f"Type: {memory.memory_type.value}")
    print(f"Importance: {memory.importance}")


def cmd_forget(args):
    """Remove a memory by ID."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    manager = MemoryManager(project_root)

    if manager.forget(args.id):
        print(f"Memory {args.id} deleted.")
    else:
        print(f"Memory {args.id} not found.")


def cmd_sessions(args):
    """List or manage sessions."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    session_memory = SessionMemory(project_root)

    if args.action == "list":
        sessions = session_memory.list_sessions(limit=args.limit)
        if not sessions:
            print("No sessions found.")
            return

        print(f"Recent sessions:\n")
        for s in sessions:
            print(f"  {s['session_id']}")
            print(f"    Created: {s['created_at']}")
            print(f"    Messages: {s['message_count']}")
            print(f"    Last: {s.get('last_message_preview', 'N/A')[:50]}")
            print()

    elif args.action == "show":
        if not args.session_id:
            print("Please provide --session-id")
            return

        session = session_memory.load_session(args.session_id)
        if not session:
            print(f"Session {args.session_id} not found.")
            return

        print(f"Session: {session.session_id}")
        print(f"Created: {session.created_at}")
        print(f"Messages: {len(session.messages)}")
        print(f"Summaries: {len(session.summaries)}")

        if args.verbose:
            print("\nMessages:")
            for msg in session.messages[-10:]:
                prefix = "[A] " if msg.is_anchor else "    "
                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                print(f"{prefix}[{msg.role}] {content}")

    elif args.action == "delete":
        if not args.session_id:
            print("Please provide --session-id")
            return

        if session_memory.delete_session(args.session_id):
            print(f"Session {args.session_id} deleted.")
        else:
            print(f"Session {args.session_id} not found.")

    elif args.action == "new":
        session = session_memory.create_session()
        print(f"Created new session: {session.session_id}")


def cmd_cleanup(args):
    """Run cleanup on memory system."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    manager = MemoryManager(project_root)

    print("Running cleanup...")
    stats = manager.cleanup(
        prune_semantic=not args.no_prune,
        compact_session=not args.no_compact,
        apply_decay=not args.no_decay,
    )

    print("Cleanup complete:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")


def cmd_export(args):
    """Export memory data."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    output_dir = Path(args.output).resolve()
    manager = MemoryManager(project_root)

    paths = manager.export_all(output_dir)
    print("Exported:")
    for key, path in paths.items():
        print(f"  - {key}: {path}")


def cmd_import(args):
    """Import memory data."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    input_path = Path(args.input).resolve()

    if not input_path.exists():
        print(f"File not found: {input_path}")
        return

    semantic = SemanticMemory(project_id=None)
    count = semantic.import_memories(input_path)
    print(f"Imported {count} memories.")


def cmd_edit(args):
    """Edit an AGENT.md file."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    file_memory = FileMemory(project_root)

    if args.scope == "global":
        file_path = config.global_memory_path
    elif args.scope == "local":
        file_path = config.get_local_memory_path(project_root)
    else:
        file_path = config.get_project_memory_path(project_root)

    if not file_path.exists():
        print(f"Memory file does not exist: {file_path}")
        print("Run 'hcode memory init' first.")
        return

    # Use default editor
    import os
    import subprocess

    editor = os.environ.get("EDITOR", "notepad" if sys.platform == "win32" else "nano")
    subprocess.call([editor, str(file_path)])


def cmd_show(args):
    """Show content of memory files."""
    project_root = Path(args.path).resolve() if args.path else Path.cwd()
    file_memory = FileMemory(project_root)

    if args.combined:
        content = file_memory.get_combined_context()
        print(content if content else "No memory files found.")
    else:
        files = file_memory.get_memory_files()
        if not files:
            print("No memory files found.")
            return

        for f in files:
            print(f"\n{'=' * 50}")
            print(f"[{f.scope}] {f.path}")
            print("=" * 50)
            print(f.content)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for memory CLI."""
    parser = argparse.ArgumentParser(prog="hcode memory", description="HCODE Memory System CLI")
    parser.add_argument("--path", "-p", help="Project path (default: current directory)")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize memory files")
    init_parser.add_argument(
        "--scope",
        "-s",
        choices=["project", "global", "local", "all"],
        default="project",
        help="Which memory files to create",
    )
    init_parser.set_defaults(func=cmd_init)

    # status command
    status_parser = subparsers.add_parser("status", help="Show memory system status")
    status_parser.set_defaults(func=cmd_status)

    # search command
    search_parser = subparsers.add_parser("search", help="Search semantic memory")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", "-l", type=int, default=10, help="Max results")
    search_parser.add_argument("--type", "-t", help="Filter by memory type")
    search_parser.set_defaults(func=cmd_search)

    # remember command
    remember_parser = subparsers.add_parser("remember", help="Add a memory")
    remember_parser.add_argument("content", help="Memory content")
    remember_parser.add_argument("--type", "-t", default="context", help="Memory type")
    remember_parser.add_argument(
        "--importance", "-i", type=float, default=0.5, help="Importance (0-1)"
    )
    remember_parser.set_defaults(func=cmd_remember)

    # forget command
    forget_parser = subparsers.add_parser("forget", help="Remove a memory")
    forget_parser.add_argument("id", type=int, help="Memory ID to delete")
    forget_parser.set_defaults(func=cmd_forget)

    # sessions command
    sessions_parser = subparsers.add_parser("sessions", help="Manage sessions")
    sessions_parser.add_argument(
        "action", choices=["list", "show", "delete", "new"], help="Session action"
    )
    sessions_parser.add_argument("--session-id", "-s", help="Session ID")
    sessions_parser.add_argument("--limit", "-l", type=int, default=10, help="Max sessions to list")
    sessions_parser.add_argument("--verbose", "-v", action="store_true", help="Show details")
    sessions_parser.set_defaults(func=cmd_sessions)

    # cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Run memory cleanup")
    cleanup_parser.add_argument("--no-prune", action="store_true", help="Skip semantic pruning")
    cleanup_parser.add_argument("--no-compact", action="store_true", help="Skip session compaction")
    cleanup_parser.add_argument("--no-decay", action="store_true", help="Skip importance decay")
    cleanup_parser.set_defaults(func=cmd_cleanup)

    # export command
    export_parser = subparsers.add_parser("export", help="Export memory data")
    export_parser.add_argument("output", help="Output directory")
    export_parser.set_defaults(func=cmd_export)

    # import command
    import_parser = subparsers.add_parser("import", help="Import memory data")
    import_parser.add_argument("input", help="Input JSON file")
    import_parser.set_defaults(func=cmd_import)

    # edit command
    edit_parser = subparsers.add_parser("edit", help="Edit memory file in editor")
    edit_parser.add_argument(
        "--scope",
        "-s",
        choices=["project", "global", "local"],
        default="project",
        help="Which memory file to edit",
    )
    edit_parser.set_defaults(func=cmd_edit)

    # show command
    show_parser = subparsers.add_parser("show", help="Show memory file contents")
    show_parser.add_argument("--combined", "-c", action="store_true", help="Show combined context")
    show_parser.set_defaults(func=cmd_show)

    return parser


def main(argv=None):
    """Main entry point for memory CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
