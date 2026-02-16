from typing import List

from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.style import Style
from rich.text import Text

from hcode.ui.theme import get_palette

# ═══════════════════════════════════════════════════════════════════════
# MAIN LOGO VARIANTS
# ═══════════════════════════════════════════════════════════════════════

LOGO_CYBER = r"""
██╗  ██╗ ██████╗ ██████╗ ██████╗ ███████╗
██║  ██║██╔════╝██╔═══██╗██╔══██╗██╔════╝
███████║██║     ██║   ██║██║  ██║█████╗
██╔══██║██║     ██║   ██║██║  ██║██╔══╝
██║  ██║╚██████╗╚██████╔╝██████╔╝███████╗
╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
"""

LOGO_NEON = r"""
    ▄█    █▄     ▄████████  ▄██████▄  ████████▄     ▄████████
   ███    ███   ███    ███ ███    ███ ███   ▀███   ███    ███
   ███    ███   ███    █▀  ███    ███ ███    ███   ███    █▀
  ▄███▄▄▄▄███▄▄ ███        ███    ███ ███    ███  ▄███▄▄▄
 ▀▀███▀▀▀▀███▀  ███        ███    ███ ███    ███ ▀▀███▀▀▀
   ███    ███   ███    █▄  ███    ███ ███    ███   ███    █▄
   ███    ███   ███    ███ ███    ███ ███   ▄███   ███    ███
   ███    █▀    ████████▀   ▀██████▀  ████████▀    ██████████
"""

LOGO_MINIMAL = r"""
 _   _  ____  ___  ____  _____
| | | |/ ___|/ _ \|  _ \| ____|
| |_| | |   | | | | | | |  _|
|  _  | |___| |_| | |_| | |___
|_| |_|\____|\___/|____/|_____|
"""

LOGO_GLITCH = r"""
╦ ╦┌─┐┌─┐┌┬┐┌─┐  ╔═╗╦  ╦
╠═╣│  │ │ ││├┤   ╠═╣║  ║
╩ ╩└─┘└─┘─┴┘└─┘  ╩ ╩╩═╝╩
"""

LOGO_FUTURISTIC = r"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ▄▄   ▄▄ ▄▄▄▄▄▄▄ ▄▄▄▄▄▄▄ ▄▄▄▄▄▄  ▄▄▄▄▄▄▄    ▄▄▄▄▄▄ ▄▄▄▄▄▄▄  ║
║  █  █▄█  █       █       █      ██       █  █      █       █ ║
║  █       █       █   ▄   █  ▄    █    ▄▄▄█  █  ▄   █   ▄   █ ║
║  █   ▄   █     ▄▄█  █ █  █ █ █   █   █▄▄▄   █ █▄█  █  █ █  █ ║
║  █  █ █  █    █  █  █▄█  █ █▄█   █    ▄▄▄█  █      █  █▄█  █ ║
║  █  █▄█  █    █▄▄█       █       █   █▄▄▄   █  ▄   █       █ ║
║  █▄▄▄▄▄▄▄█▄▄▄▄▄▄▄█▄▄▄▄▄▄▄█▄▄▄▄▄▄██▄▄▄▄▄▄▄█  █▄█ █▄▄█▄▄▄▄▄▄▄█ ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

LOGO_SMALL = r"""
╦ ╦╔═╗╔═╗╔╦╗╔═╗
╠═╣║  ║ ║ ║║║╣
╩ ╩╚═╝╚═╝═╩╝╚═╝
"""

LOGO_TECH = r"""
┌─┐┌─┐┌┬┐┌─┐  ┬ ┬┌─┐┌─┐┌┬┐┌─┐
│  │ │ │││├┤   ├─┤│  │ │ ││├┤
└─┘└─┘─┴┘└─┘  ┴ ┴└─┘└─┘─┴┘└─┘
"""

LOGO_BLOCK = r"""
█░█ █▀▀ █▀█ █▀▄ █▀▀
█▀█ █▄▄ █▄█ █▄▀ ██▄
"""

