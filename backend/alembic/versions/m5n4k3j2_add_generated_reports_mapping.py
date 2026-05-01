"""Add generated_reports table for mapping report caching

Revision ID: m5n4k3j2
Revises: 20250430_0002
Create Date: 2026-05-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'm5n4k3j2'
down_revision: Union[str, Sequence[str], None] = '20250430_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
