"""Add OSINT tables

Revision ID: cd954586ac25
Revises: 361def0cfaed
Create Date: 2025-10-18 20:24:22.408820

"""
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'cd954586ac25'
down_revision = '361def0cfaed'
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

    def index_exists(table_name: str, index_name: str) -> bool:
        current_inspector = inspect(op.get_bind())
        indexes = {idx['name'] for idx in current_inspector.get_indexes(table_name, schema=schema)}
        return index_name in indexes

    if not table_exists('osint_scans'):
        op.create_table(
            'osint_scans',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('url', sa.String(length=512), nullable=True),
            sa.Column('domain', sa.String(length=255), nullable=True),
            sa.Column('email', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            **schema_kwargs,
        )
        with op.batch_alter_table('osint_scans', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_osint_scans_created_at'), ['created_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_osint_scans_domain'), ['domain'], unique=False)
            batch_op.create_index(batch_op.f('ix_osint_scans_email'), ['email'], unique=False)

    if not table_exists('osint_findings'):
        op.create_table(
            'osint_findings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('scan_id', sa.Integer(), nullable=False),
            sa.Column('service', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('data_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['scan_id'], [f'{schema}.osint_scans.id']),
            sa.PrimaryKeyConstraint('id'),
            **schema_kwargs,
        )
        with op.batch_alter_table('osint_findings', schema=schema) as batch_op:
            batch_op.create_index(batch_op.f('ix_osint_findings_created_at'), ['created_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_osint_findings_scan_id'), ['scan_id'], unique=False)

    if not column_exists('companies', 'user_id'):
        with op.batch_alter_table('companies', schema=schema) as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f('ix_companies_user_id'), ['user_id'], unique=False)
            batch_op.create_foreign_key('fk_companies_user_id', f'{schema}.users', ['user_id'], ['id'])

    if not column_exists('counterparties', 'user_id'):
        with op.batch_alter_table('counterparties', schema=schema) as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f('ix_counterparties_user_id'), ['user_id'], unique=False)
            batch_op.create_foreign_key('fk_counterparties_user_id', f'{schema}.users', ['user_id'], ['id'])

    if column_exists('verification_checks', 'user_id'):
        index_name = op.f('ix_verification_checks_user_id')
        needs_index = not index_exists('verification_checks', index_name)
        with op.batch_alter_table('verification_checks', schema=schema) as batch_op:
            batch_op.alter_column('user_id', existing_type=sa.INTEGER(), nullable=False)
            if needs_index:
                batch_op.create_index(index_name, ['user_id'], unique=False)

    # ### end Alembic commands ###


def downgrade():
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

    if column_exists('verification_checks', 'user_id'):
        indexes = {idx['name'] for idx in inspect(op.get_bind()).get_indexes('verification_checks', schema=schema)}
        with op.batch_alter_table('verification_checks', schema=schema) as batch_op:
            if op.f('ix_verification_checks_user_id') in indexes:
                batch_op.drop_index(batch_op.f('ix_verification_checks_user_id'))
            batch_op.alter_column('user_id', existing_type=sa.INTEGER(), nullable=True)

    if column_exists('counterparties', 'user_id'):
        indexes = {idx['name'] for idx in inspect(op.get_bind()).get_indexes('counterparties', schema=schema)}
        with op.batch_alter_table('counterparties', schema=schema) as batch_op:
            if op.f('ix_counterparties_user_id') in indexes:
                batch_op.drop_index(batch_op.f('ix_counterparties_user_id'))
            batch_op.drop_constraint('fk_counterparties_user_id', type_='foreignkey')
            batch_op.drop_column('user_id')

    if column_exists('companies', 'user_id'):
        indexes = {idx['name'] for idx in inspect(op.get_bind()).get_indexes('companies', schema=schema)}
        with op.batch_alter_table('companies', schema=schema) as batch_op:
            if op.f('ix_companies_user_id') in indexes:
                batch_op.drop_index(batch_op.f('ix_companies_user_id'))
            batch_op.drop_constraint('fk_companies_user_id', type_='foreignkey')
            batch_op.drop_column('user_id')

    if table_exists('osint_findings'):
        indexes = {idx['name'] for idx in inspect(op.get_bind()).get_indexes('osint_findings', schema=schema)}
        with op.batch_alter_table('osint_findings', schema=schema) as batch_op:
            if op.f('ix_osint_findings_scan_id') in indexes:
                batch_op.drop_index(batch_op.f('ix_osint_findings_scan_id'))
            if op.f('ix_osint_findings_created_at') in indexes:
                batch_op.drop_index(batch_op.f('ix_osint_findings_created_at'))
        op.drop_table('osint_findings', **schema_kwargs)

    if table_exists('osint_scans'):
        indexes = {idx['name'] for idx in inspect(op.get_bind()).get_indexes('osint_scans', schema=schema)}
        with op.batch_alter_table('osint_scans', schema=schema) as batch_op:
            if op.f('ix_osint_scans_email') in indexes:
                batch_op.drop_index(batch_op.f('ix_osint_scans_email'))
            if op.f('ix_osint_scans_domain') in indexes:
                batch_op.drop_index(batch_op.f('ix_osint_scans_domain'))
            if op.f('ix_osint_scans_created_at') in indexes:
                batch_op.drop_index(batch_op.f('ix_osint_scans_created_at'))
        op.drop_table('osint_scans', **schema_kwargs)
    # ### end Alembic commands ###
