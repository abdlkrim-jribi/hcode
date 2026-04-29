"""
Interactive selector component for Hcode CLI.
Provides a modern, keyboard-navigable menu for confirmations and options.
Uses prompt_toolkit for full keyboard navigation and high-fidelity UI.
"""


import asyncio
from typing import List, Tuple, Optional, Any

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

from hcode.ui.theme import get_palette

async def select_option_async(options: List[Tuple[str, str, str]], title: str = "Select an option") -> Optional[str]:
    """
    Display an interactive selection menu.
    
    Args:
        options: List of tuples (id, label, description)
        title: Menu title
        
    Returns:
        The id of the selected option, or None if aborted.
    """
    palette = get_palette()
    
    # Define styles based on Hcode palette
    # Map hex colors to prompt_toolkit-compatible color names or #rrggbb
    style = Style.from_dict({
        'title': f'bold {palette.primary}',
        'selected': f'bold {palette.accent}',
        'selected_line': f'bg:{palette.bg_elevated} {palette.text_primary}',
        'description': f'{palette.text_muted} italic',
        'gutter': f'{palette.primary}',
        'option': f'{palette.text_secondary}',
        'cursor': f'bold {palette.accent}',
    })

    class State:
        def __init__(self):
            self.current_index = 0

    state = State()

    kb = KeyBindings()

    @kb.add('up')
    @kb.add('w')
    def _(event):
        state.current_index = (state.current_index - 1) % len(options)

    @kb.add('down')
    @kb.add('s')
    def _(event):
        state.current_index = (state.current_index + 1) % len(options)

    @kb.add('enter')
    def _(event):
        selected_id = options[state.current_index][0]
        event.app.exit(result=selected_id)

    @kb.add('c-c')
    @kb.add('escape')
    @kb.add('q')
    def _(event):
        event.app.exit(result=None)

    def get_formatted_text():
        result = []
        # Header
        result.append(('class:gutter', '  ▍ '))
        result.append(('class:title', f'{title}\n'))
        result.append(('', '  │\n'))
        
        for i, (opt_id, label, desc) in enumerate(options):
            is_selected = (i == state.current_index)
            
            # Gutter
            gutter_style = 'class:cursor' if is_selected else 'class:gutter'
            gutter_char = '➧ ' if is_selected else '  '
            result.append((gutter_style, f'  {gutter_char}'))
            
            # Label
            style_class = 'class:selected' if is_selected else 'class:option'
            result.append((style_class, f' {label:<15} '))
            
            # Description (only for selected or dim for others)
            if is_selected:
                result.append(('class:description', f' {desc}'))
            else:
                result.append(('class:description', f' {desc[:30]}...'))
            
            result.append(('', '\n'))
        
        result.append(('', '\n'))
        return result

    application = Application(
        layout=Layout(
            HSplit([
                Window(content=FormattedTextControl(get_formatted_text), height=len(options) + 4),
            ])
        ),
        key_bindings=kb,
        style=style,
        full_screen=False,
    )

    try:
        return await application.run_async()
    except Exception:
        return None
