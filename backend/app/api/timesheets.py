from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.timesheet import TimesheetCreate, TimesheetResponse
from app.services import timesheet_service
from app.services.timesheet_service import TimesheetAccessDeniedError, TimesheetNotFoundError

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


@router.get("", response_model=list[TimesheetResponse])
def list_timesheets(user_id: UUID | None = None, db: Session = Depends(get_db)):
    return timesheet_service.list_timesheets(db, user_id)


@router.post("", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
def create_timesheet(payload: TimesheetCreate, db: Session = Depends(get_db)):
    return timesheet_service.create_timesheet(db, payload)


@router.get("/{timesheet_id}", response_model=TimesheetResponse)
def get_timesheet(timesheet_id: UUID, db: Session = Depends(get_db)):
    try:
        return timesheet_service.get_timesheet(db, timesheet_id)
    except TimesheetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timesheet not found.") from exc


@router.put("/{timesheet_id}", response_model=TimesheetResponse)
def update_timesheet(timesheet_id: UUID, payload: TimesheetCreate, db: Session = Depends(get_db)):
    try:
        return timesheet_service.update_timesheet(db, timesheet_id, payload)
    except TimesheetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timesheet not found.") from exc
    except TimesheetAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this timesheet.") from exc


@router.delete("/{timesheet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timesheet(timesheet_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    try:
        timesheet_service.delete_timesheet(db, timesheet_id, user_id)
    except TimesheetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timesheet not found.") from exc
    except TimesheetAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this timesheet.") from exc
