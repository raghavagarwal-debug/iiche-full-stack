"""
Unit & integration tests for IIChE Admin Live Events Update spec requirements.
"""

from datetime import datetime, timedelta, timezone
import pytest


@pytest.mark.asyncio
async def test_admin_live_events_spec_requirements(client, admin_user, regular_user):
    admin_email = admin_user.email
    student_email = regular_user.email

    # 1. Admin login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )
    assert login_res.status_code == 200

    # 2. Test Admin Users CSV Export
    users_csv = await client.get("/api/v1/admin/users/export")
    assert users_csv.status_code == 200
    assert "text/csv" in users_csv.headers["content-type"]
    assert "Full Name,Email" in users_csv.text
    assert admin_email in users_csv.text

    # 3. Admin creates a Draft event
    draft_payload = {
        "title": "Draft Internal Secret Workshop",
        "description": "Preparing content",
        "event_date": (datetime.now(timezone.utc) + timedelta(days=20)).isoformat(),
        "venue": "Lab 101",
        "capacity": 50,
        "is_active": True,
        "status": "draft",
        "registration_open": False,
    }
    draft_res = await client.post("/api/v1/admin/events", json=draft_payload)
    assert draft_res.status_code == 201
    draft_event = draft_res.json()
    assert draft_event["status"] == "draft"
    assert draft_event["registration_status"] == "coming_soon"

    # 4. Verify Draft event does NOT appear on public GET /api/v1/events
    public_res = await client.get("/api/v1/events")
    assert public_res.status_code == 200
    public_titles = [e["title"] for e in public_res.json()]
    assert "Draft Internal Secret Workshop" not in public_titles

    # 5. Admin creates a Published event with future deadline
    pub_payload = {
        "title": "Live AI & Process Control Symposium",
        "description": "AI applications in process control",
        "event_date": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat(),
        "registration_deadline": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        "venue": "Main Hall",
        "capacity": 100,
        "is_active": True,
        "status": "published",
        "registration_open": True,
    }
    pub_res = await client.post("/api/v1/admin/events", json=pub_payload)
    assert pub_res.status_code == 201
    pub_event = pub_res.json()
    assert pub_event["status"] == "published"
    assert pub_event["registration_status"] == "open"
    pub_id = pub_event["id"]

    # 6. Verify Published event appears on public GET /api/v1/events with registration_status = 'open'
    public_res_2 = await client.get("/api/v1/events")
    assert public_res_2.status_code == 200
    pub_match = next((e for e in public_res_2.json() if e["id"] == pub_id), None)
    assert pub_match is not None
    assert pub_match["registration_status"] == "open"

    # 7. Student registers for the event
    await client.post("/api/v1/auth/logout")
    await client.post(
        "/api/v1/auth/login",
        json={"email": student_email, "password": "StudentPass123!"},
    )
    reg_res = await client.post(f"/api/v1/events/{pub_id}/register")
    assert reg_res.status_code == 201

    # 8. Admin verifies registrant count and single event CSV export
    await client.post("/api/v1/auth/logout")
    await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )
    admin_events = await client.get("/api/v1/admin/events")
    assert admin_events.status_code == 200
    admin_pub = next((e for e in admin_events.json() if e["id"] == pub_id), None)
    assert admin_pub is not None
    assert admin_pub["registrant_count"] == 1

    event_csv = await client.get(f"/api/v1/admin/events/{pub_id}/registrations/export")
    assert event_csv.status_code == 200
    assert "text/csv" in event_csv.headers["content-type"]
    assert student_email in event_csv.text

    # 9. Update deadline to past date -> confirm registration_status automatically flips to 'closed'
    past_deadline = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    patch_res = await client.patch(
        f"/api/v1/admin/events/{pub_id}",
        json={"registration_deadline": past_deadline},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["registration_status"] == "closed"
