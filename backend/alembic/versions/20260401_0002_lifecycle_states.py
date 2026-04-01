"""Add opportunity lifecycle states and tracking

Revision ID: 20260401_0002
Revises: 20260401_0001
Create Date: 2026-04-01 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '20260401_0002'
down_revision = '20260401_0001'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    if not _table_exists('opportunity_lifecycle'):
        op.create_table(
            'opportunity_lifecycle',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('opportunity_id', sa.Integer(), nullable=False),
            sa.Column('current_state', sa.String(50), nullable=False, server_default='discovered'),
            sa.Column('discovered_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('saved_at', sa.DateTime(), nullable=True),
            sa.Column('analyzing_at', sa.DateTime(), nullable=True),
            sa.Column('planning_at', sa.DateTime(), nullable=True),
            sa.Column('executing_at', sa.DateTime(), nullable=True),
            sa.Column('launched_at', sa.DateTime(), nullable=True),
            sa.Column('paused_at', sa.DateTime(), nullable=True),
            sa.Column('archived_at', sa.DateTime(), nullable=True),
            sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'opportunity_id', name='uq_opportunity_lifecycle'),
        )
        op.create_index('ix_opportunity_lifecycle_user_id', 'opportunity_lifecycle', ['user_id'])
        op.create_index('ix_opportunity_lifecycle_current_state', 'opportunity_lifecycle', ['current_state'])

    if not _table_exists('lifecycle_state_transitions'):
        op.create_table(
            'lifecycle_state_transitions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('lifecycle_id', sa.Integer(), nullable=False),
            sa.Column('from_state', sa.String(50), nullable=False),
            sa.Column('to_state', sa.String(50), nullable=False),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('transitioned_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['lifecycle_id'], ['opportunity_lifecycle.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_lifecycle_state_transitions_lifecycle_id', 'lifecycle_state_transitions', ['lifecycle_id'])

    if not _table_exists('lifecycle_milestones'):
        op.create_table(
            'lifecycle_milestones',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('lifecycle_id', sa.Integer(), nullable=False),
            sa.Column('state', sa.String(50), nullable=False),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['lifecycle_id'], ['opportunity_lifecycle.id'], ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_lifecycle_milestones_lifecycle_id', 'lifecycle_milestones', ['lifecycle_id'])
        op.create_index('ix_lifecycle_milestones_state', 'lifecycle_milestones', ['state'])


def downgrade() -> None:
    if _table_exists('lifecycle_milestones'):
        op.drop_index('ix_lifecycle_milestones_state', 'lifecycle_milestones')
        op.drop_index('ix_lifecycle_milestones_lifecycle_id', 'lifecycle_milestones')
        op.drop_table('lifecycle_milestones')
    if _table_exists('lifecycle_state_transitions'):
        op.drop_index('ix_lifecycle_state_transitions_lifecycle_id', 'lifecycle_state_transitions')
        op.drop_table('lifecycle_state_transitions')
    if _table_exists('opportunity_lifecycle'):
        op.drop_index('ix_opportunity_lifecycle_current_state', 'opportunity_lifecycle')
        op.drop_index('ix_opportunity_lifecycle_user_id', 'opportunity_lifecycle')
        op.drop_table('opportunity_lifecycle')
