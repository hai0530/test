"""Auth tests."""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.core.security import verify_token
from app.models.auth_session import AuthSession


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login after registration."""
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "password123"},
    )

    # Then login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_email_identity_is_case_insensitive(client: AsyncClient):
    """Registration and login use one canonical email identity."""
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": "CaseUser@Example.com", "password": "password123"},
    )
    assert registered.status_code == 201

    duplicate = await client.post(
        "/api/v1/auth/register",
        json={"email": "caseuser@example.com", "password": "password123"},
    )
    assert duplicate.status_code == 400

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "CASEUSER@EXAMPLE.COM", "password": "password123"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient):
    """Test getting current user info."""
    # Register and get token
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "password123"},
    )
    token = reg_response.json()["access_token"]

    # Get current user
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """Test logout endpoint."""
    # Register and get token
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "logout@example.com", "password": "password123"},
    )
    token = reg_response.json()["access_token"]

    # Logout
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"


@pytest.mark.asyncio
async def test_expired_access_token_is_rejected(client: AsyncClient):
    """Expired JWTs should not authenticate the user."""
    expired_token = create_access_token(
        data={"sub": "00000000-0000-0000-0000-000000000010"},
        expires_delta=timedelta(minutes=-5),
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_used_as_access_token(client: AsyncClient):
    """Refresh credentials must not authorize protected API requests."""
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": "refresh-only@example.com", "password": "password123"},
    )
    refresh_token = registration.json()["refresh_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tampered_access_token_is_rejected(client: AsyncClient):
    """Changing a signed JWT must invalidate it."""
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": "tampered@example.com", "password": "password123"},
    )
    token = registration.json()["access_token"]
    header, payload, signature = token.split(".")
    changed_first_char = "a" if signature[0] != "a" else "b"
    tampered_token = ".".join((header, payload, f"{changed_first_char}{signature[1:]}"))

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_rejects_replay(client: AsyncClient):
    """Each refresh credential is one-time-use and cannot be replayed."""
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": "rotation@example.com", "password": "password123"},
    )
    original = registration.json()

    rotated = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original["refresh_token"]},
    )
    assert rotated.status_code == 200
    replacement = rotated.json()
    assert replacement["refresh_token"] != original["refresh_token"]

    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original["refresh_token"]},
    )
    assert replay.status_code == 401
    assert replay.json()["detail"] == "Invalid refresh token"

    # Reuse detection revokes the active descendant in the same family too.
    descendant_reuse = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": replacement["refresh_token"]},
    )
    assert descendant_reuse.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_the_supplied_refresh_session(client: AsyncClient):
    """Logout invalidates the device session on the server."""
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": "revoke@example.com", "password": "password123"},
    )
    credentials = registration.json()

    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {credentials['access_token']}"},
        json={"refresh_token": credentials["refresh_token"]},
    )
    assert logout.status_code == 200

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": credentials["refresh_token"]},
    )
    assert refreshed.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_body_revokes_all_user_sessions(client: AsyncClient):
    """The legacy no-body logout remains supported as a global logout."""
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": "global-revoke@example.com", "password": "password123"},
    )
    credentials = registration.json()

    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {credentials['access_token']}"},
    )
    assert logout.status_code == 200

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": credentials["refresh_token"]},
    )
    assert refreshed.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_is_persisted_only_as_a_hash(
    client: AsyncClient, db_session
):
    """A database read must not recover the bearer credential."""
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": "hashed-session@example.com", "password": "password123"},
    )
    refresh_token = registration.json()["refresh_token"]
    payload = verify_token(refresh_token)

    result = await db_session.execute(
        select(AuthSession).where(AuthSession.jti == payload["jti"])
    )
    session = result.scalar_one()

    assert session.token_hash != refresh_token
    assert len(session.token_hash) == 64
