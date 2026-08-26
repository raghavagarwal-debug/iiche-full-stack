"""
Pytest configuration and shared fixtures for API testing.
Uses an in-memory SQLite database for fast unit & integration tests.
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.db.base import Base
from app.main import app
from app.models.user import User
from app.core.security import hash_password

# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh database schema for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, monkeypatch):
    """FastAPI AsyncClient configured with test database dependency override and console email."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "email_provider", "console")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async def add_csrf_header(request):
        if request.method.upper() in {"POST", "PATCH", "PUT", "DELETE"}:
            cookies = request.headers.get("cookie", "").split(";")
            csrf_cookie = next(
                (part.split("=", 1)[1].strip() for part in cookies if part.strip().startswith("csrf_token=")),
                None,
            )
            if csrf_cookie:
                request.headers["X-CSRF-Token"] = csrf_cookie

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        event_hooks={"request": [add_csrf_header]},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user in the test database."""
    user = User(
        full_name="Admin User",
        email="admin@bitmesra.ac.in",
        password_hash=hash_password("AdminPass123!"),
        is_active=True,
        is_email_verified=True,
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def regular_user(db_session: AsyncSession) -> User:
    """Create a regular user in the test database."""
    user = User(
        full_name="Regular Student",
        email="student@bitmesra.ac.in",
        password_hash=hash_password("StudentPass123!"),
        is_active=True,
        is_email_verified=True,
        role="user",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
