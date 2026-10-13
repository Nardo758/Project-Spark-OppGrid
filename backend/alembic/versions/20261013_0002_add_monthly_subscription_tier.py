"""Add MONTHLY to the subscriptions tier enum

Revision ID: 20261013_0002
Revises: 20261013_0001
Create Date: 2026-10-13

SQLAlchemy Enum(SubscriptionTier) persists member values on PostgreSQL.
This adds MONTHLY ('OppGrid Monthly') when that native enum already exists.
Downgrade is a no-op: PostgreSQL cannot drop an enum value that may already
be stored, and existing subscriber rows are left in place.
"""
import re

from alembic import op
import sqlalchemy as sa


revision = "20261013_0002"
down_revision = "20261013_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    row = conn.execute(
        sa.text(
            """
            SELECT t.typname
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_type t ON a.atttypid = t.oid
            WHERE c.relname = 'subscriptions'
              AND a.attname = 'tier'
              AND t.typtype = 'e'
            """
        )
    ).fetchone()
    if not row:
        return
    typname = row[0]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", typname or ""):
        return
    with op.get_context().autocommit_block():
        op.execute(f"ALTER TYPE {typname} ADD VALUE IF NOT EXISTS 'MONTHLY'")


def downgrade() -> None:
    pass
