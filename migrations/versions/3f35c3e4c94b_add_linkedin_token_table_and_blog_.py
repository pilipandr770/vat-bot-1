"""Add LinkedIn token table and blog linkedin fields

Revision ID: 3f35c3e4c94b
Revises: f1e2d3c4b5a6
Create Date: 2026-04-14 23:55:28.668954

"""
from alembic import op
import sqlalchemy as sa
import os

# revision identifiers, used by Alembic.
revision = '3f35c3e4c94b'
down_revision = 'f1e2d3c4b5a6'
branch_labels = None
depends_on = None

SCHEMA = os.environ.get('DB_SCHEMA') or None


def upgrade():
    # Create linkedin_tokens table
    op.create_table(
        'linkedin_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('organization_id', sa.String(length=50), nullable=True),
        sa.Column('member_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )

    # Add LinkedIn fields to blog_posts
    with op.batch_alter_table('blog_posts', schema=SCHEMA) as batch_op:
        batch_op.add_column(sa.Column('linkedin_post_id', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('linkedin_posted_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('blog_posts', schema=SCHEMA) as batch_op:
        batch_op.drop_column('linkedin_posted_at')
        batch_op.drop_column('linkedin_post_id')

    op.drop_table('linkedin_tokens', schema=SCHEMA)

    op.create_table('linkedin_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('access_token', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('organization_id', sa.String(length=50), nullable=True),
    sa.Column('member_id', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    schema='vat_verification'
    )
    with op.batch_alter_table('teamguard_phishing_tests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_teamguard_phishing_tests_owner_user_id'))
        batch_op.drop_index(batch_op.f('ix_teamguard_phishing_tests_tracking_token'))

    op.drop_table('teamguard_phishing_tests')
    with op.batch_alter_table('teamguard_phishing_clicks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_teamguard_phishing_clicks_member_id'))
        batch_op.drop_index(batch_op.f('ix_teamguard_phishing_clicks_test_id'))

    op.drop_table('teamguard_phishing_clicks')
    with op.batch_alter_table('teamguard_security_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_teamguard_security_events_created_at'))
        batch_op.drop_index(batch_op.f('ix_teamguard_security_events_member_id'))
        batch_op.drop_index(batch_op.f('ix_teamguard_security_events_owner_user_id'))

    op.drop_table('teamguard_security_events')
    with op.batch_alter_table('teamguard_password_assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_teamguard_password_assignments_member_id'))

    op.drop_table('teamguard_password_assignments')
    op.drop_table('teamguard_password_policy')
    with op.batch_alter_table('teamguard_members', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_teamguard_members_owner_user_id'))

    op.drop_table('teamguard_members')
    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('alerts_check_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'verification_checks', ['check_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('blog_posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('linkedin_post_id', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('linkedin_posted_at', sa.DateTime(), nullable=True))
        batch_op.drop_constraint(batch_op.f('blog_posts_slug_key'), type_='unique')
        batch_op.drop_index(batch_op.f('ix_blog_posts_category'))
        batch_op.drop_index(batch_op.f('ix_blog_posts_is_published'))
        batch_op.drop_index(batch_op.f('ix_blog_posts_published_at'))
        batch_op.drop_index(batch_op.f('ix_blog_posts_slug'))
        batch_op.create_index(batch_op.f('ix_vat_verification_blog_posts_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_vat_verification_blog_posts_is_published'), ['is_published'], unique=False)
        batch_op.create_index(batch_op.f('ix_vat_verification_blog_posts_published_at'), ['published_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_vat_verification_blog_posts_slug'), ['slug'], unique=True)

    with op.batch_alter_table('check_results', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('check_results_check_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'verification_checks', ['check_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('companies_user_id_fkey1'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'users', ['user_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('counterparties', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('counterparties_user_id_fkey1'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'users', ['user_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('known_counterparty', schema=None) as batch_op:
        batch_op.alter_column('trust_level',
               existing_type=postgresql.ENUM('low', 'medium', 'high', 'vip', name='trust_levels'),
               type_=sa.Enum('low', 'medium', 'high', 'vip', name='trust_levels', schema='vat_verification'),
               existing_nullable=True)

    with op.batch_alter_table('mail_account', schema=None) as batch_op:
        batch_op.alter_column('provider',
               existing_type=postgresql.ENUM('gmail', 'outlook', 'imap', name='provider_types'),
               type_=sa.Enum('gmail', 'outlook', 'imap', name='provider_types', schema='vat_verification'),
               existing_nullable=False)
        batch_op.drop_constraint(batch_op.f('mail_account_user_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'users', ['user_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('mail_draft', schema=None) as batch_op:
        batch_op.alter_column('suggested_by',
               existing_type=postgresql.ENUM('assistant', 'rule', 'manual', name='suggested_by_types'),
               type_=sa.Enum('assistant', 'rule', 'manual', name='suggested_by_types', schema='vat_verification'),
               existing_nullable=True)
        batch_op.drop_constraint(batch_op.f('mail_draft_account_id_fkey'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('mail_draft_message_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'mail_message', ['message_id'], ['id'], referent_schema='vat_verification')
        batch_op.create_foreign_key(None, 'mail_account', ['account_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('mail_message', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=postgresql.ENUM('new', 'scanned', 'drafted', 'sent', 'quarantined', 'skipped', name='status_types'),
               type_=sa.Enum('new', 'scanned', 'drafted', 'sent', 'quarantined', 'skipped', name='status_types', schema='vat_verification'),
               existing_nullable=True)
        batch_op.drop_constraint(batch_op.f('mail_message_account_id_fkey'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('mail_message_counterparty_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'mail_account', ['account_id'], ['id'], referent_schema='vat_verification')
        batch_op.create_foreign_key(None, 'known_counterparty', ['counterparty_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('mail_rule', schema=None) as batch_op:
        batch_op.alter_column('action',
               existing_type=postgresql.ENUM('auto_reply', 'draft', 'quarantine', 'ignore', name='action_types'),
               type_=sa.Enum('auto_reply', 'draft', 'quarantine', 'ignore', name='action_types', schema='vat_verification'),
               existing_nullable=True)

    with op.batch_alter_table('osint_findings', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('osint_findings_scan_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'osint_scans', ['scan_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('payments_subscription_id_fkey'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('payments_user_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'users', ['user_id'], ['id'], referent_schema='vat_verification')
        batch_op.create_foreign_key(None, 'subscriptions', ['subscription_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('pentesting_logs', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('pentesting_logs_user_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'users', ['user_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('pentesting_quotas', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('pentesting_quotas_subscription_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'subscriptions', ['subscription_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('scan_report', schema=None) as batch_op:
        batch_op.alter_column('verdict',
               existing_type=postgresql.ENUM('safe', 'suspicious', 'malicious', name='verdict_types'),
               type_=sa.Enum('safe', 'suspicious', 'malicious', name='verdict_types', schema='vat_verification'),
               existing_nullable=False)
        batch_op.drop_constraint(batch_op.f('scan_report_message_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'mail_message', ['message_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('subscriptions_user_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'users', ['user_id'], ['id'], referent_schema='vat_verification')

    with op.batch_alter_table('verification_checks', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('verification_checks_counterparty_id_fkey'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('verification_checks_company_id_fkey'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('verification_checks_user_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(None, 'counterparties', ['counterparty_id'], ['id'], referent_schema='vat_verification')
        batch_op.create_foreign_key(None, 'users', ['user_id'], ['id'], referent_schema='vat_verification')
        batch_op.create_foreign_key(None, 'companies', ['company_id'], ['id'], referent_schema='vat_verification')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('verification_checks', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('verification_checks_user_id_fkey'), 'users', ['user_id'], ['id'])
        batch_op.create_foreign_key(batch_op.f('verification_checks_company_id_fkey'), 'companies', ['company_id'], ['id'])
        batch_op.create_foreign_key(batch_op.f('verification_checks_counterparty_id_fkey'), 'counterparties', ['counterparty_id'], ['id'])

    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('subscriptions_user_id_fkey'), 'users', ['user_id'], ['id'])

    with op.batch_alter_table('scan_report', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('scan_report_message_id_fkey'), 'mail_message', ['message_id'], ['id'])
        batch_op.alter_column('verdict',
               existing_type=sa.Enum('safe', 'suspicious', 'malicious', name='verdict_types', schema='vat_verification'),
               type_=postgresql.ENUM('safe', 'suspicious', 'malicious', name='verdict_types'),
               existing_nullable=False)

    with op.batch_alter_table('pentesting_quotas', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('pentesting_quotas_subscription_id_fkey'), 'subscriptions', ['subscription_id'], ['id'])

    with op.batch_alter_table('pentesting_logs', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('pentesting_logs_user_id_fkey'), 'users', ['user_id'], ['id'])

    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('payments_user_id_fkey'), 'users', ['user_id'], ['id'])
        batch_op.create_foreign_key(batch_op.f('payments_subscription_id_fkey'), 'subscriptions', ['subscription_id'], ['id'])

    with op.batch_alter_table('osint_findings', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('osint_findings_scan_id_fkey'), 'osint_scans', ['scan_id'], ['id'])

    with op.batch_alter_table('mail_rule', schema=None) as batch_op:
        batch_op.alter_column('action',
               existing_type=sa.Enum('auto_reply', 'draft', 'quarantine', 'ignore', name='action_types', schema='vat_verification'),
               type_=postgresql.ENUM('auto_reply', 'draft', 'quarantine', 'ignore', name='action_types'),
               existing_nullable=True)

    with op.batch_alter_table('mail_message', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('mail_message_counterparty_id_fkey'), 'known_counterparty', ['counterparty_id'], ['id'])
        batch_op.create_foreign_key(batch_op.f('mail_message_account_id_fkey'), 'mail_account', ['account_id'], ['id'])
        batch_op.alter_column('status',
               existing_type=sa.Enum('new', 'scanned', 'drafted', 'sent', 'quarantined', 'skipped', name='status_types', schema='vat_verification'),
               type_=postgresql.ENUM('new', 'scanned', 'drafted', 'sent', 'quarantined', 'skipped', name='status_types'),
               existing_nullable=True)

    with op.batch_alter_table('mail_draft', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('mail_draft_message_id_fkey'), 'mail_message', ['message_id'], ['id'])
        batch_op.create_foreign_key(batch_op.f('mail_draft_account_id_fkey'), 'mail_account', ['account_id'], ['id'])
        batch_op.alter_column('suggested_by',
               existing_type=sa.Enum('assistant', 'rule', 'manual', name='suggested_by_types', schema='vat_verification'),
               type_=postgresql.ENUM('assistant', 'rule', 'manual', name='suggested_by_types'),
               existing_nullable=True)

    with op.batch_alter_table('mail_account', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('mail_account_user_id_fkey'), 'users', ['user_id'], ['id'])
        batch_op.alter_column('provider',
               existing_type=sa.Enum('gmail', 'outlook', 'imap', name='provider_types', schema='vat_verification'),
               type_=postgresql.ENUM('gmail', 'outlook', 'imap', name='provider_types'),
               existing_nullable=False)

    with op.batch_alter_table('known_counterparty', schema=None) as batch_op:
        batch_op.alter_column('trust_level',
               existing_type=sa.Enum('low', 'medium', 'high', 'vip', name='trust_levels', schema='vat_verification'),
               type_=postgresql.ENUM('low', 'medium', 'high', 'vip', name='trust_levels'),
               existing_nullable=True)

    with op.batch_alter_table('counterparties', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('counterparties_user_id_fkey1'), 'users', ['user_id'], ['id'])

    with op.batch_alter_table('companies', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('companies_user_id_fkey1'), 'users', ['user_id'], ['id'])

    with op.batch_alter_table('check_results', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('check_results_check_id_fkey'), 'verification_checks', ['check_id'], ['id'])

    with op.batch_alter_table('blog_posts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_vat_verification_blog_posts_slug'))
        batch_op.drop_index(batch_op.f('ix_vat_verification_blog_posts_published_at'))
        batch_op.drop_index(batch_op.f('ix_vat_verification_blog_posts_is_published'))
        batch_op.drop_index(batch_op.f('ix_vat_verification_blog_posts_category'))
        batch_op.create_index(batch_op.f('ix_blog_posts_slug'), ['slug'], unique=True)
        batch_op.create_index(batch_op.f('ix_blog_posts_published_at'), ['published_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_blog_posts_is_published'), ['is_published'], unique=False)
        batch_op.create_index(batch_op.f('ix_blog_posts_category'), ['category'], unique=False)
        batch_op.create_unique_constraint(batch_op.f('blog_posts_slug_key'), ['slug'])
        batch_op.drop_column('linkedin_posted_at')
        batch_op.drop_column('linkedin_post_id')

    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('alerts_check_id_fkey'), 'verification_checks', ['check_id'], ['id'])

    op.create_table('teamguard_members',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('teamguard_members_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('owner_user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('full_name', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('email', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('position', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('access_level', sa.VARCHAR(length=20), server_default=sa.text("'employee'::character varying"), autoincrement=False, nullable=False),
    sa.Column('password_last_changed', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('password_rotation_days', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
    sa.Column('notes', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], name='teamguard_members_owner_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='teamguard_members_pkey'),
    postgresql_ignore_search_path=False
    )
    with op.batch_alter_table('teamguard_members', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_teamguard_members_owner_user_id'), ['owner_user_id'], unique=False)

    op.create_table('teamguard_password_policy',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('owner_user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('rotation_days', sa.INTEGER(), server_default=sa.text('90'), autoincrement=False, nullable=False),
    sa.Column('min_length', sa.INTEGER(), server_default=sa.text('12'), autoincrement=False, nullable=False),
    sa.Column('require_uppercase', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
    sa.Column('require_digit', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
    sa.Column('require_special', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
    sa.Column('reminder_days_before', sa.INTEGER(), server_default=sa.text('7'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], name=op.f('teamguard_password_policy_owner_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('teamguard_password_policy_pkey')),
    sa.UniqueConstraint('owner_user_id', name=op.f('teamguard_password_policy_owner_user_id_key'))
    )
    op.create_table('teamguard_password_assignments',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('member_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('password_hash', sa.VARCHAR(length=64), autoincrement=False, nullable=True),
    sa.Column('sent_via', sa.VARCHAR(length=20), server_default=sa.text("'email'::character varying"), autoincrement=False, nullable=True),
    sa.Column('sent_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('sent_by_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('acknowledged', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('acknowledged_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['member_id'], ['teamguard_members.id'], name=op.f('teamguard_password_assignments_member_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('teamguard_password_assignments_pkey'))
    )
    with op.batch_alter_table('teamguard_password_assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_teamguard_password_assignments_member_id'), ['member_id'], unique=False)

    op.create_table('teamguard_security_events',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('member_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('owner_user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('event_type', sa.VARCHAR(length=50), autoincrement=False, nullable=False),
    sa.Column('description', sa.VARCHAR(length=500), autoincrement=False, nullable=True),
    sa.Column('performed_by', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['member_id'], ['teamguard_members.id'], name=op.f('teamguard_security_events_member_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('teamguard_security_events_pkey'))
    )
    with op.batch_alter_table('teamguard_security_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_teamguard_security_events_owner_user_id'), ['owner_user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_teamguard_security_events_member_id'), ['member_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_teamguard_security_events_created_at'), ['created_at'], unique=False)

    op.create_table('teamguard_phishing_clicks',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('test_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('member_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('clicked_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('ip_hash', sa.VARCHAR(length=64), autoincrement=False, nullable=True),
    sa.Column('user_agent_snippet', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['member_id'], ['teamguard_members.id'], name=op.f('teamguard_phishing_clicks_member_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['test_id'], ['teamguard_phishing_tests.id'], name=op.f('teamguard_phishing_clicks_test_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('teamguard_phishing_clicks_pkey'))
    )
    with op.batch_alter_table('teamguard_phishing_clicks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_teamguard_phishing_clicks_test_id'), ['test_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_teamguard_phishing_clicks_member_id'), ['member_id'], unique=False)

    op.create_table('teamguard_phishing_tests',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('owner_user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('subject_line', sa.VARCHAR(length=300), autoincrement=False, nullable=False),
    sa.Column('template_type', sa.VARCHAR(length=30), server_default=sa.text("'link_click'::character varying"), autoincrement=False, nullable=False),
    sa.Column('tracking_token', sa.VARCHAR(length=64), autoincrement=False, nullable=False),
    sa.Column('sent_to_member_ids_json', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('status', sa.VARCHAR(length=20), server_default=sa.text("'draft'::character varying"), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('sent_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('completed_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], name=op.f('teamguard_phishing_tests_owner_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('teamguard_phishing_tests_pkey')),
    sa.UniqueConstraint('tracking_token', name=op.f('teamguard_phishing_tests_tracking_token_key'))
    )
    with op.batch_alter_table('teamguard_phishing_tests', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_teamguard_phishing_tests_tracking_token'), ['tracking_token'], unique=False)
        batch_op.create_index(batch_op.f('ix_teamguard_phishing_tests_owner_user_id'), ['owner_user_id'], unique=False)

    op.drop_table('linkedin_tokens', schema='vat_verification')
    # ### end Alembic commands ###
