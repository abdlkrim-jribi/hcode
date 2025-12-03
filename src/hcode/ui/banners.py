"""
HCode Futuristic ASCII Art Banners and Branding
Features animated gradients and glowing effects.
"""
from rich.console import Console, Group, RenderableType
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.style import Style
from rich.padding import Padding
from rich.box import ROUNDED, DOUBLE, HEAVY
from typing import List, Optional
import random
import time

from .theme import get_theme, get_palette, ColorUtils


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
    lines = text.split('\n')

    for line in lines:
        if not line.strip():
            result.append('\n')
            continue

        for i, char in enumerate(line):
            if char.strip():  # Only color non-whitespace
                color_index = int((i / max(len(line), 1)) * (len(colors) - 1))
                color = colors[min(color_index, len(colors) - 1)]
                result.append(char, style=Style(color=color, bold=True))
            else:
                result.append(char)
        result.append('\n')

    return result


def create_vertical_gradient_text(text: str, colors: List[str]) -> Text:
    """Create text with vertical gradient (colors change per line)."""
    result = Text()
    lines = text.split('\n')

    for line_idx, line in enumerate(lines):
        if not line.strip():
            result.append('\n')
            continue

        color_index = int((line_idx / max(len(lines), 1)) * (len(colors) - 1))
        color = colors[min(color_index, len(colors) - 1)]

        result.append(line, style=Style(color=color, bold=True))
        result.append('\n')

    return result


def create_rainbow_text(text: str) -> Text:
    """Create text with rainbow colors."""
    rainbow_colors = [
        "#FF0000", "#FF7F00", "#FFFF00", "#00FF00",
        "#00FFFF", "#0000FF", "#8B00FF", "#FF00FF"
    ]
    return create_gradient_text(text, rainbow_colors)


# ═══════════════════════════════════════════════════════════════════════
# BANNER DISPLAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def get_cyberpunk_gradient() -> List[str]:
    """Get the cyberpunk color gradient."""
    return [
        "#FF00FF",  # Magenta
        "#FF00CC",
        "#FF0099",
        "#FF0066",
        "#FF0033",
        "#FF3300",
        "#FF6600",
        "#FF9900",
        "#FFCC00",
        "#FFFF00",  # Yellow
        "#CCFF00",
        "#99FF00",
        "#66FF00",
        "#33FF00",
        "#00FF00",  # Green
        "#00FF33",
        "#00FF66",
        "#00FF99",
        "#00FFCC",
        "#00FFFF",  # Cyan
    ]


