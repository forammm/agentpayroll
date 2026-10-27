"""Full end-to-end flow through the real HTTP API (Prompt 6 definition of done):

    create timesheet -> configure payroll rules -> upload a synthetic payslip
    -> extract payroll fields -> run verification -> save result
    -> result appears on the dashboard

Uses a synthetic PDF (tests/pdf_factory.py) - no real personal payslip data.
This is a backend-only end-to-end test: no browser automation is available in
this environment, so it exercises every HTTP boundary the frontend would call,
but not the rendered UI itself (see the final report for how the UI layer was
verified instead).
"""

from decimal import Decimal

from tests.pdf_factory import build_text_payslip_pdf


def test_full_timesheet_to_dashboard_flow(client, seeded_user):
    user_id = str(seeded_user.id)

    # 1. Create a timesheet matching the payslip's pay period.
    timesheet_response = client.post(
        "/api/v1/timesheets",
        json={
            "user_id": user_id,
            "work_date": "2026-06-01",
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "break_minutes": 30,
            "shift_type": "normal",
        },
    )
    assert timesheet_response.status_code == 201

    # 2. Configure payroll rules.
    rules_response = client.post(
        "/api/v1/payroll-rules",
        json={
            "user_id": user_id,
            "normal_rate": "30.00", "overtime_rate": "45.00", "saturday_rate": "37.50",
            "sunday_rate": "45.00", "public_holiday_rate": "60.00", "overnight_rate": "33.00",
            "early_morning_rate": "31.50", "evening_rate": "31.50",
        },
    )
    assert rules_response.status_code == 201

    # 3-4. Upload a synthetic payslip and confirm extraction.
    pdf_bytes = build_text_payslip_pdf(
        employer="Acme Pty Ltd", period_start="01/06/2026", period_end="01/06/2026",
        gross_pay="225.00", net_pay="180.00", tax="45.00", superannuation="25.88", deductions="0.00",
    )
    upload_response = client.post(
        "/api/v1/payslips/upload",
        params={"user_id": user_id},
        files={"file": ("payslip.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_response.status_code == 200
    payslip_body = upload_response.json()
    payslip_id = payslip_body["id"]
    assert payslip_body["gross_pay"] == "225.00"

    # 5. Run verification (LangGraph workflow).
    run_response = client.post("/api/v1/verification/run", json={"user_id": user_id, "payslip_id": payslip_id})
    assert run_response.status_code == 200
    verification_body = run_response.json()
    assert verification_body["status"] == "MATCH"
    assert verification_body["expected_gross_pay"] == "225.00"
    assert verification_body["actual_gross_pay"] == "225.00"

    # 6. Confirm the result was saved and is independently retrievable.
    get_response = client.get(f"/api/v1/verification/{payslip_id}", params={"user_id": user_id})
    assert get_response.status_code == 200
    assert get_response.json()["id"] == verification_body["id"]

    # 7. Confirm it shows up on the dashboard.
    dashboard_response = client.get(f"/api/v1/dashboard/{user_id}")
    assert dashboard_response.status_code == 200
    dashboard_body = dashboard_response.json()
    assert dashboard_body["latest_verification"]["id"] == verification_body["id"]
    assert dashboard_body["hours_logged_current_period"] == "7.50"
    assert len(dashboard_body["history"]) == 1
