from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.payroll_summary import PayrollCalculationRequest, PayrollSummary
from app.services.payroll_calculator import calculate_payroll_for_timesheet
from app.services.validation_service import PayrollValidationError

router = APIRouter(tags=["payroll calculation"])


@router.post("/calculate-payroll", response_model=PayrollSummary)
def calculate_payroll(payload: PayrollCalculationRequest, db: Session = Depends(get_db)):
    try:
        return calculate_payroll_for_timesheet(db, payload.timesheet_id)
    except PayrollValidationError as exc:
        message = str(exc)
        status_code = 404 if message in {"Timesheet not found", "Missing payroll rules for employee"} else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
