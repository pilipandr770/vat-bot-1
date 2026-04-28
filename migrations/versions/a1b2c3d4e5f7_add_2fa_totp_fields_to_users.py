"""add 2fa totp fields to users

Revision ID: a1b2c3d4e5f7
Revises: 74cfb2cea80e
Create Date: 2026-04-28 20:00:00.000000

Adds TOTP two-factor authentication fields to the users table.
"""
from alembic import op
import sqlalchemy as sa
import os

revision = 'a1b2c3d4e5f7'
down_revision = '74cfb2cea80e'
branch_labels = None
depends_on = None

SCHEMA = os.environ.get('DB_SCHEMA') or None


def upgrade():
    op.add_column(
        'users',
        sa.Column('totp_secret', sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        'users',
        sa.Column('totp_enabled', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')),
        schema=SCHEMA,
    )


def downgrade():
    op.drop_column('users', 'totp_enabled', schema=SCHEMA)
    op.drop_column('users', 'totp_secret', schema=SCHEMA)
