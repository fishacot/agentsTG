"""add task_id to chat_messages

Revision ID: g1h3i5j7k019
Revises: a9c2e4f6b018
Create Date: 2026-05-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g1h3i5j7k019"
down_revision: Union[str, Sequence[str], None] = "a9c2e4f6b018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("task_id", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_chat_messages_task_id", "chat_messages", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_task_id", table_name="chat_messages")
    op.drop_column("chat_messages", "task_id")
