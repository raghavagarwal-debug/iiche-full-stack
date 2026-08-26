"""
Redis-backed rate limiting middleware.
Per Section 12: rate limiting on auth and password-reset endpoints.
Uses atomic INCR-first pattern to prevent TOCTOU race conditions under high concurrency.
"""

import logging

import redis.asyncio as redis
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection (initialized on app startup)
redis_client: redis.Redis | None = None


async def init_redis() -> None:
    """Initialize the Redis client with a sized connection pool. Called on FastAPI startup."""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.redis_max_connections,
        )
        await redis_client.ping()
        logger.info("Redis connected successfully (pool max=%d)", settings.redis_max_connections)
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Rate limiting will be disabled.")
        redis_client = None
        if settings.is_production:
            raise RuntimeError("Redis is required for production rate limiting") from e


async def close_redis() -> None:
    """Close the Redis client. Called on FastAPI shutdown."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


def _parse_rate_limit(rate_str: str) -> tuple[int, int]:
    """
    Parse a rate limit string like '10/minute' into (max_requests, window_seconds).
    """
    parts = rate_str.split("/")
    if len(parts) != 2:
        return 100, 60  # Fallback

    max_requests = int(parts[0])
    unit = parts[1].lower()

    window_map = {"second": 1, "minute": 60, "hour": 3600}
    window_seconds = window_map.get(unit, 60)

    return max_requests, window_seconds


async def check_rate_limit(key: str, rate_str: str) -> None:
    """
    Check rate limit using an atomic INCR-first pattern.
    INCR is atomic in Redis — it creates the key if missing and returns the new count
    in a single operation, eliminating the TOCTOU race of the old GET-then-INCR approach.
    Raises HTTP 429 if the limit is exceeded.
    """
    if not redis_client:
        return  # Rate limiting disabled if Redis isn't available

    max_requests, window_seconds = _parse_rate_limit(rate_str)
    redis_key = f"ratelimit:{key}"

    try:
        pipe = redis_client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window_seconds)
        results = await pipe.execute()

        current_count = results[0]  # INCR returns the new value atomically
        if current_count > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service is temporarily unavailable.",
            ) from e


async def check_otp_cooldown(email: str) -> None:
    """
    Check the resend cooldown for OTP requests.
    Per Section 4.5: 60-second resend cooldown.
    """
    if not redis_client:
        return

    cooldown_key = f"otp_cooldown:{email.lower()}"
    try:
        was_set = await redis_client.set(
            cooldown_key,
            "1",
            ex=settings.otp_resend_cooldown_seconds,
            nx=True,
        )
        if not was_set:
            ttl = await redis_client.ttl(cooldown_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {ttl} seconds before requesting a new OTP.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"OTP cooldown check failed: {e}")
        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting service is temporarily unavailable.",
            ) from e
