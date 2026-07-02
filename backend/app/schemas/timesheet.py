from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TimesheetCreate(BaseModel):
    user_id: UUID
    work_date: date
    start_time: time
    end_time: time
    break_minutes: int = Field(default=0, ge=0, le=1440)
    shift_type: str = Field(default="normal", max_length=40)

    @model_validator(mode="after")
    def validate_times(self) -> "TimesheetCreate":
        if self.start_time == self.end_time:
            raise ValueError("start_time and end_time must differ")
        return self


class TimesheetResponse(TimesheetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    hours_worked: Decimal
    created_at: datetime
