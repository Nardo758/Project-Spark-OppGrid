"""Add identify location tables (micro_markets, success_profiles, identify_location_cache)

Revision ID: 20250430_0001
Revises: a1b2c3d4e5f6_add_economic_snapshot_to_generated_reports
Create Date: 2025-04-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250430_0001'
down_revision = 'a1b2c3d4e5f6_add_economic_snapshot_to_generated_reports'
branch_labels = None
depends_on = None


def upgrade():
    # Create micro_markets table
    op.create_table(
        'micro_markets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('market_name', sa.String(255), nullable=False),
        sa.Column('metro', sa.String(100), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('polygon_geojson', sa.JSON(), nullable=False),
        sa.Column('center_latitude', sa.Float(), nullable=False),
        sa.Column('center_longitude', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('demographic_profile', sa.Text(), nullable=True),
        sa.Column('typical_archetypes', sa.Text(), nullable=True),
        sa.Column('avg_foot_traffic', sa.Integer(), nullable=True),
        sa.Column('avg_demographic_fit', sa.Float(), nullable=True),
        sa.Column('avg_competition_density', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_micro_market_metro_state', 'micro_markets', ['metro', 'state'])
    op.create_index('ix_micro_market_name', 'micro_markets', ['market_name'])
    
    # Create success_profiles table
    op.create_table(
        'success_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(100), nullable=False),
        sa.Column('candidate_id', sa.String(100), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('business_description', sa.Text(), nullable=True),
        sa.Column('location_name', sa.String(255), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('zip_code', sa.String(10), nullable=True),
        sa.Column('neighborhood', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('archetype', sa.String(50), nullable=False),
        sa.Column('archetype_confidence', sa.Float(), nullable=False),
        sa.Column('candidate_profile', sa.JSON(), nullable=False),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('promoted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_success_profile_user_id', 'success_profiles', ['user_id'])
    op.create_index('ix_success_profile_request_id', 'success_profiles', ['request_id'])
    op.create_index('ix_success_profile_category', 'success_profiles', ['category'])
    
    # Create identify_location_cache table
    op.create_table(
        'identify_location_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(255), nullable=False, unique=True),
        sa.Column('request_id', sa.String(100), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('target_market', sa.JSON(), nullable=False),
        sa.Column('market_boundary', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key', name='uq_cache_key')
    )
    op.create_index('ix_cache_category', 'identify_location_cache', ['category'])
    op.create_index('ix_cache_expires_at', 'identify_location_cache', ['expires_at'])


def downgrade():
    op.drop_table('identify_location_cache')
    op.drop_table('success_profiles')
    op.drop_table('micro_markets')
