"""
Security utilities — Argon2id password hashing, session tokens, CSRF.
Per Section 4: never store plaintext passwords.
Per Section 12: Argon2id hashing, secure cookies, CSRF protection.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

# Argon2id hasher with secure defaults
_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an Argon2id hash. Returns False on mismatch."""
    try:
        return _ph.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Check if a password hash needs to be rehashed (e.g., after parameter changes)."""
    return _ph.check_needs_rehash(password_hash)


# --- Session Tokens ---

def generate_session_token() -> str:
    """Generate a cryptographically secure session token (64-byte URL-safe)."""
    return secrets.token_urlsafe(64)


def hash_session_token(token: str) -> str:
    """
    Hash a session token for storage.
    We use SHA-256 because session tokens are already high-entropy random values,
    so a fast hash is sufficient (unlike passwords which are low-entropy).
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_session_expiry() -> datetime:
    """Return the expiry datetime for a new session."""
    return datetime.now(timezone.utc) + timedelta(hours=settings.session_expire_hours)


# --- CSRF Tokens ---

def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token_from_cookie: str, token_from_header: str) -> bool:
    """Verify CSRF token using constant-time comparison."""
    if not token_from_cookie or not token_from_header:
        return False
    return hmac.compare_digest(token_from_cookie, token_from_header)


# --- OTP Hashing ---

def hash_otp(otp: str) -> str:
    """Hash an OTP for storage. Uses SHA-256 since OTPs are short-lived."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit OTP. Per Section 4.5."""
    return f"{secrets.randbelow(1000000):06d}"


def generate_reset_token() -> str:
    """Generate a short-lived password reset token (issued after OTP verification)."""
    return secrets.token_urlsafe(48)
