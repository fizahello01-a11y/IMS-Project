"""
core/metrics.py
───────────────
Throughput metrics – tracks signals/sec and prints to console every 5s.
"""
import asyncio
import logging
import time
from collections import deque

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self):
        self._total: int = 0
        self._window: deque = deque()   # timestamps of recent signals
        self._lock = asyncio.Lock()

    async def record_signal(self):
        """Call this each time a signal is ingested."""
        async with self._lock:
            self._total += 1
            self._window.append(time.monotonic())

    async def current_rate(self) -> float:
        """Signals per second over the last 5 seconds."""
        async with self._lock:
            now = time.monotonic()
            cutoff = now - 5.0
            while self._window and self._window[0] < cutoff:
                self._window.popleft()
            return len(self._window) / 5.0

    @property
    def total(self) -> int:
        return self._total

    async def print_loop(self):
        """Background task: prints throughput every 5 seconds."""
        while True:
            await asyncio.sleep(5)
            rate = await self.current_rate()
            print(
                f"[METRICS] Throughput: {rate:.1f} signals/sec | "
                f"Total ingested: {self._total:,}",
                flush=True
            )
