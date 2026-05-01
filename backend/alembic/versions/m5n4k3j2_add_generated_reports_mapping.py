"""Add generated_reports table for mapping report caching

Revision ID: m5n4k3j2
Revises: u8w1q0u8p6av
Create Date: 2026-05-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'm5n4k3j2'
down_revision: Union[str, Sequence[str], None] = 'u8w1q0u8p6av'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create generated_reports table for mapping analysis PDFs"""
    
    # Create enum for report types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE reporttype AS ENUM (
                'identify_location',
                'clone_success'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.create_table(
        'generated_reports',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('request_id', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('report_type', sa.String(50), nullable=False, index=True),
        sa.Column('source_analysis_id', sa.String(100), nullable=True, index=True),
        sa.Column('source_request_id', sa.String(100), nullable=True, index=True),
        sa.Column('source_data', postgresql.JSONB(), nullable=True),
        sa.Column('pdf_content', sa.LargeBinary(), nullable=True),
        sa.Column('pdf_filename', sa.String(255), nullable=False),
        sa.Column('pdf_size_bytes', sa.Integer(), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('ai_model_used', sa.String(50), nullable=True),
        sa.Column('generator_version', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('access_count', sa.Integer(), default=0),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_valid', sa.Integer(), default=1),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    
    # Create index for cache expiration queries
    op.create_index('idx_generated_reports_expires', 'generated_reports', ['expires_at'])
    # Create index for user reports
    op.create_index('idx_generated_reports_user_type', 'generated_reports', ['user_id', 'report_type'])


def downgrade() -> None:
    """Drop generated_reports table"""
    op.drop_index('idx_generated_reports_user_type', table_name='generated_reports')
    op.drop_index('idx_generated_reports_expires', table_name='generated_reports')
    op.drop_table('generated_reports')
    op.execute('DROP TYPE IF EXISTS reporttype')
