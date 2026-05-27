"""initial: users, notes, finance_transactions

Revision ID: 361a0f436028
Revises:
Create Date: 2026-05-24 03:31:41.928651

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "361a0f436028"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
