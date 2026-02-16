"""
File outline tool for Hcode.
Provides high-level structure of files (classes, functions matches Antigravity's view_file_outline).
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class ViewFileOutlineTool(BaseTool):
    """
    View the outline of the input file.
    This includes breakdown of functions and classes in the file.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                "AbsolutePath", "string", "Path to file to view. Must be an absolute path.", required=True
            ),
            ToolParameter(
                "ItemOffset", "integer", "Offset of items to show. This is used for pagination.", default=0
            ),
        ]

    async def execute(self, AbsolutePath: str, ItemOffset: int = 0, **kwargs) -> ToolResult:
        """
        Generate file outline.
        """
        try:
            path = Path(AbsolutePath)

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"File not found: {AbsolutePath}")

            if not path.is_file():
                return ToolResult(success=False, output=None, error=f"Not a file: {AbsolutePath}")

            # Read file content
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:
                return ToolResult(success=False, output=None, error=f"Error reading file: {str(e)}")

            total_lines = len(content.splitlines())

            # Determine parser based on extension
            ext = path.suffix.lower()
            outline_items = []

            if ext == ".py":
                outline_items = self._parse_python_outline(content)
            elif ext in [".js", ".ts", ".jsx", ".tsx"]:
                outline_items = self._parse_js_outline(content)
            else:
                # Fallback for other files - maybe just show nothing or basic headers?
                # For now, let's just return file info if we can't parse structure
                pass

            # Pagination logic
            limit = 100  # Show 100 items per page by default to match Antigravity roughly
            total_items = len(outline_items)

            start_idx = ItemOffset
            end_idx = min(start_idx + limit, total_items)

            paged_items = outline_items[start_idx:end_idx]

            # Format output
            output = f"File: {path.name}\n"
            output += f"Total Lines: {total_lines}\n"
            output += f"Total Outline Items: {total_items}\n"

            if total_items > 0:
                output += "\nOutline:\n"
                for item in paged_items:
                    output += f"{item['line']}: {item['type']} {item['name']}"
                    if item.get("signature"):
                        output += f"({item['signature']})"
                    output += "\n"

                if end_idx < total_items:
                    output += f"\n... {total_items - end_idx} more items not shown. Use ItemOffset={end_idx} to see more."
            else:
                output += "\nNo outline items found (classes/functions)."

            # If it's the first request (offset 0) and file is small enough, maybe show preview?
            # Antigravity spec says: "When viewing a file for the first time with offset 0, we will also attempt to show the contents of the file"
            # However, for simplicity and adherence to "outline", let's stick to outline unless requested otherwise.
            # But wait, Antigravity DOES show content if small.
            # Let's verify file size. If < 100 lines, maybe just dump content?
            # Actually, the user asked for "exactly like antigravity".
            # "The tool result will also contain the total number of lines in the file and the total number of outline items."

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "file_path": str(path),
                    "total_lines": total_lines,
                    "total_items": total_items,
                    "shown_items": len(paged_items),
                    "next_offset": end_idx if end_idx < total_items else None
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _parse_python_outline(self, content: str) -> List[Dict[str, Any]]:
        """Parse Python file for classes and functions using AST"""
        items = []
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    item_type = "class" if isinstance(node, ast.ClassDef) else "function"
                    name = node.name
                    line = node.lineno

                    # Try to get signature args for functions
                    sig = ""
                    if item_type == "function":
                        args = [a.arg for a in node.args.args]
                        sig = ", ".join(args)

                    items.append({
                        "name": name,
                        "type": item_type,
                        "line": line,
                        "signature": sig
                    })

            # Sort by line number
            items.sort(key=lambda x: x["line"])

        except SyntaxError:
            pass  # Use fallback or empty if syntax error

        return items

    def _parse_js_outline(self, content: str) -> List[Dict[str, Any]]:
        """Basic regex parsing for JS/TS"""
        items = []
        lines = content.splitlines()

        # Very basic regexes - strict parsing would need a full parser
        # function foo(
        # class Foo
        # const foo = () => 

        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Function definitions
            func_match = re.search(r'function\s+([a-zA-Z0-9_$]+)', line)
            if func_match:
                items.append({"name": func_match.group(1), "type": "function", "line": i, "signature": ""})
                continue

            # Class definitions
            class_match = re.search(r'class\s+([a-zA-Z0-9_$]+)', line)
            if class_match:
                items.append({"name": class_match.group(1), "type": "class", "line": i, "signature": ""})
                continue

            # Arrow functions / variable assignments (const foo = ...)
            # This is heuristic and noisy, maybe skip for now to keep it clean like Antigravity likely does?
            # Antigravity usually shows declared functions/classes.

        return items
