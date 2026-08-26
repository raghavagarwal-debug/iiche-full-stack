"""
Pydantic schemas export package.
"""

from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    ForgotPasswordRequest,
    VerifyOTPRequest,
    ResetPasswordRequest,
    MessageResponse,
    OTPVerifyResponse,
)
from app.schemas.user import UserResponse
from app.schemas.event import EventResponse, EventCreate, EventUpdate
from app.schemas.registration import (
    RegistrationResponse,
    RegistrationWithEventResponse,
    AdminRegistrationResponse,
)
from app.schemas.admin import (
    AdminUserResponse,
    AdminUserUpdate,
    AdminStatsResponse,
)

__all__ = [
    "SignupRequest",
    "LoginRequest",
    "ForgotPasswordRequest",
    "VerifyOTPRequest",
    "ResetPasswordRequest",
    "MessageResponse",
    "OTPVerifyResponse",
    "UserResponse",
    "EventResponse",
    "EventCreate",
    "EventUpdate",
    "RegistrationResponse",
    "RegistrationWithEventResponse",
    "AdminRegistrationResponse",
    "AdminUserResponse",
    "AdminUserUpdate",
    "AdminStatsResponse",
]
