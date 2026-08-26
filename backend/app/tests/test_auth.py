"""
Tests for authentication, health, and user endpoints — Phase 1 verification.
"""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_signup_success(client):
    payload = {
        "full_name": "Test User",
        "email": "test@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "test.recovery@gmail.com",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    assert "Account created successfully" in response.json()["message"]


@pytest.mark.asyncio
async def test_signup_password_mismatch(client):
    payload = {
        "full_name": "Test User",
        "email": "test2@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "DifferentPassword123",
        "recovery_email": "test2.recovery@gmail.com",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_weak_password(client):
    payload = {
        "full_name": "Test User",
        "email": "test3@bitmesra.ac.in",
        "password": "weak",
        "confirm_password": "weak",
        "recovery_email": "test3.recovery@gmail.com",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_same_recovery_email(client):
    """Recovery email equal to primary email must be rejected (Section 4)."""
    payload = {
        "full_name": "Test User",
        "email": "same@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "same@bitmesra.ac.in",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_profile_recovery_email_is_saved_and_can_be_edited(client):
    signup_payload = {
        "full_name": "Profile User",
        "email": "profile@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "old.recovery@gmail.com",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    assert login_response.status_code == 200

    update_response = await client.patch(
        "/api/v1/users/me",
        json={"recovery_email": "  New.Recovery@Example.COM  "},
    )
    assert update_response.status_code == 200
    assert update_response.json()["recovery_email"] == "new.recovery@example.com"

    profile_response = await client.get("/api/v1/users/me")
    assert profile_response.status_code == 200
    assert profile_response.json()["recovery_email"] == "new.recovery@example.com"


@pytest.mark.asyncio
async def test_profile_same_recovery_email_is_rejected(client):
    signup_payload = {
        "full_name": "Same Email User",
        "email": "same.profile@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "different.recovery@gmail.com",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    assert login_response.status_code == 200

    update_response = await client.patch(
        "/api/v1/users/me",
        json={"recovery_email": "SAME.PROFILE@BITMESRA.AC.IN"},
    )
    assert update_response.status_code == 400
    assert "different from your account email" in update_response.json()["detail"]


@pytest.mark.asyncio
async def test_profile_recovery_email_cannot_be_blank(client):
    signup_payload = {
        "full_name": "Blank Recovery User",
        "email": "blank.profile@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "blank.recovery@gmail.com",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    assert login_response.status_code == 200

    update_response = await client.patch(
        "/api/v1/users/me",
        json={"recovery_email": "   "},
    )
    assert update_response.status_code == 422


@pytest.mark.asyncio
async def test_signup_duplicate_email(client):
    payload = {
        "full_name": "Test User",
        "email": "duplicate@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "dup.recovery@gmail.com",
    }
    res1 = await client.post("/api/v1/auth/signup", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/signup", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client):
    # Signup first
    signup_payload = {
        "full_name": "Login User",
        "email": "login@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "login.recovery@gmail.com",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    # Login
    login_payload = {
        "email": "login@bitmesra.ac.in",
        "password": "Password123",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "login@bitmesra.ac.in"
    assert "session_token" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_password(client):
    signup_payload = {
        "full_name": "User One",
        "email": "user1@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "user1.recovery@gmail.com",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    login_payload = {
        "email": "user1@bitmesra.ac.in",
        "password": "WrongPassword123",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_me_authenticated(client):
    signup_payload = {
        "full_name": "Me User",
        "email": "me@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "me.recovery@gmail.com",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    # Login to set cookie
    await client.post("/api/v1/auth/login", json={"email": "me@bitmesra.ac.in", "password": "Password123"})

    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["full_name"] == "Me User"


@pytest.mark.asyncio
async def test_logout(client):
    signup_payload = {
        "full_name": "Logout User",
        "email": "logout@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "logout.recovery@gmail.com",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)
    await client.post("/api/v1/auth/login", json={"email": "logout@bitmesra.ac.in", "password": "Password123"})

    logout_res = await client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200

    # Me call should now fail
    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 401


@pytest.mark.asyncio
async def test_google_login_mock(client, monkeypatch):
    # Call google login endpoint without GOOGLE_CLIENT_ID configured
    from app.core.config import settings
    monkeypatch.setattr(settings, "google_mock_login_enabled", True)
    response = await client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert response.status_code == 307
    assert "events.html?auth=success" in response.headers["location"]
    assert "session_token" in response.cookies

    # Verify session is authenticated
    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "google.user@bitmesra.ac.in"
