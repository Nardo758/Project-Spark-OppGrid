"""widen generated_reports.title from varchar(255) to text

Revision ID: 20260401_0004
Revises: 20260401_0003
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260401_0004"
down_revision = "20260401_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "generated_reports",
        "title",
        existing_type=sa.String(255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "generated_reports",
        "title",
        existing_type=sa.Text(),
        type_=sa.String(255),
        existing_nullable=True,
    )
