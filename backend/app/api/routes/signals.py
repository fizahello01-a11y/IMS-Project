"""
api/routes/signals.py
─────────────────────
POST /signals – high-throughput signal ingestion endpoint.

Returns 202 Accepted immediately.
Actual processing happens in the background worker.
"""
from fastapi import APIRouter, HTTPException, Request
import uuid

from app.schemas import SignalIn, SignalOut

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.post("", response_model=SignalOut, status_code=202)
async def ingest_signal(signal: SignalIn, request: Request):
    """
    Accept a monitoring signal.

    - Rate limited (429 if too many requests)
    - Non-blocking (returns immediately, processed in background)
    - Debounced (100 signals for same component → 1 Work Item)
    """
    # Access shared app state (set in main.py lifespan)
    limiter = request.app.state.rate_limiter
    ring_buffer = request.app.state.ring_buffer

    # ── Rate Limit Check ──────────────────────────────────────────────
    allowed = await limiter.acquire()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down signal emission."
        )

    # ── Buffer Push (non-blocking) ────────────────────────────────────
    signal_id = str(uuid.uuid4())
    payload = {
        "signal_id": signal_id,
        **signal.model_dump(),
    }
    clean_insert = await ring_buffer.put(payload)

    return SignalOut(
        accepted=True,
        signal_id=signal_id,
        message="Signal accepted" if clean_insert else "Signal accepted (buffer near capacity)",
    )


@router.get("/raw/{work_item_id}")
async def get_raw_signals(work_item_id: str, request: Request, limit: int = 100):
    """
    Fetch raw signals for a Work Item from MongoDB.
    Used by the Incident Detail panel.
    """
    from app.db.mongo import get_mongo_db
    from app.config import settings

    db = get_mongo_db()
    col = db[settings.mongo_signals_collection]

    cursor = col.find(
        {"work_item_id": work_item_id},
        {"_id": 0}
    ).sort("received_at", -1).limit(limit)

    signals = await cursor.to_list(length=limit)
    return {"signals": signals, "count": len(signals)}
