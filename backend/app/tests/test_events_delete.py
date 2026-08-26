"""
Tests for Admin Event Deletion (Single delete and Bulk checkbox delete).
"""

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from app.models.event import Event
from app.models.registration import Registration


@pytest.mark.asyncio
async def test_single_and_bulk_event_delete(client, db_session, admin_user, regular_user):
    admin_email = admin_user.email
    student_email = regular_user.email

    now = datetime.now(timezone.utc)
    ev1 = Event(
        title="Test Event 1 to Delete",
        event_category="Workshop",
        description="To be deleted",
        venue="Room A",
        event_date=now + timedelta(days=5),
        status="published",
        registration_open=True,
    )
    ev2 = Event(
        title="Test Event 2 to Delete",
        event_category="Seminar",
        description="To be deleted",
        venue="Room B",
        event_date=now + timedelta(days=6),
        status="published",
        registration_open=True,
    )
    ev3 = Event(
        title="Test Event 3 to Keep",
        event_category="Competition",
        description="To keep",
        venue="Room C",
        event_date=now + timedelta(days=7),
        status="published",
        registration_open=True,
    )
    db_session.add_all([ev1, ev2, ev3])
    await db_session.commit()
    await db_session.refresh(ev1)
    await db_session.refresh(ev2)
    await db_session.refresh(ev3)

    # Register student to ev1
    reg1 = Registration(user_id=regular_user.id, event_id=ev1.id, status="registered")
    db_session.add(reg1)
    await db_session.commit()

    # 1. Non-admin cannot delete
    await client.post(
        "/api/v1/auth/login",
        json={"email": student_email, "password": "StudentPass123!"},
    )
    del_forbidden = await client.delete(f"/api/v1/admin/events/{ev1.id}")
    assert del_forbidden.status_code == 403

    bulk_forbidden = await client.post(
        "/api/v1/admin/events/bulk-delete",
        json={"event_ids": [str(ev1.id)]},
    )
    assert bulk_forbidden.status_code == 403

    # 2. Admin logs in
    await client.post("/api/v1/auth/logout")
    await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )

    # 3. Single delete ev1
    del_res = await client.delete(f"/api/v1/admin/events/{ev1.id}")
    assert del_res.status_code == 200
    assert "deleted successfully" in del_res.json()["message"]

    # Verify ev1 and its registration are gone
    events_res = await client.get("/api/v1/events")
    remaining_ids = [e["id"] for e in events_res.json()]
    assert str(ev1.id) not in remaining_ids

    # 4. Bulk delete ev2
    bulk_res = await client.post(
        "/api/v1/admin/events/bulk-delete",
        json={"event_ids": [str(ev2.id)]},
    )
    assert bulk_res.status_code == 200
    assert "Successfully deleted 1 event" in bulk_res.json()["message"]

    # Verify ev3 is still there
    events_res2 = await client.get("/api/v1/events")
    remaining_ids2 = [e["id"] for e in events_res2.json()]
    assert str(ev2.id) not in remaining_ids2
    assert str(ev3.id) in remaining_ids2


@pytest.mark.asyncio
async def test_delete_all_events_does_not_resurrect_on_seed_or_relogin(client, db_session, admin_user):
    from app.main import _seed_default_events

    admin_email = admin_user.email

    # Login as admin
    await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )

    # Get all events
    list_res = await client.get("/api/v1/admin/events")
    assert list_res.status_code == 200
    all_events = list_res.json()
    all_ids = [e["id"] for e in all_events]

    if all_ids:
        # Delete all events via bulk-delete
        bulk_del = await client.post(
            "/api/v1/admin/events/bulk-delete",
            json={"event_ids": all_ids},
        )
        assert bulk_del.status_code == 200

    # Verify event count is 0
    after_del_res = await client.get("/api/v1/admin/events")
    assert after_del_res.status_code == 200
    assert len(after_del_res.json()) == 0

    # Simulate server reload / seeding check
    await _seed_default_events()

    # Re-login as admin
    await client.post("/api/v1/auth/logout")
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_email, "password": "AdminPass123!"},
    )
    assert login_res.status_code == 200

    # Verify events remain 0 and were NOT resurrected
    recheck_res = await client.get("/api/v1/admin/events")
    assert recheck_res.status_code == 200
    assert len(recheck_res.json()) == 0

