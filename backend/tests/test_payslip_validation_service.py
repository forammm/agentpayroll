from datetime import date
from decimal import Decimal

from app.schemas.payslip_extraction import PayslipExtractedFields
from app.services.payslip_validation_service import validate_extracted_fields


def test_complete_consistent_fields_yield_extracted_status_with_no_issues():
    fields = PayslipExtractedFields(
        gross_pay=Decimal("1000.00"),
        net_pay=Decimal("800.00"),
        tax_withheld=Decimal("180.00"),
        deductions=Decimal("20.00"),
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 14),
    )
    warnings, errors, status = validate_extracted_fields(fields, used_ocr=False)
    assert warnings == []
    assert errors == []
    assert status == "EXTRACTED"


def test_missing_gross_and_net_pay_is_an_error_and_needs_review():
    fields = PayslipExtractedFields()
    warnings, errors, status = validate_extracted_fields(fields, used_ocr=False)
    assert any("gross pay" in e.lower() and "net pay" in e.lower() for e in errors)
    assert status == "NEEDS_REVIEW"


def test_missing_net_pay_only_is_a_warning_not_an_error():
    fields = PayslipExtractedFields(gross_pay=Decimal("1000.00"))
    warnings, errors, status = validate_extracted_fields(fields, used_ocr=False)
    assert errors == []
    assert any("net pay" in w.lower() for w in warnings)
    assert status == "NEEDS_REVIEW"


def test_negative_gross_pay_is_an_error():
    fields = PayslipExtractedFields(gross_pay=Decimal("-100.00"), net_pay=Decimal("80.00"))
    _, errors, status = validate_extracted_fields(fields, used_ocr=False)
    assert any("gross pay cannot be negative" in e.lower() for e in errors)
    assert status == "NEEDS_REVIEW"


def test_net_pay_exceeding_gross_pay_is_a_warning():
    fields = PayslipExtractedFields(gross_pay=Decimal("500.00"), net_pay=Decimal("5000.00"))
    warnings, errors, status = validate_extracted_fields(fields, used_ocr=False)
    assert any("net pay is greater than gross pay" in w.lower() for w in warnings)


def test_period_end_before_start_is_an_error():
    fields = PayslipExtractedFields(
        gross_pay=Decimal("1000.00"), net_pay=Decimal("800.00"),
        period_start=date(2026, 6, 14), period_end=date(2026, 6, 1),
    )
    _, errors, _ = validate_extracted_fields(fields, used_ocr=False)
    assert any("end date is before the start date" in e.lower() for e in errors)


def test_negative_hours_is_an_error():
    fields = PayslipExtractedFields(gross_pay=Decimal("1000.00"), net_pay=Decimal("800.00"), ordinary_hours=Decimal("-5"))
    _, errors, _ = validate_extracted_fields(fields, used_ocr=False)
    assert any("ordinary hours cannot be negative" in e.lower() for e in errors)


def test_ocr_extraction_always_needs_review():
    fields = PayslipExtractedFields(gross_pay=Decimal("1000.00"), net_pay=Decimal("800.00"))
    warnings, errors, status = validate_extracted_fields(fields, used_ocr=True)
    assert errors == []
    assert any("ocr" in w.lower() for w in warnings)
    assert status == "NEEDS_REVIEW"


def test_unreconciled_totals_produce_a_warning():
    fields = PayslipExtractedFields(
        gross_pay=Decimal("1000.00"), net_pay=Decimal("500.00"),
        tax_withheld=Decimal("100.00"), deductions=Decimal("0.00"),
    )
    warnings, _, _ = validate_extracted_fields(fields, used_ocr=False)
    assert any("does not reconcile" in w.lower() for w in warnings)
