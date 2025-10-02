"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-10-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create companies table
    op.create_table('companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vat_number', sa.String(length=20), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('legal_address', sa.Text(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_vat_number'), 'companies', ['vat_number'], unique=False)

    # Create counterparties table
    op.create_table('counterparties',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vat_number', sa.String(length=20), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('contact_person', sa.String(length=255), nullable=True),
        sa.Column('country', sa.String(length=5), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_counterparties_company_name'), 'counterparties', ['company_name'], unique=False)
    op.create_index(op.f('ix_counterparties_country'), 'counterparties', ['country'], unique=False)
    op.create_index(op.f('ix_counterparties_vat_number'), 'counterparties', ['vat_number'], unique=False)

    # Create verification_checks table
    op.create_table('verification_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('counterparty_id', sa.Integer(), nullable=False),
        sa.Column('check_date', sa.DateTime(), nullable=True),
        sa.Column('overall_status', sa.String(length=20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('is_monitoring_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['counterparty_id'], ['counterparties.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verification_checks_check_date'), 'verification_checks', ['check_date'], unique=False)

    # Create check_results table
    op.create_table('check_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('check_id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('data_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['check_id'], ['verification_checks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_check_results_created_at'), 'check_results', ['created_at'], unique=False)
    op.create_index(op.f('ix_check_results_service_name'), 'check_results', ['service_name'], unique=False)

    # Create alerts table
    op.create_table('alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('check_id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('is_sent', sa.Boolean(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['check_id'], ['verification_checks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alerts_created_at'), 'alerts', ['created_at'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_alerts_created_at'), table_name='alerts')
    op.drop_table('alerts')
    op.drop_index(op.f('ix_check_results_service_name'), table_name='check_results')
    op.drop_index(op.f('ix_check_results_created_at'), table_name='check_results')
    op.drop_table('check_results')
    op.drop_index(op.f('ix_verification_checks_check_date'), table_name='verification_checks')
    op.drop_table('verification_checks')
    op.drop_index(op.f('ix_counterparties_vat_number'), table_name='counterparties')
    op.drop_index(op.f('ix_counterparties_country'), table_name='counterparties')
    op.drop_index(op.f('ix_counterparties_company_name'), table_name='counterparties')
    op.drop_table('counterparties')
    op.drop_index(op.f('ix_companies_vat_number'), table_name='companies')
    op.drop_table('companies')