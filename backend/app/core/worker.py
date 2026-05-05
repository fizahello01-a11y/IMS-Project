"""
core/worker.py
──────────────
Background async worker that drains the ring buffer.

Flow:
  ring_buffer.get() → debounce → save signal to MongoDB
                                → maybe create Work Item in PostgreSQL
                                → invalidate Redis cache
                                → send alert

Uses tenacity for retry logic on DB writes.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.core.buffer import RingBuffer
from app.core.debounce import DebounceEngine
from app.core.metrics import MetricsCollector
from app.db.postgres import AsyncSessionLocal
from app.db.mongo import get_mongo_db
from app.db.redis import cache_delete
from app.db.models.work_item import WorkItem
from app.workflow.alerting.base import get_alert_strategy

logger = logging.getLogger(__name__)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _save_signal_to_mongo(signal: dict):
    """Save raw signal to MongoDB with retry."""
    db = get_mongo_db()
    col = db[settings.mongo_signals_collection]
    await col.insert_one(signal)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _create_work_item(session: AsyncSession, signal: dict) -> WorkItem:
    """Create a Work Item in PostgreSQL with retry."""
    strategy = get_alert_strategy(signal["component_type"])
    priority = strategy.get_priority()

    work_item = WorkItem(
        id=uuid.uuid4(),
        component_id=signal["component_id"],
        component_type=signal["component_type"],
        priority=priority,
        status="OPEN",
        title=f"[{priority}] {signal['component_type']} issue on {signal['component_id']}",
        signal_count="1",
    )
    session.add(work_item)
    await session.commit()
    await session.refresh(work_item)
    return work_item


async def process_signal(
    signal: dict,
    debounce: DebounceEngine,
    metrics: MetricsCollector,
):
    """
    Process one signal from the ring buffer:
    1. Record metrics
    2. Debounce check
    3. Save raw signal to MongoDB
    4. Maybe create Work Item in PostgreSQL
    5. Invalidate Redis cache
    6. Send alert
    """
    await metrics.record_signal()

    component_id = signal.get("component_id", "UNKNOWN")
    should_create, existing_work_item_id = await debounce.process(component_id, signal)

    # Determine work_item_id
    work_item_id = existing_work_item_id

    if should_create:
        try:
            async with AsyncSessionLocal() as session:
                work_item = await _create_work_item(session, signal)
                work_item_id = str(work_item.id)
                await debounce.set_work_item_id(component_id, work_item_id)

            # Send alert (Strategy Pattern)
            strategy = get_alert_strategy(signal["component_type"])
            await strategy.send({
                "id": work_item_id,
                "component_id": component_id,
                "component_type": signal.get("component_type"),
            })

            # Invalidate dashboard cache so UI sees the new incident
            await cache_delete("dashboard:active_incidents")
            logger.info(f"[Worker] Created Work Item {work_item_id} for {component_id}")
        except Exception as e:
            logger.error(f"[Worker] Failed to create Work Item: {e}")
    else:
        # Increment signal count in PostgreSQL (best-effort, not critical path)
        if work_item_id and work_item_id != "__pending__":
            try:
                from sqlalchemy import text as sql_text
                async with AsyncSessionLocal() as session:
                    await session.execute(
                        sql_text(
                            "UPDATE work_items SET signal_count = (CAST(signal_count AS INTEGER) + 1)::TEXT "
                            "WHERE id = :id"
                        ),
                        {"id": work_item_id},
                    )
                    await session.commit()
            except Exception:
                pass  # non-critical – audit log in MongoDB is the source of truth

    # Save raw signal to MongoDB (audit log — always happens)
    enriched_signal = {
        **signal,
        "_id": str(uuid.uuid4()),
        "work_item_id": work_item_id,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await _save_signal_to_mongo(enriched_signal)
    except Exception as e:
        logger.error(f"[Worker] MongoDB write failed after retries: {e}")


async def drain_worker(ring_buffer: RingBuffer, debounce: DebounceEngine, metrics: MetricsCollector):
    """
    Long-running background task.
    Continuously drains the ring buffer and processes each signal.
    """
    logger.info("[Worker] Buffer drain worker started")
    while True:
        try:
            signal = await ring_buffer.get()
            # Process concurrently – don't await sequentially (slow)
            asyncio.create_task(process_signal(signal, debounce, metrics))
            ring_buffer.task_done()
        except asyncio.CancelledError:
            logger.info("[Worker] Drain worker shutting down")
            break
        except Exception as e:
            logger.error(f"[Worker] Unexpected error: {e}")
            await asyncio.sleep(0.1)
