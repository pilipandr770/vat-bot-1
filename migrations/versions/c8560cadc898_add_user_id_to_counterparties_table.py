"""Add user_id to counterparties table

Revision ID: c8560cadc898
Revises: cd954586ac25
Create Date: 2025-10-27 23:58:27.752486

"""
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'c8560cadc898'
down_revision = 'cd954586ac25'
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

    def index_exists(table_name: str, index_name: str) -> bool:
        current_inspector = inspect(op.get_bind())
        indexes = {idx['name'] for idx in current_inspector.get_indexes(table_name, schema=schema)}
        return index_name in indexes

    def fk_exists(table_name: str, fk_name: str) -> bool:
        current_inspector = inspect(op.get_bind())
        fks = {fk['name'] for fk in current_inspector.get_foreign_keys(table_name, schema=schema)}
        return fk_name in fks

    if table_exists('companies'):
        has_column = column_exists('companies', 'user_id')
        needs_index = not index_exists('companies', op.f('ix_companies_user_id'))
        needs_fk = not fk_exists('companies', 'fk_companies_user_id')

        if not has_column or needs_index or needs_fk:
            with op.batch_alter_table('companies', schema=schema) as batch_op:
                if not has_column:
                    batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
                if needs_index:
                    batch_op.create_index(batch_op.f('ix_companies_user_id'), ['user_id'], unique=False)
                if needs_fk:
                    batch_op.create_foreign_key(
                        'fk_companies_user_id',
                        'users',
                        ['user_id'],
                        ['id'],
                        referent_schema=schema,
                    )

    if table_exists('counterparties'):
        has_column = column_exists('counterparties', 'user_id')
        needs_index = not index_exists('counterparties', op.f('ix_counterparties_user_id'))
        needs_fk = not fk_exists('counterparties', 'fk_counterparties_user_id')

        if not has_column or needs_index or needs_fk:
            with op.batch_alter_table('counterparties', schema=schema) as batch_op:
                if not has_column:
                    batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
                if needs_index:
                    batch_op.create_index(batch_op.f('ix_counterparties_user_id'), ['user_id'], unique=False)
                if needs_fk:
                    batch_op.create_foreign_key(
                        'fk_counterparties_user_id',
                        'users',
                        ['user_id'],
                        ['id'],
                        referent_schema=schema,
                    )

    if table_exists('verification_checks') and column_exists('verification_checks', 'user_id'):
        column_info = next(
            (
                col
                for col in inspect(op.get_bind()).get_columns('verification_checks', schema=schema)
                if col['name'] == 'user_id'
            ),
            None,
        )
        needs_alter = bool(column_info and column_info.get('nullable'))
        needs_index = not index_exists('verification_checks', op.f('ix_verification_checks_user_id'))

        if needs_alter or needs_index:
            with op.batch_alter_table('verification_checks', schema=schema) as batch_op:
                if needs_alter:
                    batch_op.alter_column('user_id', existing_type=sa.INTEGER(), nullable=False)
                if needs_index:
                    batch_op.create_index(batch_op.f('ix_verification_checks_user_id'), ['user_id'], unique=False)


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

    def index_exists(table_name: str, index_name: str) -> bool:
        current_inspector = inspect(op.get_bind())
        indexes = {idx['name'] for idx in current_inspector.get_indexes(table_name, schema=schema)}
        return index_name in indexes

    def fk_exists(table_name: str, fk_name: str) -> bool:
        current_inspector = inspect(op.get_bind())
        fks = {fk['name'] for fk in current_inspector.get_foreign_keys(table_name, schema=schema)}
        return fk_name in fks

    if table_exists('verification_checks') and column_exists('verification_checks', 'user_id'):
        column_info = next(
            (
                col
                for col in inspect(op.get_bind()).get_columns('verification_checks', schema=schema)
                if col['name'] == 'user_id'
            ),
            None,
        )
        needs_alter = bool(column_info and not column_info.get('nullable'))
        needs_index_drop = index_exists('verification_checks', op.f('ix_verification_checks_user_id'))

        if needs_alter or needs_index_drop:
            with op.batch_alter_table('verification_checks', schema=schema) as batch_op:
                if needs_index_drop:
                    batch_op.drop_index(batch_op.f('ix_verification_checks_user_id'))
                if needs_alter:
                    batch_op.alter_column('user_id', existing_type=sa.INTEGER(), nullable=True)

    if table_exists('counterparties') and column_exists('counterparties', 'user_id'):
        drop_index = index_exists('counterparties', op.f('ix_counterparties_user_id'))
        drop_fk = fk_exists('counterparties', 'fk_counterparties_user_id')

        with op.batch_alter_table('counterparties', schema=schema) as batch_op:
            if drop_fk:
                batch_op.drop_constraint('fk_counterparties_user_id', type_='foreignkey')
            if drop_index:
                batch_op.drop_index(batch_op.f('ix_counterparties_user_id'))
            batch_op.drop_column('user_id')

    if table_exists('companies') and column_exists('companies', 'user_id'):
        drop_index = index_exists('companies', op.f('ix_companies_user_id'))
        drop_fk = fk_exists('companies', 'fk_companies_user_id')

        with op.batch_alter_table('companies', schema=schema) as batch_op:
            if drop_fk:
                batch_op.drop_constraint('fk_companies_user_id', type_='foreignkey')
            if drop_index:
                batch_op.drop_index(batch_op.f('ix_companies_user_id'))
            batch_op.drop_column('user_id')
