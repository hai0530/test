import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import verify_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
)
from app.services.session_service import (
    get_refresh_session_for_update,
    issue_token_pair,
    is_refresh_session_valid,
    revoke_family,
    revoke_refresh_token,
    revoke_user_sessions,
)

router = APIRouter()


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    try:
        user = await create_user(db, user_data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    return await issue_token_pair(db, user.id)


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return tokens."""
    user = await authenticate_user(db, user_data.email, user_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return await issue_token_pair(db, user.id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    payload = verify_token(request.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not isinstance(user_id, str) or not isinstance(jti, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = await get_user_by_id(db, user_uuid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    session = await get_refresh_session_for_update(db, jti)
    if session is None or session.user_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # A rotated token is never valid again. Reuse indicates token theft, so
    # revoke every credential in the family before returning the error.
    if session.revoked_at is not None:
        await revoke_family(db, session.family_id)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if not is_refresh_session_valid(session, request.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    token_response = await issue_token_pair(db, user_uuid, session.family_id)
    new_payload = verify_token(token_response.refresh_token)
    new_jti = new_payload.get("jti") if new_payload else None
    session.revoked_at = session.revoked_at or datetime.now(timezone.utc)
    session.revoke_reason = "rotated"
    session.replaced_by_jti = new_jti
    return token_response


@router.post("/logout")
async def logout(
    refresh_request: RefreshTokenRequest | None = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current refresh session, or all sessions if omitted."""
    if refresh_request is None:
        await revoke_user_sessions(db, current_user.id)
    else:
        revoked = await revoke_refresh_token(
            db,
            refresh_request.refresh_token,
            current_user.id,
        )
        # If the access token was refreshed while this request was in flight,
        # the submitted refresh member may already be rotated. Revoke the
        # user's active sessions so logout still has the expected effect.
        if not revoked:
            await revoke_user_sessions(db, current_user.id)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    return current_user
