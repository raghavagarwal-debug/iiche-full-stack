"""
Async SQLAlchemy engine and session factory.
Connection pooling is configured here for production readiness.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

is_sqlite = "sqlite" in settings.database_url
connect_args = {"check_same_thread": False} if is_sqlite else {}
pool_kwargs = {} if is_sqlite else {
    "pool_size": settings.db_pool_size,
    "max_overflow": settings.db_max_overflow,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
    **pool_kwargs,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)



async def get_db() -> AsyncSession:
    """Dependency that yields a database session, auto-closing on exit."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
