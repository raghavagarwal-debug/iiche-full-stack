"""
Auth API routes — Section 9: signup, login, logout, /me, forgot password, Google OAuth.
Routers are thin — business logic lives in services/.
"""

import logging
import hmac

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, verify_csrf
from app.core.security import generate_csrf_token
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    OTPVerifyResponse,
    ResetPasswordRequest,
    ResetSessionResponse,
    SignupRequest,
    VerifyOTPRequest,
    VerifyRecoveryEmailRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.email_service import get_email_sender
from app.services.google_auth_service import GoogleAuthService
from app.services.otp_service import OTPService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# --- Signup ---

@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    data: SignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new account. Per Section 4.1.
    Recovery email is required and stored atomically with user creation.
    """
    from app.middleware.rate_limit import check_rate_limit
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"signup:{client_ip}", settings.rate_limit_signup)

    try:
        await AuthService.signup(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return MessageResponse(message="Account created successfully. You can now log in.")


# --- Login ---

@router.post("/login", response_model=UserResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Log in with email + password. Sets a secure HttpOnly session cookie.
    Per Section 4.2.
    """
    from app.middleware.rate_limit import check_rate_limit
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"login:{client_ip}", settings.rate_limit_login)
    await check_rate_limit(f"login:{data.email.strip().lower()}", settings.rate_limit_login)

    try:
        user, token = await AuthService.login(db, data.email, data.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Set session cookie (HttpOnly, Secure, SameSite per Section 4.2)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="none",
        max_age=settings.session_expire_hours * 3600,
        path="/",
    )

    # Set CSRF token (readable by frontend JS for the double-submit pattern)
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # Frontend needs to read this
        secure=settings.secure_cookies,
        samesite="none",
        max_age=settings.session_expire_hours * 3600,
        path="/",
    )

    return UserResponse.model_validate(user)


# --- Logout ---

