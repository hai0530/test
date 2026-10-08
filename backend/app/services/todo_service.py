import uuid
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.todo import Todo
from app.models.todo_tag import TodoTag
from app.schemas.todo import TodoCreate


async def get_todo_by_id_for_user(
    db: AsyncSession, todo_id: uuid.UUID, user_id: uuid.UUID
) -> Todo | None:
    result = await db.execute(
        select(Todo)
        .options(selectinload(Todo.tags))
        .execution_options(populate_existing=True)
        .where(Todo.id == todo_id, Todo.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_todo(
    db: AsyncSession, todo_data: TodoCreate, user_id: uuid.UUID
) -> Todo:
    todo = Todo(
        title=todo_data.title,
        description=todo_data.description,
        user_id=user_id,
    )
    db.add(todo)
    await db.flush()
    await db.refresh(todo)
    return todo


async def get_todos(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
    tag_id: uuid.UUID | None = None,
    keyword: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[Todo], int]:
    """Get a filtered, consistently ordered todo page for one user."""
    filters = _build_filters(
        user_id=user_id,
        status_filter=status_filter,
        tag_id=tag_id,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )
    query = (
        select(Todo)
        .options(selectinload(Todo.tags))
        .where(*filters)
        .order_by(Todo.created_at.desc(), Todo.id.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    todos = list(result.scalars().all())

    count_query = select(func.count()).select_from(Todo).where(*filters)
    total = await db.execute(count_query)

    return todos, total.scalar_one()


def _build_filters(
    *,
    user_id: uuid.UUID,
    status_filter: str | None,
    tag_id: uuid.UUID | None,
    keyword: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[object]:
    filters: list[object] = [Todo.user_id == user_id]
    if status_filter == "completed":
        filters.append(Todo.completed.is_(True))
    elif status_filter == "active":
        filters.append(Todo.completed.is_(False))
    if tag_id is not None:
        filters.append(
            Todo.id.in_(select(TodoTag.todo_id).where(TodoTag.tag_id == tag_id))
        )
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(
            func.lower(Todo.title).like(func.lower(pattern))
            | func.lower(Todo.description).like(func.lower(pattern))
        )
    if date_from is not None:
        filters.append(Todo.created_at >= date_from)
    if date_to is not None:
        filters.append(Todo.created_at < date_to)
    return filters


async def update_todo(
    db: AsyncSession, todo: Todo, update_data: dict[str, object]
) -> Todo:
    for key, value in update_data.items():
        setattr(todo, key, value)
    await db.flush()
    await db.refresh(todo)
    return todo


async def delete_todo(db: AsyncSession, todo: Todo) -> None:
    await db.execute(delete(TodoTag).where(TodoTag.todo_id == todo.id))
    await db.delete(todo)
    await db.flush()


async def bulk_update_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    todo_ids: list[uuid.UUID],
    completed: bool,
) -> int:
    """Update only owned todos, rejecting a mixed-ownership request atomically."""
    unique_ids = set(todo_ids)
    owned_count = await db.scalar(
        select(func.count(Todo.id)).where(
            Todo.user_id == user_id,
            Todo.id.in_(unique_ids),
        )
    )
    if owned_count != len(unique_ids):
        return 0

    result = await db.execute(
        update(Todo)
        .where(Todo.user_id == user_id, Todo.id.in_(unique_ids))
        .values(completed=completed)
    )
    await db.flush()
    return result.rowcount or 0
