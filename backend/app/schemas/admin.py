"""
Admin dashboard request and response schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AdminUserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    profile_image_url: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    role: str
    google_subject_id: Optional[str] = None
    auth_provider: str = "email"
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = Field(None, pattern="^(user|admin)$")


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    google_users: int
    total_events: int
    total_registrations: int
    online_users: int = 0


class OnlineUserResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: str
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
