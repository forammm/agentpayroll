"""Node 8: turn the structured, already-decided result into plain English.

Always runs, even for NEEDS_REVIEW, so the employee gets a plain-English note
about what's missing - not just a bare status code. If the LLM is disabled,
unavailable, times out, errors, refuses, or returns something that fails
schema validation, this node falls back to a deterministic template built
only from the structured result already computed in Nodes 5-7. Verification
itself never fails because of this node.
"""

from decimal import Decimal

from app.config import settings
from app.langgraph_app.state import PayrollVerificationState
from app.langgraph_app.tools.llm_client import AnthropicExplanationClient, ExplanationClient, LlmGenerationError
from app.schemas.verification import VerificationExplanation


def generate_explanation_node(llm_client: ExplanationClient | None = None):
    client = llm_client or AnthropicExplanationClient()

    def _node(state: PayrollVerificationState) -> dict:
        context = _build_context(state)

        if settings.llm_enabled:
            try:
                explanation = client.generate_explanation(context)
                return {"explanation": explanation, "explanation_warnings": [], "used_llm": True, "stage": "generate_explanation"}
            except LlmGenerationError as exc:
                warning = f"AI-generated explanation unavailable ({exc}); showing a basic summary instead."
            except Exception:  # noqa: BLE001 - this node must never fail verification
                warning = "AI-generated explanation unavailable due to an unexpected error; showing a basic summary instead."
        else:
            warning = None

        explanation = _fallback_explanation(state)
        warnings = [warning] if warning else []
        return {"explanation": explanation, "explanation_warnings": warnings, "used_llm": False, "stage": "generate_explanation"}

    return _node


def _build_context(state: PayrollVerificationState) -> dict:
    classification = state.get("classification", "NEEDS_REVIEW")
    comparison = state.get("comparison")
    summary = state.get("payroll_summary")
    minimized = state.get("minimized_fields", {})

    context: dict = {
        "classification": classification,
        "employer_name": minimized.get("employer_name"),
        "pay_period_start": minimized.get("pay_period_start"),
        "pay_period_end": minimized.get("pay_period_end"),
        "blocking_errors": state.get("blocking_errors", []),
        "warnings": state.get("field_warnings", []) + state.get("timesheet_warnings", []) + (comparison.discrepancies if comparison else []),
    }
    if comparison is not None:
        context.update(
            expected_gross_pay=str(comparison.expected_gross_pay),
            actual_gross_pay=str(comparison.actual_gross_pay) if comparison.actual_gross_pay is not None else None,
            expected_net_pay=str(comparison.expected_net_pay) if comparison.expected_net_pay is not None else None,
            actual_net_pay=str(comparison.actual_net_pay) if comparison.actual_net_pay is not None else None,
            gross_difference=str(comparison.gross_difference) if comparison.gross_difference is not None else None,
            net_difference=str(comparison.net_difference) if comparison.net_difference is not None else None,
            tolerance=str(comparison.tolerance),
        )
    if summary is not None:
        context["calculation_breakdown"] = {
            "ordinary_hours": str(summary.ordinary_hours),
            "overtime_hours": str(summary.overtime_hours),
            "weekend_hours": str(summary.weekend_hours),
            "public_holiday_hours": str(summary.public_holiday_hours),
            "hourly_rate": str(summary.hourly_rate),
            "penalty_rates_applied": summary.penalty_rates_applied,
        }
    return context


def _fallback_explanation(state: PayrollVerificationState) -> VerificationExplanation:
    classification = state.get("classification", "NEEDS_REVIEW")
    comparison = state.get("comparison")
    blocking_errors = state.get("blocking_errors", [])

    if classification == "NEEDS_REVIEW":
        reasons = blocking_errors or (comparison.discrepancies if comparison else []) or ["Not enough information was available to complete verification."]
        return VerificationExplanation(
            summary="This payslip needs manual review - automated verification could not reach a confident result.",
            evidence=[],
            uncertainties=reasons,
            next_steps=["Check the items listed above and try again once they're resolved, or ask your payroll team to confirm the missing details."],
        )

    assert comparison is not None
    gross_text = _diff_sentence("gross pay", comparison.expected_gross_pay, comparison.actual_gross_pay, comparison.gross_difference)
    net_text = (
        _diff_sentence("net pay", comparison.expected_net_pay, comparison.actual_net_pay, comparison.net_difference)
        if comparison.expected_net_pay is not None
        else None
    )
    evidence = [text for text in (gross_text, net_text) if text]

    if classification == "MATCH":
        summary = "Your payslip matches the pay calculated from your timesheets and payroll rules, within the allowed tolerance."
        next_steps = ["No action needed - the figures line up with what was expected."]
    elif classification == "UNDERPAID":
        summary = "Your payslip shows less pay than expected based on your timesheets and payroll rules."
        next_steps = ["Double-check your timesheets and pay rates are up to date, then raise this with your payroll team."]
    else:
        summary = "Your payslip shows more pay than expected based on your timesheets and payroll rules."
        next_steps = ["Double-check your timesheets and pay rates are up to date - this may be a one-off adjustment."]

    return VerificationExplanation(
        summary=summary,
        evidence=evidence,
        uncertainties=comparison.discrepancies,
        next_steps=next_steps,
    )


def _diff_sentence(label: str, expected: Decimal | None, actual: Decimal | None, difference: Decimal | None) -> str | None:
    if expected is None or actual is None or difference is None:
        return None
    return f"Expected {label} of ${expected}, payslip shows ${actual} (difference: ${difference})."
