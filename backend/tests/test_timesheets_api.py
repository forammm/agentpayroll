"""Tests for timesheet CRUD endpoints added in Prompt 6 (PUT/DELETE/{id} - list
and create already existed). Covers persistence, validation, and the ownership
check on mutation endpoints (list/create were already scoped by user_id itself
and need no separate check - see app/services/timesheet_service.py)."""


def _payload(user_id, work_date="2026-06-01", start_time="09:00:00", end_time="17:00:00", break_minutes=30, shift_type="normal"):
    return {
        "user_id": str(user_id),
        "work_date": work_date,
        "start_time": start_time,
        "end_time": end_time,
        "break_minutes": break_minutes,
        "shift_type": shift_type,
    }


def test_create_and_list_timesheets(client, seeded_user):
    response = client.post("/api/v1/timesheets", json=_payload(seeded_user.id))
    assert response.status_code == 201
    body = response.json()
    assert body["hours_worked"] == "7.50"

    list_response = client.get("/api/v1/timesheets", params={"user_id": str(seeded_user.id)})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_create_timesheet_rejects_equal_start_and_end_time(client, seeded_user):
    response = client.post("/api/v1/timesheets", json=_payload(seeded_user.id, start_time="09:00:00", end_time="09:00:00"))
    assert response.status_code == 422


def test_get_update_and_delete_timesheet(client, seeded_user):
    created = client.post("/api/v1/timesheets", json=_payload(seeded_user.id)).json()
    timesheet_id = created["id"]

    get_response = client.get(f"/api/v1/timesheets/{timesheet_id}")
    assert get_response.status_code == 200

    update_response = client.put(f"/api/v1/timesheets/{timesheet_id}", json=_payload(seeded_user.id, end_time="18:00:00"))
    assert update_response.status_code == 200
    assert update_response.json()["hours_worked"] == "8.50"

    delete_response = client.delete(f"/api/v1/timesheets/{timesheet_id}", params={"user_id": str(seeded_user.id)})
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/timesheets/{timesheet_id}")
    assert missing_response.status_code == 404


def test_get_nonexistent_timesheet_returns_404(client):
    import uuid

    response = client.get(f"/api/v1/timesheets/{uuid.uuid4()}")
    assert response.status_code == 404


def test_update_timesheet_rejects_cross_user_ownership(client, seeded_user, make_user):
    other_user = make_user()
    created = client.post("/api/v1/timesheets", json=_payload(seeded_user.id)).json()

    response = client.put(f"/api/v1/timesheets/{created['id']}", json=_payload(other_user.id))
    assert response.status_code == 403


def test_delete_timesheet_rejects_cross_user_ownership(client, seeded_user, make_user):
    other_user = make_user()
    created = client.post("/api/v1/timesheets", json=_payload(seeded_user.id)).json()

    response = client.delete(f"/api/v1/timesheets/{created['id']}", params={"user_id": str(other_user.id)})
    assert response.status_code == 403


def test_delete_nonexistent_timesheet_returns_404(client, seeded_user):
    import uuid

    response = client.delete(f"/api/v1/timesheets/{uuid.uuid4()}", params={"user_id": str(seeded_user.id)})
    assert response.status_code == 404