def create_banner(
    style: str = "cyber",
    show_version: bool = True,
    show_tagline: bool = True,
    version: str = "1.0.0"
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

    # Create gradient logo
    gradient_colors = get_cyberpunk_gradient()
    gradient_logo = create_gradient_text(logo, gradient_colors)

    elements = []

    # Center the logo
    elements.append(Align.center(gradient_logo))

    # Decorative line
    deco_line = Text("━" * 60, style=f"bold {palette.border_default}")
    elements.append(Align.center(deco_line))

    if show_version or show_tagline:
        version_text = Text()

        if show_version:
            version_text.append(f"v{version}", style=f"bold {palette.primary}")
            version_text.append(" │ ", style=palette.text_muted)

        if show_tagline:
            version_text.append("AI-Powered Coding Agent", style=f"italic {palette.secondary}")
            version_text.append(" │ ", style=palette.text_muted)

        version_text.append("◉ ", style=f"bold {palette.success}")
        version_text.append("ONLINE", style=f"bold {palette.success}")

        elements.append(Align.center(version_text))

    # Return centered group
    return Align.center(Group(*elements))


def create_animated_banner(
    console: Console,
    style: str = "cyber",
    animation_frames: int = 5,
    frame_delay: float = 0.1
) -> None:
    """Display animated startup banner with glow effect."""
    palette = get_palette()

    logos = {
        "cyber": LOGO_CYBER,
        "neon": LOGO_NEON,
        "minimal": LOGO_MINIMAL,
        "small": LOGO_SMALL,
        "block": LOGO_BLOCK,
    }

    logo = logos.get(style, LOGO_CYBER)
    gradient_colors = get_cyberpunk_gradient()

    # Animation: fade in effect
    for frame in range(animation_frames):
        intensity = (frame + 1) / animation_frames

        # Create faded colors
        faded_colors = []
        for color in gradient_colors:
            r, g, b = ColorUtils.hex_to_rgb(color)
            r = int(r * intensity)
            g = int(g * intensity)
            b = int(b * intensity)
            faded_colors.append(ColorUtils.rgb_to_hex(r, g, b))

        gradient_logo = create_gradient_text(logo, faded_colors)

        console.clear()
        console.print()
        console.print(Align.center(gradient_logo))
        time.sleep(frame_delay)

    # Final frame with full colors
    console.clear()
    console.print()
    final_banner = create_banner(style=style)
    console.print(Align.center(final_banner))
    console.print()


# ═══════════════════════════════════════════════════════════════════════
# SECTION HEADERS
# ═══════════════════════════════════════════════════════════════════════

def create_section_header(
    title: str,
    icon: str = "◆",
    style: str = "default"
) -> Panel:
    """Create a futuristic section header."""
    palette = get_palette()

    header_text = Text()
    header_text.append(f" {icon} ", style=f"bold {palette.secondary}")
    header_text.append(title.upper(), style=f"bold {palette.primary}")
    header_text.append(f" {icon} ", style=f"bold {palette.secondary}")

    return Panel(
        Align.center(header_text),
        border_style=f"bold {palette.border_default}",
        box=DOUBLE,
        padding=(0, 2),
    )


def create_subsection_header(title: str, icon: str = "▸") -> Text:
    """Create a smaller subsection header."""
    palette = get_palette()

    text = Text()
    text.append(f" {icon} ", style=f"bold {palette.accent}")
    text.append(title, style=f"bold {palette.text_primary}")

    return text


# ═══════════════════════════════════════════════════════════════════════
# DECORATIVE ELEMENTS
# ═══════════════════════════════════════════════════════════════════════

def create_divider(
    width: int = 60,
    style: str = "single",
    label: Optional[str] = None
) -> Text:
    """Create a decorative divider line."""
    palette = get_palette()

    divider_chars = {
        "single": "─",
        "double": "═",
        "thick": "━",
        "dotted": "┄",
        "dashed": "┅",
        "wave": "∿",
    }

    char = divider_chars.get(style, "─")

    if label:
        side_len = (width - len(label) - 4) // 2
        line = f"{char * side_len} {label} {char * side_len}"
    else:
        line = char * width

    return Text(line, style=f"{palette.border_default}")


def create_glow_text(text: str, color: Optional[str] = None) -> Text:
    """Create text with simulated glow effect."""
    palette = get_palette()
    glow_color = color or palette.glow_color

    result = Text()
    result.append(text, style=f"bold {glow_color}")

    return result


def create_neon_box(content: str, width: int = 40) -> Panel:
    """Create a neon-styled box."""
    palette = get_palette()

    return Panel(
        Text(content, style=f"{palette.text_primary}"),
        border_style=f"bold {palette.primary}",
        box=ROUNDED,
        padding=(1, 2),
        width=width,
    )


# ═══════════════════════════════════════════════════════════════════════
# STARTUP SEQUENCES
# ═══════════════════════════════════════════════════════════════════════

def display_welcome(console: Console, compact: bool = False) -> None:
    """Display complete welcome sequence."""
    if compact:
        banner = create_banner(style="small", show_tagline=False)
    else:
        banner = create_banner(style="cyber")

    console.print()
    console.print(Align.center(banner))
    console.print()


def display_startup_animation(console: Console, duration: float = 1.0) -> None:
    """Display animated startup sequence."""
    palette = get_palette()
    frames = ["◐", "◓", "◑", "◒"]
    steps = int(duration / 0.1)

    for i in range(steps):
        frame = frames[i % len(frames)]
        text = Text()
        text.append(f" {frame} ", style=f"bold {palette.primary}")
        text.append("Initializing HCode...", style=palette.text_secondary)

        console.clear()
        console.print(Align.center(text))
        time.sleep(0.1)

    # Show ready message
    console.clear()
    ready_text = Text()
    ready_text.append(" ◉ ", style=f"bold {palette.success}")
    ready_text.append("HCode Ready", style=f"bold {palette.success}")
    console.print(Align.center(ready_text))
    time.sleep(0.5)


# ═══════════════════════════════════════════════════════════════════════
# QUICK ACCESS BANNERS
# ═══════════════════════════════════════════════════════════════════════

def quick_banner() -> Text:
    """Get a minimal inline banner."""
    palette = get_palette()

    text = Text()
    text.append("◈ ", style=f"bold {palette.secondary}")
    text.append("HCode", style=f"bold {palette.primary}")
    text.append(" │ ", style=palette.text_muted)
    text.append("AI Agent", style=f"italic {palette.text_secondary}")

    return text


def status_banner(status: str = "ready") -> Text:
    """Get a status-aware banner."""
    palette = get_palette()

    status_configs = {
        "ready": ("◉", palette.success, "Ready"),
        "thinking": ("◐", palette.warning, "Thinking"),
        "executing": ("▶", palette.info, "Executing"),
        "error": ("✗", palette.error, "Error"),
        "offline": ("○", palette.text_muted, "Offline"),
    }

    icon, color, label = status_configs.get(
        status, ("○", palette.text_muted, status.title())
    )

    text = Text()
    text.append("◈ ", style=f"bold {palette.secondary}")
    text.append("HCode", style=f"bold {palette.primary}")
    text.append(" │ ", style=palette.text_muted)
    text.append(f"{icon} ", style=f"bold {color}")
    text.append(label, style=f"bold {color}")

    return text
