"""Todo tests."""

import json

import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, email: str = "todo@example.com") -> str:
    """Helper to register and get auth token."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_create_todo(client: AsyncClient):
    """Test creating a new todo."""
    token = await get_auth_token(client, "create@example.com")

    response = await client.post(
        "/api/v1/todos",
        json={"title": "Test Todo", "description": "A test todo item"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Todo"
    assert data["description"] == "A test todo item"
    assert data["completed"] is False


@pytest.mark.asyncio
async def test_get_todos(client: AsyncClient):
    """Test getting todo list."""
    token = await get_auth_token(client, "list@example.com")

    # Create a todo first
    await client.post(
        "/api/v1/todos",
        json={"title": "List Todo"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get todos
    response = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_update_todo(client: AsyncClient):
    """Test updating a todo."""
    token = await get_auth_token(client, "update@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Update Me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Update it
    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Updated Title", "completed": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_todo(client: AsyncClient):
    """Test deleting a todo."""
    token = await get_auth_token(client, "delete@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Delete Me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Delete it
    response = await client.delete(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_single_todo(client: AsyncClient):
    """Test getting a single todo by ID."""
    token = await get_auth_token(client, "single@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Single Todo", "description": "Get me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Get it
    response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Todo"


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_todo(client: AsyncClient):
    """User B must not read, update, or delete User A's todo."""
    user_a_token = await get_auth_token(client, "owner@example.com")
    user_b_token = await get_auth_token(client, "other@example.com")

    created = await client.post(
        "/api/v1/todos",
        json={"title": "Private Todo", "description": "secret"},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    todo_id = created.json()["id"]

    read_response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert read_response.status_code in {403, 404}

    update_response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Hacked"},
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert update_response.status_code in {403, 404}

    delete_response = await client.delete(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert delete_response.status_code in {403, 404}


@pytest.mark.asyncio
async def test_partial_todo_update_keeps_existing_description(client: AsyncClient):
    """Updating only title should not clear description."""
    token = await get_auth_token(client, "partial@example.com")

    created = await client.post(
        "/api/v1/todos",
        json={"title": "Original", "description": "Keep me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Updated title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated title"
    assert data["description"] == "Keep me"


@pytest.mark.asyncio
async def test_toggle_completed_false_persists(client: AsyncClient):
    """Toggling a completed todo back to false should persist."""
    token = await get_auth_token(client, "toggle@example.com")

    created = await client.post(
        "/api/v1/todos",
        json={"title": "Toggle me", "description": "check"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = created.json()["id"]

    first_update = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"completed": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first_update.status_code == 200
    assert first_update.json()["completed"] is True

    second_update = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"completed": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second_update.status_code == 200
    assert second_update.json()["completed"] is False


class InMemoryRedis:
    """Minimal Redis stand-in for cache behavior tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def delete_by_pattern(self, pattern: str) -> int:
        prefix = pattern[:-1] if pattern.endswith("*") else pattern
        keys = [key for key in self.store if key.startswith(prefix)]
        for key in keys:
            del self.store[key]
        return len(keys)


@pytest.mark.asyncio
async def test_create_todo_invalidates_list_cache(client: AsyncClient, redis_override):
    """Creating a todo must invalidate cached list responses for that user."""
    fake_redis = InMemoryRedis()
    redis_override(fake_redis)

    token = await get_auth_token(client, "cache@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    list_response = await client.get("/api/v1/todos", headers=headers)
    assert list_response.status_code == 200
    cache_key = next(iter(fake_redis.store))
    assert json.loads(fake_redis.store[cache_key])["total"] == 0

    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Fresh todo"},
        headers=headers,
    )
    assert create_response.status_code == 201
    assert cache_key not in fake_redis.store


@pytest.mark.asyncio
async def test_update_todo_invalidates_list_cache(client: AsyncClient, redis_override):
    fake_redis = InMemoryRedis()
    redis_override(fake_redis)

    token = await get_auth_token(client, "cache-update@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/v1/todos", json={"title": "Before"}, headers=headers
    )
    todo_id = created.json()["id"]
    await client.get("/api/v1/todos", headers=headers)
    cache_key = next(iter(fake_redis.store))

    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "After"},
        headers=headers,
    )
    assert response.status_code == 200
    assert cache_key not in fake_redis.store


@pytest.mark.asyncio
async def test_delete_todo_invalidates_list_cache(client: AsyncClient, redis_override):
    fake_redis = InMemoryRedis()
    redis_override(fake_redis)

    token = await get_auth_token(client, "cache-delete@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/v1/todos", json={"title": "Delete"}, headers=headers
    )
    todo_id = created.json()["id"]
    await client.get("/api/v1/todos", headers=headers)
    cache_key = next(iter(fake_redis.store))

    response = await client.delete(f"/api/v1/todos/{todo_id}", headers=headers)
    assert response.status_code == 204
    assert cache_key not in fake_redis.store
