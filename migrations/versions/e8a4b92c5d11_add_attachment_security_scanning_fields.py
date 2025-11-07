"""Add attachment security scanning fields to MailMessage

Revision ID: e8a4b92c5d11
Revises: cd954586ac25
Create Date: 2025-11-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8a4b92c5d11'
down_revision = 'cd954586ac25'
branch_labels = None
depends_on = None


def upgrade():
    """Add fields for storing attachment scan results and quarantine status"""
    # Add new columns to mail_messages table
    with op.batch_alter_table('mail_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('attachments_json', sa.Text(), nullable=True, server_default='[]'))
        batch_op.add_column(sa.Column('has_attachments', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('has_dangerous_attachments', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('is_quarantined', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('quarantine_reason', sa.String(length=500), nullable=True))
    
    # Set default values for existing records
    op.execute("UPDATE mail_messages SET attachments_json = '[]' WHERE attachments_json IS NULL")
    op.execute("UPDATE mail_messages SET has_attachments = false WHERE has_attachments IS NULL")
    op.execute("UPDATE mail_messages SET has_dangerous_attachments = false WHERE has_dangerous_attachments IS NULL")
    op.execute("UPDATE mail_messages SET is_quarantined = false WHERE is_quarantined IS NULL")


def downgrade():
    """Remove attachment scanning fields"""
    with op.batch_alter_table('mail_messages', schema=None) as batch_op:
        batch_op.drop_column('quarantine_reason')
        batch_op.drop_column('is_quarantined')
        batch_op.drop_column('has_dangerous_attachments')
        batch_op.drop_column('has_attachments')
        batch_op.drop_column('attachments_json')
