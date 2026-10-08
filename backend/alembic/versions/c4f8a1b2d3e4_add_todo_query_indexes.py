"""add todo query performance indexes

Revision ID: c4f8a1b2d3e4
Revises: a0790c76a129
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "c4f8a1b2d3e4"
down_revision: Union[str, None] = "a0790c76a129"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_todos_user_id_created_at_id",
        "todos",
        ["user_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_todos_user_id_completed_created_at",
        "todos",
        ["user_id", "completed", "created_at"],
        unique=False,
    )
    op.create_index("ix_todos_user_id", "todos", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_todos_user_id", table_name="todos")
    op.drop_index("ix_todos_user_id_completed_created_at", table_name="todos")
    op.drop_index("ix_todos_user_id_created_at_id", table_name="todos")