LOGO_DOTS = r"""
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⡟⠛⠛⠛⠛⠛⠛⠛⠛⣿⣿⣿⣿⣿⡟⠛⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⡇⠀⢠⣶⣶⣶⣶⡆⠀⣿⣿⣿⣿⡏⠀⣴⠀⢹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⡇⠀⢸⣿⣿⣿⣿⡇⠀⣿⣿⣿⣿⠁⣼⣿⡆⠀⣿⣿⡿⠿⠿⣿⣿⣿⣿⣿
⣿⣿⡇⠀⢸⣿⣿⣿⣿⡇⠀⣿⣿⣿⣿⠀⣿⣿⡇⠀⣿⡏⠀⣶⡄⠈⢿⣿⣿⣿
⣿⣿⣧⣀⣸⣿⣿⣿⣿⣇⣀⣿⣿⣿⣿⣆⠘⣿⠇⣰⣿⡇⠀⣿⡇⠀⢸⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣤⣾⣿⣿⣿⣶⣿⣷⣶⣿⣿⣿⣿
"""


# ═══════════════════════════════════════════════════════════════════════
# GRADIENT TEXT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def create_gradient_text(text: str, colors: List[str]) -> Text:
    """Create text with gradient colors across characters."""
    result = Text()
    lines = text.split("\n")

    for line in lines:
        if not line.strip():
            result.append("\n")
            continue

        for i, char in enumerate(line):
            if char.strip():  # Only color non-whitespace
                color_index = int((i / max(len(line), 1)) * (len(colors) - 1))
                color = colors[min(color_index, len(colors) - 1)]
                result.append(char, style=Style(color=color, bold=True))
            else:
                result.append(char)
        result.append("\n")

    return result


# ═══════════════════════════════════════════════════════════════════════
# BANNER DISPLAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def get_neon_green_gradient() -> List[str]:
    """Get the neon green gradient for HCODE branding.
    
    This creates a stunning neon green effect specifically for the logo.
    """
    return [
        "#00FF00",  # Pure green
        "#0FFF0F",
        "#1FFF1F",
        "#2FFF2F",
        "#39FF14",  # Neon green (signature color)
        "#39FF14",
        "#39FF14",
        "#3FFF3F",
        "#4FFF4F",
        "#5FFF5F",
        "#00FF88",  # Mint green
        "#00FF99",
        "#00FFAA",  # Cyan-green
        "#00FFBB",
        "#00FFCC",
        "#00FFDD",
        "#00FFEE",
        "#00FFFF",  # Cyan accent
        "#33FFFF",
        "#66FFFF",  # Light cyan
    ]


def create_banner(
        style: str = "cyber",
        show_version: bool = True,
        show_tagline: bool = True,
        version: str = "1.0.0",
) -> RenderableType:
    """Create a styled banner with logo and optional info, centered in the terminal."""
    palette = get_palette()

    # Select logo
    logos = {
        "cyber": LOGO_CYBER,
        "neon": LOGO_NEON,
        "minimal": LOGO_MINIMAL,
        "glitch": LOGO_GLITCH,
        "futuristic": LOGO_FUTURISTIC,
        "small": LOGO_SMALL,
        "tech": LOGO_TECH,
        "block": LOGO_BLOCK,
        "dots": LOGO_DOTS,
    }

    logo = logos.get(style, LOGO_CYBER)

    # Use NEON GREEN gradient for the HCODE logo
    gradient_colors = get_neon_green_gradient()

    elements = []

    # Main Logo (centered)
    logo_text = logo.strip("\n")
    gradient_logo = create_gradient_text(logo_text, gradient_colors)

    elements.append(Align.center(gradient_logo))

    # Enhanced decorative line with glow effect
    deco_line = Text()
    deco_line.append("━" * 60, style=f"bold #39FF14")  # Neon green separator
    elements.append(Align.center(deco_line))

    if show_version or show_tagline:
        version_text = Text()

        if show_version:
            version_text.append(f"v{version}", style=f"bold #39FF14")
            version_text.append(" │ ", style=palette.text_muted)

        if show_tagline:
            version_text.append("AI-Powered Coding Agent", style=f"italic {palette.secondary}")
            version_text.append(" │ ", style=palette.text_muted)

        version_text.append("◉ ", style=f"bold #39FF14")
        version_text.append("ONLINE", style=f"bold #39FF14")

        elements.append(Align.center(version_text))

    # Return centered group
    return Align.center(Group(*elements))


