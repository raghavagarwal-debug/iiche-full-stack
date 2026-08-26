"""
Admin API routes — Section 8.
All endpoints require admin role, checked server-side via require_admin dependency.
"""

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin, verify_csrf
from app.models.event import Event
from app.models.otp import PasswordResetOTP
from app.models.registration import Registration
from app.models.session import Session
from app.models.user import User
from app.schemas.admin import AdminStatsResponse, AdminUserResponse, AdminUserUpdate, OnlineUserResponse
from app.schemas.auth import MessageResponse
from app.schemas.event import EventBulkDeleteRequest, EventCreate, EventResponse, EventUpdate
from app.schemas.registration import AdminRegistrationResponse
from app.services.event_service import EventService
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/admin", tags=["Admin"])


def _csv_safe(value) -> str:
    """Prevent spreadsheet formula injection in exported administrator CSV files."""
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


# --- Event Management ---

@router.get("/events", response_model=list[EventResponse])
async def list_all_events(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: list all events with computed status & registrant_count."""
    events_with_counts = await EventService.list_all_events(db, skip=skip, limit=limit)
    return [EventService.to_event_response(ev, count) for ev, count in events_with_counts]


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
async def create_event(
    data: EventCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: create a new event (status: draft | published)."""
    event = await EventService.create_event(db, data, created_by_id=admin.id)
    return EventService.to_event_response(event, 0)


@router.patch("/events/{event_id}", response_model=EventResponse, dependencies=[Depends(verify_csrf)])
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: update an event. PATCH semantics."""
    try:
        event = await EventService.update_event(db, event_id, data)
        row = await EventService.get_event_with_count(db, event_id)
        count = row[1] if row else 0
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return EventService.to_event_response(event, count)


@router.delete("/events/{event_id}", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
async def delete_event(
    event_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: delete an event."""
    try:
        await EventService.delete_event(db, event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return MessageResponse(message="Event deleted successfully")


@router.post("/events/bulk-delete", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
async def bulk_delete_events(
    data: EventBulkDeleteRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: bulk delete selected events from the database."""
    try:
        count = await EventService.bulk_delete_events(db, data.event_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return MessageResponse(message=f"Successfully deleted {count} event(s) from the database")



# --- Registration Management ---

@router.get("/events/{event_id}/registrations", response_model=list[AdminRegistrationResponse])
async def list_event_registrations(
    event_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: view all registrations for an event with user details, paginated."""
    event = await EventService.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    registrations = await RegistrationService.get_event_registrations(db, event_id, skip=skip, limit=limit)
    return registrations


@router.get("/events/{event_id}/registrations/export")
async def export_event_registrations(
    event_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: export registrations for a specific event as CSV."""
    event = await EventService.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    registrations = await RegistrationService.get_event_registrations(db, event_id, skip=0, limit=5000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Status", "Registered At"])

    for reg in registrations:
        writer.writerow([
            _csv_safe(reg["user_full_name"]),
            _csv_safe(reg["user_email"]),
            _csv_safe(reg["status"]),
            _csv_safe(reg["registered_at"].isoformat() if reg["registered_at"] else ""),
        ])

    output.seek(0)

    clean_title = "".join([c if c.isalnum() else "_" for c in event.title]).strip("_")
    filename = f"{clean_title}_registrations.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/events/{event_id}/registrations", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
async def delete_event_registrations(
    event_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: delete/clear all participant registrations for a specific event from the database."""
    event = await EventService.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    await db.execute(
        delete(Registration).where(Registration.event_id == event_id)
    )
    await db.commit()

    return MessageResponse(
        message=f"All participant registrations for '{event.title}' have been cleared from the database."
    )


# --- Dashboard Stats & User Management ---

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: retrieve aggregate system metrics for dashboard header."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (
        await db.execute(select(func.count(User.id)).where(User.is_active.is_(True)))
    ).scalar() or 0
    google_users = (
        await db.execute(select(func.count(User.id)).where(User.google_subject_id.is_not(None)))
    ).scalar() or 0
    total_events = (await db.execute(select(func.count(Event.id)))).scalar() or 0
    total_registrations = (
        await db.execute(select(func.count(Registration.id)))
    ).scalar() or 0

    # Count online users (non-expired sessions, distinct users)
    online_users = (
        await db.execute(
            select(func.count(func.distinct(Session.user_id)))
            .where(Session.expires_at > now)
        )
    ).scalar() or 0

    # Lightweight cleanup: remove expired sessions older than 24h to prevent unbounded growth
    from datetime import timedelta
    from sqlalchemy import delete
    cutoff = now - timedelta(hours=24)
    await db.execute(delete(Session).where(Session.expires_at < cutoff))
    await db.commit()

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        google_users=google_users,
        total_events=total_events,
        total_registrations=total_registrations,
        online_users=online_users,
    )


@router.get("/users", response_model=list[AdminUserResponse])
async def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: str | None = Query(None, description="Search by name or email"),
    role: str | None = Query(None, description="Filter by user role ('user' or 'admin')"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: list all registered and logged-in users with search & filters."""
    stmt = select(User)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
            )
        )

    if role:
        stmt = stmt.where(User.role == role.strip().lower())

    stmt = stmt.order_by(User.last_login_at.desc().nulls_last(), User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()

    user_responses = []
    for u in users:
        provider = "Google" if u.google_subject_id else "Email"
        resp = AdminUserResponse(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            profile_image_url=u.profile_image_url,
            is_active=u.is_active,
            is_email_verified=u.is_email_verified,
            role=u.role,
            google_subject_id=u.google_subject_id,
            auth_provider=provider,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )
        user_responses.append(resp)

    return user_responses


@router.get("/users/export")
async def export_all_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: export all registered accounts as CSV streamed from database."""
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Full Name", "Email", "Auth Provider", "Role", "Active", "Created At", "Last Login"
    ])

    for u in users:
        provider = "Google" if u.google_subject_id else "Email"
        writer.writerow([
            _csv_safe(u.full_name),
            _csv_safe(u.email),
            _csv_safe(provider),
            _csv_safe(u.role),
            _csv_safe("Yes" if u.is_active else "No"),
            _csv_safe(u.created_at.isoformat() if u.created_at else ""),
            _csv_safe(u.last_login_at.isoformat() if u.last_login_at else "Never"),
        ])

    output.seek(0)
    filename = "IIChE_All_Registered_Accounts.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse, dependencies=[Depends(verify_csrf)])
async def update_user_status(
    user_id: UUID,
    data: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: toggle user active state or change role."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == admin.id and data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own admin account",
        )

    if user.id == admin.id and data.role is not None and data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove administrator privileges from your own account",
        )

    if data.is_active is not None:
        user.is_active = data.is_active
    if data.role is not None:
        user.role = data.role

    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        profile_image_url=user.profile_image_url,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        role=user.role,
        google_subject_id=user.google_subject_id,
        auth_provider="Google" if user.google_subject_id else "Email",
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.delete("/users/{user_id}", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
async def delete_user_by_admin(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin: permanently delete a user account from the database.
    Deletes associated sessions, registrations, and OTPs.
    Prevents self-deletion of the logged-in admin account.
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own admin account",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_email = user.email

    # Explicit cascade cleanup
    await db.execute(delete(Session).where(Session.user_id == user_id))
    await db.execute(delete(Registration).where(Registration.user_id == user_id))
    await db.execute(delete(PasswordResetOTP).where(PasswordResetOTP.user_id == user_id))

    # Delete user from DB
    await db.delete(user)
    await db.commit()

    return MessageResponse(message=f"User {user_email} successfully deleted from database")


@router.get("/online-users", response_model=list[OnlineUserResponse])
async def get_online_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: list users with active (non-expired) sessions — currently online."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    stmt = (
        select(User)
        .join(Session, Session.user_id == User.id)
        .where(Session.expires_at > now)
        .distinct()
        .order_by(User.last_login_at.desc().nulls_last())
        .limit(100)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [OnlineUserResponse.model_validate(u) for u in users]

