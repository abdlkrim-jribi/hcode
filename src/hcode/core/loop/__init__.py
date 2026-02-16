"""
Hcode Core Loop Module.

Provides the main agent execution loop controller.
"""

from .agent_loop import AgentLoopController, LoopState, Phase, StopReason

# Alias for compatibility
LoopPhase = Phase

__all__ = [
    "AgentLoopController",
    "LoopState",
    "Phase",
    "LoopPhase",
    "StopReason",
]
