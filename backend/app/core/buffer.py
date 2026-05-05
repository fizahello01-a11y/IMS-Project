"""
core/buffer.py
──────────────
In-memory ring buffer using asyncio.Queue.

WHY THIS EXISTS:
  The ingestion API must return 202 instantly even if the DB is slow.
  Signals are placed here, and a background worker drains them to storage.
  If the buffer fills (DB very slow), the OLDEST item is dropped (not the newest).

CAPACITY: 100,000 signals by default (configurable via BUFFER_SIZE env var).
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


class RingBuffer:
    def __init__(self, maxsize: int = 100_000):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._dropped: int = 0

    async def put(self, item: dict) -> bool:
        """
        Non-blocking put. If full, drops the oldest item to make room.
        Returns True if inserted cleanly, False if a drop occurred.
        """
        try:
            self._queue.put_nowait(item)
            return True
        except asyncio.QueueFull:
            # Drop oldest to make room for newest (ring behavior)
            try:
                self._queue.get_nowait()
                self._dropped += 1
            except asyncio.QueueEmpty:
                pass
            try:
                self._queue.put_nowait(item)
            except asyncio.QueueFull:
                pass
            logger.warning(f"Ring buffer full – total drops: {self._dropped}")
            return False

    async def get(self) -> dict:
        """Blocking get – waits until an item is available."""
        return await self._queue.get()

    def task_done(self):
        self._queue.task_done()

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def dropped(self) -> int:
        return self._dropped

    @property
    def capacity(self) -> int:
        return self._queue.maxsize
