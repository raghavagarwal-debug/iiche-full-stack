"""
User response and update schemas — never expose password_hash or sensitive fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    recovery_email: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    role: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    recovery_email: Optional[EmailStr] = None

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v or len(v) < 2:
                raise ValueError("Full name must be at least 2 characters")
            if len(v) > 255:
                raise ValueError("Full name must be at most 255 characters")
        return v

    @field_validator("recovery_email")
    @classmethod
    def recovery_email_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not v:
                raise ValueError("Recovery email is required")
        return v
