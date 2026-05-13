"""Add confidence_tier, contributing_sources, macro_context to opportunities

Revision ID: 20260513_0001
Revises: m5n4k3j2
Create Date: 2026-05-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260513_0001'
down_revision = 'm5n4k3j2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('opportunities', sa.Column(
        'confidence_tier', sa.String(20), nullable=True
    ))
    op.add_column('opportunities', sa.Column(
        'contributing_sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True
    ))
    op.add_column('opportunities', sa.Column(
        'macro_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True
    ))
    op.create_index(
        'ix_opportunities_confidence_tier',
        'opportunities',
        ['confidence_tier'],
    )


def downgrade():
    op.drop_index('ix_opportunities_confidence_tier', table_name='opportunities')
    op.drop_column('opportunities', 'macro_context')
    op.drop_column('opportunities', 'contributing_sources')
    op.drop_column('opportunities', 'confidence_tier')
