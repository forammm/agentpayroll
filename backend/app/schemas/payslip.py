from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.payslip_extraction import ExtractedEarningLine, PayslipStatus


class PayslipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    file_name: str
    status: PayslipStatus
    used_ocr: bool
    created_at: datetime

    employer_name: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    pay_date: date | None = None
    gross_pay: Decimal | None = None
    net_pay: Decimal | None = None
    tax_deducted: Decimal | None = None
    superannuation: Decimal | None = None
    deductions: Decimal | None = None
    ordinary_hours: Decimal | None = None
    overtime_hours: Decimal | None = None
    weekend_or_holiday_hours: Decimal | None = None
    hourly_rate: Decimal | None = None
    earnings_breakdown: list[ExtractedEarningLine] | None = None

    extraction_warnings: list[str] | None = None
    extraction_errors: list[str] | None = None
