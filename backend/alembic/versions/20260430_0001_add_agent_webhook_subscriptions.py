"""Add agent_webhook_subscriptions table for webhook subscription management

Revision ID: 20260430_0001
Revises: a1b2c3d4e5f6
Create Date: 2026-04-30 02:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260430_0001'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('agent_webhook_subscriptions',
    sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('agent_api_key_id', sa.String(length=255), nullable=False),
    sa.Column('webhook_url', sa.Text(), nullable=False),
    sa.Column('webhook_url_hash', sa.String(length=64), nullable=True),
    sa.Column('events', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('vertical_filter', sa.String(length=100), nullable=True),
    sa.Column('city_filter', sa.String(length=100), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('subscription_id')
    )
    
    op.create_index(op.f('ix_agent_webhook_subscriptions_active'), 'agent_webhook_subscriptions', ['active'], unique=False)
    op.create_index(op.f('ix_agent_webhook_subscriptions_agent_api_key_id'), 'agent_webhook_subscriptions', ['agent_api_key_id'], unique=False)
    op.create_index(op.f('ix_agent_webhook_subscriptions_created_at'), 'agent_webhook_subscriptions', ['created_at'], unique=False)
    op.create_index(op.f('ix_agent_webhook_subscriptions_webhook_url_hash'), 'agent_webhook_subscriptions', ['webhook_url_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_agent_webhook_subscriptions_webhook_url_hash'), table_name='agent_webhook_subscriptions')
    op.drop_index(op.f('ix_agent_webhook_subscriptions_created_at'), table_name='agent_webhook_subscriptions')
    op.drop_index(op.f('ix_agent_webhook_subscriptions_agent_api_key_id'), table_name='agent_webhook_subscriptions')
    op.drop_index(op.f('ix_agent_webhook_subscriptions_active'), table_name='agent_webhook_subscriptions')
    op.drop_table('agent_webhook_subscriptions')
