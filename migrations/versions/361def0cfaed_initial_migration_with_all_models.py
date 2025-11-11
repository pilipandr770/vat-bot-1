"""Initial migration with all models

Revision ID: 361def0cfaed
Revises: 
Create Date: 2025-10-03 10:33:24.189840

"""
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '361def0cfaed'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    schema = os.environ.get('DB_SCHEMA', 'public')

    def table_exists(table_name: str) -> bool:
        current_inspector = inspect(op.get_bind())
        return table_name in current_inspector.get_table_names(schema=schema)

    def column_exists(table_name: str, column_name: str) -> bool:
        current_inspector = inspect(op.get_bind())
        if table_name not in current_inspector.get_table_names(schema=schema):
            return False
        columns = {col['name'] for col in current_inspector.get_columns(table_name, schema=schema)}
        return column_name in columns

    schema_kwargs = {'schema': schema}

    if not table_exists('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('email', sa.String(length=120), nullable=False),
            sa.Column('password_hash', sa.String(length=255), nullable=False),
            sa.Column('company_name', sa.String(length=200), nullable=True),
            sa.Column('first_name', sa.String(length=100), nullable=True),
            sa.Column('last_name', sa.String(length=100), nullable=True),
            sa.Column('phone', sa.String(length=50), nullable=True),
            sa.Column('country', sa.String(length=2), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('is_admin', sa.Boolean(), nullable=True),
            sa.Column('is_email_confirmed', sa.Boolean(), nullable=True),
            sa.Column('email_confirmation_token', sa.String(length=100), nullable=True),
            sa.Column('password_reset_token', sa.String(length=100), nullable=True),
            sa.Column('password_reset_expires', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_login', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email_confirmation_token'),
            sa.UniqueConstraint('password_reset_token'),
            **schema_kwargs,
        )
        with op.batch_alter_table('users', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_users_created_at'), ['created_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    if not table_exists('companies'):
        op.create_table(
            'companies',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('vat_number', sa.String(length=20), nullable=False),
            sa.Column('company_name', sa.String(length=255), nullable=False),
            sa.Column('legal_address', sa.Text(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=True),
            sa.Column('phone', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], [f'{schema}.users.id']),
            **schema_kwargs,
        )
        with op.batch_alter_table('companies', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_companies_user_id'), ['user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_companies_vat_number'), ['vat_number'], unique=False)

    if not table_exists('counterparties'):
        op.create_table(
            'counterparties',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('vat_number', sa.String(length=20), nullable=True),
            sa.Column('company_name', sa.String(length=255), nullable=False),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('email', sa.String(length=255), nullable=True),
            sa.Column('domain', sa.String(length=255), nullable=True),
            sa.Column('contact_person', sa.String(length=255), nullable=True),
            sa.Column('country', sa.String(length=5), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], [f'{schema}.users.id']),
            **schema_kwargs,
        )
        with op.batch_alter_table('counterparties', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_counterparties_user_id'), ['user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_counterparties_company_name'), ['company_name'], unique=False)

    if not table_exists('verification_checks'):
        op.create_table(
            'verification_checks',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('company_id', sa.Integer(), nullable=False),
            sa.Column('counterparty_id', sa.Integer(), nullable=False),
            sa.Column('check_date', sa.DateTime(), nullable=True),
            sa.Column('overall_status', sa.String(length=20), nullable=False),
            sa.Column('confidence_score', sa.Float(), nullable=True),
            sa.Column('is_monitoring_active', sa.Boolean(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], [f'{schema}.users.id']),
            sa.ForeignKeyConstraint(['company_id'], [f'{schema}.companies.id']),
            sa.ForeignKeyConstraint(['counterparty_id'], [f'{schema}.counterparties.id']),
            **schema_kwargs,
        )
        with op.batch_alter_table('verification_checks', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_verification_checks_check_date'), ['check_date'], unique=False)
            batch_op.create_index(batch_op.f('ix_verification_checks_user_id'), ['user_id'], unique=False)

    if not column_exists('verification_checks', 'user_id'):
        with op.batch_alter_table('verification_checks', schema=schema) as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_verification_checks_user_id', f'{schema}.users', ['user_id'], ['id'])

    if not table_exists('check_results'):
        op.create_table(
            'check_results',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('check_id', sa.Integer(), nullable=False),
            sa.Column('service_name', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('confidence_score', sa.Float(), nullable=True),
            sa.Column('data_json', sa.Text(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('response_time_ms', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['check_id'], [f'{schema}.verification_checks.id'], ondelete='CASCADE'),
            **schema_kwargs,
        )
        with op.batch_alter_table('check_results', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_check_results_service_name'), ['service_name'], unique=False)
            batch_op.create_index(batch_op.f('ix_check_results_created_at'), ['created_at'], unique=False)

    if not table_exists('alerts'):
        op.create_table(
            'alerts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('check_id', sa.Integer(), nullable=False),
            sa.Column('alert_type', sa.String(length=50), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('severity', sa.String(length=20), nullable=False),
            sa.Column('is_sent', sa.Boolean(), nullable=True),
            sa.Column('sent_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['check_id'], [f'{schema}.verification_checks.id']),
            **schema_kwargs,
        )
        with op.batch_alter_table('alerts', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_alerts_created_at'), ['created_at'], unique=False)

    if not table_exists('subscriptions'):
        op.create_table(
            'subscriptions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('plan', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('stripe_subscription_id', sa.String(length=100), nullable=True),
            sa.Column('stripe_customer_id', sa.String(length=100), nullable=True),
            sa.Column('api_calls_limit', sa.Integer(), nullable=True),
            sa.Column('api_calls_used', sa.Integer(), nullable=True),
            sa.Column('start_date', sa.DateTime(), nullable=True),
            sa.Column('end_date', sa.DateTime(), nullable=True),
            sa.Column('canceled_at', sa.DateTime(), nullable=True),
            sa.Column('monthly_price', sa.Float(), nullable=True),
            sa.Column('currency', sa.String(length=3), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], [f'{schema}.users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('stripe_subscription_id'),
            **schema_kwargs,
        )
        with op.batch_alter_table('subscriptions', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_subscriptions_plan'), ['plan'], unique=False)
            batch_op.create_index(batch_op.f('ix_subscriptions_status'), ['status'], unique=False)

    if not table_exists('payments'):
        op.create_table(
            'payments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('subscription_id', sa.Integer(), nullable=True),
            sa.Column('stripe_payment_intent_id', sa.String(length=100), nullable=True),
            sa.Column('stripe_invoice_id', sa.String(length=100), nullable=True),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('currency', sa.String(length=3), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('invoice_url', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['subscription_id'], [f'{schema}.subscriptions.id']),
            sa.ForeignKeyConstraint(['user_id'], [f'{schema}.users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('stripe_payment_intent_id'),
            **schema_kwargs,
        )
        with op.batch_alter_table('payments', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_payments_created_at'), ['created_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_payments_status'), ['status'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    schema = os.environ.get('DB_SCHEMA', 'public')

    def table_exists(table_name: str) -> bool:
        current_inspector = inspect(op.get_bind())
        return table_name in current_inspector.get_table_names(schema=schema)

    schema_kwargs = {'schema': schema}

    def drop_indexes(table_name: str, index_names: list[str]) -> None:
        existing_indexes = {idx['name'] for idx in inspect(op.get_bind()).get_indexes(table_name, schema=schema)}
        with op.batch_alter_table(table_name, schema=schema) as batch_op:
            for idx_name in index_names:
                if idx_name in existing_indexes:
                    batch_op.drop_index(idx_name)

    if table_exists('payments'):
        drop_indexes('payments', [op.f('ix_payments_status'), op.f('ix_payments_created_at')])
        op.drop_table('payments', **schema_kwargs)

    if table_exists('subscriptions'):
        drop_indexes('subscriptions', [op.f('ix_subscriptions_status'), op.f('ix_subscriptions_plan')])
        op.drop_table('subscriptions', **schema_kwargs)

    if table_exists('alerts'):
        drop_indexes('alerts', [op.f('ix_alerts_created_at')])
        op.drop_table('alerts', **schema_kwargs)

    if table_exists('check_results'):
        drop_indexes('check_results', [op.f('ix_check_results_created_at'), op.f('ix_check_results_service_name')])
        op.drop_table('check_results', **schema_kwargs)

    if table_exists('verification_checks'):
        fk_names = {fk['name'] for fk in inspect(op.get_bind()).get_foreign_keys('verification_checks', schema=schema)}
        with op.batch_alter_table('verification_checks', schema=schema) as batch_op:
            if 'fk_verification_checks_user_id' in fk_names:
                batch_op.drop_constraint('fk_verification_checks_user_id', type_='foreignkey')
        drop_indexes('verification_checks', [op.f('ix_verification_checks_user_id'), op.f('ix_verification_checks_check_date')])
        op.drop_table('verification_checks', **schema_kwargs)

    if table_exists('counterparties'):
        drop_indexes('counterparties', [op.f('ix_counterparties_company_name'), op.f('ix_counterparties_user_id')])
        op.drop_table('counterparties', **schema_kwargs)

    if table_exists('companies'):
        drop_indexes('companies', [op.f('ix_companies_vat_number'), op.f('ix_companies_user_id')])
        op.drop_table('companies', **schema_kwargs)

    if table_exists('users'):
        drop_indexes('users', [op.f('ix_users_email'), op.f('ix_users_created_at')])
        op.drop_table('users', **schema_kwargs)
    # ### end Alembic commands ###
