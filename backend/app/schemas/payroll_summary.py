from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PayrollCalculationRequest(BaseModel):
    timesheet_id: UUID


class PayrollSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: UUID
    pay_period: str
    ordinary_hours: Decimal
    overtime_hours: Decimal
    weekend_hours: Decimal
    public_holiday_hours: Decimal
    early_morning_hours: Decimal
    evening_hours: Decimal
    overnight_hours: Decimal
    hourly_rate: Decimal
    overtime_rate: Decimal
    penalty_rates_applied: list[str]
    gross_pay: Decimal
    estimated_tax: Decimal
    estimated_super: Decimal
    net_pay: Decimal
