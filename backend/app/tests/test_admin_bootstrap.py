"""Integration coverage for the persistent initial administrator bootstrap."""

import pytest
from sqlalchemy import func, select

from app.core.security import verify_password
from app.models.user import User
from app.services.bootstrap_service import ensure_initial_admin


@pytest.mark.asyncio
async def test_initial_admin_is_created_once_and_uses_normal_auth_flow(
    client, db_session, monkeypatch
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "initial_admin_name", "Bootstrap Administrator")
    monkeypatch.setattr(settings, "initial_admin_email", "Bootstrap.Admin@Example.com")
    monkeypatch.setattr(settings, "initial_admin_password", "BootstrapPass123!")

    first = await ensure_initial_admin(db_session)
    second = await ensure_initial_admin(db_session)

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert first.email == "bootstrap.admin@example.com"
    assert first.role == "admin"
    assert first.password_hash != "BootstrapPass123!"
    assert first.password_hash.startswith("$argon2id$")
    assert verify_password("BootstrapPass123!", first.password_hash)
    count = await db_session.scalar(
        select(func.count(User.id)).where(User.email == "bootstrap.admin@example.com")
    )
    assert count == 1

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "BOOTSTRAP.ADMIN@example.com", "password": "BootstrapPass123!"},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "admin"
    assert "session_token" in login.cookies

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    admin_stats = await client.get("/api/v1/admin/stats")
    assert admin_stats.status_code == 200

    regular_signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Ordinary User",
            "email": "ordinary@example.com",
            "password": "OrdinaryPass123!",
            "confirm_password": "OrdinaryPass123!",
            "recovery_email": "ordinary.recovery@example.com",
        },
    )
    assert regular_signup.status_code == 201
    regular_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ordinary@example.com", "password": "OrdinaryPass123!"},
    )
    assert regular_login.status_code == 200
    assert regular_login.json()["role"] == "user"

    denied = await client.get("/api/v1/admin/stats")
    assert denied.status_code == 403
