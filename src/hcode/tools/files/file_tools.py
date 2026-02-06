"""
File operation tools for Hcode.
Includes Read, Write, Edit, Glob tools similar to Hcode.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass

from hcode.tools.base.base_tool import BaseTool, ToolResult, ToolParameter, ToolCategory


class ReadTool(BaseTool):
    """
    View the contents of a file from the local filesystem.
    Text file usage:
    - The lines of the file are 1-indexed
    - The first time you read a new file the tool will enforce reading 800 lines to understand as much about the file as possible
    - The output of this tool call will be the file contents from StartLine to EndLine (inclusive)
    - You can view at most 800 lines at a time
    - To view the whole file do not pass StartLine or EndLine arguments
    Binary file usage:
    - Do not provide StartLine or EndLine arguments, this tool always returns the entire file (if manageable)
    """

    MAX_LINES = 800

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
                "StartLine", 
                "integer", 
                "Optional. Startline to view, 1-indexed as usual, inclusive. This value must be less than or equal to EndLine.",
                default=None
            ),
            ToolParameter(
                "EndLine", 
                "integer", 
                "Optional. Endline to view, 1-indexed as usual, inclusive. This value must be greater than or equal to StartLine.",
                default=None
            ),
            # Legacy parameters for backward compatibility
            ToolParameter("file_path", "string", "Alias for AbsolutePath", default=None),
            ToolParameter("path", "string", "Alias for AbsolutePath", default=None),
            ToolParameter("offset", "integer", "Alias for StartLine", default=None),
            ToolParameter("limit", "integer", "Implies EndLine (StartLine + limit)", default=None),
        ]
    
    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        # Check required: AbsolutePath (or file_path or path)
        if "AbsolutePath" not in kwargs and "file_path" not in kwargs and "path" not in kwargs:
             return False, "Missing required parameter: AbsolutePath (or file_path)"
        return True, None

    async def execute(
        self, 
        AbsolutePath: str = None, 
        StartLine: Optional[int] = None, 
        EndLine: Optional[int] = None,
        file_path: str = None,
        offset: int = None,
        limit: int = None,
        **kwargs
    ) -> ToolResult:
        """Read file contents with detailed control"""
        
        # 1. Parameter Normalization
        # Support legacy params if new ones aren't provided
        path_str = AbsolutePath or file_path or kwargs.get("path")
        if not path_str:
            return ToolResult(success=False, output=None, error="AbsolutePath (or file_path) is required")
            
        start = StartLine
        if start is None and offset is not None:
             start = offset
             
        end = EndLine
        if end is None and limit is not None and start is not None:
            end = start + limit
            
        try:
            path = Path(path_str)

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"File not found: {path_str}")

            if not path.is_file():
                return ToolResult(success=False, output=None, error=f"Not a file: {path_str}")

            # Check for binary file (simple heuristic)
            is_binary = False
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                     # Read first chunk to check for null bytes or encoding issues?
                     # For now, relying on encoding="utf-8", errors="ignore" makes it "text safe" mostly.
                     # But let's read distinct lines.
                     all_lines = f.readlines()
            except Exception as e:
                # If we really can't read it as text
                 return ToolResult(success=False, output=None, error=f"Error reading file (binary?): {str(e)}")

            total_lines = len(all_lines)
            
            # 2. Logic for viewing range
            # Rules:
            # - 1-indexed
            # - Max 800 lines
            # - If start/end not provided, view first 800.
            
            if start is None:
                start = 1
            if end is None:
                end = min(total_lines, start + self.MAX_LINES - 1)
                # If default view covers the whole file, great. If not, it's capped.
            
            # Validate Constraints
            if start < 1:
                start = 1
            if start > total_lines and total_lines > 0:
                 # Start beyond file?
                 return ToolResult(success=False, output=None, error=f"StartLine {start} is beyond end of file ({total_lines} lines)")
            
            if end > total_lines:
                end = total_lines
            
            if end < start:
                 return ToolResult(success=False, output=None, error=f"EndLine {end} cannot be less than StartLine {start}")

            count_requested = end - start + 1
            if count_requested > self.MAX_LINES:
                # Enforce limit
                end = start + self.MAX_LINES - 1
                truncated = True
                truncation_msg = f" (Request > {self.MAX_LINES} lines, truncated)"
            else:
                truncated = False
                truncation_msg = ""
            
            selected_lines = all_lines[start-1 : end]
            
            # 3. Format Output
            output_str = ""
            for idx, line in enumerate(selected_lines, start=start):
                # rstrip line to avoid double newlines if line has one, but keep indentation
                # actually, 'cat -n' style usually preserves the line end, but we are appending to string.
                # let's strip the newline char from the line itself for formatting.
                clean_line = line.rstrip('\n\r') 
                output_str += f"{idx:6d}\t{clean_line}\n"
                
            return ToolResult(
                success=True,
                output=output_str,
                metadata={
                    "file_path": str(path),
                    "total_lines": total_lines,
                    "lines_shown": len(selected_lines),
                    "start_line": start,
                    "end_line": end,
                    "truncated": truncated
                }
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class WriteTool(BaseTool):
    """
    Write content to files, creating them if they don't exist.
    Includes validation to verify the file was written correctly.

    Supports:
    - Full file writes (default)
    - Append mode for chunked/continuation writes
    - Partial content detection and recovery
    - Preview mode for reviewing changes before applying
    """

    # Class-level tracking of partial writes for continuation
    _partial_writes: Dict[str, str] = {}

    def __init__(
        self,
        root_dir: Optional[str] = None,
        preview_mode: bool = False,
        console: Optional[Any] = None,
    ):
        super().__init__()
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())
        self.preview_mode = preview_mode
        self._console = console
        self._pending_proposals: Dict[str, Any] = {}

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("TargetFile", "string", "Absolute path to write to", required=True),
            ToolParameter("CodeContent", "string", "Content to write", required=True),
            ToolParameter(
                "mode",
                "string",
                "Write mode: 'overwrite' (default) or 'append' for chunked writes",
                default="overwrite",
            ),
            ToolParameter(
                "is_partial",
                "boolean",
                "Indicates this is partial content that may be continued",
                default=False,
            ),
            ToolParameter(
                "preview",
                "boolean",
                "Preview changes before applying (requires approval)",
                default=False,
            ),
            # Legacy parameters
            ToolParameter("file_path", "string", "Alias for TargetFile", default=None),
            ToolParameter("content", "string", "Alias for CodeContent", default=None),
            ToolParameter("Content", "string", "Alias for CodeContent", default=None),
        ]

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        # Check required: TargetFile (or file_path)
        if "TargetFile" not in kwargs and "file_path" not in kwargs:
             return False, "Missing required parameter: TargetFile (or file_path)"
        
        # Check required: CodeContent (or content)
        if "CodeContent" not in kwargs and "content" not in kwargs and "Content" not in kwargs:
             return False, "Missing required parameter: CodeContent (or content)"
             
        return True, None

    def _validate_content(self, content: str, file_path: str) -> List[str]:
        """
        Validate content before writing.

        Returns list of warnings/issues found.
        """
        issues = []

        # Check for escaped newlines that should be actual newlines
        if "\\n" in content and "\n" not in content:
            issues.append(
                "Content contains escaped newlines (\\n) but no actual newlines - may be incorrectly escaped"
            )

        # Check for Python syntax issues (basic check for .py files)
        if file_path.endswith(".py"):
            # Check for obvious syntax issues
            if content.count("(") != content.count(")"):
                issues.append("Mismatched parentheses")
            if content.count("[") != content.count("]"):
                issues.append("Mismatched brackets")
            if content.count("{") != content.count("}"):
                issues.append("Mismatched braces")

            # Check for triple-quoted strings being properly closed
            triple_double = content.count('"""')
            triple_single = content.count("'''")
            if triple_double % 2 != 0:
                issues.append("Unclosed triple-double-quote string")
            if triple_single % 2 != 0:
                issues.append("Unclosed triple-single-quote string")

        return issues

    def _detect_truncation(self, content: str, file_path: str) -> tuple[bool, str]:
        """
        Detect if content appears to be truncated.

        Returns:
            Tuple of (is_truncated, reason)
        """
        if not content:
            return False, ""

        # Check for common truncation indicators
        truncation_indicators = [
            # Ends with incomplete syntax
            (content.rstrip().endswith(","), "ends with trailing comma"),
            (content.rstrip().endswith("{"), "ends with open brace"),
            (content.rstrip().endswith("["), "ends with open bracket"),
            (content.rstrip().endswith(":"), "ends with colon"),
            (content.rstrip().endswith("\\"), "ends with backslash"),
            # Unclosed brackets/braces (for code files)
            (content.count("{") > content.count("}"), "unclosed braces"),
            (content.count("[") > content.count("]"), "unclosed brackets"),
            (content.count("(") > content.count(")"), "unclosed parentheses"),
            # Unclosed quotes
            (content.count('"') % 2 == 1, "unclosed double quotes"),
            # Unclosed code blocks (for markdown)
            (content.count("```") % 2 == 1, "unclosed code block"),
            # HTML/XML unclosed tags (basic check)
            (
                file_path.endswith((".html", ".xml", ".htm"))
                and content.count("<") > content.count(">"),
                "unclosed HTML tags",
            ),
        ]

        for is_truncated, reason in truncation_indicators:
            if is_truncated:
                return True, reason

        return False, ""

    async def execute(
        self,
        TargetFile: str = None,
        CodeContent: str = None,
        mode: str = "overwrite",
        is_partial: bool = False,
        preview: bool = False,
        file_path: str = None,
        content: str = None,
        **kwargs,
    ) -> ToolResult:
        """
        Write content to file with validation and robustness features.

        Supports:
        - Standard overwrite mode
        - Append mode for chunked/continuation writes
        - Partial content detection and recovery
        - Preview mode for reviewing changes before applying
        """
        # Parameter Normalization
        file_path = TargetFile or file_path
        content = CodeContent or content or kwargs.get("Content")
        
        if not file_path:
            return ToolResult(success=False, output="", error="TargetFile (or file_path) is required")
        if content is None: # Content can be empty string
             return ToolResult(success=False, output="", error="CodeContent (or content) is required")
        try:
            # Check if preview mode is enabled (either instance or parameter)
            use_preview = preview or self.preview_mode

            if use_preview:
                return await self._execute_with_preview(file_path, content, mode, is_partial)

            path = Path(file_path)
            file_key = str(path.absolute())

            # Allow overwriting if mode is overwrite
            if path.exists() and mode == "overwrite":
                 # Check if the content is exactly the same (idempotent write) - strictly optional optimization
                 try:
                     with open(path, "r", encoding="utf-8", errors="ignore") as f:
                         current_content = f.read()
                     if current_content == content:
                         return ToolResult(
                            success=True, 
                            output=f"File {path} already has this content (no change made).",
                            metadata={"bytes_written": 0, "verified": True}
                         )
                 except:
                     pass

            # Handle append mode for chunked writes
            if mode == "append":
                # Append to existing file or partial write buffer
                existing_content = ""
                if path.exists():
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        existing_content = f.read()
                elif file_key in self._partial_writes:
                    existing_content = self._partial_writes[file_key]

                content = existing_content + content

            # Validate content before writing
            issues = self._validate_content(content, file_path)
            if issues:
                # Log warnings but still proceed
                import sys

                for issue in issues:
                    print(f"Warning: {issue}", file=sys.stderr)

            # Check for truncation
            is_truncated, truncation_reason = self._detect_truncation(content, file_path)
            if is_truncated:
                issues.append(f"Content may be truncated: {truncation_reason}")
                # Store partial content for potential continuation
                self._partial_writes[file_key] = content

            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            # Verify the file was written correctly
            try:
                with open(path, "r", encoding="utf-8") as f:
                    written_content = f.read()

                if written_content != content:
                    # Don't fail completely - file was written, just verification mismatch
                    issues.append("File verification: minor content mismatch detected")
            except Exception as verify_error:
                issues.append(f"File verification skipped: {verify_error}")

            # Count lines for info
            line_count = content.count("\n") + 1

            # Clear partial write buffer on successful full write
            if not is_partial and not is_truncated and file_key in self._partial_writes:
                del self._partial_writes[file_key]

            result_msg = f"File written successfully: {path}"
            if issues:
                result_msg += f"\nWarnings: {'; '.join(issues)}"

            if is_truncated:
                result_msg += f"\n\n⚠️ Content appears truncated ({truncation_reason}). You can continue with mode='append'."

            return ToolResult(
                success=True,
                output=result_msg,
                metadata={
                    "file_path": str(path),
                    "bytes_written": len(content.encode("utf-8")),
                    "line_count": line_count,
                    "warnings": issues if issues else None,
                    "verified": True,
                    "is_truncated": is_truncated,
                    "truncation_reason": truncation_reason if is_truncated else None,
                    "mode": mode,
                },
            )

        except Exception as e:
            # Even on error, try to save partial content
            try:
                if content:
                    self._partial_writes[str(Path(file_path).absolute())] = content
            except:
                pass
            return ToolResult(success=False, output=None, error=str(e))

    async def _execute_with_preview(
        self, file_path: str, content: str, mode: str = "overwrite", is_partial: bool = False
    ) -> ToolResult:
        """Execute write with preview mode - shows diff before applying"""
        from .diff_tools import ChangeProposal, ChangeOperation

        path = Path(file_path)

        # Get existing content
        old_content = ""
        if path.exists():
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                old_content = f.read()

        # Handle append mode
        if mode == "append":
            final_content = old_content + content
        else:
            final_content = content

        # Create proposal
        operation = ChangeOperation.WRITE if path.exists() else ChangeOperation.CREATE
        proposal = ChangeProposal(
            file_path=str(path),
            operation=operation,
            old_content=old_content,
            new_content=final_content,
        )

        # Compute diff and analyze
        proposal.compute_diff()
        proposal.analyze_safety()

        # Store proposal
        self._pending_proposals[proposal.id] = proposal

        # Display preview
        self._display_preview(proposal)

        return ToolResult(
            success=True,
            output=f"Preview generated for: {path}\nProposal ID: {proposal.id}\n"
            f"+{proposal.additions} additions, -{proposal.deletions} deletions\n"
            f"Use apply_proposal('{proposal.id}') to apply this change.",
            metadata={
                "proposal_id": proposal.id,
                "preview_mode": True,
                "file_path": str(path),
                "operation": operation.value,
                "additions": proposal.additions,
                "deletions": proposal.deletions,
                "warnings": len(proposal.safety_warnings),
                "has_critical": proposal.has_critical_warnings(),
            },
        )

    def _display_preview(self, proposal) -> None:
        """Display the change preview"""
        if not self._console:
            return

        try:
            from ..ui import DiffDisplay
            from rich.panel import Panel
            from rich.text import Text

            # Show diff
            diff_panel = DiffDisplay.render(
                filename=os.path.basename(proposal.file_path),
                old_content=proposal.old_content,
                new_content=proposal.new_content,
                context_lines=3,
                show_stats=True,
            )
            self._console.print(diff_panel)

            # Show warnings
            if proposal.safety_warnings:
                warning_text = Text()
                warning_text.append("\nSafety Warnings:\n", style="bold yellow")
                for w in proposal.safety_warnings:
                    style = {"info": "blue", "warning": "yellow", "critical": "red bold"}[w.level]
                    warning_text.append(f"  [{w.level.upper()}] ", style=style)
                    warning_text.append(f"{w.message}\n")
                self._console.print(warning_text)

        except ImportError:
            pass

    def get_pending_proposal(self, proposal_id: str):
        """Get a pending proposal by ID"""
        return self._pending_proposals.get(proposal_id)

    async def apply_proposal(self, proposal_id: str, force: bool = False) -> ToolResult:
        """Apply a pending proposal"""
        proposal = self._pending_proposals.get(proposal_id)
        if not proposal:
            return ToolResult(
                success=False, output=None, error=f"No pending proposal with ID: {proposal_id}"
            )

        if proposal.has_critical_warnings() and not force:
            return ToolResult(
                success=False,
                output=None,
                error="Critical warnings present. Use force=True to override.",
            )

        # Apply the change
        path = Path(proposal.file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            f.write(proposal.new_content)

        # Clean up
        del self._pending_proposals[proposal_id]

        return ToolResult(
            success=True,
            output=f"Change applied: {proposal.file_path} (+{proposal.additions}/-{proposal.deletions})",
            metadata={"applied": True, "proposal_id": proposal_id},
        )

    @classmethod
    def get_partial_content(cls, file_path: str) -> Optional[str]:
        """
        Get any partial content stored for a file path.

        This allows recovery of truncated writes.
        """
        file_key = str(Path(file_path).absolute())
        return cls._partial_writes.get(file_key)

    @classmethod
    def clear_partial_content(cls, file_path: str = None):
        """
        Clear partial content buffer.

        Args:
            file_path: Specific file to clear, or None to clear all
        """
        if file_path:
            file_key = str(Path(file_path).absolute())
            if file_key in cls._partial_writes:
                del cls._partial_writes[file_key]
        else:
            cls._partial_writes.clear()


class EditTool(BaseTool):
    """
    Edit files by replacing exact string matches.
    Uses old_string/new_string replacement for precise editing.
    Shows Claude Code-style diff display after changes.
    Supports preview mode for reviewing changes before applying.
    """

    def __init__(
        self,
        root_dir: Optional[str] = None,
        console: Optional[Any] = None,
        preview_mode: bool = False,
    ):
        super().__init__()
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())
        self._file_read_cache = {}
        self._console = console
        self.preview_mode = preview_mode
        self._pending_proposals: Dict[str, Any] = {}

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("TargetFile", "string", "Absolute path to file", required=True),
            ToolParameter("TargetContent", "string", "Exact string to replace", required=True),
            ToolParameter("ReplacementContent", "string", "Replacement string", required=True),
            ToolParameter("replace_all", "boolean", "Replace all occurrences", default=False),
            ToolParameter(
                "preview",
                "boolean",
                "Preview changes before applying (requires approval)",
                default=False,
            ),
            # Legacy parameters
            ToolParameter("file_path", "string", "Alias for TargetFile", default=None),
            ToolParameter("old_string", "string", "Alias for TargetContent", default=None),
            ToolParameter("new_string", "string", "Alias for ReplacementContent", default=None),
        ]

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        # Check required: TargetFile (or file_path)
        if "TargetFile" not in kwargs and "file_path" not in kwargs:
             return False, "Missing required parameter: TargetFile (or file_path)"

        # Check required: TargetContent (or old_string)
        if "TargetContent" not in kwargs and "old_string" not in kwargs:
             return False, "Missing required parameter: TargetContent (or old_string)"
             
        # Check required: ReplacementContent (or new_string)
        if "ReplacementContent" not in kwargs and "new_string" not in kwargs:
             return False, "Missing required parameter: ReplacementContent (or new_string)"
             
        return True, None

    def _show_diff(self, file_path: str, old_content: str, new_content: str) -> str:
        """Generate and optionally display diff"""
        try:
            from ..ui import DiffDisplay, console as styled_console

            # Use provided console or default
            display_console = self._console or styled_console

            # Render the diff panel
            diff_panel = DiffDisplay.render(
                filename=os.path.basename(file_path),
                old_content=old_content,
                new_content=new_content,
                context_lines=3,
                show_stats=True,
            )

            # Display the diff
            display_console.print(diff_panel)

            # Also return a text summary
            import difflib

            diff_lines = list(
                difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile="before",
                    tofile="after",
                    lineterm="",
                )
            )

            additions = sum(
                1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
            )
            deletions = sum(
                1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
            )

            return f"+{additions} -{deletions}"

        except ImportError:
            # Fallback if CLI styles not available
            return "diff displayed"
        except Exception as e:
            return f"diff error: {e}"

    def _fuzzy_find(self, content: str, target: str) -> tuple[bool, str, int]:
        """
        Attempt to find target in content using fuzzy matching.
        Strategy: 
        1. Strip target to ignore indentation/newlines at ends.
        2. Split by whitespace and rejoin with \s+ to allow flexible whitespace.
        
        Returns:
            Tuple of (found, matched_string, count_matches)
        """
        import re
        
        # 1. Handling Indentation/Line Breaks issues:
        # Strip the target string. This allows finding the block even if 
        # the user provided extra indentation or newlines at the start/end
        # that aren't strictly part of the content signature.
        clean_target = target.strip()
        if not clean_target:
             return False, "", 0
             
        # 2. Flexible Whitespace:
        # Split by whitespace sequences to handle "  " vs " " vs "\n" mismatch
        parts = re.split(r"\s+", clean_target)
        
        # Escape each part to treat as literal
        escaped_parts = [re.escape(p) for p in parts]
        
        # Join with \s+ pattern (one or more whitespace characters)
        # This matches: "a b" -> "a\s+b" -> matching "a  b", "a\nb", etc.
        fuzzy_pattern_str = r"\s+".join(escaped_parts)
        
        # Compile pattern
        try:
            pattern = re.compile(fuzzy_pattern_str, re.DOTALL)
            matches = list(pattern.finditer(content))
            
            if not matches:
                return False, "", 0
                
            # If unique match found, return the exact string that matched
            if len(matches) == 1:
                return True, matches[0].group(0), 1
                
            return True, "", len(matches)
            
        except re.error:
            # Fallback for complex patterns or regex errors
            return False, "", 0

    async def execute(
        self,
        TargetFile: str = None,
        TargetContent: str = None,
        ReplacementContent: str = None,
        replace_all: bool = False,
        preview: bool = False,
        file_path: str = None,
        old_string: str = None,
        new_string: str = None,
        **kwargs,  # Accept and ignore unknown parameters for model compatibility
    ) -> ToolResult:
        """Edit file by replacing TargetContent with ReplacementContent"""
        # Parameter Normalization
        final_path = TargetFile or file_path
        final_old = TargetContent or old_string
        final_new = ReplacementContent or new_string # Can be empty
        
        if not final_path:
            return ToolResult(success=False, output="", error="TargetFile (or file_path) is required")
        if final_old is None:
            return ToolResult(success=False, output="", error="TargetContent (or old_string) is required")
        if final_new is None:
            return ToolResult(success=False, output="", error="ReplacementContent (or new_string) is required")

        # Map to legacy variables for body compatibility
        file_path = final_path
        old_string = final_old
        new_string = final_new

        try:
            # Check if preview mode is enabled
            use_preview = preview or self.preview_mode

            if use_preview:
                return await self._execute_with_preview(
                    final_path, final_old, final_new, replace_all
                )

            path = Path(final_path)

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"File not found: {final_path}")

            # Read file
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Store original content for diff
            original_content = content
            
            # Match state tracking
            match_found = False
            actual_old_string = old_string

            # 1. Try exact match
            if old_string in content:
                match_found = True
            else:
                # 2. Try fuzzy match (fallback)
                fuzzy_found, fuzzy_match, match_count = self._fuzzy_find(content, old_string)
                if fuzzy_found:
                    if match_count == 1:
                        match_found = True
                        actual_old_string = fuzzy_match
                        # Log that we used fuzzy matching
                        # (Ideally we'd warn the user, but for now we proceed if unique)
                    elif match_count > 1:
                        return ToolResult(
                            success=False,
                            output=None,
                            error=f"String not found exactly, and fuzzy match found {match_count} occurrences. Please be more specific or use replace_all=True with exact string.",
                        )
            
            if not match_found:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"String not found in file (tried exact and fuzzy match): {old_string[:100]}...",
                )

            # Check if replacement would be ambiguous
            if not replace_all and content.count(actual_old_string) > 1:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"String appears {content.count(actual_old_string)} times. Use replace_all=True or provide more context.",
                )

            # Perform replacement
            if replace_all:
                if actual_old_string != old_string:
                     # If using fuzzy match, we can't easily replace-all safely without regex logic for all occurrences
                     # For now, restrict fuzzy-match to single replacement or demand exact string for global replace
                     return ToolResult(
                        success=False,
                        output=None,
                        error="Fuzzy matching is only supported for single replacements. Please verify the exact string for global replacement.",
                     )
                new_content = content.replace(actual_old_string, new_string)
                replacements = content.count(actual_old_string)
            else:
                new_content = content.replace(actual_old_string, new_string, 1)
                replacements = 1

            # Write back
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # Show diff
            diff_summary = self._show_diff(str(path), original_content, new_content)
            
            return_msg = f"File edited successfully. Replaced {replacements} occurrence(s). ({diff_summary})"
            if actual_old_string != old_string:
                return_msg += "\nNote: Used fuzzy matching to ignore whitespace differences."

            return ToolResult(
                success=True,
                output=return_msg,
                metadata={
                    "file_path": str(path),
                    "replacements": replacements,
                    "old_length": len(actual_old_string),
                    "new_length": len(new_string),
                    "diff_summary": diff_summary,
                    "fuzzy_match": actual_old_string != old_string
                },
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    async def _execute_with_preview(
        self, file_path: str, old_string: str, new_string: str, replace_all: bool = False
    ) -> ToolResult:
        """Execute edit with preview mode - shows diff before applying"""
        from .diff_tools import ChangeProposal, ChangeOperation

        path = Path(file_path)

        if not path.exists():
            return ToolResult(success=False, output=None, error=f"File not found: {file_path}")

        # Read file
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Store original content
        original_content = content

        # Check if old_string exists
        if old_string not in content:
            return ToolResult(
                success=False, output=None, error=f"String not found in file: {old_string[:100]}..."
            )

        # Check if replacement would be ambiguous
        if not replace_all and content.count(old_string) > 1:
            return ToolResult(
                success=False,
                output=None,
                error=f"String appears {content.count(old_string)} times. Use replace_all=True or provide more context.",
            )

        # Perform replacement (in memory only)
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replacements = content.count(old_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            replacements = 1

        # Create proposal
        proposal = ChangeProposal(
            file_path=str(path),
            operation=ChangeOperation.EDIT,
            old_content=original_content,
            new_content=new_content,
            old_string=old_string,
            new_string=new_string,
            replace_all=replace_all,
        )

        # Compute diff and analyze
        proposal.compute_diff()
        proposal.analyze_safety()

        # Store proposal
        self._pending_proposals[proposal.id] = proposal

        # Display preview
        self._display_preview(proposal)

        return ToolResult(
            success=True,
            output=f"Preview generated for: {path}\nProposal ID: {proposal.id}\n"
            f"Replacing {replacements} occurrence(s)\n"
            f"+{proposal.additions} additions, -{proposal.deletions} deletions\n"
            f"Use apply_proposal('{proposal.id}') to apply this change.",
            metadata={
                "proposal_id": proposal.id,
                "preview_mode": True,
                "file_path": str(path),
                "operation": ChangeOperation.EDIT.value,
                "replacements": replacements,
                "additions": proposal.additions,
                "deletions": proposal.deletions,
                "warnings": len(proposal.safety_warnings),
                "has_critical": proposal.has_critical_warnings(),
            },
        )

    def _display_preview(self, proposal) -> None:
        """Display the change preview"""
        if not self._console:
            return

        try:
            from ..ui import DiffDisplay
            from rich.text import Text

            # Show diff
            diff_panel = DiffDisplay.render(
                filename=os.path.basename(proposal.file_path),
                old_content=proposal.old_content,
                new_content=proposal.new_content,
                context_lines=3,
                show_stats=True,
            )
            self._console.print(diff_panel)

            # Show warnings
            if proposal.safety_warnings:
                warning_text = Text()
                warning_text.append("\nSafety Warnings:\n", style="bold yellow")
                for w in proposal.safety_warnings:
                    style = {"info": "blue", "warning": "yellow", "critical": "red bold"}[w.level]
                    warning_text.append(f"  [{w.level.upper()}] ", style=style)
                    warning_text.append(f"{w.message}\n")
                self._console.print(warning_text)

        except ImportError:
            pass

    def get_pending_proposal(self, proposal_id: str):
        """Get a pending proposal by ID"""
        return self._pending_proposals.get(proposal_id)

    async def apply_proposal(self, proposal_id: str, force: bool = False) -> ToolResult:
        """Apply a pending proposal"""
        proposal = self._pending_proposals.get(proposal_id)
        if not proposal:
            return ToolResult(
                success=False, output=None, error=f"No pending proposal with ID: {proposal_id}"
            )

        if proposal.has_critical_warnings() and not force:
            return ToolResult(
                success=False,
                output=None,
                error="Critical warnings present. Use force=True to override.",
            )

        # Apply the change
        path = Path(proposal.file_path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(proposal.new_content)

        # Show diff after applying
        diff_summary = self._show_diff(str(path), proposal.old_content, proposal.new_content)

        # Clean up
        del self._pending_proposals[proposal_id]

        return ToolResult(
            success=True,
            output=f"Change applied: {proposal.file_path} (+{proposal.additions}/-{proposal.deletions}) ({diff_summary})",
            metadata={"applied": True, "proposal_id": proposal_id},
        )


class MultiEditTool(BaseTool):
    """
    Makes multiple sequential edits to a single file.
    More efficient than multiple Edit tool calls.
    Shows Claude Code-style diff display after all changes.
    """

    def __init__(self, root_dir: Optional[str] = None, console: Optional[Any] = None):
        super().__init__()
        self.name = "MultiEdit"
        self.category = ToolCategory.FILE_OPERATION
        self.root_dir = Path(root_dir or os.getcwd())
        self._console = console

    def _show_diff(self, file_path: str, old_content: str, new_content: str) -> str:
        """Generate and optionally display diff"""
        try:
            from ..ui import DiffDisplay, console as styled_console

            display_console = self._console or styled_console

            diff_panel = DiffDisplay.render(
                filename=os.path.basename(file_path),
                old_content=old_content,
                new_content=new_content,
                context_lines=3,
                show_stats=True,
            )

            display_console.print(diff_panel)

            import difflib

            diff_lines = list(
                difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    lineterm="",
                )
            )

            additions = sum(
                1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
            )
            deletions = sum(
                1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
            )

            return f"+{additions} -{deletions}"

        except ImportError:
            return "diff displayed"
        except Exception as e:
            return f"diff error: {e}"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path", type="string", description="Absolute path to file", required=True
            ),
            ToolParameter(
                name="edits",
                type="array",
                description="Array of edit objects with old_string, new_string, and optional replace_all",
                required=True,
            ),
        ]

    async def execute(self, file_path: str, edits: List[Dict[str, Any]], **kwargs) -> ToolResult:
        """Apply multiple edits to a file"""
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(success=False, output=None, error=f"File not found: {file_path}")

            # Read file once
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            total_replacements = 0
            edit_results = []

            # Apply each edit sequentially
            for i, edit in enumerate(edits):
                old_string = edit.get("old_string")
                new_string = edit.get("new_string")
                replace_all = edit.get("replace_all", False)

                if not old_string or new_string is None:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Edit {i+1}: old_string and new_string are required",
                    )

                # Check if old_string exists
                if old_string not in content:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Edit {i+1}: String not found in file: {old_string[:100]}...",
                    )

                # Check if replacement would be ambiguous
                count = content.count(old_string)
                if not replace_all and count > 1:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Edit {i+1}: String appears {count} times. Use replace_all=true or provide more context.",
                    )

                # Perform replacement
                if replace_all:
                    content = content.replace(old_string, new_string)
                    replacements = count
                else:
                    content = content.replace(old_string, new_string, 1)
                    replacements = 1

                total_replacements += replacements
                edit_results.append(
                    {
                        "edit_number": i + 1,
                        "replacements": replacements,
                        "old_length": len(old_string),
                        "new_length": len(new_string),
                    }
                )

            # Write back only if changes were made
            if content != original_content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Show diff
                diff_summary = self._show_diff(str(path), original_content, content)

                return ToolResult(
                    success=True,
                    output=f"File edited successfully. Applied {len(edits)} edits with {total_replacements} total replacements. ({diff_summary})",
                    metadata={
                        "file_path": str(path),
                        "total_edits": len(edits),
                        "total_replacements": total_replacements,
                        "edit_results": edit_results,
                        "diff_summary": diff_summary,
                    },
                )
            else:
                return ToolResult(
                    success=True,
                    output="No changes were needed.",
                    metadata={"file_path": str(path), "total_edits": 0, "total_replacements": 0},
                )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class GlobTool(BaseTool):
    """
    Find files matching glob patterns.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("Pattern", "string", "Glob pattern (e.g., '**/*.py')", required=True),
            ToolParameter("SearchDirectory", "string", "Directory to search in", default=None),
            # Legacy parameters
            ToolParameter("pattern", "string", "Alias for Pattern", default=None),
            ToolParameter("path", "string", "Alias for SearchDirectory", default=None),
        ]
        
    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        # Check required: Pattern (or pattern)
        if "Pattern" not in kwargs and "pattern" not in kwargs:
             return False, "Missing required parameter: Pattern (or pattern)"
        return True, None

    async def execute(self, Pattern: str = None, SearchDirectory: str = None, pattern: str = None, path: Optional[str] = None, **kwargs) -> ToolResult:
        """Find files matching pattern"""
        # Parameter Normalization
        final_pattern = Pattern or pattern
        final_path = SearchDirectory or path

        if not final_pattern:
             return ToolResult(success=False, output="", error="Pattern (or pattern) is required")

        try:
            search_dir = Path(final_path) if final_path else self.root_dir

            if not search_dir.exists():
                return ToolResult(
                    success=False, output=None, error=f"Directory not found: {search_dir}"
                )

            # Handle absolute glob patterns (e.g. D:\path\to\*.py)
            if Path(final_pattern).is_absolute():
                # Use os.path.split to handle robust splitting including wildcards
                import glob as glob_module
                if glob_module.has_magic(final_pattern):
                    # It's an absolute path with magic
                    # Try to find the base directory
                    base_part = final_pattern
                    while glob_module.has_magic(base_part):
                         base_part = os.path.dirname(base_part)
                    
                    if base_part and os.path.exists(base_part):
                        search_dir = Path(base_part)
                        # Construct relative pattern
                        full_pat = Path(final_pattern)
                        try:
                            final_pattern = str(full_pat.relative_to(search_dir))
                        except ValueError:
                             # Fallback if relative conversion fails
                             pass
                else:
                    # No magic, just an absolute path
                    p = Path(final_pattern)
                    search_dir = p.parent
                    final_pattern = p.name

            # Fallback path logic
            if not search_dir.exists():
                return ToolResult(
                    success=False, output=None, error=f"Directory not found: {search_dir}"
                )

            # Find matching files
            matches = list(search_dir.glob(final_pattern))

            # Sort by modification time (most recent first)
            matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            # Convert to relative paths
            relative_matches = []
            for match in matches:
                try:
                    rel = match.relative_to(self.root_dir)
                    relative_matches.append(str(rel))
                except ValueError:
                    relative_matches.append(str(match))

            if relative_matches:
                output = "\n".join(relative_matches)
            else:
                # No matches - provide helpful hints
                # Find subdirectories that might be relevant
                subdirs = []
                try:
                    for item in search_dir.iterdir():
                        if item.is_dir() and not item.name.startswith('.'):
                            # Look for CI/config related directories
                            name_lower = item.name.lower()
                            if any(keyword in name_lower for keyword in [
                                'ci', 'config', 'github', 'gitlab', 'zuul', 'jenkins',
                                'workflow', 'pipeline', 'azure', 'build'
                            ]):
                                subdirs.append(item.name)
                except Exception:
                    pass
                
                output = "No matches found"
                if subdirs:
                    output += f"\n\nHINT: Found potentially relevant directories: {', '.join(subdirs)}"
                    output += "\nTry searching within these directories using the 'path' parameter."

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "pattern": final_pattern,
                    "search_dir": str(search_dir),
                    "matches": len(relative_matches),
                },
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))



class GrepTool(BaseTool):
    """
    Search for patterns in files using ripgrep-style interface.
    """

    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()
        self.category = ToolCategory.SEARCH
        self.root_dir = Path(root_dir or os.getcwd())

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("Query", "string", "Search pattern (regex)", required=True),
            ToolParameter("SearchPath", "string", "File or directory to search", required=True),
            ToolParameter("Includes", "array", "Glob patterns to filter files", default=None),
            ToolParameter("MatchPerLine", "boolean", "Show each matching line", default=False),
            # Legacy parameters
            ToolParameter("pattern", "string", "Alias for Query", default=None),
            ToolParameter("path", "string", "Alias for SearchPath", default=None),
            ToolParameter("glob", "string", "Alias for Includes", default=None),
            
            ToolParameter("case_insensitive", "boolean", "Case insensitive search", default=False),
            ToolParameter(
                "output_mode",
                "string",
                "Output mode: content, files_with_matches, count",
                default="files_with_matches",
            ),
            ToolParameter("context_before", "integer", "Lines of context before match", default=0),
            ToolParameter("context_after", "integer", "Lines of context after match", default=0),
        ]

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate parameters allowing for strict aliases"""
        # Check required: Query (or pattern)
        if "Query" not in kwargs and "pattern" not in kwargs:
             return False, "Missing required parameter: Query (or pattern)"
        
        # Check required: SearchPath (or path)
        if "SearchPath" not in kwargs and "path" not in kwargs:
             return False, "Missing required parameter: SearchPath (or path)"
             
        return True, None

    async def execute(
        self,
        Query: str = None,
        SearchPath: str = None,
        Includes: List[str] = None,
        MatchPerLine: bool = False,
        pattern: str = None,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        case_insensitive: bool = False,
        output_mode: str = "files_with_matches",
        context_before: int = 0,
        context_after: int = 0,
        **kwargs,  # Accept and ignore unknown parameters for model compatibility
    ) -> ToolResult:
        """Search for pattern in files"""
        import re

        # Parameter Normalization
        final_query = Query or pattern
        final_path = SearchPath or path
        final_includes = Includes or glob
        
        if not final_query:
             return ToolResult(success=False, output="", error="Query (or pattern) is required")
        
        # Handle MatchPerLine override
        if MatchPerLine:
            output_mode = "content"
        
        # SearchPath is technically optional in legacy, but prompt requires it. 
        # We'll use root_dir if not provided, for legacy support.
        
        try:
            search_path = Path(final_path) if final_path else self.root_dir

            # Handle glob as list or string (model may pass list)
            if isinstance(final_includes, list):
                final_includes = final_includes[0] if final_includes else None  # Use first pattern if list
            
            # Handle absolute glob patterns (e.g. D:\path\to\*.py)
            if final_includes and Path(final_includes).is_absolute():
                glob_path = Path(final_includes)
                search_path = glob_path.parent
                final_includes = glob_path.name
            
            # Compile regex pattern
            flags = re.IGNORECASE if case_insensitive else 0
            regex = re.compile(final_query, flags)

            results = []

            # Determine files to search
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                # Use glob pattern or search all files
                if final_includes:
                    files_to_search = list(search_path.glob(final_includes))
                else:
                    files_to_search = [f for f in search_path.rglob("*") if f.is_file()]

            # Search in files
            for file_path in files_to_search:
                # Skip binary files and common ignore patterns
                if any(part.startswith(".") for part in file_path.parts):
                    continue
                if "node_modules" in file_path.parts or "__pycache__" in file_path.parts:
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    matches_in_file = []
                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            matches_in_file.append((line_num, line.rstrip()))

                    if matches_in_file:
                        rel_path = (
                            file_path.relative_to(self.root_dir)
                            if file_path.is_relative_to(self.root_dir)
                            else file_path
                        )

                        if output_mode == "files_with_matches":
                            results.append(str(rel_path))
                        elif output_mode == "count":
                            results.append(f"{rel_path}:{len(matches_in_file)}")
                        elif output_mode == "content":
                            for line_num, line in matches_in_file:
                                results.append(f"{rel_path}:{line_num}:{line}")

                except Exception:
                    continue

            if results:
                output = "\n".join(results)
            else:
                # No matches - provide helpful hints with regex patterns
                hints = []
                
                # Analyze the pattern to suggest alternatives
                # Extract potential keywords from the pattern
                import re as re_module
                # Remove regex special chars to get base words
                clean_pattern = re_module.sub(r'[.*+?^${}()|\[\]\\]', ' ', final_query)
                words = [w for w in clean_pattern.replace('_', ' ').replace('-', ' ').split() if len(w) > 2]
                
                if len(words) >= 2:
                    # Suggest regex with wildcards between words
                    hints.append(f"Try regex pattern: {words[0]}.*{words[1]}")
                    hints.append(f"Try reversed: {words[1]}.*{words[0]}")
                    hints.append(f"Try hyphenated: {words[0]}-{words[1]} or {words[1]}-{words[0]}")
                elif len(words) == 1:
                    hints.append(f"Try broader search with just: {words[0]}")
                
                # Suggest case-insensitive if not already
                if not case_insensitive:
                    hints.append("Try with case_insensitive=True")
                
                # Look for config directories
                subdirs = []
                try:
                    for item in search_path.iterdir():
                        if item.is_dir() and not item.name.startswith('.'):
                            name_lower = item.name.lower()
                            if any(keyword in name_lower for keyword in [
                                'ci', 'config', 'github', 'gitlab', 'zuul', 'jenkins',
                                'workflow', 'pipeline', 'azure', 'build'
                            ]):
                                subdirs.append(item.name)
                except Exception:
                    pass
                
                if subdirs:
                    hints.append(f"Try searching in: {', '.join(subdirs)}")
                
                output = "No matches found"
                if hints:
                    output += "\n\nHINTS (try these patterns):\n- " + "\n- ".join(hints)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "pattern": final_query,
                    "matches": len(results) if output_mode == "files_with_matches" else sum(len(r.split('\n')) for r in results),
                    "output_mode": output_mode,
                },
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


