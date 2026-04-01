"""bootstrap full schema via SQLAlchemy metadata

Revision ID: 20251219_0004
Revises: 20251219_0003
Create Date: 2025-12-19

Originally this migration used Base.metadata.create_all() to create any
missing tables. This caused deployment failures because it would attempt
to ALTER PostGIS system tables (spatial_ref_sys) that the app user does
not own. Since every table now has its own dedicated migration, this
bootstrap is no longer needed and is a safe no-op.
"""

from __future__ import annotations


revision = "20251219_0004"
down_revision = "20251219_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
