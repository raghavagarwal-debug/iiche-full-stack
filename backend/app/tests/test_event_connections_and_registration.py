"""
Integration tests for the 6 connected IIChE events, status toggling, and registration flows.
"""

from datetime import datetime, timedelta, timezone
import pytest
from app.models.event import Event


@pytest.mark.asyncio
async def test_six_connected_events_and_registration_lifecycle(client, db_session, admin_user, regular_user):
    admin_email = admin_user.email
    student_email = regular_user.email

    now = datetime.now(timezone.utc)
    seeded_events = [
        Event(
            title="Design Workshop Layout and Design Tools",
            event_category="Workshop",
            description="Learn modern poster design",
            venue="Online",
            event_date=now + timedelta(days=14),
            registration_deadline=now + timedelta(days=13),
            capacity=100,
            is_active=True,
            status="published",
            registration_open=True,
        ),
        Event(
            title="MATLAB and Simulink for Chemical Engineers",
            event_category="Workshop",
            description="Numerical computation using MATLAB",
            venue="Lab 302",
            event_date=now + timedelta(days=21),
            registration_deadline=now + timedelta(days=20),
            capacity=80,
            is_active=True,
            status="published",
            registration_open=True,
        ),
        Event(
            title="Aspen and HYSYS Master Class",
            event_category="Workshop",
            description="Process design using Aspen Plus",
            venue="Virtual / Teams",
            event_date=now + timedelta(days=30),
            registration_deadline=now + timedelta(days=29),
            capacity=120,
            is_active=True,
            status="published",
            registration_open=True,
        ),
        Event(
            title="Alumni and Career Guidance Talk",
            event_category="Alumni Talks",
            description="Alumni placement preparation",
            venue="Main Auditorium",
            event_date=now + timedelta(days=10),
            registration_deadline=now + timedelta(days=9),
            capacity=200,
            is_active=True,
            status="published",
            registration_open=True,
        ),
        Event(
            title="IICHE Talks GATE Preparation Series",
            event_category="Alumni Talks",
            description="GATE preparation series",
            venue="Online (Google Meet)",
            event_date=now + timedelta(days=45),
            registration_deadline=now + timedelta(days=44),
            capacity=300,
            is_active=True,
            status="published",
            registration_open=True,
        ),
        Event(
            title="Coalescence 26 Flagship Fest",
            event_category="Flagship",
            description="Annual chemical engineering symposium",
            venue="BIT Mesra Campus",
            event_date=now + timedelta(days=60),
            registration_deadline=now + timedelta(days=55),
            capacity=500,
            is_active=True,
            status="published",
            registration_open=True,
        ),
    ]
    db_session.add_all(seeded_events)
    await db_session.commit()

    # 1. Fetch public events
    public_res = await client.get("/api/v1/events")
    assert public_res.status_code == 200
    events = public_res.json()
    titles = [e["title"] for e in events]

    # Verify Structural and FEA and Fluent CFD is NOT present
    assert "Structural and FEA and Fluent CFD" not in titles
    assert "DW-Sim Process Simulation Workshop" not in titles

    # Verify all 6 active events are present
    expected_events = [
        "Coalescence 26 Flagship Fest",
        "Aspen and HYSYS Master Class",
        "MATLAB and Simulink for Chemical Engineers",
        "Design Workshop Layout and Design Tools",
        "Alumni and Career Guidance Talk",
        "IICHE Talks GATE Preparation Series",
    ]
    for ev_title in expected_events:
        assert ev_title in titles, f"Missing event: {ev_title}"

    # 2. Find Aspen event
    aspen_ev = next(e for e in events if e["title"] == "Aspen and HYSYS Master Class")
    aspen_id = aspen_ev["id"]
    assert aspen_ev["registration_status"] == "open"

    # 3. Admin login and set Aspen to draft
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )
    assert login_res.status_code == 200

    patch_res = await client.patch(
        f"/api/v1/admin/events/{aspen_id}",
        json={"status": "draft", "registration_open": False},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["registration_status"] == "coming_soon"

    # 4. Student tries to register for draft event -> should be rejected
    await client.post("/api/v1/auth/logout")
    await client.post(
        "/api/v1/auth/login",
        json={"email": student_email, "password": "StudentPass123!"},
    )
    reg_draft_res = await client.post(f"/api/v1/events/{aspen_id}/register")
    assert reg_draft_res.status_code == 400

    # 5. Admin sets Aspen back to published
    await client.post("/api/v1/auth/logout")
    await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )
    patch_pub_res = await client.patch(
        f"/api/v1/admin/events/{aspen_id}",
        json={"status": "published", "registration_open": True},
    )
    assert patch_pub_res.status_code == 200
    assert patch_pub_res.json()["registration_status"] == "open"

    # 6. Student registers successfully for Aspen
    await client.post("/api/v1/auth/logout")
    await client.post(
        "/api/v1/auth/login",
        json={"email": student_email, "password": "StudentPass123!"},
    )
    reg_pub_res = await client.post(f"/api/v1/events/{aspen_id}/register")
    assert reg_pub_res.status_code == 201
    assert reg_pub_res.json()["event_id"] == aspen_id

    # 7. Student tries to register duplicate -> should be rejected
    reg_dup_res = await client.post(f"/api/v1/events/{aspen_id}/register")
    assert reg_dup_res.status_code == 400
    assert "already registered" in reg_dup_res.json()["detail"].lower()

    # 8. Check student's registered events list
    my_regs_res = await client.get("/api/v1/users/me/registrations")
    assert my_regs_res.status_code == 200
    my_reg_ids = [r["event_id"] for r in my_regs_res.json()]
    assert aspen_id in my_reg_ids
