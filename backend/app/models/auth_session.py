import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuthSession(Base):
    """Server-side state for one refresh-token family member.

    The raw refresh token is never persisted. ``token_hash`` is used as a
    second integrity check after the signed JWT has been verified. A family is
    revoked when a rotated token is replayed, protecting the whole credential
    chain after theft.
    """

    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    jti: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoke_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    replaced_by_jti: Mapped[str | None] = mapped_column(String(36), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="auth_sessions")

    __table_args__ = (
        Index("ix_auth_sessions_user_id_revoked_at", "user_id", "revoked_at"),
        Index("ix_auth_sessions_family_id", "family_id"),
    )

    def __repr__(self) -> str:
        return f"<AuthSession {self.jti}>"
