import threading
import time
from typing import Any, Callable, Dict, List, Optional


# =============================================================================
# BATCH CONTEXT WRITER
# =============================================================================

class BatchContextWriter:
    """
    Batches context writes to reduce I/O overhead.
    """

    def __init__(
            self,
            flush_threshold: int = 10,
            flush_interval: float = 5.0,
            write_callback: Optional[Callable[[List[Dict]], None]] = None,
    ):
        self._buffer: List[Dict[str, Any]] = []
        self._threshold = flush_threshold
        self._interval = flush_interval
        self._callback = write_callback
        self._lock = threading.Lock()
        self._last_flush = time.time()
        self._flush_count = 0
        self._message_count = 0
        self._running = True
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()

    def add(self, message: Dict[str, Any]):
        with self._lock:
            self._buffer.append(message)
            self._message_count += 1
            if len(self._buffer) >= self._threshold:
                self._flush_internal()

    def _timer_loop(self):
        while self._running:
            time.sleep(1.0)
            with self._lock:
                elapsed = time.time() - self._last_flush
                if elapsed >= self._interval and self._buffer:
                    self._flush_internal()

    def _flush_internal(self):
        if not self._buffer:
            return
        messages = self._buffer.copy()
        self._buffer.clear()
        self._last_flush = time.time()
        self._flush_count += 1
        if self._callback:
            try:
                self._callback(messages)
            except Exception:
                self._buffer = messages + self._buffer

    def flush(self):
        with self._lock:
            self._flush_internal()

    def stop(self):
        self._running = False
        self.flush()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "buffered": len(self._buffer),
            "total_messages": self._message_count,
            "flush_count": self._flush_count,
            "avg_batch_size": self._message_count / max(1, self._flush_count),
        }


_context_writer: Optional[BatchContextWriter] = None


def get_context_writer() -> BatchContextWriter:
    global _context_writer
    if _context_writer is None:
        _context_writer = BatchContextWriter()
    return _context_writer
