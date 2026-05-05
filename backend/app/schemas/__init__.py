"""
schemas/signal.py  – Input schema for incoming signals
schemas/work_item.py – Work Item request/response schemas
schemas/rca.py – RCA request/response schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════════════════════════════
# SIGNAL SCHEMAS
# ═══════════════════════════════════════════════════════════════════════

class SignalIn(BaseModel):
    """Shape of a signal posted by monitoring agents."""
    component_id:   str = Field(..., min_length=1, max_length=128,
                                description="e.g. CACHE_CLUSTER_01")
    component_type: str = Field(..., min_length=1, max_length=64,
                                description="RDBMS | CACHE | API | QUEUE | MCP_HOST | NOSQL")
    error_code:     str = Field(..., description="e.g. CONNECTION_TIMEOUT")
    message:        str = Field(default="", max_length=1024)
    severity:       str = Field(default="P2", pattern="^P[0-3]$")
    metadata:       dict = Field(default_factory=dict)

    @field_validator("component_type")
    @classmethod
    def upper_component_type(cls, v: str) -> str:
        return v.upper()

    @field_validator("severity")
    @classmethod
    def upper_severity(cls, v: str) -> str:
        return v.upper()


class SignalOut(BaseModel):
    """What we return to the caller after accepting a signal."""
    accepted: bool
    signal_id: str
    work_item_id: Optional[str] = None
    message: str


# ═══════════════════════════════════════════════════════════════════════
# WORK ITEM SCHEMAS
# ═══════════════════════════════════════════════════════════════════════

class WorkItemOut(BaseModel):
    """Full Work Item as returned by the API."""
    model_config = {"from_attributes": True}

    id:              UUID
    component_id:    str
    component_type:  str
    priority:        str
    status:          str
    title:           str
    signal_count:    str
    created_at:      datetime
    updated_at:      datetime
    mttr_minutes:    Optional[float] = None
    rca:             Optional["RCAOut"] = None


class StatusTransitionIn(BaseModel):
    """Request body to change Work Item status."""
    status: str = Field(..., description="OPEN | INVESTIGATING | RESOLVED | CLOSED")


# ═══════════════════════════════════════════════════════════════════════
# RCA SCHEMAS
# ═══════════════════════════════════════════════════════════════════════

class RCACreate(BaseModel):
    """Request body to submit an RCA."""
    incident_start:      datetime
    incident_end:        datetime
    root_cause_category: str = Field(..., min_length=1, max_length=128)
    fix_applied:         str = Field(..., min_length=10)
    prevention_steps:    str = Field(..., min_length=10)


class RCAOut(BaseModel):
    """RCA as returned in API responses."""
    model_config = {"from_attributes": True}

    id:                  UUID
    work_item_id:        UUID
    incident_start:      datetime
    incident_end:        datetime
    root_cause_category: str
    fix_applied:         str
    prevention_steps:    str
    submitted_at:        datetime


# Forward reference resolution
WorkItemOut.model_rebuild()
