"""Add economic_snapshot column to generated_reports

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('generated_reports', sa.Column('economic_snapshot', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('generated_reports', 'economic_snapshot')
