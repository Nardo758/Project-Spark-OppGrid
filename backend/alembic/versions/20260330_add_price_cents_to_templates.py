"""Add price_cents to report_templates

Revision ID: 20260330_price
Revises: 
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260330_price'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('report_templates', sa.Column('price_cents', sa.Integer(), nullable=True, server_default='4900'))

def downgrade():
    op.drop_column('report_templates', 'price_cents')
