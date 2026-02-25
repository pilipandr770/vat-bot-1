"""add blog_posts table

Revision ID: b3f1a2c9d8e7
Revises: 6264f693f114
Create Date: 2026-02-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import os

# revision identifiers, used by Alembic.
revision = 'b3f1a2c9d8e7'
down_revision = '6264f693f114'
branch_labels = None
depends_on = None

SCHEMA = os.environ.get('DB_SCHEMA', 'public')


def upgrade():
    op.create_table(
        'blog_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('slug', sa.String(length=300), nullable=False),
        sa.Column('meta_description', sa.String(length=500), nullable=True),
        sa.Column('meta_keywords', sa.String(length=500), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('tags_json', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('source_title', sa.String(length=300), nullable=True),
        sa.Column('read_time_minutes', sa.Integer(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=True, default=0),
        sa.Column('is_published', sa.Boolean(), nullable=True, default=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('schema_markup', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        schema=SCHEMA
    )
    op.create_index('ix_blog_posts_slug', 'blog_posts', ['slug'], unique=True, schema=SCHEMA)
    op.create_index('ix_blog_posts_published_at', 'blog_posts', ['published_at'], schema=SCHEMA)
    op.create_index('ix_blog_posts_category', 'blog_posts', ['category'], schema=SCHEMA)
    op.create_index('ix_blog_posts_is_published', 'blog_posts', ['is_published'], schema=SCHEMA)


def downgrade():
    op.drop_index('ix_blog_posts_is_published', table_name='blog_posts', schema=SCHEMA)
    op.drop_index('ix_blog_posts_category', table_name='blog_posts', schema=SCHEMA)
    op.drop_index('ix_blog_posts_published_at', table_name='blog_posts', schema=SCHEMA)
    op.drop_index('ix_blog_posts_slug', table_name='blog_posts', schema=SCHEMA)
    op.drop_table('blog_posts', schema=SCHEMA)
