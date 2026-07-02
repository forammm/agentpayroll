from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.timesheet import Timesheet
from app.schemas.timesheet import TimesheetCreate


def _hours(payload: TimesheetCreate) -> Decimal:
    start = datetime.combine(payload.work_date, payload.start_time)
    end = datetime.combine(payload.work_date, payload.end_time)
    if end < start:
        end += timedelta(days=1)
    minutes = max(0, int((end - start).total_seconds() / 60) - payload.break_minutes)
    return (Decimal(minutes) / Decimal(60)).quantize(Decimal("0.01"))


def create_timesheet(db: Session, payload: TimesheetCreate) -> Timesheet:
    record = Timesheet(**payload.model_dump(), hours_worked=_hours(payload))
    db.add(record); db.commit(); db.refresh(record)
    return record


def list_timesheets(db: Session, user_id: UUID | None = None) -> list[Timesheet]:
    query = select(Timesheet).order_by(Timesheet.work_date.desc())
    if user_id:
        query = query.where(Timesheet.user_id == user_id)
    return list(db.scalars(query).all())
