"""
Event request/response schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EventResponse(BaseModel):
    id: UUID
    title: str = Field(max_length=500)
    description: Optional[str] = Field(None, max_length=10000)
    event_date: datetime
    registration_deadline: Optional[datetime] = None
    venue: Optional[str] = Field(None, max_length=500)
    capacity: Optional[int] = None
    is_active: bool
    status: str = "draft"
    registration_open: bool = False
    registration_status: str = "coming_soon"  # computed: coming_soon | open | closed
    registrant_count: int = 0
    created_by: Optional[UUID] = None
    banner_image_url: Optional[str] = Field(None, max_length=2048)
    organizer: Optional[str] = Field(None, max_length=255)
    event_category: Optional[str] = Field(None, max_length=100)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: datetime
    registration_deadline: Optional[datetime] = None
    venue: Optional[str] = None
    capacity: Optional[int] = None
    is_active: bool = True
    status: Optional[str] = None  # draft | published
    registration_open: bool = False
    banner_image_url: Optional[str] = None
    organizer: Optional[str] = None
    event_category: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Event title is required")
        return v

    @field_validator("capacity")
    @classmethod
    def capacity_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("Capacity must be at least 1")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in ("draft", "published"):
            raise ValueError("Status must be 'draft' or 'published'")
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=10000)
    event_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    venue: Optional[str] = Field(None, max_length=500)
    capacity: Optional[int] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    registration_open: Optional[bool] = None
    banner_image_url: Optional[str] = Field(None, max_length=2048)
    organizer: Optional[str] = Field(None, max_length=255)
    event_category: Optional[str] = Field(None, max_length=100)

    @field_validator("title")
    @classmethod
    def update_title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Event title is required")
        return v

    @field_validator("capacity")
    @classmethod
    def update_capacity_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("Capacity must be at least 1")
        return v

    @field_validator("status")
    @classmethod
    def update_status_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if v not in ("draft", "published"):
                raise ValueError("Status must be 'draft' or 'published'")
        return v


class EventBulkDeleteRequest(BaseModel):
    event_ids: list[UUID]

    @field_validator("event_ids")
    @classmethod
    def event_ids_not_empty(cls, v: list[UUID]) -> list[UUID]:
        if not v:
            raise ValueError("At least one event ID must be provided for deletion")
        return v
