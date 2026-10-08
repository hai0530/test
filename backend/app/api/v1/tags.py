import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis
from app.core.redis import RedisClient
from app.db.session import get_db
from app.models.user import User
from app.schemas.tag import TagCreate, TagResponse, TagUpdate
from app.services.tag_service import (
    create_tag,
    delete_tag,
    get_tag_by_name,
    get_tag_for_user,
    list_tags,
    update_tag,
)

router = APIRouter()


async def _invalidate_user_todo_cache(redis: RedisClient, user_id: uuid.UUID) -> None:
    await redis.delete_by_pattern(f"todos:user:{user_id}:*")


@router.get("", response_model=list[TagResponse])
async def get_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_tags(db, current_user.id)


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_new_tag(
    data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    if await get_tag_by_name(db, data.name, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tag name already exists"
        )
    try:
        tag = await create_tag(db, data, current_user.id)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tag name already exists"
        )
    await db.commit()
    await _invalidate_user_todo_cache(redis, current_user.id)
    return tag


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_existing_tag(
    tag_id: uuid.UUID,
    data: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    tag = await get_tag_for_user(db, tag_id, current_user.id)
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )
    if data.name and await get_tag_by_name(db, data.name, current_user.id, tag.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tag name already exists"
        )
    try:
        updated = await update_tag(db, tag, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tag name already exists"
        )
    await db.commit()
    await _invalidate_user_todo_cache(redis, current_user.id)
    return updated


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_tag(
    tag_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    tag = await get_tag_for_user(db, tag_id, current_user.id)
    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )
    await delete_tag(db, tag)
    await db.commit()
    await _invalidate_user_todo_cache(redis, current_user.id)
    return None
