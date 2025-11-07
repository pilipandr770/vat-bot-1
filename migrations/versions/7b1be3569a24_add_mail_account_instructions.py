"""Add reply instructions field to mail accounts

Revision ID: 7b1be3569a24
Revises: 2de5c7b8a921
Create Date: 2025-11-07 18:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b1be3569a24'
down_revision = '2de5c7b8a921'
branch_labels = None
depends_on = None

SCHEMA = 'vat_verification'


def upgrade():
    op.add_column(
        'mail_account',
        sa.Column('reply_instructions', sa.Text(), nullable=True),
        schema=SCHEMA
    )


def downgrade():
    op.drop_column('mail_account', 'reply_instructions', schema=SCHEMA)
