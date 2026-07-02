from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.payroll_rule import PayrollRuleCreate, PayrollRuleResponse
from app.services import payroll_rule_service

router = APIRouter(prefix="/payroll-rules", tags=["payroll rules"])


@router.get("/{user_id}", response_model=PayrollRuleResponse)
def get_rule(user_id: UUID, db: Session = Depends(get_db)):
    rule = payroll_rule_service.get_latest_rule(db, user_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Payroll rule not found")
    return rule


@router.post("", response_model=PayrollRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(payload: PayrollRuleCreate, db: Session = Depends(get_db)):
    return payroll_rule_service.create_payroll_rule(db, payload)
