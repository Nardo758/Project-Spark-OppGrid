"""add opportunity signals table

Revision ID: 20260620_0002
Revises: 20260620_0001
Create Date: 2026-06-20

"""

from alembic import op
import sqlalchemy as sa


revision = "20260620_0002"
down_revision = "20260620_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunity_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=True, index=True),
        sa.Column(
            "opportunity_id",
            sa.Integer(),
            sa.ForeignKey("opportunities.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("signal_type", sa.String(length=50), nullable=False, index=True),
        sa.Column("signal_value", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column(
            "paired_contact_id",
            sa.Integer(),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_lookup_source", sa.String(length=50), nullable=True),
        sa.Column("actioned", sa.Boolean(), nullable=False, server_default="false", index=True),
        sa.Column("actioned_by_user_id", sa.Integer(), nullable=True),
        sa.Column("actioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("idx_signal_unpaired", "opportunity_signals", ["actioned", "paired_contact_id"])
    op.create_index("idx_signal_type_detected", "opportunity_signals", ["signal_type", "detected_at"])


def downgrade() -> None:
    op.drop_index("idx_signal_type_detected", table_name="opportunity_signals")
    op.drop_index("idx_signal_unpaired", table_name="opportunity_signals")
    op.drop_table("opportunity_signals")
