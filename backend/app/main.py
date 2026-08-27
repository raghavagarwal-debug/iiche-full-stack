"""
IIChE Backend — FastAPI Application Entry Point.
Per Section 3: browser → CDN → load balancer → this FastAPI app → DB/Redis.
Per Section 9: all routes under /api/v1/.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import admin, auth, events, registrations, users
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.middleware.body_limit import RequestBodyLimitMiddleware
from app.middleware.rate_limit import close_redis, init_redis, redis_client
from app.middleware.request_id import RequestIDMiddleware

# Import all models so Base.metadata knows about them
from app.models.user import User  # noqa: F401
from app.models.session import Session  # noqa: F401
from app.models.otp import PasswordResetOTP  # noqa: F401
from app.models.event import Event  # noqa: F401
from app.models.registration import Registration  # noqa: F401
from app.models.system_setting import SystemSetting  # noqa: F401

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def _seed_default_events():
    """
    Seed initial IIChE events ONLY on fresh initial database creation.
    Never re-seeds if the system has already been initialized (even if an admin
    deletes all events from the database).
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.db.session import async_session_factory
    from app.models.event import Event
    from app.models.system_setting import SystemSetting
    from app.models.user import User

    async with async_session_factory() as session:
        # Multiple Gunicorn workers can start together. Serialize the event
        # bootstrap on PostgreSQL so only one worker inserts the initial rows.
        if "sqlite" not in settings.database_url:
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext('iiche:default_events_seed'))")
            )

        # 1. Check if initial setup was already completed
        setting_res = await session.execute(
            select(SystemSetting).where(SystemSetting.key == "initial_events_seeded")
        )
        setting = setting_res.scalar_one_or_none()

        if setting and setting.value == "true":
            # Initial seeding already occurred. Do not recreate deleted events.
            return

        # 2. Check if database is already in use (e.g. existing users or existing events)
        user_res = await session.execute(select(User.id).limit(1))
        has_users = user_res.scalars().first() is not None

        event_res = await session.execute(select(Event.id).limit(1))
        has_events = event_res.scalars().first() is not None

        if has_users or has_events:
            # Existing database without setting record — mark initialized and do not overwrite
            session.add(SystemSetting(key="initial_events_seeded", value="true"))
            await session.commit()
            return

        # 3. Fresh blank database — seed default events once
        now = datetime.now(timezone.utc)
        default_events = [
            Event(
                title="Design Workshop Layout and Design Tools",
                event_category="Workshop",
                description="Learn the fundamentals of modern poster design, layout composition, visual hierarchy, and hands-on creative projects using Canva.",
                venue="Online",
                event_date=now + timedelta(days=14),
                registration_deadline=now + timedelta(days=13),
                capacity=100,
                is_active=True,
                status="published",
                registration_open=True,
            ),
            Event(
                title="MATLAB and Simulink for Chemical Engineers",
                event_category="Workshop",
                description="Numerical computation, reaction kinetics modeling, and process control simulation using MATLAB.",
                venue="Lab 302",
                event_date=now + timedelta(days=21),
                registration_deadline=now + timedelta(days=20),
                capacity=80,
                is_active=True,
                status="published",
                registration_open=True,
            ),

            Event(
                title="Alumni and Career Guidance Talk",
                event_category="Alumni Talks",
                description="Interactive session with distinguished alumni working in Core Energy, EPC, and Process Industries.",
                venue="Main Auditorium",
                event_date=now + timedelta(days=10),
                registration_deadline=now + timedelta(days=9),
                capacity=200,
                is_active=True,
                status="published",
                registration_open=True,
            ),
            Event(
                title="IICHE Talks GATE Preparation Series",
                event_category="Alumni Talks",
                description="GATE Chemical Engineering preparation series with top rankers sharing strategies, subject weightage, and study resources.",
                venue="Online (Google Meet)",
                event_date=now + timedelta(days=45),
                registration_deadline=now + timedelta(days=44),
                capacity=300,
                is_active=True,
                status="published",
                registration_open=True,
            ),
            Event(
                title="Coalescence 26 Flagship Fest",
                event_category="Flagship",
                description="The annual chemical engineering symposium featuring paper presentations, chem-e-car, and technical competitions.",
                venue="BIT Mesra Campus",
                event_date=now + timedelta(days=60),
                registration_deadline=now + timedelta(days=55),
                capacity=500,
                is_active=True,
                status="published",
                registration_open=True,
            ),
        ]
        session.add_all(default_events)
        session.add(SystemSetting(key="initial_events_seeded", value="true"))
        await session.commit()
        logger.info("Seeded default IIChE events into fresh database")


