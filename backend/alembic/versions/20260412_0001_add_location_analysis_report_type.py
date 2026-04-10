"""Add location_analysis to reporttype enum and merge heads

Revision ID: 20260412_0001
Revises: 20260411_0002, 20260409_0003
Create Date: 2026-04-12

"""
from typing import Sequence, Union
from alembic import op

revision: str = "20260412_0001"
down_revision: Union[str, Sequence[str], None] = ("20260411_0002", "20260409_0003")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE reporttype ADD VALUE IF NOT EXISTS 'location_analysis'")


def downgrade() -> None:
    pass
