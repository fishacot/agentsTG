"""add user_tasks and user_contacts

Revision ID: d4e6f8a0c205
Revises: c3d5f7a2b104
Create Date: 2026-05-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e6f8a0c205"
down_revision: Union[str, Sequence[str], None] = "c3d5f7a2b104"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("due_date", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_tasks_telegram_user_id", "user_tasks", ["telegram_user_id"])
    op.create_index("ix_user_tasks_status", "user_tasks", ["status"])

    op.create_table(
        "user_contacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=False),
        sa.Column(
            "agent_key",
            sa.String(length=64),
            server_default="personal_assistant",
            nullable=False,
        ),
        sa.Column(
            "last_inbound_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_outbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_contacts_telegram_user_id", "user_contacts", ["telegram_user_id"]
    )
    op.create_index("ix_user_contacts_chat_id", "user_contacts", ["chat_id"])


def downgrade() -> None:
    op.drop_index("ix_user_contacts_chat_id", table_name="user_contacts")
    op.drop_index("ix_user_contacts_telegram_user_id", table_name="user_contacts")
    op.drop_table("user_contacts")
    op.drop_index("ix_user_tasks_status", table_name="user_tasks")
    op.drop_index("ix_user_tasks_telegram_user_id", table_name="user_tasks")
    op.drop_table("user_tasks")
