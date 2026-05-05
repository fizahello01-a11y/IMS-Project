"""
db/models/work_item.py
──────────────────────
SQLAlchemy ORM models for PostgreSQL.
These define the table schema for Work Items and RCA records.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, Float, ForeignKey, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(timezone.utc)


class WorkItem(Base):
    """
    A Work Item represents one deduplicated incident.
    Many raw signals → one Work Item (via debounce engine).
    """
    __tablename__ = "work_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component_id    = Column(String(128), nullable=False, index=True)
    component_type  = Column(String(64),  nullable=False)   # RDBMS, CACHE, API …
    priority        = Column(String(8),   nullable=False)   # P0, P1, P2
    status          = Column(String(32), nullable=False, default="OPEN", index=True)
    title           = Column(String(256), nullable=False)
    signal_count    = Column(String(16),  nullable=False, default="1")  # stored as str for easy display
    created_at      = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at      = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    # MTTR is auto-calculated when RCA is submitted
    mttr_minutes    = Column(Float, nullable=True)

    rca = relationship("RCA", back_populates="work_item", uselist=False, cascade="all, delete-orphan")


class RCA(Base):
    """
    Root Cause Analysis record.
    A Work Item CANNOT move to CLOSED without a complete RCA.
    """
    __tablename__ = "rca_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_item_id = Column(UUID(as_uuid=True), ForeignKey("work_items.id", ondelete="CASCADE"), unique=True, nullable=False)

    incident_start      = Column(DateTime(timezone=True), nullable=False)
    incident_end        = Column(DateTime(timezone=True), nullable=False)
    root_cause_category = Column(String(128), nullable=False)   # e.g. "Network Partition"
    fix_applied         = Column(Text, nullable=False)
    prevention_steps    = Column(Text, nullable=False)
    submitted_at        = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    work_item = relationship("WorkItem", back_populates="rca")