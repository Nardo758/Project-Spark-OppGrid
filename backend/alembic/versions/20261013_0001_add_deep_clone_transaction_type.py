"""Add DEEP_CLONE to the transactions type enum

Revision ID: 20261013_0001
Revises: 20260513_0001
Create Date: 2026-10-13

SQLAlchemy Enum(TransactionType) persists member names on PostgreSQL
in a native enum named transactiontype. This adds DEEP_CLONE when that
type already exists. Downgrade is a no-op: PostgreSQL cannot drop an
enum value that may already be stored.
"""
from alembic import op
import sqlalchemy as sa


revision = "20261013_0001"
down_revision = "20260513_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    exists = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transactiontype')")
    ).scalar()
    if not exists:
        return
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'DEEP_CLONE'")


def downgrade() -> None:
    pass
