from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.verification import VerificationResultResponse


class DashboardSummary(BaseModel):
    """Real aggregated data for the dashboard - never fabricated. latest_verification
    and hours_logged are explicitly nullable: a missing value means "nothing to show
    yet", not zero. See app.services.dashboard_service.get_dashboard_summary.
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    latest_verification: VerificationResultResponse | None = None
    hours_logged_current_period: Decimal | None = None
    history: list[VerificationResultResponse] = []
