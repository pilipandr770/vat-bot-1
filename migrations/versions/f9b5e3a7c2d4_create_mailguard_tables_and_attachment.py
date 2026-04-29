"""Create MailGuard tables and add attachment scanning fields

Revision ID: f9b5e3a7c2d4
Revises: af13f0999271
Create Date: 2025-11-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import os

# revision identifiers, used by Alembic.
revision = 'f9b5e3a7c2d4'
down_revision = 'af13f0999271'
branch_labels = None
depends_on = None

SCHEMA = os.environ.get('DB_SCHEMA') or None
_s = f'{SCHEMA}.' if SCHEMA else ''


def upgrade():
    # Drop existing enum types if they exist (from failed migrations)
    op.execute(f'DROP TYPE IF EXISTS {_s}provider_types CASCADE')
    op.execute(f'DROP TYPE IF EXISTS {_s}action_types CASCADE')
    op.execute(f'DROP TYPE IF EXISTS {_s}status_types CASCADE')
    op.execute(f'DROP TYPE IF EXISTS {_s}suggested_by_types CASCADE')
    op.execute(f'DROP TYPE IF EXISTS {_s}verdict_types CASCADE')

    # Create mail_account table
    op.create_table('mail_account',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('provider', sa.Enum('gmail', 'outlook', 'imap', name='provider_types', schema=SCHEMA), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('access_token', sa.Text(), nullable=True),
    sa.Column('refresh_token', sa.Text(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('host', sa.String(length=255), nullable=True),
    sa.Column('port', sa.Integer(), nullable=True),
    sa.Column('login', sa.String(length=255), nullable=True),
    sa.Column('password', sa.Text(), nullable=True),
    sa.Column('settings_json', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], [f'{_s}users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA
    )

    # Create known_counterparty table
    op.create_table('known_counterparty',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('domain', sa.String(length=255), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('priority', sa.Integer(), nullable=True),
    sa.Column('assistant_profile_id', sa.String(length=100), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA
    )

    # Create mail_rule table
    op.create_table('mail_rule',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_enabled', sa.Boolean(), nullable=True),
    sa.Column('match_from', sa.String(length=255), nullable=True),
    sa.Column('match_domain', sa.String(length=255), nullable=True),
    sa.Column('match_subject_regex', sa.String(length=500), nullable=True),
    sa.Column('action', sa.Enum('auto_reply', 'draft', 'quarantine', 'ignore', name='action_types', schema=SCHEMA), nullable=True),
    sa.Column('requires_human', sa.Boolean(), nullable=True),
    sa.Column('workhours_json', sa.Text(), nullable=True),
    sa.Column('priority', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA
    )

    # Create mail_message table WITH attachment scanning fields
    op.create_table('mail_message',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('provider_msg_id', sa.String(length=255), nullable=False),
    sa.Column('thread_id', sa.String(length=255), nullable=True),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('counterparty_id', sa.Integer(), nullable=True),
    sa.Column('from_email', sa.String(length=255), nullable=False),
    sa.Column('subject', sa.String(length=500), nullable=False),
    sa.Column('received_at', sa.DateTime(), nullable=False),
    sa.Column('risk_score', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('new', 'scanned', 'drafted', 'sent', 'quarantined', 'skipped', name='status_types', schema=SCHEMA), nullable=True),
    sa.Column('labels', sa.String(length=500), nullable=True),
    sa.Column('meta_json', sa.Text(), nullable=True),
    # Attachment scanning fields
    sa.Column('attachments_json', sa.Text(), nullable=True),
    sa.Column('has_attachments', sa.Boolean(), nullable=True),
    sa.Column('has_dangerous_attachments', sa.Boolean(), nullable=True),
    sa.Column('is_quarantined', sa.Boolean(), nullable=True),
    sa.Column('quarantine_reason', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], [f'{_s}mail_account.id'], ),
    sa.ForeignKeyConstraint(['counterparty_id'], [f'{_s}known_counterparty.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider_msg_id'),
    schema=SCHEMA
    )

    # Create mail_draft table
    op.create_table('mail_draft',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('to_email', sa.String(length=255), nullable=False),
    sa.Column('subject', sa.String(length=500), nullable=False),
    sa.Column('body_html', sa.Text(), nullable=True),
    sa.Column('body_text', sa.Text(), nullable=True),
    sa.Column('attachments_json', sa.Text(), nullable=True),
    sa.Column('suggested_by', sa.Enum('assistant', 'rule', 'manual', name='suggested_by_types', schema=SCHEMA), nullable=True),
    sa.Column('approved_by_user', sa.Boolean(), nullable=True),
    sa.Column('sent_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], [f'{_s}mail_account.id'], ),
    sa.ForeignKeyConstraint(['message_id'], [f'{_s}mail_message.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA
    )

    # Create scan_report table
    op.create_table('scan_report',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=False),
    sa.Column('verdict', sa.Enum('safe', 'suspicious', 'malicious', name='verdict_types', schema=SCHEMA), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.Column('details_json', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['message_id'], [f'{_s}mail_message.id'], ),
    sa.PrimaryKeyConstraint('id'),
    schema=SCHEMA
    )


def downgrade():
    op.drop_table('scan_report', schema=SCHEMA)
    op.drop_table('mail_draft', schema=SCHEMA)
    op.drop_table('mail_message', schema=SCHEMA)
    op.drop_table('mail_rule', schema=SCHEMA)
    op.drop_table('known_counterparty', schema=SCHEMA)
    op.drop_table('mail_account', schema=SCHEMA)

    # Drop enums
    op.execute(f'DROP TYPE IF EXISTS {_s}provider_types')
    op.execute(f'DROP TYPE IF EXISTS {_s}action_types')
    op.execute(f'DROP TYPE IF EXISTS {_s}status_types')
    op.execute(f'DROP TYPE IF EXISTS {_s}suggested_by_types')
    op.execute(f'DROP TYPE IF EXISTS {_s}verdict_types')
