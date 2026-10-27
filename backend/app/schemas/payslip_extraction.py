from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

# UPLOADED: file accepted, not yet processed (not currently observed in responses - extraction
#   runs synchronously - kept for API stability once async/background processing is introduced).
# PROCESSING: extraction in progress (same note as above).
# EXTRACTED: extraction completed with no warnings or errors.
# NEEDS_REVIEW: extraction completed but produced warnings, errors, or used OCR.
# FAILED: no usable data could be extracted at all (corrupted/unsupported content reaching this
#   stage, or a scanned PDF with no OCR available).
PayslipStatus = Literal["UPLOADED", "PROCESSING", "EXTRACTED", "NEEDS_REVIEW", "FAILED"]


class ExtractedEarningLine(BaseModel):
    """One row of an earnings/pay components table, e.g. {label: 'Base hours', amount: 1234.56}."""

    model_config = ConfigDict(from_attributes=True)
    label: str
    amount: Decimal


class PayslipExtractedFields(BaseModel):
    """Structured payroll data pulled from a payslip PDF.

    Every field is optional: a missing value must be represented as None, never as 0 or an
    invented default. This schema carries only the fields needed for payroll verification -
    it deliberately excludes bank account numbers, addresses, tax file/government ID numbers,
    and any other personal data found on a payslip.
    """

    employer_name: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    pay_date: date | None = None
    gross_pay: Decimal | None = None
    net_pay: Decimal | None = None
    tax_withheld: Decimal | None = None
    superannuation: Decimal | None = None
    deductions: Decimal | None = None
    ordinary_hours: Decimal | None = None
    overtime_hours: Decimal | None = None
    weekend_or_holiday_hours: Decimal | None = None
    hourly_rate: Decimal | None = None
    earnings_breakdown: list[ExtractedEarningLine] = []
