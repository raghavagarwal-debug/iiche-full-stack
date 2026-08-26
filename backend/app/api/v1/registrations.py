"""
Registration API routes — Section 9.
Authenticated users can register/unregister for events.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, verify_csrf
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.registration import RegistrationResponse
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/events", tags=["Registrations"])


@router.post("/{event_id}/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
async def register_for_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register the authenticated user for an event.
    Per Section 7: concurrency-safe, capacity-checked, duplicate-prevented.
    Per Section 22: rejects if registration_open is False.
    """
    try:
        registration = await RegistrationService.register(db, current_user, event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return RegistrationResponse.model_validate(registration)


@router.delete("/{event_id}/register", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
async def cancel_registration(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the authenticated user's registration for an event."""
    try:
        await RegistrationService.cancel_registration(db, current_user, event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return MessageResponse(message="Registration cancelled successfully")


@router.get("/{event_id}/registration-status")
async def check_registration_status(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if the current user is registered for a specific event."""
    registration = await RegistrationService.check_user_registration(
        db, current_user.id, event_id
    )
    return {
        "is_registered": registration is not None,
        "registration": RegistrationResponse.model_validate(registration) if registration else None,
    }
