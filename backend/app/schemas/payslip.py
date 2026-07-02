from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PayslipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    file_name: str
    period_start: date | None = None
    period_end: date | None = None
    gross_pay: Decimal | None = None
    tax_deducted: Decimal | None = None
    deductions: Decimal | None = None
    upload_status: str
    created_at: datetime
