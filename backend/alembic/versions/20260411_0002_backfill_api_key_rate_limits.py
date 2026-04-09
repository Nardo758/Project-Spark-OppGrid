"""Backfill api_key rate limits for v2.1 tier values

Revision ID: 20260411_0002
Revises: 20260411_0001
Create Date: 2026-04-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "20260411_0002"
down_revision = "20260411_0001"
branch_labels = None
depends_on = None


# v2.1 canonical RPM and daily limits per tier (spec-compliant)
# Map: (tier_name, new_rpm, new_daily)
TIER_BACKFILL = [
    # Core v2.1 tiers
    ("explorer",        0,    0),
    ("builder",        10,  250),
    ("scaler",         50, 1250),
    ("enterprise",    500, 10000),
    # API-only tiers
    ("api_starter",    10,  250),
    ("api_professional", 50, 1250),
    ("api_enterprise", 500, 10000),
    # Legacy aliases — map to nearest v2.1 equivalent limits
    ("starter",        10,  250),
    ("growth",         10,  250),
    ("team",           10,  250),
    ("professional",   50, 1250),
    ("pro",            50, 1250),
    ("business",       50, 1250),
    ("free",            0,    0),
]


def upgrade() -> None:
    conn = op.get_bind()
    for tier, rpm, daily in TIER_BACKFILL:
        conn.execute(
            sa.text(
                """
                UPDATE api_keys
                SET rate_limit_rpm = :rpm,
                    daily_limit    = :daily
                WHERE tier = :tier
                """
            ),
            {"rpm": rpm, "daily": daily, "tier": tier},
        )


def downgrade() -> None:
    # Reverting to pre-v2.1 values is not safe without knowing original values.
    # No-op on downgrade — run a manual restore from backup if needed.
    pass
