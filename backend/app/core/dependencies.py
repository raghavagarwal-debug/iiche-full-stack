"""
FastAPI dependency injection — database sessions, authentication, authorization.
Per Section 20.1: backend is the source of truth for authentication and authorization.
"""

from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_session_token, verify_csrf_token
from app.db.session import async_session_factory
from app.models.session import Session
from app.models.user import User


async def get_db():
    """Yield an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    request: Request,
    session_token_cookie: str | None = Cookie(None, alias="session_token"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate the session cookie or Bearer token, return the authenticated user.
    Returns 401 if the session is missing, expired, or invalid.
    """
    session_token = session_token_cookie
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        session_token = auth_header.split(" ")[1]

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token_hash = hash_session_token(session_token)

    result = await db.execute(
        select(Session).where(Session.token_hash == token_hash)
    )
    db_session = result.scalar_one_or_none()

    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    expires_at = db_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        # Session expired — clean it up
        await db.delete(db_session)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    # Fetch the user
    user_result = await db.execute(
        select(User).where(User.id == db_session.user_id)
    )
    user = user_result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_current_user_optional(
    request: Request,
    session_token_cookie: str | None = Cookie(None, alias="session_token"),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Like get_current_user but returns None instead of raising 401.
    Used for endpoints that behave differently for authenticated vs anonymous users.
    """
    session_token = session_token_cookie
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        session_token = auth_header.split(" ")[1]

    if not session_token:
        return None
    try:
        return await get_current_user(request, session_token_cookie, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require admin role. Per Section 8: admin checked server-side, never trust frontend.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def verify_csrf(request: Request) -> None:
    """
    CSRF verification for state-changing endpoints using double-submit cookie pattern.
    Per Section 5B item 4: CSRF protection because we use cookie-based auth.
    Bypassed if the request is authenticated via Bearer token, as Bearer tokens are immune to CSRF.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return

    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")

    if not verify_csrf_token(csrf_cookie or "", csrf_header or ""):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )
