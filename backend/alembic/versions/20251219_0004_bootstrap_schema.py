"""bootstrap full schema via SQLAlchemy metadata

Revision ID: 20251219_0004
Revises: 20251219_0003
Create Date: 2025-12-19

This migration creates any missing tables using SQLAlchemy's metadata. It exists
to support clean provisioning in new environments now that we rely on Alembic
instead of runtime `create_all()`.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect, event


# revision identifiers, used by Alembic.
revision = "20251219_0004"
down_revision = "20251219_0003"
branch_labels = None
depends_on = None


POSTGIS_SYSTEM_TABLES = {
    "spatial_ref_sys",
    "geometry_columns",
    "geography_columns",
    "raster_columns",
    "raster_overviews",
    "layer",
    "topology",
}


def _postgis_ddl_filter(conn, cursor, statement, parameters, context, executemany):
    """
    before_cursor_execute hook: replace any DDL statement that references a
    PostGIS-owned system table with a harmless SELECT 1.

    GeoAlchemy2 (and PostGIS extension setup) sometimes emits:
        ALTER TABLE "spatial_ref_sys" ADD PRIMARY KEY ("srid")
    which fails on hosted PostgreSQL because the app user is not the table owner.
    Swapping it for SELECT 1 lets create_all continue without aborting.
    """
    for table in POSTGIS_SYSTEM_TABLES:
        if table in statement:
            return "SELECT 1", ()
    return statement, parameters


def upgrade() -> None:
    # Ensure models are registered on Base.metadata.
    import app.models  # noqa: F401
    from app.db.database import Base

    bind = op.get_bind()
    inspector = inspect(bind)
    existing = set(inspector.get_table_names())

    missing_tables = [
        t for name, t in Base.metadata.tables.items()
        if name not in existing and name not in POSTGIS_SYSTEM_TABLES
    ]
    if not missing_tables:
        return

    # Attach the filter so PostGIS system-table DDL is silently no-op'd.
    event.listen(bind, "before_cursor_execute", _postgis_ddl_filter, retval=True)
    try:
        Base.metadata.create_all(bind=bind, tables=missing_tables)
    finally:
        event.remove(bind, "before_cursor_execute", _postgis_ddl_filter)


def downgrade() -> None:
    # No-op: we don't attempt to drop the entire schema automatically.
    pass

