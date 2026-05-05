"""
core/rate_limiter.py
────────────────────
Token Bucket rate limiter (async-safe).

HOW IT WORKS:
  Imagine a bucket that holds tokens. Tokens refill at a fixed rate.
  Each request consumes 1 token. If bucket is empty → reject with 429.
  This smooths out bursts without blocking the event loop.
"""
import asyncio
import time


class TokenBucketLimiter:
    def __init__(self, rate: int = 1000, capacity: int = 5000):
        """
        Args:
            rate:     tokens added per second (= max sustained req/sec)
            capacity: max burst size (bucket depth)
        """
        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """
        Try to consume 1 token.
        Returns True if allowed, False if rate limit exceeded.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            # Add tokens proportional to time elapsed
            self._tokens = min(
                self.capacity,
                self._tokens + elapsed * self.rate
            )
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    @property
    def available_tokens(self) -> float:
        return self._tokens
