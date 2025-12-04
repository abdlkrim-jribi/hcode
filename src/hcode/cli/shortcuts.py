"""
Keyboard shortcuts for Hcode CLI.

Provides keyboard shortcut handling for common operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Dict, Any, List


class ShortcutAction(Enum):
    """Available shortcut actions"""

    TOGGLE_MODE = "toggle_mode"
    SWITCH_TO_AUTO = "switch_auto"
    SWITCH_TO_INTERACTIVE = "switch_interactive"
    SWITCH_TO_PLAN = "switch_plan"
    SHOW_HELP = "show_help"
    SHOW_TASKS = "show_tasks"
    CLEAR_SCREEN = "clear_screen"
    CANCEL = "cancel"
    CONFIRM = "confirm"
    SUBMIT = "submit"


@dataclass
class KeyBinding:
    """A keyboard shortcut binding"""

    key: str
    action: ShortcutAction
    description: str
    modifiers: List[str] = None

    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = []

    def matches(self, key_event: Dict[str, Any]) -> bool:
        """Check if key event matches this binding"""
        # Check key
        if key_event.get("key", "").lower() != self.key.lower():
            return False

        # Check modifiers
        event_mods = set(key_event.get("modifiers", []))
        binding_mods = set(self.modifiers)

        return event_mods == binding_mods

    def get_display(self) -> str:
        """Get display string for the shortcut"""
        parts = []

        # Add modifiers
        mod_display = {
            "ctrl": "Ctrl",
            "shift": "Shift",
            "alt": "Alt",
            "meta": "Cmd" if is_macos() else "Win",
        }

        for mod in self.modifiers:
            parts.append(mod_display.get(mod, mod.capitalize()))

        # Add key
        key_display = {
            "tab": "Tab",
            "enter": "Enter",
            "escape": "Esc",
            "space": "Space",
            "backspace": "Backspace",
            "delete": "Del",
        }

        parts.append(key_display.get(self.key.lower(), self.key.upper()))

        return "+".join(parts)


def is_macos() -> bool:
    """Check if running on macOS"""
    import platform

    return platform.system() == "Darwin"


class ShortcutManager:
    """
    Manages keyboard shortcuts.

    Provides:
    - Default shortcut bindings
    - Custom shortcut registration
    - Key event handling
    """

    # Default shortcuts
    DEFAULT_BINDINGS = [
        KeyBinding(
            key="tab",
            action=ShortcutAction.TOGGLE_MODE,
            description="Toggle between Interactive and Auto modes",
            modifiers=["shift"],
        ),
        KeyBinding(
            key="a",
            action=ShortcutAction.SWITCH_TO_AUTO,
            description="Switch to Auto mode",
            modifiers=["ctrl", "shift"],
        ),
        KeyBinding(
            key="i",
            action=ShortcutAction.SWITCH_TO_INTERACTIVE,
            description="Switch to Interactive mode",
            modifiers=["ctrl", "shift"],
        ),
        KeyBinding(
            key="p",
            action=ShortcutAction.SWITCH_TO_PLAN,
            description="Switch to Plan mode",
            modifiers=["ctrl", "shift"],
        ),
        KeyBinding(
            key="h", action=ShortcutAction.SHOW_HELP, description="Show help", modifiers=["ctrl"]
        ),
        KeyBinding(
            key="t",
            action=ShortcutAction.SHOW_TASKS,
            description="Show task list",
            modifiers=["ctrl"],
        ),
        KeyBinding(
            key="l",
            action=ShortcutAction.CLEAR_SCREEN,
            description="Clear screen",
            modifiers=["ctrl"],
        ),
        KeyBinding(
            key="c",
            action=ShortcutAction.CANCEL,
            description="Cancel current operation",
            modifiers=["ctrl"],
        ),
        KeyBinding(
            key="enter", action=ShortcutAction.SUBMIT, description="Submit input", modifiers=[]
        ),
        KeyBinding(
            key="y", action=ShortcutAction.CONFIRM, description="Confirm action", modifiers=[]
        ),
    ]

    def __init__(self):
        """Initialize shortcut manager"""
        self.bindings: List[KeyBinding] = list(self.DEFAULT_BINDINGS)
        self.callbacks: Dict[ShortcutAction, Callable] = {}
        self.enabled = True

    def register_callback(self, action: ShortcutAction, callback: Callable[[], None]):
        """
        Register callback for action.

        Args:
            action: Shortcut action
            callback: Callback function
        """
        self.callbacks[action] = callback

    def add_binding(self, binding: KeyBinding):
        """
        Add custom key binding.

        Args:
            binding: Key binding to add
        """
        # Remove existing binding for same key combo
        self.bindings = [
            b
            for b in self.bindings
            if not (b.key == binding.key and b.modifiers == binding.modifiers)
        ]
        self.bindings.append(binding)

    def remove_binding(self, key: str, modifiers: List[str] = None):
        """
        Remove key binding.

        Args:
            key: Key to remove
            modifiers: Modifiers for the key
        """
        modifiers = modifiers or []
        self.bindings = [
            b for b in self.bindings if not (b.key == key and set(b.modifiers) == set(modifiers))
        ]

    def handle_key(self, key_event: Dict[str, Any]) -> Optional[ShortcutAction]:
        """
        Handle key event.

        Args:
            key_event: Key event dictionary with 'key' and 'modifiers'

        Returns:
            Action if matched, None otherwise
        """
        if not self.enabled:
            return None

        for binding in self.bindings:
            if binding.matches(key_event):
                action = binding.action

                # Call callback if registered
                if action in self.callbacks:
                    self.callbacks[action]()

                return action

        return None

    def get_bindings_for_action(self, action: ShortcutAction) -> List[KeyBinding]:
        """Get all bindings for an action"""
        return [b for b in self.bindings if b.action == action]

    def get_help_text(self) -> str:
        """Get formatted help text for shortcuts"""
        lines = ["Keyboard Shortcuts:", ""]

        # Group by action type
        mode_shortcuts = []
        nav_shortcuts = []
        other_shortcuts = []

        for binding in self.bindings:
            if "mode" in binding.action.value.lower():
                mode_shortcuts.append(binding)
            elif binding.action in [
                ShortcutAction.SHOW_HELP,
                ShortcutAction.SHOW_TASKS,
                ShortcutAction.CLEAR_SCREEN,
            ]:
                nav_shortcuts.append(binding)
            else:
                other_shortcuts.append(binding)

        if mode_shortcuts:
            lines.append("Mode Switching:")
            for b in mode_shortcuts:
                lines.append(f"  {b.get_display():<15} {b.description}")
            lines.append("")

        if nav_shortcuts:
            lines.append("Navigation:")
            for b in nav_shortcuts:
                lines.append(f"  {b.get_display():<15} {b.description}")
            lines.append("")

        if other_shortcuts:
            lines.append("Other:")
            for b in other_shortcuts:
                lines.append(f"  {b.get_display():<15} {b.description}")

        return "\n".join(lines)

    def enable(self):
        """Enable shortcut handling"""
        self.enabled = True

    def disable(self):
        """Disable shortcut handling"""
        self.enabled = False


class PromptToolkitShortcuts:
    """
    Shortcut integration for prompt_toolkit.

    Provides key bindings for use with prompt_toolkit input.
    """

    def __init__(self, shortcut_manager: ShortcutManager):
        """
        Initialize prompt_toolkit shortcuts.

        Args:
            shortcut_manager: Shortcut manager instance
        """
        self.manager = shortcut_manager

    def get_key_bindings(self):
        """
        Get prompt_toolkit key bindings.

        Returns:
            KeyBindings instance
        """
        try:
            from prompt_toolkit.key_binding import KeyBindings
            from prompt_toolkit.keys import Keys

            kb = KeyBindings()

            # Map our modifiers to prompt_toolkit
            def get_pt_key(binding: KeyBinding):
                """Convert binding to prompt_toolkit key"""
                key = binding.key.lower()
                mods = binding.modifiers

                # Build prompt_toolkit key sequence
                if "ctrl" in mods and "shift" in mods:
                    return (Keys.ControlShift, key)
                elif "ctrl" in mods:
                    return (Keys.Control, key)
                elif "shift" in mods and key == "tab":
                    return Keys.BackTab
                elif "alt" in mods:
                    return (Keys.Alt, key)
                else:
                    return key

            # Register each binding
            for binding in self.manager.bindings:
                pt_key = get_pt_key(binding)
                action = binding.action

                # Create handler
                def make_handler(act):
                    def handler(event):
                        if act in self.manager.callbacks:
                            self.manager.callbacks[act]()

                    return handler

                # Register with prompt_toolkit
                if isinstance(pt_key, tuple):

                    @kb.add(*pt_key)
                    def _(event, act=action):
                        if act in self.manager.callbacks:
                            self.manager.callbacks[act]()

                elif pt_key == Keys.BackTab:

                    @kb.add(Keys.BackTab)
                    def _(event, act=action):
                        if act in self.manager.callbacks:
                            self.manager.callbacks[act]()

            return kb

        except ImportError:
            # prompt_toolkit not available
            return None


def create_readline_shortcuts(shortcut_manager: ShortcutManager):
    """
    Set up readline key bindings.

    Args:
        shortcut_manager: Shortcut manager instance
    """
    try:
        import readline

        # Note: readline has limited shortcut support
        # Most shortcuts need to be handled at input level

        # We can set up some basic ones
        # For example, Ctrl+L for clear
        readline.parse_and_bind('"\C-l": clear-screen')

    except ImportError:
        # readline not available (Windows)
        pass


def setup_shortcuts_for_agent(agent, shortcut_manager: ShortcutManager):
    """
    Set up shortcut callbacks for an autonomous agent.

    Args:
        agent: AutonomousCodingAgent instance
        shortcut_manager: Shortcut manager instance
    """
    from ..agent.modes import AgentMode

    # Mode toggle
    def toggle_mode():
        if agent.get_mode() == AgentMode.INTERACTIVE:
            agent.set_mode(AgentMode.AUTO)
        else:
            agent.set_mode(AgentMode.INTERACTIVE)

    shortcut_manager.register_callback(ShortcutAction.TOGGLE_MODE, toggle_mode)

    # Direct mode switches
    shortcut_manager.register_callback(
        ShortcutAction.SWITCH_TO_AUTO, lambda: agent.set_mode(AgentMode.AUTO)
    )
    shortcut_manager.register_callback(
        ShortcutAction.SWITCH_TO_INTERACTIVE, lambda: agent.set_mode(AgentMode.INTERACTIVE)
    )
    shortcut_manager.register_callback(
        ShortcutAction.SWITCH_TO_PLAN, lambda: agent.set_mode(AgentMode.PLAN)
    )
