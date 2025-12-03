"""
Legacy compatibility layer for cli.styles.animations.

Re-exports animation components from the new hcode.ui module.
"""

from hcode.ui import (
    spinner,
    thinking,
    loading,
    countdown,
    ThinkingAnimation,
    WaveAnimation,
    PulsingText,
    LoadingDots,
    Countdown,
    StreamingText,
    GlitchEffect,
    CyberProgress,
    AnimatedMessage,
    CYBER_SPINNERS,
)


class AnimatedSpinner:
    """Legacy AnimatedSpinner - wraps ThinkingAnimation."""

    def __init__(self, console=None, message="Processing"):
        from hcode.ui import get_console
        self.console = console or get_console()
        self.message = message
        self._anim = None

    def start(self):
        self._anim = ThinkingAnimation(self.console)
        self._anim.start()

    def stop(self, message=None):
        if self._anim:
            self._anim.stop(message)
            self._anim = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


class TypingAnimation:
    """Legacy TypingAnimation - wraps StreamingText."""

    def __init__(self, console=None, speed=0.02):
        from hcode.ui import get_console
        self.console = console or get_console()
        self.speed = speed
        self._stream = StreamingText(self.console, speed=speed)

    def type(self, text: str):
        """Type text with animation."""
        self._stream.stream_sync(text)

    async def type_async(self, text: str):
        """Type text with animation (async)."""
        await self._stream.stream(text)


class ProgressAnimation:
    """Legacy ProgressAnimation - wraps CyberProgress."""

    def __init__(self, console=None, description="Processing"):
        from hcode.ui import get_console
        self.console = console or get_console()
        self.description = description

    def track(self, total: int):
        """Track progress."""
        progress = CyberProgress(self.console, description=self.description)
        return progress.track(total)


__all__ = [
    # Context managers
    "spinner",
    "thinking",
    "loading",
    "countdown",

    # Classes
    "ThinkingAnimation",
    "WaveAnimation",
    "PulsingText",
    "LoadingDots",
    "Countdown",
    "StreamingText",
    "GlitchEffect",
    "CyberProgress",
    "AnimatedMessage",

    # Legacy classes
    "AnimatedSpinner",
    "TypingAnimation",
    "ProgressAnimation",

    # Constants
    "CYBER_SPINNERS",
]
