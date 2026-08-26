"""
Password reset OTP model — Section 6 of the architecture spec.
Stores hashed OTPs with expiry, usage, and attempt tracking.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UUID, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    otp_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    reset_token_hash: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 4-step state machine for recovery-email-verified password reset (Section 7.3)
    # Values: email_submitted → recovery_verified → otp_verified → allowed_to_reset
    stage: Mapped[str] = mapped_column(
        String(30), default="email_submitted", nullable=False, server_default="email_submitted"
    )
    # Track recovery email verification attempts separately from OTP attempts
    recovery_attempt_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PasswordResetOTP user_id={self.user_id} used={self.is_used}>"
