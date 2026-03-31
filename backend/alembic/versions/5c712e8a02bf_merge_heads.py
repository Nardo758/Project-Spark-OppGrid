"""merge heads

Revision ID: 5c712e8a02bf
Revises: 20260121_0001, 20260203_saved_searches, 20260330_price, add_purchased_templates
Create Date: 2026-03-31 02:07:30.987972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c712e8a02bf'
down_revision: Union[str, Sequence[str], None] = ('20260121_0001', '20260203_saved_searches', '20260330_price', 'add_purchased_templates')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
