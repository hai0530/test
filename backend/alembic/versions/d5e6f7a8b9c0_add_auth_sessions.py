"""add server-side refresh token sessions

Revision ID: d5e6f7a8b9c0
Revises: c4f8a1b2d3e4
Create Date: 2026-10-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4f8a1b2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(length=32), nullable=True),
        sa.Column("replaced_by_jti", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index(
        "ix_auth_sessions_user_id_revoked_at",
        "auth_sessions",
        ["user_id", "revoked_at"],
        unique=False,
    )
    op.create_index(
        "ix_auth_sessions_family_id",
        "auth_sessions",
        ["family_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_family_id", table_name="auth_sessions")
    op.drop_index(
        "ix_auth_sessions_user_id_revoked_at", table_name="auth_sessions"
    )
    op.drop_table("auth_sessions")
