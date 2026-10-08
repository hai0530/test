import uuid

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TodoTag(Base):
    """Many-to-many link between a todo and a user-owned tag."""

    __tablename__ = "todo_tags"
    __table_args__ = (
        Index("ix_todo_tags_tag_id", "tag_id"),
        Index("ix_todo_tags_todo_id", "todo_id"),
    )

    todo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("todos.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
