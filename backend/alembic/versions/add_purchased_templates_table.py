"""Add purchased_templates table

Revision ID: add_purchased_templates
Revises: 
Create Date: 2026-03-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_purchased_templates'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'purchased_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('template_slug', sa.String(100), nullable=False, index=True),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('amount_paid', sa.Integer(), default=0),
        sa.Column('original_price', sa.Integer(), default=0),
        sa.Column('discount_percent', sa.Integer(), default=0),
        sa.Column('stripe_session_id', sa.String(255), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(255), nullable=True),
        sa.Column('uses_remaining', sa.Integer(), default=-1),
        sa.Column('purchased_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['report_templates.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_purchased_templates_user_id', 'purchased_templates', ['user_id'])
    op.create_index('ix_purchased_templates_template_slug', 'purchased_templates', ['template_slug'])


def downgrade():
    op.drop_index('ix_purchased_templates_template_slug', table_name='purchased_templates')
    op.drop_index('ix_purchased_templates_user_id', table_name='purchased_templates')
    op.drop_table('purchased_templates')
