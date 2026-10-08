"""Health and observability endpoint tests."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.redis import redis_client


@pytest.mark.asyncio
async def test_health_aliases_are_live(client: AsyncClient):
    response = await client.get("/health")
    live_response = await client.get("/health/live")

    assert response.status_code == 200
    assert live_response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert live_response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_ready_reports_dependency_status(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(redis_client, "ping", AsyncMock(return_value=True))

    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "redis": "ok"},
    }


@pytest.mark.asyncio
async def test_ready_returns_service_unavailable_when_redis_is_down(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr(redis_client, "ping", AsyncMock(return_value=False))

    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "ok", "redis": "error"},
    }


@pytest.mark.asyncio
async def test_request_id_is_echoed_and_generated(client: AsyncClient):
    response = await client.get("/health/live", headers={"X-Request-ID": "test-123"})
    generated_response = await client.get("/health/live")

    assert response.headers["X-Request-ID"] == "test-123"
    assert generated_response.headers["X-Request-ID"]
    assert len(generated_response.headers["X-Request-ID"]) == 36
