"""Add slot_purchases idempotency table

Prevents Stripe webhook retries from double-crediting slot purchases.
Each fulfilled checkout session is recorded once; retries are skipped.

Revision ID: 20260409_0001
Revises: 20260401_0005
Create Date: 2026-04-09
"""

from alembic import op
import sqlalchemy as sa

revision = "20260409_0001"
down_revision = "20260401_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slot_purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stripe_session_id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("slots", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_session_id", name="uq_slot_purchases_session_id"),
    )
    op.create_index("ix_slot_purchases_id", "slot_purchases", ["id"])
    op.create_index("ix_slot_purchases_stripe_session_id", "slot_purchases", ["stripe_session_id"])
    op.create_index("ix_slot_purchases_user_id", "slot_purchases", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_slot_purchases_user_id", table_name="slot_purchases")
    op.drop_index("ix_slot_purchases_stripe_session_id", table_name="slot_purchases")
    op.drop_index("ix_slot_purchases_id", table_name="slot_purchases")
    op.drop_table("slot_purchases")
