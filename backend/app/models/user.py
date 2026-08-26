"""
User model — Section 6 of the architecture spec.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, UUID, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    google_subject_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    profile_image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)

    # Recovery email — used as a second knowledge factor for password reset (Section 3.1 of spec)
    recovery_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    recovery_email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_users_email_lower", func.lower(email), unique=True),
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
