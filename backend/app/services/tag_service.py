import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.models.todo_tag import TodoTag
from app.schemas.tag import TagCreate, TagUpdate


async def list_tags(db: AsyncSession, user_id: uuid.UUID) -> list[Tag]:
    result = await db.execute(
        select(Tag).where(Tag.user_id == user_id).order_by(func.lower(Tag.name), Tag.id)
    )
    return list(result.scalars().all())


async def get_tag_for_user(
    db: AsyncSession, tag_id: uuid.UUID, user_id: uuid.UUID
) -> Tag | None:
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_tag_by_name(
    db: AsyncSession, name: str, user_id: uuid.UUID, exclude_id: uuid.UUID | None = None
) -> Tag | None:
    query = select(Tag).where(
        Tag.user_id == user_id,
        func.lower(Tag.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.where(Tag.id != exclude_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_tag(db: AsyncSession, data: TagCreate, user_id: uuid.UUID) -> Tag:
    tag = Tag(user_id=user_id, name=data.name, color=data.color)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return tag


async def update_tag(db: AsyncSession, tag: Tag, data: TagUpdate) -> Tag:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tag, key, value)
    await db.flush()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag: Tag) -> None:
    await db.execute(delete(TodoTag).where(TodoTag.tag_id == tag.id))
    await db.delete(tag)
    await db.flush()


async def attach_tag(
    db: AsyncSession, todo_id: uuid.UUID, tag_id: uuid.UUID
) -> TodoTag:
    mapping = TodoTag(todo_id=todo_id, tag_id=tag_id)
    db.add(mapping)
    await db.flush()
    return mapping


async def get_mapping(
    db: AsyncSession, todo_id: uuid.UUID, tag_id: uuid.UUID
) -> TodoTag | None:
    result = await db.execute(
        select(TodoTag).where(
            TodoTag.todo_id == todo_id,
            TodoTag.tag_id == tag_id,
        )
    )
    return result.scalar_one_or_none()


async def detach_tag(db: AsyncSession, mapping: TodoTag) -> None:
    await db.delete(mapping)
    await db.flush()
