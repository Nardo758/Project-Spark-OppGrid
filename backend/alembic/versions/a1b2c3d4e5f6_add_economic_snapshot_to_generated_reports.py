"""Add economic_snapshot column to generated_reports

Revision ID: a1b2c3d4e5f6
Revises: 20260412_0001
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '20260412_0001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE generated_reports ADD COLUMN IF NOT EXISTS economic_snapshot TEXT"
    )


def downgrade():
    op.drop_column('generated_reports', 'economic_snapshot')
