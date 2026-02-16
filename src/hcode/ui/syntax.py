"""
HCode Custom Syntax Highlighting
Cyberpunk-themed code rendering.
"""

import os
from typing import Optional, List, Dict

from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from hcode.ui.theme import get_palette

# ═══════════════════════════════════════════════════════════════════════
# CUSTOM SYNTAX THEMES
# ═══════════════════════════════════════════════════════════════════════

# Cyberpunk color scheme mapping (for reference)
CYBERPUNK_TOKENS = {
    "default": "#f8f8f2",
    "whitespace": "",
    "comment": "#6272a4",
    "comment.preproc": "#ff79c6",
    "keyword": "#ff79c6",
    "keyword.declaration": "#8be9fd",
    "keyword.namespace": "#ff79c6",
    "keyword.type": "#8be9fd",
    "operator": "#ff79c6",
    "name": "#f8f8f2",
    "name.attribute": "#50fa7b",
    "name.builtin": "#8be9fd",
    "name.class": "#50fa7b",
    "name.constant": "#bd93f9",
    "name.decorator": "#50fa7b",
    "name.exception": "#ff5555",
    "name.function": "#50fa7b",
    "name.label": "#8be9fd",
    "name.tag": "#ff79c6",
    "name.variable": "#f8f8f2",
    "string": "#f1fa8c",
    "string.escape": "#ff79c6",
    "string.regex": "#f1fa8c",
    "number": "#bd93f9",
    "punctuation": "#f8f8f2",
    "generic.deleted": "#ff5555",
    "generic.inserted": "#50fa7b",
    "generic.heading": "#f8f8f2",
    "generic.error": "#ff5555",
    "error": "#ff5555",
}

# ═══════════════════════════════════════════════════════════════════════
# LANGUAGE DETECTION
# ═══════════════════════════════════════════════════════════════════════

EXTENSION_TO_LANGUAGE: Dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".pyx": "cython",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".scala": "scala",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".fish": "fish",
    ".ps1": "powershell",
    ".sql": "sql",
    ".xml": "xml",
    ".svg": "xml",
    ".r": "r",
    ".swift": "swift",
    ".lua": "lua",
    ".pl": "perl",
    ".vim": "vim",
    ".dockerfile": "dockerfile",
    ".makefile": "makefile",
    ".cmake": "cmake",
    ".tf": "terraform",
    ".hcl": "hcl",
    ".vue": "vue",
    ".svelte": "svelte",
    ".elm": "elm",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".clj": "clojure",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".fs": "fsharp",
}


def detect_language(filename: str) -> str:
    """Detect language from filename."""
    ext = os.path.splitext(filename.lower())[1]
    return EXTENSION_TO_LANGUAGE.get(ext, "text")


# ═══════════════════════════════════════════════════════════════════════
# CYBER SYNTAX HIGHLIGHTER
# ═══════════════════════════════════════════════════════════════════════


class CyberSyntax:
    """Cyberpunk-styled syntax highlighter."""

    def __init__(
            self,
            theme: str = "dracula",
            line_numbers: bool = True,
            word_wrap: bool = True,
            tab_size: int = 4,
            background_color: Optional[str] = None,
    ):
        self.theme = theme
        self.line_numbers = line_numbers
        self.word_wrap = word_wrap
        self.tab_size = tab_size
        self.background_color = background_color

    def highlight(
            self,
            code: str,
            language: str = "python",
            title: Optional[str] = None,
            show_path: bool = False,
            path: Optional[str] = None,
            start_line: int = 1,
            highlight_lines: Optional[List[int]] = None,
    ) -> Panel:
        """Highlight code with cyberpunk styling."""
        palette = get_palette()

        syntax = Syntax(
            code,
            language,
            theme=self.theme,
            line_numbers=self.line_numbers,
            word_wrap=self.word_wrap,
            tab_size=self.tab_size,
            background_color=self.background_color or palette.bg_dark,
            start_line=start_line,
            highlight_lines=set(highlight_lines) if highlight_lines else None,
        )

        # Build title
        panel_title = None
        if title or (show_path and path):
            panel_title = Text()
            panel_title.append("◈ ", style=f"bold {palette.secondary}")

            if title:
                panel_title.append(title, style=f"bold {palette.primary}")
            elif path:
                panel_title.append(path, style=f"bold {palette.primary} italic")

            panel_title.append(f"  [{language}]", style=palette.text_muted)

        return Panel(
            syntax,
            title=panel_title,
            border_style=palette.border_default,
            padding=(1, 2),
            expand=True,
        )

    def inline_code(self, code: str) -> Text:
        """Format inline code snippet."""
        palette = get_palette()

        text = Text()
        text.append("`", style=f"bold {palette.text_muted}")
        text.append(code, style=f"bold {palette.primary} on {palette.bg_medium}")
        text.append("`", style=f"bold {palette.text_muted}")

        return text


# ═══════════════════════════════════════════════════════════════════════
# DIFF HIGHLIGHTER
# ═══════════════════════════════════════════════════════════════════════


class DiffHighlighter:
    """Highlight code diffs with additions/deletions."""

    def __init__(self):
        pass

    def highlight_inline_diff(
            self,
            old_text: str,
            new_text: str,
    ) -> Text:
        """Highlight inline diff (old → new)."""
        palette = get_palette()

        text = Text()
        text.append(old_text, style=f"strike {palette.diff_removed}")
        text.append(" → ", style=palette.text_muted)
        text.append(new_text, style=f"bold {palette.diff_added}")

        return text


# ═══════════════════════════════════════════════════════════════════════
# CODE BLOCK FORMATTER
# ═══════════════════════════════════════════════════════════════════════


class CodeBlock:
    """Format code blocks with various styles."""

    @staticmethod
    def create(
            code: str,
            language: str = "python",
            title: Optional[str] = None,
            theme: str = "dracula",
            line_numbers: bool = True,
    ) -> Panel:
        """Create a styled code block."""
        highlighter = CyberSyntax(theme=theme, line_numbers=line_numbers)
        return highlighter.highlight(code, language, title=title)


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def highlight_code(
        code: str,
        language: str = "python",
        title: Optional[str] = None,
        line_numbers: bool = True,
) -> Panel:
    """Quick function to highlight code."""
    highlighter = CyberSyntax(line_numbers=line_numbers)
    return highlighter.highlight(code, language, title=title)


def highlight_file(
        filepath: str,
        title: Optional[str] = None,
        line_numbers: bool = True,
) -> Panel:
    """Highlight code from a file."""
    language = detect_language(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    display_title = title or os.path.basename(filepath)
    return highlight_code(code, language, title=display_title, line_numbers=line_numbers)


def inline_code(code: str) -> Text:
    """Format inline code."""
    highlighter = CyberSyntax()
    return highlighter.inline_code(code)


def diff_text(old: str, new: str) -> Text:
    """Create inline diff display."""
    highlighter = DiffHighlighter()
    return highlighter.highlight_inline_diff(old, new)
