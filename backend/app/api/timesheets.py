from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.timesheet import TimesheetCreate, TimesheetResponse
from app.services import timesheet_service

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


@router.get("", response_model=list[TimesheetResponse])
def list_timesheets(user_id: UUID | None = None, db: Session = Depends(get_db)):
    return timesheet_service.list_timesheets(db, user_id)


@router.post("", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
def create_timesheet(payload: TimesheetCreate, db: Session = Depends(get_db)):
    return timesheet_service.create_timesheet(db, payload)
