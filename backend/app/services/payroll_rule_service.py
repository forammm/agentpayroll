from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payroll_rule import PayrollRule
from app.schemas.payroll_rule import PayrollRuleCreate


def create_payroll_rule(db: Session, payload: PayrollRuleCreate) -> PayrollRule:
    rule = PayrollRule(**payload.model_dump())
    db.add(rule); db.commit(); db.refresh(rule)
    return rule


def get_latest_rule(db: Session, user_id: UUID) -> PayrollRule | None:
    query = select(PayrollRule).where(PayrollRule.user_id == user_id).order_by(PayrollRule.created_at.desc())
    return db.scalar(query)
