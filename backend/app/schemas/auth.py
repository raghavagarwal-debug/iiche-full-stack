"""
Auth request/response schemas — validated by Pydantic.
Per Section 12: input validation on every request.
"""

import re
from pydantic import BaseModel, EmailStr, ValidationInfo, field_validator


class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str
    recovery_email: EmailStr

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) < 2:
            raise ValueError("Full name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Full name must be at most 255 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        if info.data and "password" in info.data:
            password = info.data.get("password")
            if password and v != password:
                raise ValueError("Passwords do not match")
        return v

    @field_validator("recovery_email")
    @classmethod
    def recovery_email_must_differ(cls, v: str, info: ValidationInfo) -> str:
        """Recovery email must be different from the primary account email (Section 4)."""
        if info.data and "email" in info.data:
            primary_email = info.data.get("email")
            if primary_email and v.strip().lower() == str(primary_email).strip().lower():
                raise ValueError("Recovery email must be different from your account email.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyRecoveryEmailRequest(BaseModel):
    """Step 2: Verify recovery email before OTP is sent (Section 7.1)."""
    reset_session_token: str
    recovery_email: EmailStr


class VerifyOTPRequest(BaseModel):
    """Step 3: Verify OTP using session token (Section 7.3 — prevents skipping Step 2)."""
    reset_session_token: str
    otp: str

    @field_validator("otp")
    @classmethod
    def otp_format(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be a 6-digit number")
        return v


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        if info.data and "new_password" in info.data:
            new_password = info.data.get("new_password")
            if new_password and v != new_password:
                raise ValueError("Passwords do not match")
        return v


class MessageResponse(BaseModel):
    message: str


class ResetSessionResponse(BaseModel):
    """Response from forgot-password/request — includes session token for next steps."""
    message: str
    reset_session_token: str
    recovery_email_required: bool = False


class OTPVerifyResponse(BaseModel):
    message: str
    reset_token: str
