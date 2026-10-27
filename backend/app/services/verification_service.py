"""Persistence for verification results produced by the LangGraph workflow
(app.langgraph_app.graph). Node 9 (save_result) calls persist_verification_result;
the API layer (app/api/verification.py) calls get_verification_result to look
up an already-saved result.
"""

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.langgraph_app.errors import AccessDeniedError, VerificationNotFoundError
from app.langgraph_app.state import PayrollVerificationState
from app.models.verification_result import VerificationResult


def persist_verification_result(db: Session, state: PayrollVerificationState) -> VerificationResult:
    comparison = state.get("comparison")
    summary = state.get("payroll_summary")
    explanation = state["explanation"]
    payslip = state["payslip"]

    warnings = (
        state.get("field_warnings", [])
        + state.get("timesheet_warnings", [])
        + state.get("explanation_warnings", [])
        + (comparison.discrepancies if comparison else [])
    )
    errors = state.get("blocking_errors", [])

    existing = db.query(VerificationResult).filter(VerificationResult.payslip_id == state["payslip_id"]).first()
    result = existing or VerificationResult(id=uuid4(), payslip_id=state["payslip_id"])

    result.user_id = state["user_id"]
    result.pay_period_start = payslip.period_start
    result.pay_period_end = payslip.period_end
    result.status = state["classification"]
    result.tolerance = comparison.tolerance if comparison else None

    result.expected_gross_pay = comparison.expected_gross_pay if comparison else None
    result.actual_gross_pay = comparison.actual_gross_pay if comparison else None
    result.expected_net_pay = comparison.expected_net_pay if comparison else None
    result.actual_net_pay = comparison.actual_net_pay if comparison else None
    result.gross_difference = comparison.gross_difference if comparison else None
    result.net_difference = comparison.net_difference if comparison else None

    result.estimated_tax = summary.estimated_tax if summary else None
    result.estimated_super = summary.estimated_super if summary else None
    result.deductions = payslip.deductions

    result.calculation_breakdown = (
        {
            "ordinary_hours": str(summary.ordinary_hours),
            "overtime_hours": str(summary.overtime_hours),
            "weekend_hours": str(summary.weekend_hours),
            "public_holiday_hours": str(summary.public_holiday_hours),
            "early_morning_hours": str(summary.early_morning_hours),
            "evening_hours": str(summary.evening_hours),
            "overnight_hours": str(summary.overnight_hours),
            "hourly_rate": str(summary.hourly_rate),
            "overtime_rate": str(summary.overtime_rate),
            "penalty_rates_applied": summary.penalty_rates_applied,
        }
        if summary
        else None
    )

    result.explanation_summary = explanation.summary
    result.explanation_evidence = explanation.evidence or None
    result.explanation_uncertainties = explanation.uncertainties or None
    result.explanation_next_steps = explanation.next_steps or None

    result.warnings = warnings or None
    result.errors = errors or None

    if existing is None:
        db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_verification_result(db: Session, user_id: UUID, payslip_id: UUID) -> VerificationResult:
    result = db.query(VerificationResult).filter(VerificationResult.payslip_id == payslip_id).first()
    if result is None:
        raise VerificationNotFoundError(payslip_id)
    if result.user_id != user_id:
        raise AccessDeniedError(payslip_id)
    return result


def list_verification_results(db: Session, user_id: UUID, limit: int = 50) -> list[VerificationResult]:
    """History for a user, newest first. Scoped entirely by the user_id filter -
    there is no secondary identifier here for a cross-user check to guard."""
    return (
        db.query(VerificationResult)
        .filter(VerificationResult.user_id == user_id)
        .order_by(VerificationResult.created_at.desc())
        .limit(limit)
        .all()
    )
