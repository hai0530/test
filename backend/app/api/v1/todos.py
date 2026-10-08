import json
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis
from app.core.redis import RedisClient
from app.db.session import get_db
from app.models.user import User
from app.schemas.todo import (
    BulkStatusResponse,
    BulkStatusUpdate,
    TodoCreate,
    TodoListResponse,
    TodoResponse,
    TodoTagCreate,
    TodoUpdate,
)
from app.services.tag_service import (
    attach_tag,
    detach_tag,
    get_mapping,
    get_tag_for_user,
)
from app.services.todo_service import (
    bulk_update_status,
    create_todo,
    delete_todo,
    get_todo_by_id_for_user,
    get_todos,
    update_todo,
)

router = APIRouter()

CACHE_TTL = 300


def _todo_cache_key(
    user_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    status_filter: str | None,
    tag_id: uuid.UUID | None,
    keyword: str | None,
    date_from: date | None,
    date_to: date | None,
) -> str:
    values = {
        "page": page,
        "page_size": page_size,
        "status": status_filter or "all",
        "tag": str(tag_id) if tag_id else "all",
        "keyword": (keyword or "").strip().lower(),
        "from": date_from.isoformat() if date_from else "all",
        "to": date_to.isoformat() if date_to else "all",
    }
    encoded = ":".join(f"{key}={values[key]}" for key in sorted(values))
    return f"todos:user:{user_id}:{encoded}"


async def _invalidate_user_todo_cache(redis: RedisClient, user_id: uuid.UUID) -> None:
    await redis.delete_by_pattern(f"todos:user:{user_id}:*")


def _as_utc_bounds(
    date_from: date | None, date_to: date | None
) -> tuple[datetime | None, datetime | None]:
    start = (
        datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        if date_from
        else None
    )
    end = (
        datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        if date_to
        else None
    )
    return start, end


def _serialize_todo(todo, user_email: str | None = None) -> TodoResponse:
    response = TodoResponse.model_validate(todo)
    return response.model_copy(update={"user_email": user_email})


@router.get("", response_model=TodoListResponse)
async def list_todos(
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1, le=100),
    size: int | None = Query(None, ge=1, le=100),
    status_filter: Literal["active", "completed", "all"] | None = Query(
        None, alias="status"
    ),
    tag_id: uuid.UUID | None = Query(None),
    keyword: str | None = Query(None, max_length=200),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    """List the authenticated user's todos with safe filtering and pagination."""
    effective_size = page_size or size or 20
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be on or before date_to",
        )
    cache_key = _todo_cache_key(
        current_user.id,
        page=page,
        page_size=effective_size,
        status_filter=status_filter,
        tag_id=tag_id,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
    )
    cached = await redis.get(cache_key)
    if cached:
        return TodoListResponse(**json.loads(cached))

    start, end = _as_utc_bounds(date_from, date_to)
    todos, total = await get_todos(
        db,
        user_id=current_user.id,
        skip=(page - 1) * effective_size,
        limit=effective_size,
        status_filter=status_filter,
        tag_id=tag_id,
        keyword=keyword,
        date_from=start,
        date_to=end,
    )
    response = TodoListResponse(
        items=[_serialize_todo(todo, current_user.email) for todo in todos],
        total=total,
        page=page,
        size=effective_size,
    )
    await redis.set(cache_key, response.model_dump_json(), ex=CACHE_TTL)
    return response


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
async def create_new_todo(
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await create_todo(db, todo_data, current_user.id)
    await db.commit()
    await _invalidate_user_todo_cache(redis, current_user.id)
    return _serialize_todo(todo, current_user.email)


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    todo = await get_todo_by_id_for_user(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )
    return _serialize_todo(todo, current_user.email)


@router.put("/{todo_id}", response_model=TodoResponse)
async def update_existing_todo(
    todo_id: uuid.UUID,
    todo_data: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await get_todo_by_id_for_user(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )
    updated_todo = await update_todo(db, todo, todo_data.model_dump(exclude_unset=True))
    await db.commit()
    await _invalidate_user_todo_cache(redis, current_user.id)
    return _serialize_todo(updated_todo, current_user.email)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await get_todo_by_id_for_user(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )
    await delete_todo(db, todo)
    await db.commit()
    await _invalidate_user_todo_cache(redis, current_user.id)
    return None


@router.post("/{todo_id}/tags", response_model=TodoResponse)
async def attach_todo_tag(
    todo_id: uuid.UUID,
    data: TodoTagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await get_todo_by_id_for_user(db, todo_id, current_user.id)
    tag = await get_tag_for_user(db, data.tag_id, current_user.id)
    if todo is None or tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo or tag not found"
        )
    if await get_mapping(db, todo_id, data.tag_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tag already attached"
        )
    try:
        await attach_tag(db, todo_id, data.tag_id)
    except IntegrityError:
        # The pre-check handles the common path; the unique composite key
        # closes the race when two attach requests arrive concurrently.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tag already attached"
        )
    await db.commit()
    await _invalidate_user_todo_cache(redis, current_user.id)
    refreshed = await get_todo_by_id_for_user(db, todo_id, current_user.id)
    return _serialize_todo(refreshed, current_user.email)


@router.delete("/{todo_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_todo_tag(
    todo_id: uuid.UUID,
    tag_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    todo = await get_todo_by_id_for_user(db, todo_id, current_user.id)
    tag = await get_tag_for_user(db, tag_id, current_user.id)
    mapping = await get_mapping(db, todo_id, tag_id)
    if todo is None or tag is None or mapping is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo tag not found"
        )
    await detach_tag(db, mapping)
    await db.commit()
    await _invalidate_user_todo_cache(redis, current_user.id)
    return None


@router.patch("/bulk-status", response_model=BulkStatusResponse)
async def update_todo_statuses(
    data: BulkStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
):
    updated_count = await bulk_update_status(
        db, current_user.id, data.todo_ids, data.completed
    )
    if updated_count != len(set(data.todo_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more todos were not found for this user",
        )
    await db.commit()
    await _invalidate_user_todo_cache(redis, current_user.id)
    return BulkStatusResponse(updated_count=updated_count)
