"""add case-insensitive user email uniqueness

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-10-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX uq_users_lower_email "
        "ON users (lower(email))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_users_lower_email")
