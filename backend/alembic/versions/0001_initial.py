"""Initial migration – create work_items and rca_records tables.

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'work_items',
        sa.Column('id',             postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('component_id',   sa.String(128), nullable=False),
        sa.Column('component_type', sa.String(64),  nullable=False),
        sa.Column('priority',       sa.String(8),   nullable=False),
        sa.Column('status',         sa.String(32),  nullable=False, server_default='OPEN'),
        sa.Column('title',          sa.String(256), nullable=False),
        sa.Column('signal_count',   sa.String(16),  nullable=False, server_default='1'),
        sa.Column('created_at',     sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at',     sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('mttr_minutes',   sa.Float(), nullable=True),
    )
    op.create_index('ix_work_items_component_id', 'work_items', ['component_id'])
    op.create_index('ix_work_items_status',       'work_items', ['status'])

    op.create_table(
        'rca_records',
        sa.Column('id',                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('work_item_id',        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('work_items.id', ondelete='CASCADE'),
                  unique=True, nullable=False),
        sa.Column('incident_start',      sa.DateTime(timezone=True), nullable=False),
        sa.Column('incident_end',        sa.DateTime(timezone=True), nullable=False),
        sa.Column('root_cause_category', sa.String(128), nullable=False),
        sa.Column('fix_applied',         sa.Text(), nullable=False),
        sa.Column('prevention_steps',    sa.Text(), nullable=False),
        sa.Column('submitted_at',        sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('rca_records')
    op.drop_table('work_items')