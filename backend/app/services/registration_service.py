"""
Registration service — concurrency-safe event registration.
Per Section 7: transaction-safe, capacity-checked, duplicate-prevented at DB level.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.event import Event
from app.models.registration import Registration
from app.models.user import User


class RegistrationService:

    @staticmethod
    async def register(db: AsyncSession, user: User, event_id: UUID) -> Registration:
        """
        Register a user for an event — concurrency-safe.
        Per Section 7: authenticate → check event active → check deadline → check capacity
                       → check duplicate → create inside transaction.
        Per Section 22: reject if registration_open is False.
        """
        # 1. Confirm event exists and is active
        # Use FOR UPDATE to serialize concurrent capacity checks on PostgreSQL (Section 7)
        stmt = select(Event).where(Event.id == event_id)
        if "sqlite" not in settings.database_url:
            stmt = stmt.with_for_update()
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()
        if not event or not event.is_active:
            raise ValueError("Event not found or inactive")

        # 2. Check status & registration_open flag
        status_val = getattr(event, "status", "published")
        if not event.registration_open or status_val == "draft":
            raise ValueError("Registration is not open for this event yet")

        # 3. Check registration deadline
        if event.registration_deadline:
            deadline = event.registration_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= deadline:
                raise ValueError("Registration deadline has passed")

        # 4. Check capacity (with row-level count to prevent race conditions)
        if event.capacity is not None:
            count_result = await db.execute(
                select(func.count(Registration.id))
                .where(
                    Registration.event_id == event_id,
                    Registration.status == "registered",
                )
            )
            current_count = count_result.scalar() or 0
            if current_count >= event.capacity:
                raise ValueError("Event is full — no more spots available")

        # 5. Create registration inside the active transaction
        registration = Registration(
            user_id=user.id,
            event_id=event_id,
            status="registered",
        )
        db.add(registration)

        try:
            await db.commit()
            await db.refresh(registration)
        except IntegrityError:
            await db.rollback()
            raise ValueError("You are already registered for this event")

        return registration

    @staticmethod
    async def cancel_registration(db: AsyncSession, user: User, event_id: UUID) -> None:
        """Cancel a user's registration for an event."""
        result = await db.execute(
            select(Registration).where(
                Registration.user_id == user.id,
                Registration.event_id == event_id,
            )
        )
        registration = result.scalar_one_or_none()
        if not registration:
            raise ValueError("Registration not found")

        await db.delete(registration)
        await db.commit()

    @staticmethod
    async def get_user_registrations(db: AsyncSession, user_id: UUID) -> list[dict]:
        """
        Get all registrations for a user with event details.
        Per Section 7: GET /api/v1/users/me/registrations
        """
        result = await db.execute(
            select(Registration, Event)
            .join(Event, Registration.event_id == Event.id)
            .where(Registration.user_id == user_id)
            .order_by(Event.event_date.desc())
        )
        rows = result.all()

        return [
            {
                "id": reg.id,
                "event_id": reg.event_id,
                "status": reg.status,
                "registered_at": reg.registered_at,
                "event_title": event.title,
                "event_date": event.event_date,
                "venue": event.venue,
            }
            for reg, event in rows
        ]

    @staticmethod
    async def get_event_registrations(
        db: AsyncSession, event_id: UUID, skip: int = 0, limit: int = 200
    ) -> list[dict]:
        """
        Admin: get all registrations for an event with user details, paginated.
        Per Section 8: GET /api/v1/admin/events/{event_id}/registrations
        """
        stmt = (
            select(Registration, User)
            .join(User, Registration.user_id == User.id)
            .where(Registration.event_id == event_id)
            .order_by(Registration.registered_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()

        return [
            {
                "id": reg.id,
                "user_id": reg.user_id,
                "event_id": reg.event_id,
                "status": reg.status,
                "registered_at": reg.registered_at,
                "user_full_name": user.full_name,
                "user_email": user.email,
            }
            for reg, user in rows
        ]

    @staticmethod
    async def check_user_registration(db: AsyncSession, user_id: UUID, event_id: UUID) -> Registration | None:
        """Check if a user is registered for a specific event."""
        result = await db.execute(
            select(Registration).where(
                Registration.user_id == user_id,
                Registration.event_id == event_id,
            )
        )
        return result.scalar_one_or_none()
