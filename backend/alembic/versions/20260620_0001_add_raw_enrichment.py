"""add raw enrichment table

Revision ID: 20260620_0001
Revises: 20260513_0001
Create Date: 2026-06-20

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260620_0001"
down_revision = "20260513_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_enrichment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("target_entity", sa.String(length=50), nullable=False, index=True),
        sa.Column("target_id", sa.Integer(), nullable=False, index=True),
        sa.Column("source", sa.String(length=50), nullable=False, index=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("field_name", sa.String(length=100), nullable=False, index=True),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("parsed_value", postgresql.JSONB(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("enriched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "rejected", "stale", name="enrichmentstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_by", sa.String(length=50), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_raw_enrichment_target", "raw_enrichment", ["target_entity", "target_id"])
    op.create_index("idx_raw_enrichment_status_expires", "raw_enrichment", ["status", "expires_at"])


def downgrade() -> None:
    op.drop_index("idx_raw_enrichment_status_expires", table_name="raw_enrichment")
    op.drop_index("idx_raw_enrichment_target", table_name="raw_enrichment")
    op.drop_table("raw_enrichment")
    op.execute("DROP TYPE IF EXISTS enrichmentstatus")
