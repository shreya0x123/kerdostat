"""add mode column to users table

Revision ID: e5f6g7h8i9j0
Revises: 30f501c4aa43
Create Date: 2026-07-22 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, Sequence[str], None] = '30f501c4aa43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('mode', sa.String(), server_default='COPILOT'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'mode')
