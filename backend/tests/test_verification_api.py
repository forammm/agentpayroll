"""HTTP-level tests for POST /api/v1/verification/run and GET /api/v1/verification/{id}.

These exercise the full real stack through the `client` TestClient fixture,
including the real AnthropicExplanationClient - there is no way to inject a
fake LLM client through the HTTP layer, and no ANTHROPIC_API_KEY is configured
in this test environment, so every run here genuinely exercises the documented
fallback behavior (not a mock) when the LLM is unavailable. See
test_verification_graph.py for tests using a mocked LLM client, and
test_llm_client.py for the LLM wrapper's own unit tests.
"""

from datetime import date
from decimal import Decimal

import pytest

WORK_DATE = date(2026, 6, 1)


def _setup_matching_case(make_payroll_rule, make_timesheet, make_payslip, user_id, **payslip_overrides):
    make_payroll_rule(user_id)
    make_timesheet(user_id, WORK_DATE)
    defaults = dict(period_start=WORK_DATE, period_end=WORK_DATE, gross_pay=Decimal("225.00"), net_pay=Decimal("180.00"))
    defaults.update(payslip_overrides)
    return make_payslip(user_id, **defaults)


def test_run_endpoint_returns_a_structured_result(client, seeded_user, make_payroll_rule, make_timesheet, make_payslip):
    payslip = _setup_matching_case(make_payroll_rule, make_timesheet, make_payslip, seeded_user.id)

    response = client.post("/api/v1/verification/run", json={"user_id": str(seeded_user.id), "payslip_id": str(payslip.id)})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "MATCH"
    assert body["payslip_id"] == str(payslip.id)
    assert body["user_id"] == str(seeded_user.id)
    assert body["expected_gross_pay"] == "225.00"
    assert "explanation_summary" in body


def test_run_endpoint_falls_back_gracefully_without_a_configured_llm(client, seeded_user, make_payroll_rule, make_timesheet, make_payslip, monkeypatch):
    # No ANTHROPIC_API_KEY is set in this environment, so the real client's
    # fallback path is what actually runs here - this is not a mock.
    payslip = _setup_matching_case(
        make_payroll_rule, make_timesheet, make_payslip, seeded_user.id,
        gross_pay=Decimal("200.00"), net_pay=Decimal("160.00"),
    )

    response = client.post("/api/v1/verification/run", json={"user_id": str(seeded_user.id), "payslip_id": str(payslip.id)})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "UNDERPAID"
    assert body["explanation_summary"]  # fallback template still produced something
    assert any("unavailable" in w.lower() for w in (body["warnings"] or []))


def test_run_endpoint_returns_404_for_unknown_payslip(client, seeded_user):
    import uuid

    response = client.post("/api/v1/verification/run", json={"user_id": str(seeded_user.id), "payslip_id": str(uuid.uuid4())})

    assert response.status_code == 404
    assert "stack" not in response.text.lower()
    assert "traceback" not in response.text.lower()


def test_run_endpoint_returns_403_for_cross_user_access(client, seeded_user, make_user, make_payroll_rule, make_timesheet, make_payslip):
    other_user = make_user()
    payslip = _setup_matching_case(make_payroll_rule, make_timesheet, make_payslip, seeded_user.id)

    response = client.post("/api/v1/verification/run", json={"user_id": str(other_user.id), "payslip_id": str(payslip.id)})

    assert response.status_code == 403


def test_get_endpoint_returns_404_before_any_run(client, seeded_user, make_payslip):
    payslip = make_payslip(seeded_user.id)

    response = client.get(f"/api/v1/verification/{payslip.id}", params={"user_id": str(seeded_user.id)})

    assert response.status_code == 404


def test_get_endpoint_returns_the_saved_result_after_a_run(client, seeded_user, make_payroll_rule, make_timesheet, make_payslip):
    payslip = _setup_matching_case(make_payroll_rule, make_timesheet, make_payslip, seeded_user.id)
    client.post("/api/v1/verification/run", json={"user_id": str(seeded_user.id), "payslip_id": str(payslip.id)})

    response = client.get(f"/api/v1/verification/{payslip.id}", params={"user_id": str(seeded_user.id)})

    assert response.status_code == 200
    assert response.json()["status"] == "MATCH"


def test_get_endpoint_returns_403_for_cross_user_access(client, seeded_user, make_user, make_payroll_rule, make_timesheet, make_payslip):
    other_user = make_user()
    payslip = _setup_matching_case(make_payroll_rule, make_timesheet, make_payslip, seeded_user.id)
    client.post("/api/v1/verification/run", json={"user_id": str(seeded_user.id), "payslip_id": str(payslip.id)})

    response = client.get(f"/api/v1/verification/{payslip.id}", params={"user_id": str(other_user.id)})

    assert response.status_code == 403


def test_run_endpoint_rejects_malformed_request_body(client, seeded_user):
    response = client.post("/api/v1/verification/run", json={"user_id": str(seeded_user.id)})  # missing payslip_id

    assert response.status_code == 422


def test_history_endpoint_lists_results_newest_first(client, db_session, seeded_user, make_payroll_rule, make_timesheet, make_payslip):
    from datetime import datetime, timedelta, timezone

    from app.models.verification_result import VerificationResult

    make_payroll_rule(seeded_user.id)
    make_timesheet(seeded_user.id, WORK_DATE)
    make_timesheet(seeded_user.id, WORK_DATE + timedelta(days=1))

    first = make_payslip(seeded_user.id, period_start=WORK_DATE, period_end=WORK_DATE, gross_pay=Decimal("225.00"), net_pay=Decimal("180.00"))
    second = make_payslip(
        seeded_user.id, period_start=WORK_DATE + timedelta(days=1), period_end=WORK_DATE + timedelta(days=1),
        gross_pay=Decimal("225.00"), net_pay=Decimal("180.00"),
    )
    client.post("/api/v1/verification/run", json={"user_id": str(seeded_user.id), "payslip_id": str(first.id)})
    client.post("/api/v1/verification/run", json={"user_id": str(seeded_user.id), "payslip_id": str(second.id)})

    # Both requests can land in the same wall-clock second under SQLite's
    # CURRENT_TIMESTAMP (second resolution) when run back-to-back in a test -
    # force a deterministic, clearly-ordered created_at for each so this test
    # verifies the ORDER BY logic itself rather than depending on real timing.
    now = datetime.now(timezone.utc)
    db_session.query(VerificationResult).filter(VerificationResult.payslip_id == first.id).update({"created_at": now - timedelta(minutes=5)})
    db_session.query(VerificationResult).filter(VerificationResult.payslip_id == second.id).update({"created_at": now})
    db_session.commit()

    response = client.get("/api/v1/verification", params={"user_id": str(seeded_user.id)})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["payslip_id"] == str(second.id)  # newest first


def test_history_endpoint_is_empty_for_a_user_with_no_verifications(client, seeded_user):
    response = client.get("/api/v1/verification", params={"user_id": str(seeded_user.id)})

    assert response.status_code == 200
    assert response.json() == []
