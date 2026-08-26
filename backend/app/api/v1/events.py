"""
Public event API routes — Section 9.
No authentication required for browsing events.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.schemas.event import EventResponse
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=list[EventResponse])
async def list_events(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Public: list active published events with pagination, computed status & registrant count.
    """
    events_with_counts = await EventService.list_active_events(db, skip=skip, limit=limit)
    return [EventService.to_event_response(ev, count) for ev, count in events_with_counts]


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: UUID, db: AsyncSession = Depends(get_db)):
    """Public: get a single event by ID."""
    row = await EventService.get_event_with_count(db, event_id)
    if not row or not row[0].is_active or row[0].status == "draft":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return EventService.to_event_response(row[0], row[1])
