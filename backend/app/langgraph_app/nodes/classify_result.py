"""Node 7: deterministic classification of the verification outcome.

This is the only place the final status is decided, and it is pure rule
evaluation over already-validated numbers - no LLM involved. Any hard error
from an earlier stage forces NEEDS_REVIEW before the numeric comparison is
even looked at, so an underpayment conclusion is never reached when required
evidence (payslip fields, timesheets, payroll rules, or the calculation
itself) was missing or unreliable. When gross and net disagree on direction,
that is treated as inconclusive evidence, not proof of a violation.
"""

from decimal import Decimal

from app.langgraph_app.state import PayrollVerificationState
from app.schemas.verification import VerificationStatus


def _side(expected: Decimal | None, actual: Decimal | None, tolerance: Decimal) -> str | None:
    if expected is None or actual is None:
        return None
    difference = actual - expected
    if difference < -tolerance:
        return "UNDERPAID"
    if difference > tolerance:
        return "OVERPAID"
    return "MATCH"


def classify_result_node(state: PayrollVerificationState) -> dict:
    hard_errors = (
        state.get("field_errors", [])
        + state.get("timesheet_errors", [])
        + state.get("rule_errors", [])
        + state.get("calculation_errors", [])
    )
    if hard_errors:
        return {
            "classification": "NEEDS_REVIEW",
            "blocking_errors": hard_errors,
            "stage": "classify_result",
        }

    comparison = state["comparison"]
    gross_side = _side(comparison.expected_gross_pay, comparison.actual_gross_pay, comparison.tolerance)
    net_side = _side(comparison.expected_net_pay, comparison.actual_net_pay, comparison.tolerance)
    sides = [side for side in (gross_side, net_side) if side is not None]

    classification: VerificationStatus
    if not sides:
        classification = "NEEDS_REVIEW"
    elif len(set(sides)) > 1:
        # Gross and net disagree on direction - inconclusive, not a violation.
        classification = "NEEDS_REVIEW"
    else:
        classification = sides[0]  # type: ignore[assignment]

    return {"classification": classification, "blocking_errors": [], "stage": "classify_result"}
