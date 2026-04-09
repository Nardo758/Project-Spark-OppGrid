"""Add public API tables: api_keys and api_usage

Creates the two tables required by the OppGrid Public API (v1):
  - api_keys: stores hashed API keys with tier / rate-limit metadata
  - api_usage: per-request metering log

Also creates the api_usage_daily materialized view for fast billing
aggregation (refreshed hourly by the background job runner).

UUID primary keys do NOT use a server_default — the ORM always generates
UUIDs in Python via uuid.uuid4() before INSERT, making this safe and
portable across all PostgreSQL versions without any extensions.

Revision ID: 20260410_0001
Revises: 20260409_0001
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260410_0001"
down_revision = "20260409_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "environment",
            sa.String(20),
            nullable=False,
            server_default="production",
        ),
        sa.Column(
            "tier",
            sa.String(20),
            nullable=False,
            server_default="starter",
        ),
        sa.Column(
            "scopes",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "rate_limit_rpm",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
        sa.Column(
            "daily_limit",
            sa.Integer(),
            nullable=False,
            server_default="1000",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "stripe_subscription_item_id", sa.String(100), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )

    op.create_index("idx_api_keys_user", "api_keys", ["user_id"])
    op.create_index("idx_api_keys_prefix", "api_keys", ["key_prefix"])
    op.create_index(
        "idx_api_keys_active",
        "api_keys",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "api_usage",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("endpoint", sa.String(200), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "tokens_consumed",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["api_key_id"],
            ["api_keys.id"],
            ondelete="SET NULL",
            name="fk_api_usage_api_key_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_api_usage_key_time",
        "api_usage",
        ["api_key_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_api_usage_endpoint",
        "api_usage",
        ["endpoint", sa.text("created_at DESC")],
    )

    op.execute(
        """
        CREATE MATERIALIZED VIEW api_usage_daily AS
        SELECT
            api_key_id,
            DATE(created_at)                                              AS usage_date,
            endpoint,
            COUNT(*)                                                      AS request_count,
            COUNT(*) FILTER (WHERE status_code >= 200 AND status_code < 300)
                                                                          AS success_count,
            COUNT(*) FILTER (WHERE status_code = 429)                     AS rate_limited_count,
            AVG(response_time_ms)                                         AS avg_latency_ms,
            SUM(tokens_consumed)                                          AS total_tokens
        FROM api_usage
        GROUP BY api_key_id, DATE(created_at), endpoint
        WITH NO DATA
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX idx_api_usage_daily_unique
            ON api_usage_daily (api_key_id, usage_date, endpoint)
        """
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS api_usage_daily")

    op.drop_index("idx_api_usage_endpoint", table_name="api_usage")
    op.drop_index("idx_api_usage_key_time", table_name="api_usage")
    op.drop_table("api_usage")

    op.drop_index("idx_api_keys_active", table_name="api_keys")
    op.drop_index("idx_api_keys_prefix", table_name="api_keys")
    op.drop_index("idx_api_keys_user", table_name="api_keys")
    op.drop_table("api_keys")
