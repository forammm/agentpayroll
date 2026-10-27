"""Validation of extracted payslip fields.

This is about data quality, not payroll correctness: it flags missing,
inconsistent, or low-confidence values so a human (or, later, the
verification workflow) knows what to double-check. It never rejects a value
just because it's unusual - only genuinely invalid combinations become
errors; everything else is a warning.
"""

from decimal import Decimal

from app.schemas.payslip_extraction import PayslipExtractedFields, PayslipStatus

# Allowance for rounding/components the parser didn't capture (e.g. small
# allowances) when reconciling gross - tax - deductions against net pay.
_RECONCILIATION_TOLERANCE = Decimal("2.00")


def validate_extracted_fields(fields: PayslipExtractedFields, used_ocr: bool) -> tuple[list[str], list[str], PayslipStatus]:
    """Returns (warnings, errors, status) for a set of extracted fields."""
    warnings: list[str] = []
    errors: list[str] = []

    if fields.gross_pay is None and fields.net_pay is None:
        errors.append("Neither gross pay nor net pay could be found on this payslip.")
    else:
        if fields.gross_pay is None:
            warnings.append("Gross pay could not be found.")
        if fields.net_pay is None:
            warnings.append("Net pay could not be found.")

    if fields.gross_pay is not None and fields.gross_pay < 0:
        errors.append("Gross pay cannot be negative.")
    if fields.net_pay is not None and fields.net_pay < 0:
        errors.append("Net pay cannot be negative.")

    if (
        fields.gross_pay is not None
        and fields.net_pay is not None
        and fields.net_pay > fields.gross_pay + _RECONCILIATION_TOLERANCE
    ):
        warnings.append("Net pay is greater than gross pay, which is unusual.")

    if fields.period_start and fields.period_end and fields.period_start > fields.period_end:
        errors.append("The pay period end date is before the start date.")
    elif fields.period_start is None and fields.period_end is None:
        warnings.append("Pay period dates could not be determined.")

    for label, value in (
        ("ordinary hours", fields.ordinary_hours),
        ("overtime hours", fields.overtime_hours),
        ("weekend or public holiday hours", fields.weekend_or_holiday_hours),
    ):
        if value is not None and value < 0:
            errors.append(f"{label.capitalize()} cannot be negative.")

    if fields.gross_pay is not None and fields.net_pay is not None:
        known_deductions = (fields.tax_withheld or Decimal("0")) + (fields.deductions or Decimal("0"))
        expected_net = fields.gross_pay - known_deductions
        if abs(expected_net - fields.net_pay) > _RECONCILIATION_TOLERANCE:
            warnings.append(
                "Net pay does not reconcile with gross pay minus tax and deductions; "
                "some components may not have been captured."
            )

    if used_ocr:
        warnings.append(
            "These values were extracted using OCR from a scanned document and may be less accurate. "
            "Please verify them."
        )

    status: PayslipStatus = "NEEDS_REVIEW" if (errors or warnings or used_ocr) else "EXTRACTED"
    return warnings, errors, status