# ═══════════════════════════════════════════════════════════════════════
# SECTION HEADERS
# ═══════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════
# DECORATIVE ELEMENTS
# ═══════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════
# STARTUP SEQUENCES
# ═══════════════════════════════════════════════════════════════════════


def display_welcome_help(console: Console) -> None:
    """Display modern frameless welcome help with tips and shortcuts (V2)."""
    from rich.columns import Columns
    from rich.padding import Padding
    from rich.table import Table
    from typing import List, Tuple

    palette = get_palette()

    # ─── Hero Header ──────────────────────────────────────────────────────────────
    # Centered, spaced out, gradient text
    console.print()
    header_text = create_gradient_text("INTERACTIVE  CHAT  MODE", ["#00FFFF", "#39FF14"])
    console.print(Align.center(header_text))
    console.print()

    # ─── Help Helpers ─────────────────────────────────────────────────────────────

    def create_gutter_block(title: str, color: str, items: List[Tuple[str, str]]) -> Table:
        """Create a block with a left gutter line."""
        # Main container is a grid with 2 columns: gutter line, content
        grid = Table.grid(padding=(0, 0))
        grid.add_column(width=2)  # The gutter line column
        grid.add_column()  # The content column

        # Header (spans both or sits above? Sits in content col usually)
        # We'll put header in content col, first row
        grid.add_row(
            " ",  # Empty gutter for header
            Text(title, style=f"bold {color}")
        )
        grid.add_row(" ", Text(""))  # Spacer

        # Content rows
        for icon, text in items:
            # Create the content row with the gutter line
            # We want a continuous line properly. 
            # Best way in Rich: A table where the first column has a side border?
            # Or just a character "│". Characters break if line wraps.
            # Robust way: A Panel with only left border? 
            # Let's try Panel with box.MINIMAL and left border only styling? 
            # Rich Panels don't easily support single-side borders.
            # Stick to "│" character for now as items are short text.

            row_content = Table.grid(padding=(0, 2))
            row_content.add_column(width=headers_width if title == "COMMANDS" else 4)  # Icon/Key width
            row_content.add_column()  # Text

            row_content.add_row(icon, f"[{palette.text_secondary}]{text}[/]")

            grid.add_row(
                Text("│", style=f"bold {color}"),
                Padding(row_content, (0, 0, 0, 1))
            )

        return grid

    # ─── Content Data ─────────────────────────────────────────────────────────────

    tips_data = [
        ("⚡", "Type naturally, Hcode understands context"),
        ("⚡", "Use /commands for special actions"),
        ("⚡", "Press Ctrl+C to interrupt, /exit to quit"),
        ("⚡", "Responses stream in real-time"),
    ]

    shortcuts_data = [
        ("[bold #111111 on #00FFFF] Tab [/]", "Autocomplete"),
        ("[bold #111111 on #00FFFF] Ctrl+Space [/]", "Show Suggestions"),
        ("[bold #111111 on #00FFFF] ↑ / ↓ [/]", "History Nav"),
        ("[bold #111111 on #00FFFF] /todos [/]", "Toggle Tasks"),
    ]

    # Calculate widths for alignment
    headers_width = 16  # Approx width for keys

    # ─── Construction ─────────────────────────────────────────────────────────────

    tips_block = create_gutter_block("TIPS", "#39FF14", tips_data)
    shortcuts_block = create_gutter_block("COMMANDS", "#00FFFF", shortcuts_data)

    # ─── Layout ───────────────────────────────────────────────────────────────────
    # Use Columns to place them side-by-side

    columns = Columns([tips_block, shortcuts_block], expand=True, align="center")
    console.print(Padding(columns, (0, 4)))
    console.print()


# ═══════════════════════════════════════════════════════════════════════
# QUICK ACCESS BANNERS
# ═══════════════════════════════════════════════════════════════════════


def quick_banner() -> Text:
    """Get a minimal inline banner."""
    palette = get_palette()

    text = Text()
    text.append("◈ ", style="bold #00FF88")  # Mint green icon
    text.append("HCode", style="bold #39FF14")  # Neon green brand
    text.append(" │ ", style=palette.text_muted)
    text.append("AI Agent", style=f"italic {palette.text_secondary}")

    return text
