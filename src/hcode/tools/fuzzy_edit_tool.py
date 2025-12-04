"""
Fuzzy edit tool for Hcode.
Allows applying changes with fuzzy matching when exact context is missing.
"""

import os
import difflib
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from hcode.tools.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class FuzzyEditTool(BaseTool):
    """
    Edit files using fuzzy matching to locate the code block to replace.
    Useful when exact line numbers or exact context matches are fragile.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.name = "FuzzyEdit"
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("file_path", "string", "Absolute path to file", required=True),
            ToolParameter("search_block", "string", "The block of code to find (approximate match)", required=True),
            ToolParameter("replace_block", "string", "The new block of code to replace it with", required=True),
            ToolParameter("threshold", "number", "Similarity threshold (0.0-1.0)", default=0.8),
        ]

    async def execute(
        self,
        file_path: str,
        search_block: str,
        replace_block: str,
        threshold: float = 0.8,
        **kwargs
    ) -> ToolResult:
        """Apply fuzzy edit"""
        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(success=False, output=None, error=f"File not found: {file_path}")

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            lines = content.splitlines(keepends=True)
            search_lines = search_block.splitlines(keepends=True)
            
            # Normalize line endings for comparison
            search_lines_norm = [l.strip() for l in search_lines if l.strip()]
            
            if not search_lines_norm:
                 return ToolResult(success=False, output=None, error="Search block is empty or whitespace only")

            best_ratio = 0.0
            best_start = -1
            best_end = -1
            
            # Sliding window search
            window_size = len(search_lines)
            # Allow for some flexibility in window size
            min_window = max(1, int(window_size * 0.8))
            max_window = int(window_size * 1.2)
            
            for size in range(min_window, max_window + 1):
                for i in range(len(lines) - size + 1):
                    window = lines[i : i + size]
                    window_norm = [l.strip() for l in window if l.strip()]
                    
                    # Quick check on length
                    if abs(len(window_norm) - len(search_lines_norm)) > size * 0.3:
                        continue

                    matcher = difflib.SequenceMatcher(None, window_norm, search_lines_norm)
                    ratio = matcher.ratio()
                    
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_start = i
                        best_end = i + size

            if best_ratio < threshold:
                return ToolResult(
                    success=False, 
                    output=None, 
                    error=f"Could not find a match with sufficient similarity (best: {best_ratio:.2f}, threshold: {threshold}). Please check the search block."
                )

            # Apply replacement
            new_lines = lines[:best_start] + [replace_block] + lines[best_end:]
            if not replace_block.endswith('\n') and best_end < len(lines):
                 new_lines[best_start] = replace_block + '\n' # Ensure newline if replacing inline
            elif replace_block.endswith('\n'):
                 new_lines = lines[:best_start] + [replace_block] + lines[best_end:]
            else:
                 # Handle case where replace block doesn't have newline but we are inserting into list of lines
                 new_lines = lines[:best_start] + [replace_block + ('\n' if best_end < len(lines) else '')] + lines[best_end:]

            
            # Reconstruct content - handle potential list of strings vs single string
            new_content = "".join(new_lines)

            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                success=True,
                output=f"Successfully applied fuzzy edit with similarity {best_ratio:.2f}",
                metadata={
                    "similarity": best_ratio,
                    "start_line": best_start + 1,
                    "end_line": best_end + 1
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
