"""
OTP service — generate, store, verify password reset OTPs.
Per Section 4.4–4.5: secure OTP lifecycle with attempt counting and rate limiting.
Extended for recovery-email-verified flow (Section 7 of recovery spec).
"""

import logging
import hmac
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_otp, generate_reset_token, hash_otp, hash_session_token
from app.models.otp import PasswordResetOTP
from app.models.session import Session
from app.models.user import User

logger = logging.getLogger(__name__)


class OTPService:

    @staticmethod
    async def create_reset_session(db: AsyncSession, user: User) -> str:
        """
        Create a new reset session after Step 1 (registered email submitted).
        Issues a reset_session_token, sets stage to 'email_submitted'.
        Does NOT send OTP yet — that happens after recovery email verification.
        """
        # Invalidate existing unused sessions for this user
        existing_result = await db.execute(
            select(PasswordResetOTP).where(
                PasswordResetOTP.user_id == user.id,
                PasswordResetOTP.is_used.is_(False),
            )
        )
        for old_record in existing_result.scalars().all():
            old_record.is_used = True

        # Generate session token
        session_token = generate_reset_token()

        otp_record = PasswordResetOTP(
            user_id=user.id,
            otp_hash="",  # OTP not generated yet — will be set in Step 2
            reset_token_hash=hash_session_token(session_token),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.reset_session_expiry_seconds),
            is_used=False,
            attempt_count=0,
            recovery_attempt_count=0,
            stage="email_submitted",
            created_at=datetime.now(timezone.utc),
        )
        db.add(otp_record)
        await db.commit()

        return session_token

    @staticmethod
    async def _get_session_record(db: AsyncSession, reset_session_token: str) -> PasswordResetOTP | None:
        """Look up a valid (unused, not expired) session by its token hash."""
        token_hash = hash_session_token(reset_session_token)
        stmt = select(PasswordResetOTP).where(
            PasswordResetOTP.reset_token_hash == token_hash,
            PasswordResetOTP.is_used.is_(False),
        )
        if "sqlite" not in settings.database_url:
            stmt = stmt.with_for_update()
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None

        # Check expiry
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None

        return record

    @staticmethod
    async def verify_recovery_email(
        db: AsyncSession, reset_session_token: str, recovery_email: str
    ) -> tuple[bool, str]:
        """
        Step 2: Verify recovery email matches the stored one for this session's user.
        On match: upgrade stage to 'recovery_verified', generate + send OTP to registered email.
        Returns (success, otp_or_error_msg). On success, otp is the plaintext OTP to email.
        """
        record = await OTPService._get_session_record(db, reset_session_token)
        if not record:
            raise ValueError("Invalid or expired session. Please start over.")

        if record.stage != "email_submitted":
            raise ValueError("Invalid session state.")

        # Check recovery email attempt limit (Section 7.4)
        if record.recovery_attempt_count >= settings.recovery_email_max_attempts:
            record.is_used = True  # Lock this session
            await db.commit()
            raise ValueError("Too many attempts. Please request a new password reset.")

        record.recovery_attempt_count += 1

        # Get the user
        user_result = await db.execute(
            select(User).where(User.id == record.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user or not user.recovery_email:
            await db.commit()
            raise ValueError("Wrong recovery email. Please try again.")

        # Compare (case-insensitive, normalized)
        if recovery_email.strip().lower() != user.recovery_email.strip().lower():
            await db.commit()
            raise ValueError("Wrong recovery email. Please try again.")

        # Match! Upgrade stage and generate OTP
        otp = generate_otp()
        record.otp_hash = hash_otp(otp)
        record.stage = "recovery_verified"
        record.attempt_count = 0  # Reset OTP attempt count

        await db.commit()

        logger.info(f"Recovery email verified for user {user.id}, OTP generated")
        return True, otp

    @staticmethod
    async def create_otp(db: AsyncSession, user: User) -> str:
        """
        Generate a 6-digit OTP, store its hash, return the plaintext OTP for emailing.
        Per Section 4.5: cryptographically secure, hashed storage, ~10 min expiry.
        Invalidates any existing unused OTPs for this user.
        """
        # Invalidate existing unused OTPs for this user
        existing_result = await db.execute(
            select(PasswordResetOTP).where(
                PasswordResetOTP.user_id == user.id,
                PasswordResetOTP.is_used.is_(False),
            )
        )
        for old_otp in existing_result.scalars().all():
            old_otp.is_used = True

        otp = generate_otp()

        otp_record = PasswordResetOTP(
            user_id=user.id,
            otp_hash=hash_otp(otp),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.otp_expiry_seconds),
            is_used=False,
            attempt_count=0,
            recovery_attempt_count=0,
            stage="recovery_verified",
            created_at=datetime.now(timezone.utc),
        )
        db.add(otp_record)
        await db.commit()

        return otp

    @staticmethod
    async def verify_otp_with_session(db: AsyncSession, reset_session_token: str, otp: str) -> str:
        """
        Step 3: Verify OTP using the session token (ensures Step 2 was completed).
        Per Section 7.3: checks stage is 'recovery_verified' to block skip attacks.
        Returns the reset_token on success.
        """
        record = await OTPService._get_session_record(db, reset_session_token)
        if not record:
            raise ValueError("Invalid or expired session. Please start over.")

        if record.stage != "recovery_verified":
            logger.warning(
                f"OTP verify attempted at wrong stage '{record.stage}' for user {record.user_id} — possible skip attack"
            )
            raise ValueError("Invalid session state. Please complete the recovery email step first.")

        # Check attempt limit
        if record.attempt_count >= settings.otp_max_attempts:
            raise ValueError("Too many attempts. Please request a new OTP.")

        # Increment attempts
        record.attempt_count += 1

        # Verify OTP hash
        if not hmac.compare_digest(hash_otp(otp), record.otp_hash):
            await db.commit()
            raise ValueError("Invalid OTP")

        # OTP is correct — issue a reset token and upgrade stage
        reset_token = generate_reset_token()

        # Create a new record with the reset_token for the final password reset step
        record.stage = "otp_verified"
        # Store the reset_token hash on the same record for the password reset step
        # We need a separate field — reuse reset_token_hash by updating it
        record.reset_token_hash = hash_session_token(reset_token)
        await db.commit()

        return reset_token

    @staticmethod
    async def verify_otp(db: AsyncSession, email: str, otp: str) -> str:
        """
        Legacy OTP verification by email (kept for backward compat).
        Per Section 4.4 Step 2: check exists, not expired, not used, matches, attempts not exceeded.
        Returns the reset_token on success.
        """

        user = await AuthService.get_user_by_email(db, email)
        if not user:
            raise ValueError("Invalid OTP")

        # Get the latest unused OTP for this user
        result = await db.execute(
            select(PasswordResetOTP)
            .where(
                PasswordResetOTP.user_id == user.id,
                PasswordResetOTP.is_used.is_(False),
            )
            .order_by(PasswordResetOTP.created_at.desc())
            .limit(1)
        )
        otp_record = result.scalar_one_or_none()

        if not otp_record:
            raise ValueError("Invalid OTP")

        # Check attempt limit
        if otp_record.attempt_count >= settings.otp_max_attempts:
            raise ValueError("Too many attempts. Please request a new OTP.")

        # Increment attempts
        otp_record.attempt_count += 1

        # Check expiry (handle both naive SQLite and aware PostgreSQL datetimes)
        expires_at = otp_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            await db.commit()
            raise ValueError("OTP has expired. Please request a new one.")

        # Verify
        if not hmac.compare_digest(hash_otp(otp), otp_record.otp_hash):
            await db.commit()
            raise ValueError("Invalid OTP")

        # OTP is correct — issue a reset token
        reset_token = generate_reset_token()
        otp_record.reset_token_hash = hash_session_token(reset_token)
        # Don't mark as used yet — that happens when the password is actually reset
        await db.commit()

        return reset_token

    @staticmethod
    async def resend_otp_with_session(db: AsyncSession, reset_session_token: str) -> str:
        """
        Resend OTP for an active session that has already passed the recovery email step.
        Returns the new plaintext OTP for emailing.
        """
        record = await OTPService._get_session_record(db, reset_session_token)
        if not record:
            raise ValueError("Invalid or expired session. Please start over.")

        if record.stage != "recovery_verified":
            raise ValueError("Invalid session state.")

        # Generate new OTP
        otp = generate_otp()
        record.otp_hash = hash_otp(otp)
        record.attempt_count = 0  # Reset attempt count for new OTP
        await db.commit()

        return otp

    @staticmethod
    async def reset_password(db: AsyncSession, reset_token: str, new_password: str) -> None:
        """
        Reset the user's password using the reset token.
        Per Section 4.4 Step 3: validate token, hash new password, invalidate token + old sessions.
        """
        from app.core.security import hash_password
        from app.services.auth_service import AuthService

        token_hash = hash_session_token(reset_token)

        stmt = select(PasswordResetOTP).where(
            PasswordResetOTP.reset_token_hash == token_hash,
            PasswordResetOTP.is_used.is_(False),
        )
        if "sqlite" not in settings.database_url:
            stmt = stmt.with_for_update()
        result = await db.execute(stmt)
        otp_record = result.scalar_one_or_none()

        if not otp_record or otp_record.stage != "otp_verified":
            raise ValueError("Invalid or expired reset token")

        # Check expiry (reset token inherits OTP expiry window)
        expires_at = otp_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise ValueError("Reset token has expired")

        # Get the user
        user_result = await db.execute(
            select(User).where(User.id == otp_record.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        # Update password
        user.password_hash = hash_password(new_password)

        # Mark OTP as used
        otp_record.is_used = True

        # Invalidate all existing sessions per spec
        await db.execute(delete(Session).where(Session.user_id == user.id))
        await db.commit()
