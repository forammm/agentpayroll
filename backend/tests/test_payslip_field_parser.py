from datetime import date
from decimal import Decimal

from app.services.payslip_field_parser import parse_date, parse_fields, parse_money
from tests.pdf_factory import (
    build_alternate_layout_payslip_pdf,
    build_multi_column_payslip_pdf,
    build_no_payroll_fields_pdf,
    build_text_payslip_pdf,
)
from app.services.pdf_validation import open_pdf_document
from app.services.pdf_text_extraction import extract_text_from_document


def _text_of(pdf_bytes: bytes) -> str:
    doc = open_pdf_document(pdf_bytes)
    try:
        text, _, _ = extract_text_from_document(doc, ocr_enabled=False)
    finally:
        doc.close()
    return text


def test_parse_money_handles_dollar_sign_and_commas():
    assert parse_money("$1,842.50") == Decimal("1842.50")


def test_parse_money_handles_parentheses_as_negative():
    assert parse_money("(42.50)") == Decimal("-42.50")


def test_parse_money_handles_leading_minus():
    assert parse_money("-42.50") == Decimal("-42.50")


def test_parse_money_returns_none_for_blank_or_garbage():
    assert parse_money("") is None
    assert parse_money(None) is None
    assert parse_money("n/a") is None


def test_parse_date_handles_multiple_formats():
    assert parse_date("01/06/2026") == date(2026, 6, 1)
    assert parse_date("2026-06-01") == date(2026, 6, 1)
    assert parse_date("1 June 2026") == date(2026, 6, 1)
    assert parse_date("June 1, 2026") == date(2026, 6, 1)


def test_parse_date_returns_none_for_unrecognised_format():
    assert parse_date("not a date") is None


def test_parse_fields_extracts_full_text_payslip():
    text = _text_of(build_text_payslip_pdf())
    fields = parse_fields(text)

    assert fields.employer_name == "Acme Pty Ltd"
    assert fields.period_start == date(2026, 6, 1)
    assert fields.period_end == date(2026, 6, 14)
    assert fields.pay_date == date(2026, 6, 18)
    assert fields.gross_pay == Decimal("1842.50")
    assert fields.net_pay == Decimal("1452.00")
    assert fields.tax_withheld == Decimal("348.00")
    assert fields.superannuation == Decimal("193.46")
    assert fields.deductions == Decimal("42.50")
    assert fields.ordinary_hours == Decimal("70.0")
    assert fields.overtime_hours == Decimal("6.5")
    assert fields.weekend_or_holiday_hours == Decimal("11.5")


def test_parse_fields_handles_alternate_employer_wording():
    text = _text_of(build_alternate_layout_payslip_pdf())
    fields = parse_fields(text)

    assert fields.employer_name == "Beacon Logistics"
    assert fields.period_start == date(2026, 6, 1)
    assert fields.period_end == date(2026, 6, 14)
    assert fields.gross_pay == Decimal("1900.00")
    assert fields.net_pay == Decimal("1500.00")
    assert fields.tax_withheld == Decimal("380.00")
    assert fields.deductions == Decimal("20.00")
    assert fields.ordinary_hours == Decimal("76")
    assert fields.overtime_hours == Decimal("2")


def test_parse_fields_handles_bare_column_header_labels():
    """Regression test: a real uploaded payslip used a 'This Pay' / 'Year To
    Date' two-column layout with a bare 'Gross' header (no 'Pay' suffix) and
    the current-period amount directly below it. gross_pay previously came
    back as None here because the parser required 'Pay'/'Earnings'/'Income'
    to immediately follow 'Gross' - fixed in payslip_field_parser.py."""
    text = _text_of(build_multi_column_payslip_pdf())
    fields = parse_fields(text)

    assert fields.gross_pay == Decimal("3092.62")  # the "This Pay" figure, not the "15,491.95" YTD one
    assert fields.net_pay == Decimal("2466.62")
    assert fields.tax_withheld == Decimal("626.00")


def test_parse_fields_leaves_missing_values_as_none_not_zero():
    text = _text_of(build_no_payroll_fields_pdf())
    fields = parse_fields(text)

    assert fields.gross_pay is None
    assert fields.net_pay is None
    assert fields.tax_withheld is None
    assert fields.superannuation is None
    assert fields.deductions is None
    assert fields.ordinary_hours is None
    assert fields.earnings_breakdown == []
