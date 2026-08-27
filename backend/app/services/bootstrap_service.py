"""Idempotent application bootstrap tasks.

Bootstrap data is created in the shared database, rather than in frontend code,
so it is available to every deployed API worker and survives redeployments.
"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


def _configured_admin_credentials() -> tuple[str, str] | None:
    """Return normalized bootstrap credentials, or None when bootstrap is disabled."""
    email = settings.initial_admin_email.strip().lower()
    password = settings.initial_admin_password

    if not email and not password:
        return None
    if not email or not password:
        raise RuntimeError(
            "INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD must be configured together"
        )
    if len(password) < 8:
        raise RuntimeError("INITIAL_ADMIN_PASSWORD must contain at least 8 characters")
    return email, password


async def ensure_initial_admin(db: AsyncSession) -> User | None:
    """Create or repair the configured bootstrap administrator exactly once.

    An existing administrator's credentials are preserved. If a matching
    non-admin account exists, it is promoted once and receives the configured
    bootstrap password; this makes a previously-created ordinary account with
    the bootstrap email usable as the intended administrator. A password is
    also assigned to an existing passwordless (Google-only) account.

    The unique normalized email index on ``users`` makes concurrent startup
    attempts safe. A losing worker handles the resulting integrity error by
    reading the account created by the winning worker.
    """
    configured = _configured_admin_credentials()
    if configured is None:
        if settings.is_production:
            raise RuntimeError(
                "Initial administrator credentials are required in production"
            )
        logger.info("Initial administrator seed skipped; credentials are not configured")
        return None

    email, password = configured
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            full_name=settings.initial_admin_name.strip() or "Initial Administrator",
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_email_verified=True,
            role="admin",
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
            logger.info("Initial administrator account created")
            return user
        except IntegrityError:
            # Another worker may have inserted the same normalized email first.
            await db.rollback()
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user is None:
                raise

    changed = False
    was_admin = user.role == "admin"
    if user.role != "admin":
        user.role = "admin"
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True
    if not user.password_hash or not was_admin:
        user.password_hash = hash_password(password)
        changed = True

    if changed:
        await db.commit()
        await db.refresh(user)
        logger.info("Initial administrator account synchronized")
    else:
        logger.info("Initial administrator account already exists")

    return user
