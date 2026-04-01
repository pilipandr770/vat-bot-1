"""Add TeamGuard team security management tables

Revision ID: a1b2c3d4e5f6
Revises: 6264f693f114
Create Date: 2026-04-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '6264f693f114'
branch_labels = None
depends_on = None

SCHEMA = 'vat_verification'


def upgrade():
    # TeamMember table
    op.create_table(
        'teamguard_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=False),
        sa.Column('position', sa.String(length=200), nullable=True),
        sa.Column('access_level', sa.String(length=20), nullable=False, server_default='employee'),
        sa.Column('password_last_changed', sa.DateTime(), nullable=True),
        sa.Column('password_rotation_days', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_user_id'], [f'{SCHEMA}.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    with op.batch_alter_table('teamguard_members', schema=SCHEMA) as batch_op:
        batch_op.create_index('ix_teamguard_members_owner_user_id', ['owner_user_id'])

    # PasswordPolicy table
    op.create_table(
        'teamguard_password_policy',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),
        sa.Column('rotation_days', sa.Integer(), nullable=False, server_default='90'),
        sa.Column('min_length', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('require_uppercase', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('require_digit', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('require_special', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('reminder_days_before', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_user_id'], [f'{SCHEMA}.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_user_id'),
        schema=SCHEMA,
    )

    # PasswordAssignment table
    op.create_table(
        'teamguard_password_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('password_hash', sa.String(length=64), nullable=True),
        sa.Column('sent_via', sa.String(length=20), nullable=True, server_default='email'),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('sent_by_user_id', sa.Integer(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['member_id'], [f'{SCHEMA}.teamguard_members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    with op.batch_alter_table('teamguard_password_assignments', schema=SCHEMA) as batch_op:
        batch_op.create_index('ix_teamguard_password_assignments_member_id', ['member_id'])

    # SecurityEvent table
    op.create_table(
        'teamguard_security_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('performed_by', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], [f'{SCHEMA}.teamguard_members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    with op.batch_alter_table('teamguard_security_events', schema=SCHEMA) as batch_op:
        batch_op.create_index('ix_teamguard_security_events_member_id', ['member_id'])
        batch_op.create_index('ix_teamguard_security_events_owner_user_id', ['owner_user_id'])
        batch_op.create_index('ix_teamguard_security_events_created_at', ['created_at'])

    # PhishingTest table
    op.create_table(
        'teamguard_phishing_tests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('subject_line', sa.String(length=300), nullable=False),
        sa.Column('template_type', sa.String(length=30), nullable=False, server_default='link_click'),
        sa.Column('tracking_token', sa.String(length=64), nullable=False),
        sa.Column('sent_to_member_ids_json', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_user_id'], [f'{SCHEMA}.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tracking_token'),
        schema=SCHEMA,
    )
    with op.batch_alter_table('teamguard_phishing_tests', schema=SCHEMA) as batch_op:
        batch_op.create_index('ix_teamguard_phishing_tests_owner_user_id', ['owner_user_id'])
        batch_op.create_index('ix_teamguard_phishing_tests_tracking_token', ['tracking_token'])

    # PhishingClick table
    op.create_table(
        'teamguard_phishing_clicks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('clicked_at', sa.DateTime(), nullable=False),
        sa.Column('ip_hash', sa.String(length=64), nullable=True),
        sa.Column('user_agent_snippet', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['member_id'], [f'{SCHEMA}.teamguard_members.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_id'], [f'{SCHEMA}.teamguard_phishing_tests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    with op.batch_alter_table('teamguard_phishing_clicks', schema=SCHEMA) as batch_op:
        batch_op.create_index('ix_teamguard_phishing_clicks_test_id', ['test_id'])
        batch_op.create_index('ix_teamguard_phishing_clicks_member_id', ['member_id'])


def downgrade():
    op.drop_table('teamguard_phishing_clicks', schema=SCHEMA)
    op.drop_table('teamguard_phishing_tests', schema=SCHEMA)
    op.drop_table('teamguard_security_events', schema=SCHEMA)
    op.drop_table('teamguard_password_assignments', schema=SCHEMA)
    op.drop_table('teamguard_password_policy', schema=SCHEMA)
    op.drop_table('teamguard_members', schema=SCHEMA)
