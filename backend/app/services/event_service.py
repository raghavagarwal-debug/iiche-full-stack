from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.registration import Registration
from app.schemas.event import EventCreate, EventResponse, EventUpdate


class EventService:

    @staticmethod
    def compute_registration_status(event: Event) -> str:
        """
        Derive event registration_status dynamically:
        - status == 'draft' -> 'coming_soon'
        - status == 'published' AND registration_open is False -> 'coming_soon'
        - status == 'published' AND now < deadline -> 'open'
        - status == 'published' AND now >= deadline -> 'closed'
        """
        now = datetime.now(timezone.utc)
        status_val = getattr(event, "status", "published")
        if status_val == "draft":
            return "coming_soon"

        if not getattr(event, "registration_open", True):
            return "coming_soon"

        if event.registration_deadline:
            deadline = event.registration_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if now >= deadline:
                return "closed"

        return "open"

    @staticmethod
    def to_event_response(event: Event, registrant_count: int = 0) -> EventResponse:
        """Convert Event model to EventResponse with computed fields."""
        reg_status = EventService.compute_registration_status(event)
        is_open = (reg_status == "open")

        return EventResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            event_date=event.event_date,
            registration_deadline=event.registration_deadline,
            venue=event.venue,
            capacity=event.capacity,
            is_active=event.is_active,
            status=getattr(event, "status", "published"),
            registration_open=is_open,
            registration_status=reg_status,
            registrant_count=registrant_count,
            created_by=getattr(event, "created_by", None),
            banner_image_url=event.banner_image_url,
            organizer=event.organizer,
            event_category=event.event_category,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

    @staticmethod
    async def list_active_events(
        db: AsyncSession, skip: int = 0, limit: int = 50
    ) -> list[tuple[Event, int]]:
        """Public: list non-draft active events with registrant_count in a single query."""
        stmt = (
            select(Event, func.count(Registration.id).label("registrant_count"))
            .outerjoin(Registration, Event.id == Registration.event_id)
            .where(
                Event.is_active.is_(True),
                or_(Event.status != "draft", Event.status.is_(None)),
            )
            .group_by(Event.id)
            .order_by(Event.event_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    @staticmethod
    async def list_all_events(
        db: AsyncSession, skip: int = 0, limit: int = 50
    ) -> list[tuple[Event, int]]:
        """Admin: list all events with registrant_count in a single query."""
        stmt = (
            select(Event, func.count(Registration.id).label("registrant_count"))
            .outerjoin(Registration, Event.id == Registration.event_id)
            .group_by(Event.id)
            .order_by(Event.event_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    @staticmethod
    async def get_event_with_count(db: AsyncSession, event_id: UUID) -> tuple[Event, int] | None:
        """Get single event with registrant_count."""
        stmt = (
            select(Event, func.count(Registration.id).label("registrant_count"))
            .outerjoin(Registration, Event.id == Registration.event_id)
            .where(Event.id == event_id)
            .group_by(Event.id)
        )
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            return None
        return (row[0], row[1])

    @staticmethod
    async def get_event(db: AsyncSession, event_id: UUID) -> Event | None:
        """Get a single event by ID."""
        result = await db.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_event(db: AsyncSession, data: EventCreate, created_by_id: UUID | None = None) -> Event:
        """Admin: create a new event."""
        payload = data.model_dump()
        status_val = payload.get("status")
        reg_open = payload.get("registration_open")

        if status_val is not None:
            payload["registration_open"] = (status_val == "published")
        else:
            payload["status"] = "published"
            if reg_open is None:
                payload["registration_open"] = False

        if created_by_id:
            payload["created_by"] = created_by_id

        event = Event(**payload)
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def update_event(db: AsyncSession, event_id: UUID, data: EventUpdate) -> Event:
        """Admin: update an event. PATCH semantics."""
        result = await db.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise ValueError("Event not found")

        update_data = data.model_dump(exclude_unset=True)

        if "status" in update_data:
            if update_data["status"] is None:
                update_data.pop("status")
            else:
                update_data["registration_open"] = (update_data["status"] == "published")
        elif "registration_open" in update_data:
            if update_data["registration_open"] is None:
                update_data.pop("registration_open")
            else:
                update_data["status"] = "published" if update_data["registration_open"] else "draft"

        for field, value in update_data.items():
            setattr(event, field, value)

        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def delete_event(db: AsyncSession, event_id: UUID) -> None:
        """Admin: delete an event."""
        result = await db.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise ValueError("Event not found")

        await db.delete(event)
        await db.commit()

    @staticmethod
    async def bulk_delete_events(db: AsyncSession, event_ids: list[UUID]) -> int:
        """Admin: delete multiple events by ID list in a single transaction."""
        if not event_ids:
            return 0

        result = await db.execute(select(Event).where(Event.id.in_(event_ids)))
        events = result.scalars().all()
        if not events:
            raise ValueError("No matching events found to delete")

        deleted_count = len(events)
        for ev in events:
            await db.delete(ev)
        await db.commit()
        return deleted_count
