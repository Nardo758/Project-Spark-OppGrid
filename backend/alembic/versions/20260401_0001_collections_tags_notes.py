"""Add Collections, Tags, and Notes for opportunities

Revision ID: 20260401_0001
Revises: 5c712e8a02bf
Create Date: 2026-04-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '20260401_0001'
down_revision = '5c712e8a02bf'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    if not _table_exists('opportunity_collections'):
        op.create_table(
            'opportunity_collections',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('color', sa.String(7), nullable=True, server_default='#3b82f6'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_opportunity_collections_user_id', 'opportunity_collections', ['user_id'])

    if not _table_exists('opportunity_tags'):
        op.create_table(
            'opportunity_tags',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('color', sa.String(7), nullable=True, server_default='#6366f1'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'name', name='uq_opportunity_tags_user_name')
        )
        op.create_index('ix_opportunity_tags_user_id', 'opportunity_tags', ['user_id'])

    if not _table_exists('opportunity_notes'):
        op.create_table(
            'opportunity_notes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('opportunity_id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_opportunity_notes_user_id', 'opportunity_notes', ['user_id'])
        op.create_index('ix_opportunity_notes_opportunity_id', 'opportunity_notes', ['opportunity_id'])

    if not _table_exists('opportunity_in_collection'):
        op.create_table(
            'opportunity_in_collection',
            sa.Column('opportunity_id', sa.Integer(), nullable=False),
            sa.Column('collection_id', sa.Integer(), nullable=False),
            sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ),
            sa.ForeignKeyConstraint(['collection_id'], ['opportunity_collections.id'], ),
            sa.PrimaryKeyConstraint('opportunity_id', 'collection_id')
        )

    if not _table_exists('opportunity_has_tag'):
        op.create_table(
            'opportunity_has_tag',
            sa.Column('opportunity_id', sa.Integer(), nullable=False),
            sa.Column('tag_id', sa.Integer(), nullable=False),
            sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ),
            sa.ForeignKeyConstraint(['tag_id'], ['opportunity_tags.id'], ),
            sa.PrimaryKeyConstraint('opportunity_id', 'tag_id')
        )

    if not _table_exists('user_saved_opportunities'):
        op.create_table(
            'user_saved_opportunities',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('opportunity_id', sa.Integer(), nullable=False),
            sa.Column('priority', sa.Integer(), nullable=False, server_default='3'),
            sa.Column('saved_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['opportunity_id'], ['opportunities.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'opportunity_id', name='uq_user_saved_opportunities')
        )
        op.create_index('ix_user_saved_opportunities_user_id', 'user_saved_opportunities', ['user_id'])
        op.create_index('ix_user_saved_opportunities_priority', 'user_saved_opportunities', ['priority'])


def downgrade() -> None:
    if _table_exists('user_saved_opportunities'):
        op.drop_index('ix_user_saved_opportunities_priority', 'user_saved_opportunities')
        op.drop_index('ix_user_saved_opportunities_user_id', 'user_saved_opportunities')
        op.drop_table('user_saved_opportunities')
    if _table_exists('opportunity_has_tag'):
        op.drop_table('opportunity_has_tag')
    if _table_exists('opportunity_in_collection'):
        op.drop_table('opportunity_in_collection')
    if _table_exists('opportunity_notes'):
        op.drop_table('opportunity_notes')
    if _table_exists('opportunity_tags'):
        op.drop_index('ix_opportunity_tags_user_id', 'opportunity_tags')
        op.drop_table('opportunity_tags')
    if _table_exists('opportunity_collections'):
        op.drop_index('ix_opportunity_collections_user_id', 'opportunity_collections')
        op.drop_table('opportunity_collections')
