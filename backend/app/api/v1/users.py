"""
User API routes — Section 9: user profile and registrations.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, verify_csrf
from app.models.otp import PasswordResetOTP
from app.models.registration import Registration
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.registration import RegistrationWithEventResponse
from app.schemas.user import UserResponse, UserUpdate
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse, dependencies=[Depends(verify_csrf)])
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's profile (e.g. full name, recovery email)."""
    from datetime import datetime, timezone
    from fastapi import HTTPException, status

    if data.full_name is not None:
        current_user.full_name = data.full_name

    if data.recovery_email is not None:
        rec_email = data.recovery_email.strip().lower()
        if rec_email == current_user.email.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recovery email must be different from your account email.",
            )
        current_user.recovery_email = rec_email
        current_user.recovery_email_verified_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.delete("/me", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
async def delete_my_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete the authenticated user's account and all associated data from the database.
    Cascades to sessions, registrations, and password reset OTPs.
    Clears session cookies on success.
    """
    user_id = current_user.id

    # Explicitly remove all related records
    await db.execute(delete(Session).where(Session.user_id == user_id))
    await db.execute(delete(Registration).where(Registration.user_id == user_id))
    await db.execute(delete(PasswordResetOTP).where(PasswordResetOTP.user_id == user_id))

    # Delete user from database
    await db.delete(current_user)
    await db.commit()

    # Clear authentication cookies
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="none" if settings.secure_cookies else "lax",
    )
    response.delete_cookie(
        key="csrf_token",
        path="/",
        secure=settings.secure_cookies,
        httponly=False,
        samesite="none" if settings.secure_cookies else "lax",
    )

    return MessageResponse(message="Your account has been deleted successfully.")


@router.get("/me/registrations", response_model=list[RegistrationWithEventResponse])
async def get_my_registrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all events the current user is registered for.
    Per Section 7: GET /api/v1/users/me/registrations
    """
    registrations = await RegistrationService.get_user_registrations(db, current_user.id)
    return registrations
