"""
core/debounce.py
────────────────
Debounce Engine – groups repeated signals into one Work Item.

RULE:
  If 100 signals arrive for the same component_id within 10 seconds,
  only ONE Work Item is created. All 100 signals link to it in MongoDB.

HOW:
  Each component_id gets a time-windowed bucket of signals.
  First signal → create Work Item.
  Signals 2-99 → link to existing Work Item, no new creation.
  Signal 100 → mark bucket as "debounced", continue linking.
"""
import asyncio
import time
import logging
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Bucket:
    work_item_id: str
    signals: list = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)
    debounced: bool = False


class DebounceEngine:
    def __init__(self):
        self._buckets: dict[str, Bucket] = {}
        self._lock = asyncio.Lock()

    async def process(self, component_id: str, signal: dict) -> tuple[bool, str | None]:
        """
        Process an incoming signal for a component.

        Returns:
            (should_create_work_item: bool, existing_work_item_id: str | None)

        Cases:
            (True,  None)     → first signal, create a Work Item
            (False, "uuid")   → duplicate, link to existing Work Item
        """
        async with self._lock:
            now = time.monotonic()
            window = settings.debounce_window_seconds
            threshold = settings.debounce_threshold

            bucket = self._buckets.get(component_id)

            # No existing bucket, or bucket is expired → fresh start
            if bucket is None or (now - bucket.created_at) > window:
                # We don't know the work_item_id yet – will be set after creation
                new_bucket = Bucket(work_item_id="__pending__")
                new_bucket.signals.append(signal)
                self._buckets[component_id] = new_bucket
                return True, None   # caller must create Work Item and call set_work_item_id

            # Bucket exists and is within window
            bucket.signals.append(signal)
            count = len(bucket.signals)

            if count == threshold and not bucket.debounced:
                bucket.debounced = True
                logger.info(f"[Debounce] {component_id} hit {threshold} signals – debounced")

            return False, bucket.work_item_id

    async def set_work_item_id(self, component_id: str, work_item_id: str):
        """Called after creating the Work Item to record its ID in the bucket."""
        async with self._lock:
            if component_id in self._buckets:
                self._buckets[component_id].work_item_id = work_item_id

    async def cleanup_expired(self):
        """Periodically remove old buckets to free memory."""
        async with self._lock:
            now = time.monotonic()
            expired = [
                k for k, b in self._buckets.items()
                if (now - b.created_at) > settings.debounce_window_seconds * 6
            ]
            for k in expired:
                del self._buckets[k]
            if expired:
                logger.debug(f"[Debounce] Cleaned up {len(expired)} expired buckets")
