"""Tests for GET /api/v1/dashboard/{user_id} - replaces the Prompt 2 mock with
real aggregation over VerificationResult/Timesheet rows (Prompt 6)."""

from datetime import date
from decimal import Decimal

from app.langgraph_app.graph import run_verification

WORK_DATE = date(2026, 6, 1)


def test_dashboard_is_empty_for_a_new_user_not_fabricated(client, seeded_user):
    response = client.get(f"/api/v1/dashboard/{seeded_user.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_verification"] is None
    assert body["hours_logged_current_period"] is None
    assert body["history"] == []


def test_dashboard_reflects_the_latest_verification(client, db_session, seeded_user, make_payroll_rule, make_timesheet, make_payslip):
    make_payroll_rule(seeded_user.id)
    make_timesheet(seeded_user.id, WORK_DATE)
    payslip = make_payslip(
        seeded_user.id, period_start=WORK_DATE, period_end=WORK_DATE,
        gross_pay=Decimal("225.00"), net_pay=Decimal("180.00"),
    )
    from tests.conftest import FakeExplanationClient

    run_verification(db_session, seeded_user.id, payslip.id, llm_client=FakeExplanationClient())

    response = client.get(f"/api/v1/dashboard/{seeded_user.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_verification"]["status"] == "MATCH"
    assert body["hours_logged_current_period"] == "7.50"
    assert len(body["history"]) == 1


def test_dashboard_history_is_scoped_to_the_requesting_user(client, db_session, seeded_user, make_user, make_payroll_rule, make_timesheet, make_payslip):
    other_user = make_user()
    make_payroll_rule(other_user.id)
    make_timesheet(other_user.id, WORK_DATE)
    payslip = make_payslip(other_user.id, period_start=WORK_DATE, period_end=WORK_DATE, gross_pay=Decimal("225.00"), net_pay=Decimal("180.00"))
    from tests.conftest import FakeExplanationClient

    run_verification(db_session, other_user.id, payslip.id, llm_client=FakeExplanationClient())

    response = client.get(f"/api/v1/dashboard/{seeded_user.id}")

    assert response.status_code == 200
    assert response.json()["history"] == []
