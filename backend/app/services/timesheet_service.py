from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.timesheet import Timesheet
from app.schemas.timesheet import TimesheetCreate


class TimesheetNotFoundError(Exception):
    def __init__(self, timesheet_id: UUID):
        super().__init__(f"Timesheet {timesheet_id} not found.")
        self.timesheet_id = timesheet_id


class TimesheetAccessDeniedError(Exception):
    """Raised when the given user_id does not own the given timesheet."""

    def __init__(self, timesheet_id: UUID):
        super().__init__("You do not have access to this timesheet.")
        self.timesheet_id = timesheet_id


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


def get_timesheet(db: Session, timesheet_id: UUID) -> Timesheet:
    record = db.get(Timesheet, timesheet_id)
    if record is None:
        raise TimesheetNotFoundError(timesheet_id)
    return record


def update_timesheet(db: Session, timesheet_id: UUID, payload: TimesheetCreate) -> Timesheet:
    record = get_timesheet(db, timesheet_id)
    if record.user_id != payload.user_id:
        raise TimesheetAccessDeniedError(timesheet_id)

    for field, value in payload.model_dump().items():
        setattr(record, field, value)
    record.hours_worked = _hours(payload)

    db.commit()
    db.refresh(record)
    return record


def delete_timesheet(db: Session, timesheet_id: UUID, user_id: UUID) -> None:
    record = get_timesheet(db, timesheet_id)
    if record.user_id != user_id:
        raise TimesheetAccessDeniedError(timesheet_id)

    db.delete(record)
    db.commit()
