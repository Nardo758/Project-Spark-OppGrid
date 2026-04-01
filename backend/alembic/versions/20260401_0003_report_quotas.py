"""Add report quota and purchase log tables

Revision ID: 20260401_0003
Revises: 20260401_0002
Create Date: 2026-04-01 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '20260401_0003'
down_revision = '20260401_0002'
branch_labels = None
depends_on = None


def _table_exists(table_name):
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    if not _table_exists('user_report_quotas'):
        op.create_table(
            'user_report_quotas',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('report_tier', sa.String(20), nullable=False),
            sa.Column('allocated', sa.Integer(), server_default='0'),
            sa.Column('used', sa.Integer(), server_default='0'),
            sa.Column('reset_date', sa.DateTime(), nullable=False),
            sa.Column('subscription_tier', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'report_tier', 'reset_date', name='unique_user_tier_period'),
        )
        op.create_index('ix_user_report_quotas_id', 'user_report_quotas', ['id'])
        op.create_index('ix_user_report_quotas_user_id', 'user_report_quotas', ['user_id'])
        op.create_index('ix_user_report_quotas_report_tier', 'user_report_quotas', ['report_tier'])

    if not _table_exists('report_purchase_logs'):
        op.create_table(
            'report_purchase_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('guest_email', sa.String(255), nullable=True),
            sa.Column('opportunity_id', sa.Integer(), nullable=True),
            sa.Column('report_tier', sa.String(20), nullable=False),
            sa.Column('payment_type', sa.String(20), server_default='stripe'),
            sa.Column('amount_cents', sa.Integer(), server_default='0'),
            sa.Column('stripe_charge_id', sa.String(255), nullable=True),
            sa.Column('report_id', sa.Integer(), nullable=True),
            sa.Column('guest_converted_to_user_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.ForeignKeyConstraint(['guest_converted_to_user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_report_purchase_logs_id', 'report_purchase_logs', ['id'])
        op.create_index('ix_report_purchase_logs_user_id', 'report_purchase_logs', ['user_id'])
        op.create_index('ix_report_purchase_logs_guest_email', 'report_purchase_logs', ['guest_email'])


def downgrade() -> None:
    if _table_exists('report_purchase_logs'):
        op.drop_table('report_purchase_logs')
    if _table_exists('user_report_quotas'):
        op.drop_table('user_report_quotas')
