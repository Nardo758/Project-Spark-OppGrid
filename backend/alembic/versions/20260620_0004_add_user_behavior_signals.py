"""add user behavior signals table

Revision ID: 20260620_0004
Revises: 20260620_0003
Create Date: 2026-06-20

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260620_0004"
down_revision = "20260620_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_behavior_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("entity_type", sa.String(length=50), nullable=False, index=True),
        sa.Column("entity_id", sa.Integer(), nullable=False, index=True),
        sa.Column("action", sa.String(length=50), nullable=False, index=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True, index=True),
    )
    op.create_index("idx_ubs_user_action", "user_behavior_signals", ["user_id", "action"])
    op.create_index("idx_ubs_entity", "user_behavior_signals", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("idx_ubs_entity", table_name="user_behavior_signals")
    op.drop_index("idx_ubs_user_action", table_name="user_behavior_signals")
    op.drop_table("user_behavior_signals")
