"""Node 3: load the timesheets covering the payslip's pay period.

Reuses the deterministic engine's own validators (validate_shift_time_range,
validate_no_shift_overlaps from app.services.validation_service) instead of
writing a second overlap-detection implementation. The SQLAlchemy filter on
user_id is what actually prevents mixing records between users - it is not
possible for this query to return another user's shifts.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.langgraph_app.state import PayrollVerificationState
from app.models.timesheet import Timesheet
from app.services.validation_service import PayrollValidationError, validate_no_shift_overlaps, validate_shift_time_range


def load_timesheet_node(db: Session):
    def _node(state: PayrollVerificationState) -> dict:
        payslip = state["payslip"]
        period_start = payslip.period_start
        period_end = payslip.period_end

        if period_start is None or period_end is None:
            return {
                "timesheets": [],
                "timesheet_errors": ["The payslip's pay period dates could not be determined, so matching timesheets could not be loaded."],
                "timesheet_warnings": [],
                "stage": "load_timesheet",
            }

        shifts = list(
            db.scalars(
                select(Timesheet)
                .where(
                    Timesheet.user_id == state["user_id"],
                    Timesheet.work_date >= period_start,
                    Timesheet.work_date <= period_end,
                )
                .order_by(Timesheet.work_date.asc(), Timesheet.start_time.asc())
            ).all()
        )

        if not shifts:
            return {
                "timesheets": [],
                "timesheet_errors": [f"No timesheet entries were found for the pay period {period_start.isoformat()} to {period_end.isoformat()}."],
                "timesheet_warnings": [],
                "stage": "load_timesheet",
            }

        errors: list[str] = []
        try:
            for shift in shifts:
                validate_shift_time_range(shift)
            validate_no_shift_overlaps(shifts)
        except PayrollValidationError as exc:
            errors.append(str(exc))

        return {
            "timesheets": shifts,
            "timesheet_errors": errors,
            "timesheet_warnings": [],
            "stage": "load_timesheet",
        }

    return _node
