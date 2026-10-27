from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# Deterministic classification only - see app.langgraph_app.nodes.classify_result.
# MATCH: actual pay is within tolerance of the calculated expected pay.
# UNDERPAID / OVERPAID: actual pay differs from expected by more than tolerance.
# NEEDS_REVIEW: evidence was missing, inconsistent, or unsupported - never a guess.
VerificationStatus = Literal["MATCH", "UNDERPAID", "OVERPAID", "NEEDS_REVIEW"]


class VerificationRunRequest(BaseModel):
    user_id: UUID
    payslip_id: UUID


class VerificationExplanation(BaseModel):
    """Plain-English explanation generated from the already-computed, validated
    result below. The LLM producing this must not alter or invent the numbers -
    see app.langgraph_app.tools.llm_client."""

    summary: str
    evidence: list[str] = []
    uncertainties: list[str] = []
    next_steps: list[str] = []


class VerificationResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payslip_id: UUID
    user_id: UUID
    status: VerificationStatus
    created_at: datetime

    pay_period_start: date | None = None
    pay_period_end: date | None = None

    expected_gross_pay: Decimal | None = None
    actual_gross_pay: Decimal | None = None
    expected_net_pay: Decimal | None = None
    actual_net_pay: Decimal | None = None
    gross_difference: Decimal | None = None
    net_difference: Decimal | None = None
    tolerance: Decimal | None = None

    estimated_tax: Decimal | None = None
    estimated_super: Decimal | None = None
    deductions: Decimal | None = None

    calculation_breakdown: dict | None = None

    explanation_summary: str | None = None
    explanation_evidence: list[str] | None = None
    explanation_uncertainties: list[str] | None = None
    explanation_next_steps: list[str] | None = None

    warnings: list[str] | None = None
    errors: list[str] | None = None
