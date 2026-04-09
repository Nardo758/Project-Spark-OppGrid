"""add company and role to users

Revision ID: 20260409_0003
Revises: 20260409_0002
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa

revision = "20260409_0003"
down_revision = "20260409_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("company", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(100), nullable=True))


def downgrade():
    op.drop_column("users", "role")
    op.drop_column("users", "company")
