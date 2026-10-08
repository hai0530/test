import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.auth_session import AuthSession
    from app.models.tag import Tag
    from app.models.todo import Todo


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("uq_users_lower_email", text("lower(email)"), unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    todos: Mapped[list["Todo"]] = relationship(  # noqa: F821
        "Todo",
        back_populates="user",
        lazy="select",
    )
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        "Tag",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    auth_sessions: Mapped[list["AuthSession"]] = relationship(  # noqa: F821
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
