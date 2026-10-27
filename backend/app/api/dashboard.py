from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/{user_id}", response_model=DashboardSummary)
def dashboard_summary(user_id: UUID, db: Session = Depends(get_db)) -> DashboardSummary:
    return get_dashboard_summary(db, user_id)
