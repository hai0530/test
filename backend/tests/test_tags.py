"""Tags, filtering, bulk status, and ownership boundary tests."""

import pytest
from httpx import AsyncClient


async def register(client: AsyncClient, email: str) -> tuple[str, dict]:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


class MemoryRedis:
    """Small Redis fake that preserves key and invalidation semantics."""

    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex=None):
        self.store[key] = value

    async def delete_by_pattern(self, pattern: str):
        prefix = pattern.removesuffix("*")
        keys = [key for key in self.store if key.startswith(prefix)]
        for key in keys:
            del self.store[key]
        return len(keys)


@pytest.mark.asyncio
async def test_tag_names_are_case_insensitive_per_user(client: AsyncClient):
    _, headers = await register(client, "tag-owner@example.com")

    created = await client.post(
        "/api/v1/tags", json={"name": "Work", "color": "#2563eb"}, headers=headers
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Work"

    duplicate = await client.post(
        "/api/v1/tags", json={"name": " work "}, headers=headers
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_tag_and_todo_ownership_is_enforced(client: AsyncClient):
    _, owner_headers = await register(client, "tag-owner-2@example.com")
    _, other_headers = await register(client, "tag-other@example.com")

    tag = await client.post(
        "/api/v1/tags", json={"name": "Private"}, headers=owner_headers
    )
    todo = await client.post(
        "/api/v1/todos", json={"title": "Owner todo"}, headers=owner_headers
    )
    todo_id = todo.json()["id"]
    tag_id = tag.json()["id"]

    cross_user_attach = await client.post(
        f"/api/v1/todos/{todo_id}/tags",
        json={"tag_id": tag_id},
        headers=other_headers,
    )
    assert cross_user_attach.status_code == 404

    cross_user_tag_update = await client.patch(
        f"/api/v1/tags/{tag_id}",
        json={"name": "Stolen"},
        headers=other_headers,
    )
    assert cross_user_tag_update.status_code == 404


@pytest.mark.asyncio
async def test_tag_filter_and_attach_detach(client: AsyncClient):
    _, headers = await register(client, "tag-filter@example.com")
    tag = await client.post("/api/v1/tags", json={"name": "Urgent"}, headers=headers)
    tag_id = tag.json()["id"]
    todo = await client.post(
        "/api/v1/todos", json={"title": "Tagged task"}, headers=headers
    )
    todo_id = todo.json()["id"]

    attached = await client.post(
        f"/api/v1/todos/{todo_id}/tags",
        json={"tag_id": tag_id},
        headers=headers,
    )
    assert attached.status_code == 200
    assert attached.json()["tags"][0]["name"] == "Urgent"

    duplicate = await client.post(
        f"/api/v1/todos/{todo_id}/tags",
        json={"tag_id": tag_id},
        headers=headers,
    )
    assert duplicate.status_code == 409

    filtered = await client.get(
        "/api/v1/todos", params={"tag_id": tag_id}, headers=headers
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == todo_id

    detached = await client.delete(
        f"/api/v1/todos/{todo_id}/tags/{tag_id}", headers=headers
    )
    assert detached.status_code == 204
    assert (
        await client.get("/api/v1/todos", params={"tag_id": tag_id}, headers=headers)
    ).json()["total"] == 0


@pytest.mark.asyncio
async def test_bulk_status_rejects_mixed_ownership_atomically(client: AsyncClient):
    _, owner_headers = await register(client, "bulk-owner@example.com")
    _, other_headers = await register(client, "bulk-other@example.com")
    owner_todo = await client.post(
        "/api/v1/todos", json={"title": "Owner"}, headers=owner_headers
    )
    other_todo = await client.post(
        "/api/v1/todos", json={"title": "Other"}, headers=other_headers
    )

    response = await client.patch(
        "/api/v1/todos/bulk-status",
        json={
            "todo_ids": [owner_todo.json()["id"], other_todo.json()["id"]],
            "completed": True,
        },
        headers=owner_headers,
    )
    assert response.status_code == 404

    owner_after = await client.get(
        f"/api/v1/todos/{owner_todo.json()['id']}", headers=owner_headers
    )
    assert owner_after.json()["completed"] is False


@pytest.mark.asyncio
async def test_filtered_todo_cache_is_scoped_and_invalidated(client, redis_override):
    redis = MemoryRedis()
    redis_override(redis)
    _, headers = await register(client, "filter-cache@example.com")

    await client.get("/api/v1/todos", params={"status": "active"}, headers=headers)
    await client.get("/api/v1/todos", params={"status": "completed"}, headers=headers)
    assert len(redis.store) == 2
    assert all("status=" in key for key in redis.store)

    todo = await client.post(
        "/api/v1/todos", json={"title": "invalidate"}, headers=headers
    )
    assert todo.status_code == 201
    assert redis.store == {}


@pytest.mark.asyncio
async def test_tag_and_bulk_mutations_invalidate_filtered_cache(client, redis_override):
    redis = MemoryRedis()
    redis_override(redis)
    _, headers = await register(client, "mapping-cache@example.com")
    tag = await client.post("/api/v1/tags", json={"name": "Work"}, headers=headers)
    todo = await client.post("/api/v1/todos", json={"title": "cached"}, headers=headers)
    tag_id = tag.json()["id"]
    todo_id = todo.json()["id"]

    await client.get("/api/v1/todos", params={"status": "active"}, headers=headers)
    assert redis.store
    attached = await client.post(
        f"/api/v1/todos/{todo_id}/tags",
        json={"tag_id": tag_id},
        headers=headers,
    )
    assert attached.status_code == 200
    assert redis.store == {}

    await client.get("/api/v1/todos", params={"tag_id": tag_id}, headers=headers)
    assert redis.store
    bulk = await client.patch(
        "/api/v1/todos/bulk-status",
        json={"todo_ids": [todo_id], "completed": True},
        headers=headers,
    )
    assert bulk.status_code == 200
    assert redis.store == {}
