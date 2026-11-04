"""
Registration response schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RegistrationResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_id: UUID
    status: str
    registered_at: datetime

    model_config = {"from_attributes": True}


class RegistrationWithEventResponse(BaseModel):
    """Registration with event details — for 'my registrations' view."""
    id: UUID
    event_id: UUID
    status: str
    registered_at: datetime
    event_title: str
    event_date: datetime
    venue: Optional[str] = None


class AdminRegistrationResponse(BaseModel):
    """Registration with user details — for admin views."""
    id: UUID
    user_id: UUID
    event_id: UUID
    status: str
    registered_at: datetime
    user_full_name: str
    user_email: str
