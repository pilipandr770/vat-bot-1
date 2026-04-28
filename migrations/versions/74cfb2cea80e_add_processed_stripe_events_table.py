"""add processed_stripe_events table

Revision ID: 74cfb2cea80e
Revises: d1e2f3a4b5c6
Create Date: 2026-04-28 18:00:00.000000

Adds deduplication log for Stripe webhook events to prevent double-processing
on retries (idempotency guard).
"""
from alembic import op
import sqlalchemy as sa
import os

revision = '74cfb2cea80e'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None

SCHEMA = os.environ.get('DB_SCHEMA') or None


def upgrade():
    op.create_table(
        'processed_stripe_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stripe_event_id', sa.String(length=100), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_event_id'),
        schema=SCHEMA,
    )
    op.create_index(
        'ix_processed_stripe_events_stripe_event_id',
        'processed_stripe_events',
        ['stripe_event_id'],
        unique=True,
        schema=SCHEMA,
    )


def downgrade():
    op.drop_index(
        'ix_processed_stripe_events_stripe_event_id',
        table_name='processed_stripe_events',
        schema=SCHEMA,
    )
    op.drop_table('processed_stripe_events', schema=SCHEMA)
