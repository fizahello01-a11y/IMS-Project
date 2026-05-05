"""
db/redis.py
───────────
Redis client using aioredis (async).
Used as HOT-PATH CACHE – dashboard state lives here.
"""
import json
from redis.asyncio import Redis, from_url

from app.config import settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = await from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def cache_set(key: str, value: dict, ttl: int = None) -> None:
    r = await get_redis()
    ttl = ttl or settings.redis_ttl_seconds
    await r.setex(key, ttl, json.dumps(value, default=str))


async def cache_get(key: str) -> dict | None:
    r = await get_redis()
    data = await r.get(key)
    return json.loads(data) if data else None


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def cache_increment(key: str) -> int:
    """Atomic counter – used for throughput metrics."""
    r = await get_redis()
    return await r.incr(key)
