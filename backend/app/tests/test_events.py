"""
Tests for Events, Registrations, and Admin APIs — Phase 4 & Phase 5 verification.
"""

from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_event_lifecycle_and_registration(client, admin_user, regular_user):
    admin_email = admin_user.email
    student_email = regular_user.email

    # 1. Admin logs in
    login_admin = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )
    assert login_admin.status_code == 200

    # 2. Admin creates event (registration_open=False by default)
    event_payload = {
        "title": "Coalescence 2026",
        "description": "Annual Chemical Engineering Symposium",
        "event_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "venue": "CAT Hall, BIT Mesra",
        "capacity": 100,
        "is_active": True,
        "registration_open": False,
    }
    create_res = await client.post("/api/v1/admin/events", json=event_payload)
    assert create_res.status_code == 201
    event_data = create_res.json()
    event_id = event_data["id"]
    assert event_data["registration_open"] is False

    # 3. Public lists active events
    list_res = await client.get("/api/v1/events")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. Regular user logs in
    await client.post("/api/v1/auth/logout")
    login_student = await client.post(
        "/api/v1/auth/login",
        json={"email": student_email, "password": "StudentPass123!"},
    )
    assert login_student.status_code == 200

    # 5. Attempt register while registration_open=False (Section 22: backend gates request)
    reg_fail = await client.post(f"/api/v1/events/{event_id}/register")
    assert reg_fail.status_code == 400
    assert "not open" in reg_fail.json()["detail"]

    # 6. Admin logs in and opens registration
    await client.post("/api/v1/auth/logout")
    await client.post("/api/v1/auth/login", json={"email": admin_email, "password": "AdminPass123!"})

    patch_res = await client.patch(
        f"/api/v1/admin/events/{event_id}",
        json={"registration_open": True},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["registration_open"] is True

    # 7. Student logs in and registers successfully
    await client.post("/api/v1/auth/logout")
    await client.post("/api/v1/auth/login", json={"email": student_email, "password": "StudentPass123!"})

    reg_success = await client.post(f"/api/v1/events/{event_id}/register")
    assert reg_success.status_code == 201
    assert reg_success.json()["event_id"] == event_id

    # 8. Attempt duplicate registration (Section 7: DB UNIQUE constraint backstop)
    dup_res = await client.post(f"/api/v1/events/{event_id}/register")
    assert dup_res.status_code == 400
    assert "already registered" in dup_res.json()["detail"]

    # 9. Student checks "My Registrations"
    my_regs = await client.get("/api/v1/users/me/registrations")
    assert my_regs.status_code == 200
    assert len(my_regs.json()) == 1
    assert my_regs.json()[0]["event_title"] == "Coalescence 2026"

    # 10. Admin checks event registration list & CSV export
    await client.post("/api/v1/auth/logout")
    await client.post("/api/v1/auth/login", json={"email": admin_email, "password": "AdminPass123!"})

    admin_view = await client.get(f"/api/v1/admin/events/{event_id}/registrations")
    assert admin_view.status_code == 200
    assert len(admin_view.json()) == 1
    assert admin_view.json()[0]["user_email"] == student_email

    csv_export = await client.get(f"/api/v1/admin/events/{event_id}/registrations/export")
    assert csv_export.status_code == 200
    assert "text/csv" in csv_export.headers["content-type"]
    assert student_email in csv_export.text


@pytest.mark.asyncio
async def test_admin_authorization_enforced(client, regular_user):
    """Ensure non-admin users get 403 when hitting admin endpoints."""
    student_email = regular_user.email
    await client.post("/api/v1/auth/login", json={"email": student_email, "password": "StudentPass123!"})

    res = await client.get("/api/v1/admin/events")
    assert res.status_code == 403
    assert "Admin access required" in res.json()["detail"]
