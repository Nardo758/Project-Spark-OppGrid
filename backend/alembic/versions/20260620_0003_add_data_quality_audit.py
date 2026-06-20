"""add data quality audit table

Revision ID: 20260620_0003
Revises: 20260620_0002
Create Date: 2026-06-20

"""

from alembic import op
import sqlalchemy as sa


revision = "20260620_0003"
down_revision = "20260620_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_quality_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dataset", sa.String(length=50), nullable=False, index=True),
        sa.Column("check_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True, index=True),
        sa.Column("total_records", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("stale_records", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("missing_records", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("accuracy_score", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("freshness_score", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("published", sa.Boolean(), nullable=False, server_default="false", index=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("idx_dqa_dataset_published", "data_quality_audits", ["dataset", "published"])


def downgrade() -> None:
    op.drop_index("idx_dqa_dataset_published", table_name="data_quality_audits")
    op.drop_table("data_quality_audits")
