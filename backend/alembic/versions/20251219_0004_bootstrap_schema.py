"""bootstrap full schema via SQLAlchemy metadata

Revision ID: 20251219_0004
Revises: 20251219_0003
Create Date: 2025-12-19

This migration creates any missing tables using SQLAlchemy's metadata. It exists
to support clean provisioning in new environments now that we rely on Alembic
instead of runtime `create_all()`.

NOTE (April 1, 2026): PostGIS removed - OppGrid doesn't use spatial features.
All location data stored as simple lat/lng floats. This migration no longer
tries to create PostGIS system tables, avoiding Replit deployment issues.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251219_0004"
down_revision = "20251219_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure models are registered on Base.metadata.
    import app.models  # noqa: F401
    from app.db.database import Base

    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names())

    # Create only app tables, skip any PostGIS system tables
    POSTGIS_SYSTEM_TABLES = {
        "spatial_ref_sys", "geometry_columns", "geography_columns",
        "raster_columns", "raster_overviews", "layer", "topology",
    }
    
    missing_tables = [
        t for name, t in Base.metadata.tables.items()
        if name not in existing and name not in POSTGIS_SYSTEM_TABLES
    ]
    if not missing_tables:
        return

    # Create tables without trying to handle PostGIS
    Base.metadata.create_all(bind=bind, tables=missing_tables)


def downgrade() -> None:
    # No-op: we don't attempt to drop the entire schema automatically.
    pass

