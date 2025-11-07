"""Add mail sync tracking fields

Revision ID: 2de5c7b8a921
Revises: f9b5e3a7c2d4
Create Date: 2025-11-07 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2de5c7b8a921'
down_revision = 'f9b5e3a7c2d4'
branch_labels = None
depends_on = None

SCHEMA = 'vat_verification'


def upgrade():
    op.add_column('mail_account', sa.Column('last_sync_at', sa.DateTime(), nullable=True), schema=SCHEMA)
    op.add_column('mail_account', sa.Column('last_history_id', sa.String(length=255), nullable=True), schema=SCHEMA)
    op.add_column('mail_message', sa.Column('body_text', sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column('mail_message', sa.Column('body_html', sa.Text(), nullable=True), schema=SCHEMA)


def downgrade():
    op.drop_column('mail_message', 'body_html', schema=SCHEMA)
    op.drop_column('mail_message', 'body_text', schema=SCHEMA)
    op.drop_column('mail_account', 'last_history_id', schema=SCHEMA)
    op.drop_column('mail_account', 'last_sync_at', schema=SCHEMA)
