"""Fix: create TeamGuard tables that may be missing in production

This migration compensates for a1b2c3d4e5f6 which was inserted into the
middle of the chain after production was already at ec82571c3e51.
Uses IF NOT EXISTS so it is safe to run on both old and new databases.

Revision ID: d1e2f3a4b5c6
Revises: ec82571c3e51
Create Date: 2026-04-20 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'd1e2f3a4b5c6'
down_revision = 'ec82571c3e51'
branch_labels = None
depends_on = None

SCHEMA = 'vat_verification'


def upgrade():
    conn = op.get_bind()

    # ── teamguard_members ────────────────────────────────────────
    conn.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.teamguard_members (
            id                    SERIAL PRIMARY KEY,
            owner_user_id         INTEGER NOT NULL
                REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            full_name             VARCHAR(200) NOT NULL,
            email                 VARCHAR(200) NOT NULL,
            position              VARCHAR(200),
            access_level          VARCHAR(20) NOT NULL DEFAULT 'employee',
            password_last_changed TIMESTAMP,
            password_rotation_days INTEGER,
            is_active             BOOLEAN NOT NULL DEFAULT true,
            notes                 TEXT,
            created_at            TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at            TIMESTAMP
        )
    """))
    conn.execute(sa.text(f"""
        CREATE INDEX IF NOT EXISTS ix_teamguard_members_owner_user_id
            ON {SCHEMA}.teamguard_members (owner_user_id)
    """))

    # ── teamguard_password_policy ────────────────────────────────
    conn.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.teamguard_password_policy (
            id                   SERIAL PRIMARY KEY,
            owner_user_id        INTEGER NOT NULL UNIQUE
                REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            rotation_days        INTEGER NOT NULL DEFAULT 90,
            min_length           INTEGER NOT NULL DEFAULT 12,
            require_uppercase    BOOLEAN NOT NULL DEFAULT true,
            require_digit        BOOLEAN NOT NULL DEFAULT true,
            require_special      BOOLEAN NOT NULL DEFAULT true,
            reminder_days_before INTEGER NOT NULL DEFAULT 7,
            updated_at           TIMESTAMP
        )
    """))

    # ── teamguard_password_assignments ───────────────────────────
    conn.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.teamguard_password_assignments (
            id              SERIAL PRIMARY KEY,
            member_id       INTEGER NOT NULL
                REFERENCES {SCHEMA}.teamguard_members(id) ON DELETE CASCADE,
            password_hash   VARCHAR(64),
            sent_via        VARCHAR(20) DEFAULT 'email',
            sent_at         TIMESTAMP NOT NULL,
            sent_by_user_id INTEGER,
            acknowledged    BOOLEAN NOT NULL DEFAULT false,
            acknowledged_at TIMESTAMP
        )
    """))
    conn.execute(sa.text(f"""
        CREATE INDEX IF NOT EXISTS ix_teamguard_password_assignments_member_id
            ON {SCHEMA}.teamguard_password_assignments (member_id)
    """))

    # ── teamguard_security_events ────────────────────────────────
    conn.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.teamguard_security_events (
            id           SERIAL PRIMARY KEY,
            member_id    INTEGER NOT NULL
                REFERENCES {SCHEMA}.teamguard_members(id) ON DELETE CASCADE,
            owner_user_id INTEGER NOT NULL,
            event_type   VARCHAR(50) NOT NULL,
            description  VARCHAR(500),
            performed_by VARCHAR(200),
            created_at   TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """))
    conn.execute(sa.text(f"""
        CREATE INDEX IF NOT EXISTS ix_teamguard_security_events_member_id
            ON {SCHEMA}.teamguard_security_events (member_id)
    """))
    conn.execute(sa.text(f"""
        CREATE INDEX IF NOT EXISTS ix_teamguard_security_events_owner_user_id
            ON {SCHEMA}.teamguard_security_events (owner_user_id)
    """))
    conn.execute(sa.text(f"""
        CREATE INDEX IF NOT EXISTS ix_teamguard_security_events_created_at
            ON {SCHEMA}.teamguard_security_events (created_at)
    """))

    # ── teamguard_phishing_tests ─────────────────────────────────
    conn.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.teamguard_phishing_tests (
            id                      SERIAL PRIMARY KEY,
            owner_user_id           INTEGER NOT NULL
                REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            name                    VARCHAR(200) NOT NULL,
            subject_line            VARCHAR(300) NOT NULL,
            template_type           VARCHAR(30) NOT NULL DEFAULT 'link_click',
            tracking_token          VARCHAR(64) NOT NULL UNIQUE,
            sent_to_member_ids_json TEXT,
            status                  VARCHAR(20) NOT NULL DEFAULT 'draft',
            created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
            sent_at                 TIMESTAMP,
            completed_at            TIMESTAMP
        )
    """))
    conn.execute(sa.text(f"""
        CREATE INDEX IF NOT EXISTS ix_teamguard_phishing_tests_owner_user_id
            ON {SCHEMA}.teamguard_phishing_tests (owner_user_id)
    """))
    conn.execute(sa.text(f"""
        CREATE INDEX IF NOT EXISTS ix_teamguard_phishing_tests_tracking_token
            ON {SCHEMA}.teamguard_phishing_tests (tracking_token)
    """))

    # ── teamguard_phishing_clicks ────────────────────────────────
    conn.execute(sa.text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.teamguard_phishing_clicks (
            id                  SERIAL PRIMARY KEY,
            test_id             INTEGER NOT NULL
                REFERENCES {SCHEMA}.teamguard_phishing_tests(id) ON DELETE CASCADE,
            member_id           INTEGER NOT NULL
                REFERENCES {SCHEMA}.teamguard_members(id) ON DELETE CASCADE,
            clicked_at          TIMESTAMP NOT NULL,
            ip_hash             VARCHAR(64),
            user_agent_snippet  VARCHAR(200)
        )
    """))
    conn.execute(sa.text(f"""
        CREATE INDEX IF NOT EXISTS ix_teamguard_phishing_clicks_test_id
            ON {SCHEMA}.teamguard_phishing_clicks (test_id)
    """))
    conn.execute(sa.text(f"""
        CREATE INDEX IF NOT EXISTS ix_teamguard_phishing_clicks_member_id
            ON {SCHEMA}.teamguard_phishing_clicks (member_id)
    """))


def downgrade():
    conn = op.get_bind()
    for tbl in [
        'teamguard_phishing_clicks',
        'teamguard_phishing_tests',
        'teamguard_security_events',
        'teamguard_password_assignments',
        'teamguard_password_policy',
        'teamguard_members',
    ]:
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {SCHEMA}.{tbl} CASCADE"))
