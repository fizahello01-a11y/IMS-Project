"""
api/routes/health.py
────────────────────
GET /health  – liveness + dependency health check
GET /metrics – throughput and buffer stats
"""
from fastapi import APIRouter, Request
from sqlalchemy import text

from app.db.postgres import AsyncSessionLocal
from app.db.mongo import get_mongo_db
from app.db.redis import get_redis

router = APIRouter(tags=["Observability"])


@router.get("/health")
async def health(request: Request):
    """
    Returns the health of all downstream dependencies.
    Used by Docker Compose health checks and load balancers.
    """
    status = {"status": "ok", "services": {}}

    # PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        status["services"]["postgres"] = "ok"
    except Exception as e:
        status["services"]["postgres"] = f"error: {e}"
        status["status"] = "degraded"

    # MongoDB
    try:
        db = get_mongo_db()
        await db.command("ping")
        status["services"]["mongo"] = "ok"
    except Exception as e:
        status["services"]["mongo"] = f"error: {e}"
        status["status"] = "degraded"

    # Redis
    try:
        r = await get_redis()
        await r.ping()
        status["services"]["redis"] = "ok"
    except Exception as e:
        status["services"]["redis"] = f"error: {e}"
        status["status"] = "degraded"

    # Buffer stats
    buf = request.app.state.ring_buffer
    status["buffer"] = {
        "size":     buf.size,
        "capacity": buf.capacity,
        "dropped":  buf.dropped,
    }

    return status


@router.get("/metrics")
async def metrics(request: Request):
    """Throughput and system metrics."""
    m = request.app.state.metrics
    buf = request.app.state.ring_buffer
    return {
        "signals_per_sec": await m.current_rate(),
        "total_signals":   m.total,
        "buffer_size":     buf.size,
        "buffer_capacity": buf.capacity,
        "buffer_dropped":  buf.dropped,
    }
