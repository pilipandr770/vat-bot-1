"""add NIS2 security training tables

Revision ID: f17652b371c2
Revises: 58b7ef54fad9
Create Date: 2026-04-19 18:02:19.318430

"""
from alembic import op
import sqlalchemy as sa
import os

revision = 'f17652b371c2'
down_revision = '58b7ef54fad9'
branch_labels = None
depends_on = None

SCHEMA = os.environ.get('DB_SCHEMA') or None
_fk_users = f'{SCHEMA}.users.id' if SCHEMA else 'users.id'
_fk_trainings = f'{SCHEMA}.nis2_trainings.id' if SCHEMA else 'nis2_trainings.id'


def upgrade():
    op.create_table(
        'nis2_trainings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('topic', sa.String(length=50), nullable=True),
        sa.Column('content_md', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('audience_json', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], [_fk_users], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    with op.batch_alter_table('nis2_trainings', schema=SCHEMA) as batch_op:
        batch_op.create_index('ix_nis2_trainings_status', ['status'], unique=False)
        batch_op.create_index('ix_nis2_trainings_user_id', ['user_id'], unique=False)

    op.create_table(
        'nis2_training_acks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('training_id', sa.Integer(), nullable=False),
        sa.Column('recipient_name', sa.String(length=200), nullable=False),
        sa.Column('recipient_email', sa.String(length=200), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('confirmed_name', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['training_id'], [_fk_trainings], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    with op.batch_alter_table('nis2_training_acks', schema=SCHEMA) as batch_op:
        batch_op.create_index('ix_nis2_training_acks_token', ['token'], unique=True)
        batch_op.create_index('ix_nis2_training_acks_training_id', ['training_id'], unique=False)


def downgrade():
    with op.batch_alter_table('nis2_training_acks', schema=SCHEMA) as batch_op:
        batch_op.drop_index('ix_nis2_training_acks_training_id')
        batch_op.drop_index('ix_nis2_training_acks_token')
    op.drop_table('nis2_training_acks', schema=SCHEMA)

    with op.batch_alter_table('nis2_trainings', schema=SCHEMA) as batch_op:
        batch_op.drop_index('ix_nis2_trainings_user_id')
        batch_op.drop_index('ix_nis2_trainings_status')
    op.drop_table('nis2_trainings', schema=SCHEMA)
