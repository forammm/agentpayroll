"""Node 5: call the existing deterministic payroll calculator.

No payroll formula lives here or anywhere else in app.langgraph_app - this node
only calls app.services.payroll_calculator.calculate_payroll_summary (the same
function app/api/payroll_calculation.py uses) and translates its validation
failure into a routable error for classify_result to turn into NEEDS_REVIEW.
"""

from app.langgraph_app.state import PayrollVerificationState
from app.services.payroll_calculator import calculate_payroll_summary
from app.services.validation_service import PayrollValidationError


def calculate_expected_pay_node(state: PayrollVerificationState) -> dict:
    try:
        summary = calculate_payroll_summary(state["timesheets"], state["payroll_rule"])
    except PayrollValidationError as exc:
        return {"calculation_errors": [str(exc)], "stage": "calculate_expected_pay"}

    return {"payroll_summary": summary, "calculation_errors": [], "stage": "calculate_expected_pay"}
