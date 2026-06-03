"""add plan_recipes table

Revision ID: a9c2e4f6b018
Revises: f8a1c3d5e927
Create Date: 2026-06-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9c2e4f6b018"
down_revision: Union[str, Sequence[str], None] = "f8a1c3d5e927"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plan_recipes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("intent_hash", sa.String(length=64), nullable=False),
        sa.Column("intent_sample", sa.String(length=512), nullable=False),
        sa.Column("steps_json", sa.JSON(), nullable=False),
        sa.Column("success_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plan_recipes_user_id", "plan_recipes", ["user_id"])
    op.create_index("ix_plan_recipes_intent_hash", "plan_recipes", ["intent_hash"])


def downgrade() -> None:
    op.drop_index("ix_plan_recipes_intent_hash", table_name="plan_recipes")
    op.drop_index("ix_plan_recipes_user_id", table_name="plan_recipes")
    op.drop_table("plan_recipes")
