"""
Unit and integration tests for Account Deletion (User Self-Deletion & Admin User Deletion).
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID
import pytest
from sqlalchemy import select

from app.models.registration import Registration
from app.models.session import Session
from app.models.user import User


@pytest.mark.asyncio
async def test_user_self_deletion(client, db_session):
    # 1. Signup a new user
    signup_data = {
        "full_name": "Delete Me User",
        "email": "deleteme@bitmesra.ac.in",
        "password": "Password123",
        "confirm_password": "Password123",
        "recovery_email": "deleteme.recovery@gmail.com",
    }
    signup_res = await client.post("/api/v1/auth/signup", json=signup_data)
    assert signup_res.status_code == 201

    # 2. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "deleteme@bitmesra.ac.in", "password": "Password123"},
    )
    assert login_res.status_code == 200
    user_id = UUID(login_res.json()["id"])

    # 3. Create a test event and register user to test cascade
    from app.models.event import Event
    event = Event(
        title="Test Cascade Event",
        description="Event to verify registration cascade deletion",
        event_date=datetime.now(timezone.utc) + timedelta(days=5),
        status="published",
        registration_open=True,
        is_active=True,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    reg_res = await client.post(f"/api/v1/events/{event.id}/register")
    assert reg_res.status_code == 201

    # Verify registration and session exists in DB
    reg_db = (await db_session.execute(
        select(Registration).where(Registration.user_id == user_id)
    )).scalar_one_or_none()
    assert reg_db is not None

    # 4. User deletes own account
    del_res = await client.delete("/api/v1/users/me")
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]

    # 5. Subsequent /auth/me call should fail with 401
    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 401

    # 6. Verify user is removed from DB
    user_db = (await db_session.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()
    assert user_db is None

    # 7. Verify registration and sessions are purged
    reg_after = (await db_session.execute(
        select(Registration).where(Registration.user_id == user_id)
    )).scalar_one_or_none()
    assert reg_after is None

    sessions_after = (await db_session.execute(
        select(Session).where(Session.user_id == user_id)
    )).scalars().all()
    assert len(sessions_after) == 0


@pytest.mark.asyncio
async def test_admin_delete_user(client, admin_user, regular_user, db_session):
    admin_email = admin_user.email
    user_to_delete_id = regular_user.id
    user_to_delete_email = regular_user.email

    # 1. Admin login
    await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )

    # 2. Admin deletes user
    del_res = await client.delete(f"/api/v1/admin/users/{user_to_delete_id}")
    assert del_res.status_code == 200
    assert "successfully deleted from database" in del_res.json()["message"]

    # 3. Verify user is deleted from database
    user_check = (await db_session.execute(
        select(User).where(User.id == user_to_delete_id)
    )).scalar_one_or_none()
    assert user_check is None


@pytest.mark.asyncio
async def test_admin_cannot_delete_self(client, admin_user):
    admin_email = admin_user.email
    admin_id = admin_user.id

    # Admin login
    await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )

    # Attempt self-deletion via admin endpoint
    del_res = await client.delete(f"/api/v1/admin/users/{admin_id}")
    assert del_res.status_code == 400
    assert "cannot delete your own admin account" in del_res.json()["detail"]


@pytest.mark.asyncio
async def test_regular_user_cannot_delete_via_admin_route(client, regular_user, admin_user):
    # Regular user login
    await client.post(
        "/api/v1/auth/login",
        json={"email": regular_user.email, "password": "StudentPass123!"},
    )

    # Attempt delete via admin endpoint
    del_res = await client.delete(f"/api/v1/admin/users/{admin_user.id}")
    assert del_res.status_code == 403


@pytest.mark.asyncio
async def test_admin_delete_event_registrations(client, admin_user, regular_user, db_session):
    from app.models.event import Event

    # 1. Create event
    event = Event(
        title="Clear Registrations Test Event",
        description="Event to verify clearing all attendee registrations",
        event_date=datetime.now(timezone.utc) + timedelta(days=10),
        status="published",
        registration_open=True,
        is_active=True,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    # 2. Register regular user
    await client.post(
        "/api/v1/auth/login",
        json={"email": regular_user.email, "password": "StudentPass123!"},
    )
    reg_res = await client.post(f"/api/v1/events/{event.id}/register")
    assert reg_res.status_code == 201

    # Verify registration in DB
    regs_before = (await db_session.execute(
        select(Registration).where(Registration.event_id == event.id)
    )).scalars().all()
    assert len(regs_before) == 1

    # 3. Admin logs in and clears all registrations for this event
    await client.post(
        "/api/v1/auth/login",
        json={"email": admin_user.email, "password": "AdminPass123!"},
    )
    del_res = await client.delete(f"/api/v1/admin/events/{event.id}/registrations")
    assert del_res.status_code == 200
    assert "cleared from the database" in del_res.json()["message"]

    # 4. Verify registrations in DB are 0
    regs_after = (await db_session.execute(
        select(Registration).where(Registration.event_id == event.id)
    )).scalars().all()
    assert len(regs_after) == 0

