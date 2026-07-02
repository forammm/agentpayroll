from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

VerificationStatus = Literal["good", "bad", "underpaid", "overpaid", "needs_review"]


class VerificationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    payslip_id: UUID
    expected_pay: Decimal
    actual_pay: Decimal
    underpaid_amount: Decimal
    overpaid_amount: Decimal
    tax_deducted: Decimal
    deductions: Decimal
    status: VerificationStatus
    notes: str | None = None
    created_at: datetime
