"""add reminder recurrence

Revision ID: e7a9b2c4d816
Revises: d4e6f8a0c205
Create Date: 2026-05-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7a9b2c4d816"
down_revision: Union[str, Sequence[str], None] = "d4e6f8a0c205"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reminders",
        sa.Column(
            "recurrence", sa.String(length=16), server_default="once", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("reminders", "recurrence")
