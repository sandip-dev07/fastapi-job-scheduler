"""change user id to uuid

Revision ID: e2a056b90055
Revises: dc454679308a
Create Date: 2026-07-24 01:10:27.052425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2a056b90055'
down_revision: Union[str, Sequence[str], None] = 'dc454679308a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Kept as a no-op so the project remains on integer IDs.
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