@router.post("/logout", response_model=MessageResponse, dependencies=[Depends(verify_csrf)])
async def logout(
    response: Response,
    session_token: str | None = Cookie(None, alias="session_token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Log out — invalidate the session. Per Section 4.3.
    """
    if session_token:
        await AuthService.logout(db, session_token)

    response.delete_cookie("session_token", path="/")
    response.delete_cookie("csrf_token", path="/")

    return MessageResponse(message="Logged out successfully")


# --- Current User ---

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Return the currently authenticated user's profile.
    Per Section 4.2: never return the password hash.
    """
    return UserResponse.model_validate(current_user)


# --- Forgot Password (Recovery-Email-Verified Flow) ---

@router.post("/forgot-password/request", response_model=ResetSessionResponse)
async def request_password_reset(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1: Request a password reset. Issues a reset_session_token.
    Does NOT send OTP — OTP is sent only after recovery email is verified in Step 2.
    Per Recovery Spec Section 5.1 & 7.2.
    """
    from app.middleware.rate_limit import check_rate_limit

    email = data.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"fp:{client_ip}", settings.rate_limit_password_reset)
    await check_rate_limit(f"fp:{email}", settings.rate_limit_password_reset)

    user = await AuthService.get_user_by_email(db, email)

    if user:
        session_token = await OTPService.create_reset_session(db, user)
    else:
        # Generate dummy session token to prevent account enumeration
        from app.core.security import generate_reset_token
        session_token = generate_reset_token()

    return ResetSessionResponse(
        message="If an account exists for this email, further instructions have been provided.",
        reset_session_token=session_token,
        recovery_email_required=False,
    )


@router.post("/forgot-password/verify-recovery-email", response_model=MessageResponse)
async def verify_recovery_email(
    data: VerifyRecoveryEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Verify the recovery email before sending OTP.
    Per Recovery Spec Section 5.2 & 7.1.
    On match: generates and sends OTP to the user's verified recovery email.
    """
    from app.middleware.rate_limit import check_rate_limit

    # Rate limit by session token hash prefix
    token_prefix = data.reset_session_token[:16] if len(data.reset_session_token) >= 16 else data.reset_session_token
    await check_rate_limit(f"recovery:{token_prefix}", settings.rate_limit_recovery_email)

    try:
        success, otp = await OTPService.verify_recovery_email(
            db, data.reset_session_token, data.recovery_email
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if success:
        # Get the user to send OTP to their verified recovery email
        from app.core.security import hash_session_token
        from app.models.otp import PasswordResetOTP
        from sqlalchemy import select

        token_hash = hash_session_token(data.reset_session_token)
        result = await db.execute(
            select(PasswordResetOTP).where(
                PasswordResetOTP.reset_token_hash == token_hash,
            )
        )
        record = result.scalar_one_or_none()
        if record:
            user_result = await db.execute(
                select(User).where(User.id == record.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user and user.recovery_email:
                email_sender = get_email_sender()
                await email_sender.send_otp_email(user.recovery_email, otp)

    return MessageResponse(
        message="Recovery email verified. OTP has been sent to your recovery email."
    )


@router.post("/forgot-password/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(
    data: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Verify the 6-digit OTP using the session token.
    Per Recovery Spec Section 7.3: ensures Step 2 (recovery email) was completed.
    """
    try:
        reset_token = await OTPService.verify_otp_with_session(
            db, data.reset_session_token, data.otp
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return OTPVerifyResponse(
        message="OTP verified successfully.",
        reset_token=reset_token,
    )


@router.post("/forgot-password/reset", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 4: Reset password using the reset token issued by verify-otp.
    Per Section 4.4 Step 3: updates password, invalidates token and active sessions.
    """
    try:
        await OTPService.reset_password(db, data.reset_token, data.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return MessageResponse(
        message="Password has been reset successfully. You can now log in with your new password."
    )


@router.post("/forgot-password/resend-otp", response_model=MessageResponse)
async def resend_otp(
    data: VerifyRecoveryEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Resend OTP for an active session that has passed recovery email verification.
    Uses VerifyRecoveryEmailRequest schema (reset_session_token + recovery_email for re-verification).
    """
    from app.middleware.rate_limit import check_otp_cooldown, check_rate_limit
    from app.core.security import hash_session_token

    token_key = hash_session_token(data.reset_session_token)
    await check_rate_limit(f"resend-otp:{token_key[:32]}", "3/minute")
    await check_otp_cooldown(token_key)

    try:
        # Re-verify recovery email and get new OTP
        success, otp = await OTPService.verify_recovery_email(
            db, data.reset_session_token, data.recovery_email
        )
    except ValueError as e:
        # If the session is already at recovery_verified stage, just resend
        try:
            otp = await OTPService.resend_otp_with_session(db, data.reset_session_token)
        except ValueError as e2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e2),
            )

    # Get user to send OTP to the verified recovery email
    from app.models.otp import PasswordResetOTP
    from sqlalchemy import select

    token_hash = hash_session_token(data.reset_session_token)
    result = await db.execute(
        select(PasswordResetOTP).where(
            PasswordResetOTP.reset_token_hash == token_hash,
        )
    )
    record = result.scalar_one_or_none()
    if record:
        user_result = await db.execute(
            select(User).where(User.id == record.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user and user.recovery_email:
            email_sender = get_email_sender()
            await email_sender.send_otp_email(user.recovery_email, otp)

    return MessageResponse(
        message="A new OTP has been sent to your recovery email."
    )




def _get_frontend_redirect_url(request: Request, path: str = "/pages/events.html?auth=success") -> str:
    """Build redirects only from the configured frontend origin."""
    return f"{settings.frontend_url}{path}"


# --- Google OAuth ---

@router.get("/google/login")
async def google_login(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Redirect to Google's authorization page or execute dev mock login if GOOGLE_CLIENT_ID is not set.
    """
    if not settings.google_client_id or not settings.google_client_id.strip():
        if not settings.google_mock_login_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google sign-in is not configured",
            )
        # Development mode: seamless mock login when credentials are not configured in .env
        user, token = await GoogleAuthService.handle_mock_login(db)

        # Set session cookie
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="none",
            max_age=settings.session_expire_hours * 3600,
            path="/",
        )

        # Set CSRF token
        csrf_token = generate_csrf_token()
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,
            secure=settings.secure_cookies,
            samesite="none",
            max_age=settings.session_expire_hours * 3600,
            path="/",
        )

        target_url = _get_frontend_redirect_url(request, "/pages/events.html?auth=success")
        response.status_code = status.HTTP_307_TEMPORARY_REDIRECT
        response.headers["Location"] = target_url
        return response

    state = GoogleAuthService.generate_state()

    # Store state in a cookie for verification on callback
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="none",
        max_age=600,  # 10 minutes
        path="/",
    )

    auth_url = GoogleAuthService.get_authorization_url(state)
    response.status_code = status.HTTP_307_TEMPORARY_REDIRECT
    response.headers["Location"] = auth_url
    return response



@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Google OAuth callback — exchange code, create/link user, redirect to frontend.
    Per Section 4.6.
    """
    # Verify state to prevent CSRF
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or not hmac.compare_digest(stored_state, state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    try:
        user, token = await GoogleAuthService.handle_callback(db, code)
    except ValueError as e:
        logger.error(f"Google OAuth error: {e}")
        # Redirect to frontend with error
        response.status_code = status.HTTP_307_TEMPORARY_REDIRECT
        response.headers["Location"] = f"{settings.frontend_url}/pages/login.html?error=google_auth_failed"
        return response

    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="none",
        max_age=settings.session_expire_hours * 3600,
        path="/",
    )

    # Set CSRF token
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="none",
        max_age=settings.session_expire_hours * 3600,
        path="/",
    )

    # Clear OAuth state cookie
    response.delete_cookie("oauth_state", path="/")

    # Redirect to frontend
    target_url = _get_frontend_redirect_url(request, "/pages/events.html?auth=success")
    response.status_code = status.HTTP_307_TEMPORARY_REDIRECT
    response.headers["Location"] = target_url
    return response
