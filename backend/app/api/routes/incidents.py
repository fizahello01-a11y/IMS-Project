"""
api/routes/incidents.py
───────────────────────
CRUD endpoints for Work Items (incidents).

GET  /incidents          – list active incidents (cached in Redis)
GET  /incidents/{id}     – get single incident with signals
PATCH /incidents/{id}/status – transition state (State Machine)
"""
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.postgres import get_db
from app.db.redis import cache_get, cache_set, cache_delete
from app.db.models.work_item import WorkItem, RCA
from app.schemas import WorkItemOut, StatusTransitionIn
from app.workflow.state_machine import WorkItemStateMachine, Status
from app.workflow.rca_validator import validate_rca, RCAValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/incidents", tags=["Incidents"])

CACHE_KEY = "dashboard:active_incidents"


@router.get("", response_model=list[WorkItemOut])
async def list_incidents(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List Work Items, sorted by priority then creation time.
    Results are cached in Redis for 30 seconds.
    """
    cache_key = f"{CACHE_KEY}:{status or 'all'}"

    # Try Redis cache first (hot path)
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Cache miss → query PostgreSQL
    query = select(WorkItem).options(selectinload(WorkItem.rca)).order_by(
        WorkItem.priority.asc(),      # P0 before P2
        desc(WorkItem.created_at)
    )
    if status:
        query = query.where(WorkItem.status == status.upper())

    result = await db.execute(query)
    items = result.scalars().all()

    # Serialize for cache + response
    serialized = [WorkItemOut.model_validate(i).model_dump(mode="json") for i in items]
    await cache_set(cache_key, serialized)

    return serialized


@router.get("/{incident_id}", response_model=WorkItemOut)
async def get_incident(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single Work Item with its RCA."""
    result = await db.execute(
        select(WorkItem)
        .options(selectinload(WorkItem.rca))
        .where(WorkItem.id == incident_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Incident not found")
    return item


@router.patch("/{incident_id}/status", response_model=WorkItemOut)
async def transition_status(
    incident_id: UUID,
    body: StatusTransitionIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Transition Work Item to a new status using the State Machine.

    Rules:
    - Transitions must follow: OPEN → INVESTIGATING → RESOLVED → CLOSED
    - CLOSED requires a complete RCA (validated here)
    """
    result = await db.execute(
        select(WorkItem)
        .options(selectinload(WorkItem.rca))
        .where(WorkItem.id == incident_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Validate state machine transition
    try:
        target = Status(body.status.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown status: {body.status}")

    sm = WorkItemStateMachine(Status(item.status))
    try:
        sm.transition(target)   # raises ValueError if invalid
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # ── CLOSED gate: must have complete RCA ───────────────────────────
    if target == Status.CLOSED:
        rca_dict = None
        if item.rca:
            rca_dict = {
                "root_cause_category": item.rca.root_cause_category,
                "fix_applied":         item.rca.fix_applied,
                "prevention_steps":    item.rca.prevention_steps,
                "incident_start":      item.rca.incident_start,
                "incident_end":        item.rca.incident_end,
            }
        try:
            validate_rca(rca_dict)
        except RCAValidationError as e:
            raise HTTPException(
                status_code=422,
                detail={"message": "Cannot close incident – RCA incomplete", "errors": e.reasons}
            )

        # Calculate MTTR
        from app.workflow.rca_validator import calculate_mttr
        item.mttr_minutes = calculate_mttr(item.rca.incident_start, item.rca.incident_end)

    item.status = target.value
    await db.commit()
    await db.refresh(item)

    # Invalidate cache so dashboard reflects new status
    await cache_delete(f"{CACHE_KEY}:all")
    await cache_delete(f"{CACHE_KEY}:{target.value}")

    logger.info(f"[Incident] {incident_id} → {target.value}")
    return item
