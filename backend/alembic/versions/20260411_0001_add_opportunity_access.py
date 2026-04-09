"""Add opportunity_access table and user_monthly_usage view (v2.1)

Implements the OppGrid API Spec v2.1 opportunity tracking schema.
Each row tracks one user × opportunity × billing_month access event.

Revision ID: 20260411_0001
Revises: 20260410_0001
Create Date: 2026-04-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260411_0001"
down_revision = "20260410_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunity_access",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "api_key_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column(
            "access_type",
            sa.String(20),
            nullable=False,
            server_default="api",
        ),
        sa.Column("billing_month", sa.Date(), nullable=False),
        sa.Column(
            "is_included",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "overage_charged",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("stripe_invoice_item_id", sa.String(100), nullable=True),
        sa.Column(
            "first_accessed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "access_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["api_key_id"],
            ["api_keys.id"],
            ondelete="SET NULL",
            name="fk_opp_access_api_key",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            ondelete="CASCADE",
            name="fk_opp_access_opportunity",
        ),
        sa.UniqueConstraint(
            "user_id", "opportunity_id", "billing_month",
            name="uq_opp_access_user_opp_month",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_opp_access_user_month",
        "opportunity_access",
        ["user_id", "billing_month"],
    )
    op.create_index(
        "idx_opp_access_overage",
        "opportunity_access",
        ["user_id", "is_included"],
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW user_monthly_usage AS
        SELECT
            user_id,
            billing_month,
            COUNT(*)                                            AS total_accessed,
            COUNT(*) FILTER (WHERE is_included)                AS included_used,
            COUNT(*) FILTER (WHERE NOT is_included)            AS overage_count,
            SUM(overage_charged)                               AS overage_total
        FROM opportunity_access
        WHERE billing_month = DATE_TRUNC('month', CURRENT_DATE)::date
        GROUP BY user_id, billing_month
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS user_monthly_usage")
    op.drop_index("idx_opp_access_overage", table_name="opportunity_access")
    op.drop_index("idx_opp_access_user_month", table_name="opportunity_access")
    op.drop_table("opportunity_access")
