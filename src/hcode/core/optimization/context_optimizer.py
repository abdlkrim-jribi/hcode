import asyncio
import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .token_counter import CachedTokenCounter

# =============================================================================
# SMART CONTEXT OPTIMIZER
# =============================================================================

class SmartContextOptimizer:
    """Optimizes context window usage."""

    def __init__(self, token_counter: CachedTokenCounter, summarizer: Optional[Callable[[List[Dict]], str]] = None):
        self.token_counter = token_counter
        self.summarizer = summarizer or self._default_summarizer

    def _default_summarizer(self, messages: List[Dict]) -> str:
        summaries = []
        for msg in messages:
            content = msg.get("content", "")
            if len(content) > 200:
                summaries.append(content[:200] + "...")
            else:
                summaries.append(content)
        return "[Compressed context]\n" + "\n".join(summaries[:5])

    def _calculate_importance(self, message: Dict, position: int, total: int) -> float:
        score = 0.0
        recency = position / total if total > 0 else 0
        score += recency * 0.3
        role = message.get("role", "")
        if role == "system": score += 0.4
        elif role == "user": score += 0.2
        elif role == "assistant": score += 0.1
        content = message.get("content", "").lower()
        if any(kw in content for kw in ["error", "fail", "bug", "fix", "important"]):
            score += 0.2
        if "```" in content: score += 0.1
        return min(score, 1.0)

    def _compress_tool_outputs(self, messages: List[Dict]) -> List[Dict]:
        compressed = []
        for msg in messages:
            if msg.get("role") == "tool":
                content = msg.get("content", "")
                if len(content) > 500:
                    truncated = content[:300] + "\n...[truncated]...\n" + content[-100:]
                    msg = {**msg, "content": truncated}
            compressed.append(msg)
        return compressed

    def optimize(self, messages: List[Dict], max_tokens: int, preserve_recent: int = 10) -> List[Dict]:
        if not messages: return messages
        current_tokens = self.token_counter.count_messages(messages)
        if current_tokens <= max_tokens: return messages
        messages = self._compress_tool_outputs(messages)
        current_tokens = self.token_counter.count_messages(messages)
        if current_tokens <= max_tokens: return messages
        if len(messages) > preserve_recent * 2:
            to_summarize = messages[:-preserve_recent]
            to_keep = messages[-preserve_recent:]
            summary = self.summarizer(to_summarize)
            summary_msg = {"role": "system", "content": summary}
            messages = [summary_msg] + to_keep
            current_tokens = self.token_counter.count_messages(messages)
            if current_tokens <= max_tokens: return messages
        total = len(messages)
        scored = [(self._calculate_importance(msg, i, total), i, msg) for i, msg in enumerate(messages)]
        scored.sort(key=lambda x: x[0], reverse=True)
        result = []
        result_tokens = 0
        for importance, idx, msg in scored:
            msg_tokens = self.token_counter.count(msg.get("content", ""))
            if result_tokens + msg_tokens <= max_tokens:
                result.append((idx, msg))
                result_tokens += msg_tokens
        result.sort(key=lambda x: x[0])
        return [msg for idx, msg in result]
