"""Refresh-token rotation and server-side session management."""

import hashlib
import hmac
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, verify_token
from app.models.auth_session import AuthSession
from app.schemas.user import TokenResponse


def hash_refresh_token(token: str) -> str:
    """Return a deterministic digest without persisting the raw credential."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utc_datetime(timestamp: int | float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _aware(value: datetime) -> datetime:
    """Normalize SQLite's naive timestamp values for safe comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _refresh_claims(token: str) -> tuple[str, uuid.UUID, datetime] | None:
    payload = verify_token(token)
    if payload is None or payload.get("type") != "refresh":
        return None

    jti = payload.get("jti")
    subject = payload.get("sub")
    expires_at = payload.get("exp")
    if not isinstance(jti, str) or not isinstance(subject, str):
        return None
    if not isinstance(expires_at, (int, float)):
        return None

    try:
        user_id = uuid.UUID(subject)
    except (ValueError, AttributeError, TypeError):
        return None
    return jti, user_id, _utc_datetime(expires_at)


async def issue_token_pair(
    db: AsyncSession,
    user_id: uuid.UUID,
    family_id: uuid.UUID | None = None,
) -> TokenResponse:
    """Issue credentials and persist the refresh member before responding."""
    family = family_id or uuid.uuid4()
    access_token = create_access_token(data={"sub": str(user_id)})
    refresh_token = create_refresh_token(
        data={"sub": str(user_id), "family_id": str(family)}
    )
    claims = _refresh_claims(refresh_token)
    if claims is None:  # pragma: no cover - guarded by our token factory
        raise RuntimeError("Generated refresh token failed validation")

    jti, _, expires_at = claims
    db.add(
        AuthSession(
            user_id=user_id,
            family_id=family,
            jti=jti,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
        )
    )
    await db.flush()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def get_refresh_session_for_update(
    db: AsyncSession,
    jti: str,
) -> AuthSession | None:
    """Lock a session row so two concurrent refreshes cannot both rotate it."""
    result = await db.execute(
        select(AuthSession).where(AuthSession.jti == jti).with_for_update()
    )
    return result.scalar_one_or_none()


def is_refresh_session_valid(session: AuthSession, token: str) -> bool:
    """Check ownership-independent token integrity and expiry."""
    if session.revoked_at is not None:
        return False
    if _aware(session.expires_at) <= datetime.now(timezone.utc):
        return False
    return hmac.compare_digest(session.token_hash, hash_refresh_token(token))


def revoke_session(
    session: AuthSession,
    reason: str,
    now: datetime | None = None,
) -> None:
    if session.revoked_at is None:
        session.revoked_at = now or datetime.now(timezone.utc)
        session.revoke_reason = reason


async def revoke_family(
    db: AsyncSession,
    family_id: uuid.UUID,
    reason: str = "reuse_detected",
) -> None:
    """Revoke every active member after a rotated token is replayed."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(AuthSession)
        .where(
            AuthSession.family_id == family_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now, revoke_reason=reason)
    )


async def revoke_user_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    reason: str = "logout",
) -> None:
    """Revoke active sessions for a global logout fallback."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now, revoke_reason=reason)
    )


async def revoke_refresh_token(
    db: AsyncSession,
    token: str,
    user_id: uuid.UUID,
) -> bool:
    """Revoke one refresh session when it belongs to the current user."""
    claims = _refresh_claims(token)
    if claims is None:
        return False
    jti, token_user_id, _ = claims
    if token_user_id != user_id:
        return False

    session = await get_refresh_session_for_update(db, jti)
    if session is None or session.user_id != user_id:
        return False
    revoke_session(session, "logout")
    return True
