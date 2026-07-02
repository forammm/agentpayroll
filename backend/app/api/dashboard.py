from uuid import UUID

from fastapi import APIRouter

from app.services.dashboard_service import get_mock_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/{user_id}")
def dashboard_summary(user_id: UUID) -> dict:
    return get_mock_summary(user_id)
