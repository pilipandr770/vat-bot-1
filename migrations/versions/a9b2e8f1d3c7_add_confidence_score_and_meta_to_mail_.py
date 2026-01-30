"""Add confidence score and meta to mail_draft

Revision ID: a9b2e8f1d3c7
Revises: 4d68551a0bb5
Create Date: 2026-01-30 15:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
import os

# revision identifiers, used by Alembic.
revision = 'a9b2e8f1d3c7'
down_revision = '4d68551a0bb5'
branch_labels = None
depends_on = None

SCHEMA = os.environ.get('DB_SCHEMA', 'public')


def upgrade():
    """Add confidence_score and meta_json columns to mail_draft table"""
    op.add_column('mail_draft',
        sa.Column('confidence_score', sa.Float(), nullable=True),
        schema=SCHEMA
    )
    op.add_column('mail_draft',
        sa.Column('meta_json', sa.Text(), nullable=True, server_default='{}'),
        schema=SCHEMA
    )


def downgrade():
    """Remove confidence_score and meta_json columns from mail_draft table"""
    op.drop_column('mail_draft', 'confidence_score', schema=SCHEMA)
    op.drop_column('mail_draft', 'meta_json', schema=SCHEMA)
