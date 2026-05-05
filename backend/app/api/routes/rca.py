"""
api/routes/rca.py
─────────────────
POST /incidents/{id}/rca – Submit or update the Root Cause Analysis.
GET  /incidents/{id}/rca – Fetch the RCA for an incident.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.db.models.work_item import WorkItem, RCA
from app.schemas import RCACreate, RCAOut
from app.workflow.rca_validator import validate_rca, RCAValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/incidents", tags=["RCA"])


@router.post("/{incident_id}/rca", response_model=RCAOut, status_code=201)
async def submit_rca(
    incident_id: UUID,
    body: RCACreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a Root Cause Analysis for an incident.

    - Validates completeness before saving.
    - Replaces existing RCA if one already exists.
    - Does NOT automatically close the incident (that's a separate step).
    """
    # Confirm the Work Item exists
    result = await db.execute(select(WorkItem).where(WorkItem.id == incident_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Validate the RCA data
    rca_dict = body.model_dump()
    try:
        validate_rca(rca_dict)
    except RCAValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={"message": "RCA validation failed", "errors": e.reasons}
        )

    # Check if RCA already exists → update it
    existing = await db.execute(select(RCA).where(RCA.work_item_id == incident_id))
    rca = existing.scalar_one_or_none()

    if rca:
        rca.incident_start      = body.incident_start
        rca.incident_end        = body.incident_end
        rca.root_cause_category = body.root_cause_category
        rca.fix_applied         = body.fix_applied
        rca.prevention_steps    = body.prevention_steps
    else:
        rca = RCA(
            work_item_id=incident_id,
            **body.model_dump()
        )
        db.add(rca)

    await db.commit()
    await db.refresh(rca)

    logger.info(f"[RCA] Submitted for incident {incident_id}")
    return rca


@router.get("/{incident_id}/rca", response_model=RCAOut)
async def get_rca(incident_id: UUID, db: AsyncSession = Depends(get_db)):
    """Fetch the RCA for an incident."""
    result = await db.execute(select(RCA).where(RCA.work_item_id == incident_id))
    rca = result.scalar_one_or_none()
    if not rca:
        raise HTTPException(status_code=404, detail="No RCA found for this incident")
    return rca
