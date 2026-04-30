"""Add datasets and dataset_purchases tables for dataset marketplace.

Revision ID: 20260430_0002
Revises: 20260430_0001
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa

revision = "20260430_0002"
down_revision = "20260430_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(36), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("dataset_type", sa.String(50), nullable=False, index=True),
        sa.Column("vertical", sa.String(100), nullable=True, index=True),
        sa.Column("city", sa.String(100), nullable=True, index=True),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("data_freshness", sa.String(255), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), nullable=False, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True, index=True),
        sa.Column("query_definition", sa.JSON(), nullable=False),
    )
    op.create_index("idx_datasets_vertical_city", "datasets", ["vertical", "city"])
    op.create_index("idx_datasets_type_active", "datasets", ["dataset_type", "is_active"])

    op.create_table(
        "dataset_purchases",
        sa.Column("id", sa.String(36), primary_key=True, index=True),
        sa.Column("dataset_id", sa.String(36), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(50), nullable=False),
        sa.Column("stripe_invoice_id", sa.String(255), nullable=True, index=True),
        sa.Column("download_url", sa.String(512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_dataset_purchases_user_dataset", "dataset_purchases", ["user_id", "dataset_id"])
    op.create_index("idx_dataset_purchases_user_created", "dataset_purchases", ["user_id", "created_at"])


def downgrade():
    op.drop_index("idx_dataset_purchases_user_created", "dataset_purchases")
    op.drop_index("idx_dataset_purchases_user_dataset", "dataset_purchases")
    op.drop_table("dataset_purchases")

    op.drop_index("idx_datasets_type_active", "datasets")
    op.drop_index("idx_datasets_vertical_city", "datasets")
    op.drop_table("datasets")
