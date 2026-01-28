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


# =============================================================================
# TOOL RESULT CACHE
# =============================================================================

@dataclass
class CachedResult:
    result: Any
    timestamp: float
    hit_count: int = 0

class ToolResultCache:
    """Caches tool results."""

    CACHEABLE_TOOLS = {"readtool", "globtool", "greptool", "lstool"}

    def __init__(self, ttl_seconds: float = 60.0, max_size: int = 500):
        self._cache: Dict[str, CachedResult] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = threading.Lock()
        self._file_mtimes: Dict[str, float] = {}
        self._hits = 0
        self._misses = 0

    def _make_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        params_str = json.dumps(params, sort_keys=True)
        return f"{tool_name}:{hashlib.md5(params_str.encode()).hexdigest()}"

    def _get_file_mtime(self, file_path: str) -> float:
        try:
            return Path(file_path).stat().st_mtime
        except (OSError, FileNotFoundError):
            return 0

    def _is_valid(self, key: str, cached: CachedResult, params: Dict[str, Any]) -> bool:
        if time.time() - cached.timestamp > self._ttl:
            return False
        file_path = params.get("file_path") or params.get("path")
        if file_path:
            current_mtime = self._get_file_mtime(file_path)
            cached_mtime = self._file_mtimes.get(file_path, 0)
            if current_mtime > cached_mtime:
                return False
        return True

    def get(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        if tool_name.lower() not in self.CACHEABLE_TOOLS:
            return None
        key = self._make_key(tool_name, params)
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            cached = self._cache[key]
            if not self._is_valid(key, cached, params):
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            cached.hit_count += 1
            return cached.result

    def set(self, tool_name: str, params: Dict[str, Any], result: Any):
        if tool_name.lower() not in self.CACHEABLE_TOOLS:
            return
        key = self._make_key(tool_name, params)
        with self._lock:
            file_path = params.get("file_path") or params.get("path")
            if file_path:
                self._file_mtimes[file_path] = self._get_file_mtime(file_path)
            self._cache[key] = CachedResult(result=result, timestamp=time.time())
            while len(self._cache) > self._max_size:
                min_key = min(self._cache.keys(), key=lambda k: self._cache[k].hit_count)
                del self._cache[min_key]

    def invalidate_file(self, file_path: str):
        with self._lock:
            self._file_mtimes[file_path] = time.time() + 1
            keys_to_remove = []
            for key in self._cache:
                if file_path in key:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del self._cache[key]

    def clear(self):
        with self._lock:
            self._cache.clear()
            self._file_mtimes.clear()

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0,
            "cache_size": len(self._cache),
            "tracked_files": len(self._file_mtimes),
        }
