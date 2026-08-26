"""
Tests for Password Reset (Recovery-Email-Verified Flow).
Step 1: Request Password Reset -> issues reset_session_token (no OTP sent yet)
Step 2: Verify Recovery Email -> checks against stored recovery email -> sends OTP to recovery email
Step 3: Verify OTP with session token -> issues short-lived reset_token
Step 4: Reset Password -> updates password, invalidates sessions
"""

import pytest
from sqlalchemy import select

from app.models.otp import PasswordResetOTP
from app.schemas.auth import SignupRequest
from app.services.auth_service import AuthService
from app.services.otp_service import OTPService


@pytest.mark.asyncio
async def test_full_recovery_email_password_reset_flow(client, db_session, monkeypatch):
    """Test full 4-step recovery-email-verified password reset flow."""
    sent_recipients = []

    class CaptureEmailSender:
        async def send_otp_email(self, to_email: str, otp: str) -> None:
            sent_recipients.append(to_email)

    monkeypatch.setattr(
        "app.api.v1.auth.get_email_sender",
        lambda: CaptureEmailSender(),
    )

    # 1. Create a test user with recovery email
    signup_data = SignupRequest(
        full_name="Reset User",
        email="reset@example.com",
        password="OldPassword123",
        confirm_password="OldPassword123",
        recovery_email="reset.recovery@gmail.com",
    )
    user = await AuthService.signup(db_session, signup_data)
    assert user is not None
    assert user.recovery_email == "reset.recovery@gmail.com"

    # Step 1: Request reset session
    req_resp = await client.post(
        "/api/v1/auth/forgot-password/request",
        json={"email": "reset@example.com"},
    )
    assert req_resp.status_code == 200
    req_data = req_resp.json()
    assert req_data["reset_session_token"] != ""
    reset_session_token = req_data["reset_session_token"]
    assert req_data["recovery_email_required"] is False

    # Step 2a: Try wrong recovery email -> should fail with 400
    bad_recovery_resp = await client.post(
        "/api/v1/auth/forgot-password/verify-recovery-email",
        json={
            "reset_session_token": reset_session_token,
            "recovery_email": "wrong.email@gmail.com",
        },
    )
    assert bad_recovery_resp.status_code == 400
    assert "Wrong recovery email" in bad_recovery_resp.json()["detail"]

    # Step 2b: Submit correct recovery email -> success
    good_recovery_resp = await client.post(
        "/api/v1/auth/forgot-password/verify-recovery-email",
        json={
            "reset_session_token": reset_session_token,
            "recovery_email": "reset.recovery@gmail.com",
        },
    )
    assert good_recovery_resp.status_code == 200
    assert "OTP has been sent" in good_recovery_resp.json()["message"]
    assert sent_recipients == ["reset.recovery@gmail.com"]

    # Step 3a: Verify with invalid OTP first
    bad_otp_resp = await client.post(
        "/api/v1/auth/forgot-password/verify-otp",
        json={
            "reset_session_token": reset_session_token,
            "otp": "000000",
        },
    )
    assert bad_otp_resp.status_code == 400
    assert "Invalid OTP" in bad_otp_resp.json()["detail"]

    # Step 3b: Get the generated OTP directly or via a fresh session for testing
    # In test environment, console email sender prints it. Let's get the active OTP from DB
    from app.core.security import hash_session_token
    token_hash = hash_session_token(reset_session_token)
    otp_record_res = await db_session.execute(
        select(PasswordResetOTP).where(PasswordResetOTP.reset_token_hash == token_hash)
    )
    otp_record = otp_record_res.scalar_one()
    assert otp_record.stage == "recovery_verified"

    # Generate a known OTP for deterministic test verification
    from app.core.security import hash_otp
    test_otp = "123456"
    otp_record.otp_hash = hash_otp(test_otp)
    await db_session.commit()

    good_otp_resp = await client.post(
        "/api/v1/auth/forgot-password/verify-otp",
        json={
            "reset_session_token": reset_session_token,
            "otp": test_otp,
        },
    )
    assert good_otp_resp.status_code == 200, f"Verify failed: {good_otp_resp.json()}"
    reset_token = good_otp_resp.json().get("reset_token")
    assert reset_token is not None

    # Step 4: Reset password
    reset_resp = await client.post(
        "/api/v1/auth/forgot-password/reset",
        json={
            "reset_token": reset_token,
            "new_password": "NewPassword123",
            "confirm_password": "NewPassword123",
        },
    )
    assert reset_resp.status_code == 200

    # Step 5: Verify user can login with new password
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "NewPassword123"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["email"] == "reset@example.com"


@pytest.mark.asyncio
async def test_skip_step_attack_blocked(client, db_session):
    """Verify that calling verify-otp directly without completing recovery email step fails."""
    signup_data = SignupRequest(
        full_name="Skip User",
        email="skip@example.com",
        password="OldPassword123",
        confirm_password="OldPassword123",
        recovery_email="skip.recovery@gmail.com",
    )
    user = await AuthService.signup(db_session, signup_data)

    # Request reset session
    req_resp = await client.post(
        "/api/v1/auth/forgot-password/request",
        json={"email": "skip@example.com"},
    )
    reset_session_token = req_resp.json()["reset_session_token"]

    # Try to verify OTP directly without completing Step 2
    skip_resp = await client.post(
        "/api/v1/auth/forgot-password/verify-otp",
        json={
            "reset_session_token": reset_session_token,
            "otp": "123456",
        },
    )
    assert skip_resp.status_code == 400
    assert "Invalid session state" in skip_resp.json()["detail"]


@pytest.mark.asyncio
async def test_reset_session_token_cannot_reset_password_before_otp(client, db_session):
    signup_data = SignupRequest(
        full_name="Pre OTP User",
        email="preotp@example.com",
        password="OldPassword123",
        confirm_password="OldPassword123",
        recovery_email="preotp.recovery@gmail.com",
    )
    await AuthService.signup(db_session, signup_data)

    req_resp = await client.post(
        "/api/v1/auth/forgot-password/request",
        json={"email": "preotp@example.com"},
    )
    reset_session_token = req_resp.json()["reset_session_token"]

    reset_resp = await client.post(
        "/api/v1/auth/forgot-password/reset",
        json={
            "reset_token": reset_session_token,
            "new_password": "AttackerPassword123",
            "confirm_password": "AttackerPassword123",
        },
    )
    assert reset_resp.status_code == 400
    assert "Invalid or expired reset token" in reset_resp.json()["detail"]


@pytest.mark.asyncio
async def test_existing_user_without_recovery_email(client, db_session):
    """Users without recovery email set receive a session token and are safely rejected at Step 2."""
    from app.models.user import User
    from app.core.security import hash_password

    # Create pre-migration user with NO recovery email
    old_user = User(
        full_name="Legacy User",
        email="legacy@example.com",
        password_hash=hash_password("Password123"),
        recovery_email=None,
        is_active=True,
    )
    db_session.add(old_user)
    await db_session.commit()

    req_resp = await client.post(
        "/api/v1/auth/forgot-password/request",
        json={"email": "legacy@example.com"},
    )
    assert req_resp.status_code == 200
    token = req_resp.json()["reset_session_token"]
    assert token != ""

    # Step 2 verification must fail with generic error
    step2_resp = await client.post(
        "/api/v1/auth/forgot-password/verify-recovery-email",
        json={
            "reset_session_token": token,
            "recovery_email": "any.recovery@gmail.com",
        },
    )
    assert step2_resp.status_code == 400
    assert "Wrong recovery email" in step2_resp.json()["detail"]
