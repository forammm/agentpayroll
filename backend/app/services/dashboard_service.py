"""Real dashboard aggregation - replaces the Prompt 2 mock. Reuses the
VerificationResult rows already produced by the LangGraph workflow (Prompt 5)
rather than recomputing or duplicating any payroll logic.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.timesheet import Timesheet
from app.models.verification_result import VerificationResult
from app.schemas.dashboard import DashboardSummary

HISTORY_LIMIT = 10


def get_dashboard_summary(db: Session, user_id: UUID) -> DashboardSummary:
    history = list(
        db.scalars(
            select(VerificationResult)
            .where(VerificationResult.user_id == user_id)
            .order_by(VerificationResult.created_at.desc())
            .limit(HISTORY_LIMIT)
        ).all()
    )
    latest = history[0] if history else None

    hours_logged = None
    if latest is not None and latest.pay_period_start is not None and latest.pay_period_end is not None:
        hours_logged = db.scalar(
            select(func.sum(Timesheet.hours_worked)).where(
                Timesheet.user_id == user_id,
                Timesheet.work_date >= latest.pay_period_start,
                Timesheet.work_date <= latest.pay_period_end,
            )
        )

    return DashboardSummary(
        user_id=user_id,
        latest_verification=latest,
        hours_logged_current_period=hours_logged,
        history=history,
    )
