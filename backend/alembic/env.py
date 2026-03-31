import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool, event

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import Base
import app.models

config = context.config

database_url = os.getenv("DATABASE_URL")
if not database_url:
    pghost = os.getenv("PGHOST", "localhost")
    pgport = os.getenv("PGPORT", "5432")
    pguser = os.getenv("PGUSER", "postgres")
    pgpassword = os.getenv("PGPASSWORD", "")
    pgdatabase = os.getenv("PGDATABASE", "replit")
    database_url = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"

config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

import re

POSTGIS_SYSTEM_TABLES = {
    "spatial_ref_sys",
    "geometry_columns",
    "geography_columns",
    "raster_columns",
    "raster_overviews",
}

_POSTGIS_DDL_RE = re.compile(
    r"""(?ix)
    \b(ALTER\s+TABLE|CREATE\s+TABLE|DROP\s+TABLE)\b
    .*?
    (?:"|')?(""" + "|".join(re.escape(t) for t in POSTGIS_SYSTEM_TABLES) + r""")(?:"|')?
    """
)


def include_object(obj, name, type_, reflected, compare_to):
    """Skip PostGIS system tables so Alembic never generates DDL for them."""
    if type_ == "table" and name in POSTGIS_SYSTEM_TABLES:
        return False
    return True


def _postgis_ddl_filter(conn, cursor, statement, parameters, context, executemany):
    """
    Global cursor-level hook: replace DDL targeting PostGIS-owned system
    tables with a harmless no-op.

    Only intercepts ALTER TABLE / CREATE TABLE / DROP TABLE statements
    that reference known PostGIS catalog tables by exact name.
    """
    if _POSTGIS_DDL_RE.search(statement):
        return "SELECT 1", ()
    return statement, parameters


def _attach_postgis_filter(connection):
    """Attach the PostGIS DDL filter to a live connection."""
    event.listen(connection, "before_cursor_execute", _postgis_ddl_filter, retval=True)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _attach_postgis_filter(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
