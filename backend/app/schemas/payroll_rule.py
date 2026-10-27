from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PayrollRuleCreate(BaseModel):
    user_id: UUID
    normal_rate: Decimal = Field(ge=0)
    overtime_rate: Decimal = Field(ge=0)
    saturday_rate: Decimal = Field(ge=0)
    sunday_rate: Decimal = Field(ge=0)
    public_holiday_rate: Decimal = Field(ge=0)
    overnight_rate: Decimal = Field(ge=0)
    early_morning_rate: Decimal = Field(ge=0)
    evening_rate: Decimal = Field(ge=0)


class PayrollRuleResponse(PayrollRuleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime
