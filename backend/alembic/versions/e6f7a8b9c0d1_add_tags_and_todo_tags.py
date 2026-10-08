"""add user-owned tags and todo tag mappings

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-10-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tags_user_id", "tags", ["user_id"], unique=False)
    op.execute(
        "CREATE UNIQUE INDEX uq_tags_user_id_lower_name "
        "ON tags (user_id, lower(name))"
    )

    op.create_table(
        "todo_tags",
        sa.Column("todo_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["todo_id"], ["todos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("todo_id", "tag_id"),
    )
    op.create_index("ix_todo_tags_tag_id", "todo_tags", ["tag_id"], unique=False)
    op.create_index("ix_todo_tags_todo_id", "todo_tags", ["todo_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_todo_tags_todo_id", table_name="todo_tags")
    op.drop_index("ix_todo_tags_tag_id", table_name="todo_tags")
    op.drop_table("todo_tags")
    op.execute("DROP INDEX uq_tags_user_id_lower_name")
    op.drop_index("ix_tags_user_id", table_name="tags")
    op.drop_table("tags")
