"""add user_profiles, user_projects, project_activity, user_facts.category

Revision ID: c3d5f7a2b104
Revises: b2c4e8f1a903
Create Date: 2026-05-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d5f7a2b104"
down_revision: Union[str, Sequence[str], None] = "b2c4e8f1a903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_facts",
        sa.Column("category", sa.String(length=32), nullable=True),
    )
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("address_as", sa.String(length=128), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("preferences_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_profiles_telegram_user_id",
        "user_profiles",
        ["telegram_user_id"],
        unique=True,
    )

    op.create_table(
        "user_projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_projects_telegram_user_id", "user_projects", ["telegram_user_id"])
    op.create_index("ix_user_projects_status", "user_projects", ["status"])

    op.create_table(
        "project_activity",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("agent_key", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["user_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_activity_project_id", "project_activity", ["project_id"])
    op.create_index(
        "ix_project_activity_telegram_user_id", "project_activity", ["telegram_user_id"]
    )


def downgrade() -> None:
    op.drop_table("project_activity")
    op.drop_table("user_projects")
    op.drop_table("user_profiles")
    op.drop_column("user_facts", "category")
