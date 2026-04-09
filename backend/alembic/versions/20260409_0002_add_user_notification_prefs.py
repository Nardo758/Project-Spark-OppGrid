"""add notification_preferences to users

Revision ID: 20260409_0002
Revises: 20260411_0002
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa

revision = "20260409_0002"
down_revision = "20260411_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("notification_preferences", sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column("users", "notification_preferences")