async def _seed_initial_admin():
    """Ensure the configured administrator exists in the shared database."""
    from app.db.session import async_session_factory
    from app.services.bootstrap_service import ensure_initial_admin

    async with async_session_factory() as session:
        await ensure_initial_admin(session)


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events."""
    logger.info("Starting IIChE Backend...")
    await init_redis()

    # Ensure all tables exist
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Safe column additions if tables were created previously
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN recovery_email VARCHAR(320)"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN recovery_email_verified_at TIMESTAMP"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE password_reset_otps ADD COLUMN stage VARCHAR(30) DEFAULT 'email_submitted'"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE password_reset_otps ADD COLUMN recovery_attempt_count INTEGER DEFAULT 0"))
            except Exception:
                pass

        logger.info("Database tables initialized successfully")
        # Events must be seeded first: the event seed intentionally treats any
        # existing user as an already-used database.
        await _seed_default_events()
        await _seed_initial_admin()
    except Exception as e:
        logger.exception("Database initialization failed: %s", e)
        raise

    logger.info(f"Frontend URL: {settings.frontend_url}")
    logger.info(f"Backend URL: {settings.backend_url}")
    logger.info(f"Email provider: {settings.email_provider}")
    logger.info(f"Google OAuth configured: {bool(settings.google_client_id)}")
    yield
    logger.info("Shutting down IIChE Backend...")
    await close_redis()
    await engine.dispose()


# --- App ---

app = FastAPI(
    title="IIChE Student Chapter API",
    description="Backend API for IIChE Student Chapter, BIT Mesra",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

@app.middleware("http")
async def expose_csrf_token(request: Request, call_next):
    """Expose the CSRF token in a header so cross-domain clients can read it."""
    response = await call_next(request)
    csrf_cookie = request.cookies.get("csrf_token")
    if csrf_cookie:
        response.headers["X-CSRF-Token"] = csrf_cookie
    return response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Apply baseline security headers even when the app runs without Nginx."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


# --- Middleware (order matters: outermost first) ---

# Request body size limit — Per Section 12: prevent memory exhaustion
app.add_middleware(RequestBodyLimitMiddleware)

# CORS — Per Section 5B item 3: never use allow_origins=["*"] for authenticated APIs
# Per Section 12: CORS restricted to the exact real frontend origin
# Dev-mode origins are kept for local development convenience
_cors_origins = [
    settings.frontend_url.rstrip("/"),
]
# Always allow common local dev ports for frontend developers testing against the live backend
_cors_origins.extend([
    "http://localhost:5500",
    "http://localhost:5501",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:5501",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://iiche-full-stack.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Authorization"],
    expose_headers=["Content-Disposition", "X-CSRF-Token"],
)

# Request ID — Per Section 13: structured logs with request IDs
# Pure ASGI middleware for better perf than BaseHTTPMiddleware
app.add_middleware(RequestIDMiddleware)


# --- API Routers (all under /api/v1) ---

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(registrations.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


# --- Infrastructure Endpoints ---

@app.get("/debug/setup_db")
async def debug_setup_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            return {"status": "success", "message": "Tables created successfully"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/health")
async def health():
    """
    Basic liveness check.
    Per Section 9: returns basic liveness, no sensitive details.
    """
    return {"status": "healthy"}


@app.get("/ready")
async def readiness():
    """
    Readiness check — verifies DB and Redis connections.
    Per Section 9: used by load balancers/orchestration.
    """
    checks = {"status": "ready", "database": "unknown", "redis": "unknown"}

    # Check database
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"
        checks["status"] = "not_ready"

    # Check Redis
    try:
        if redis_client:
            await redis_client.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not_configured"
    except Exception as e:
        checks["redis"] = f"error: {type(e).__name__}"
        checks["status"] = "not_ready"

    status_code = 200 if checks["status"] == "ready" else 503
    return JSONResponse(content=checks, status_code=status_code)


# --- Global Exception Handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler — never expose sensitive internals.
    Per Section 12: generic error messages.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"An internal error occurred: {str(exc)}"},
    )
