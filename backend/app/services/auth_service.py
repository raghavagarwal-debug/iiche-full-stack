"""
Auth service — signup, login, logout business logic.
Per Section 16: business logic in services/, not routers.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    generate_session_token,
    get_session_expiry,
    hash_password,
    hash_session_token,
    needs_rehash,
    verify_password,
)
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import SignupRequest


class AuthService:

    @staticmethod
    async def signup(db: AsyncSession, data: SignupRequest) -> User:
        """
        Create a new user account.
        Per Section 4.1: normalize email, check duplicates, hash password.
        Per Recovery Email Spec Section 4: store recovery_email atomically.
        """
        email = data.email.strip().lower()
        recovery_email = data.recovery_email.strip().lower()

        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == email)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("An account with this email already exists")

        user = User(
            full_name=data.full_name.strip(),
            email=email,
            password_hash=hash_password(data.password),
            recovery_email=recovery_email,
            recovery_email_verified_at=datetime.now(timezone.utc),
            is_active=True,
            is_email_verified=False,
            role="user",
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError("An account with this email already exists") from exc
        await db.refresh(user)
        return user

    @staticmethod
    async def login(db: AsyncSession, email: str, password: str) -> tuple[User, str]:
        """
        Authenticate with email + password, return (user, session_token).
        Per Section 4.2: normalize email, verify hash, create session.
        """
        email = email.strip().lower()

        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise ValueError("Invalid email or password")

        if not user.password_hash:
            # Google-only account — no password set
            raise ValueError("Invalid email or password")

        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is inactive")

        # Rehash if Argon2 parameters have changed
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)

        # Create a server-side session
        token = generate_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=get_session_expiry(),
        )
        db.add(session)
        await db.commit()

        return user, token

    @staticmethod
    async def logout(db: AsyncSession, session_token: str) -> None:
        """
        Invalidate the session. Per Section 4.3.
        """
        token_hash = hash_session_token(session_token)
        result = await db.execute(
            select(Session).where(Session.token_hash == token_hash)
        )
        db_session = result.scalar_one_or_none()
        if db_session:
            await db.delete(db_session)
            await db.commit()

    @staticmethod
    async def invalidate_all_sessions(db: AsyncSession, user_id) -> None:
        """Invalidate all sessions for a user (e.g., after password reset). Uses bulk DELETE."""
        await db.execute(delete(Session).where(Session.user_id == user_id))
        await db.commit()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        """Look up a user by normalized email."""
        result = await db.execute(
            select(User).where(User.email == email.strip().lower())
        )
        return result.scalar_one_or_none()
