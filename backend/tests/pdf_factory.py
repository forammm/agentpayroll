"""Builds small synthetic PDFs in memory for tests. No real payslips are used
or stored anywhere in this repo - every value here is fabricated."""

import io

import pymupdf
from PIL import Image, ImageDraw


def build_text_payslip_pdf(
    employer: str = "Acme Pty Ltd",
    period_start: str = "01/06/2026",
    period_end: str = "14/06/2026",
    pay_date: str = "18/06/2026",
    gross_pay: str = "1,842.50",
    net_pay: str = "1,452.00",
    tax: str = "348.00",
    superannuation: str = "193.46",
    deductions: str = "42.50",
    ordinary_hours: str = "70.0",
    overtime_hours: str = "6.5",
    weekend_hours: str = "11.5",
    hourly_rate: str = "26.50",
) -> bytes:
    """A straightforward label: value payslip layout with an embedded text layer."""
    lines = [
        f"Employer: {employer}",
        f"Pay Period: {period_start} to {period_end}",
        f"Pay Date: {pay_date}",
        "",
        "Earnings",
        f"Ordinary hours      {ordinary_hours}   {hourly_rate}   {gross_pay}",
        "",
        f"Gross Pay: ${gross_pay}",
        f"Tax Withheld: ${tax}",
        f"Superannuation: ${superannuation}",
        f"Deductions: ${deductions}",
        f"Net Pay: ${net_pay}",
        f"Ordinary Hours: {ordinary_hours}",
        f"Overtime Hours: {overtime_hours}",
        f"Weekend Hours: {weekend_hours}",
    ]
    return _render_text_pdf(lines)


def build_alternate_layout_payslip_pdf() -> bytes:
    """A different employer's wording for the same fields, to exercise the
    parser's label variants rather than one fixed layout."""
    lines = [
        "Company: Beacon Logistics",
        "Period Start: 2026-06-01",
        "Period End: 2026-06-14",
        "Net Amount: $1,500.00",
        "Gross Earnings: $1,900.00",
        "PAYG Tax: $380.00",
        "Total Deductions: $20.00",
        "Normal Hours: 76",
        "Overtime Hours: 2",
    ]
    return _render_text_pdf(lines)


def build_multi_column_payslip_pdf() -> bytes:
    """A 'This Pay' / 'Year To Date' two-column layout where the row label is a
    bare word ("Gross", not "Gross Pay") with the current-period amount directly
    below it, followed by the YTD figure - a real-world payroll system format
    that previously made gross_pay extraction fail (the parser required the
    word "Pay"/"Earnings"/"Income" to directly follow "Gross")."""
    lines = [
        "Pay Period: 01/06/2026 to 14/06/2026",
        "This Pay",
        "Year To Date",
        "Gross",
        "3,092.62",
        "15,491.95",
        "Tax",
        "626.00",
        "2,152.00",
        "Net Pay",
        "2,466.62",
        "13,339.95",
    ]
    return _render_text_pdf(lines)


def build_minimal_payslip_pdf(gross_pay: str = "1000.00", net_pay: str = "800.00") -> bytes:
    return _render_text_pdf([f"Gross Pay: ${gross_pay}", f"Net Pay: ${net_pay}"])


def build_payslip_with_only_gross_pdf(gross_pay: str = "1000.00") -> bytes:
    return _render_text_pdf([f"Gross Pay: ${gross_pay}", "Pay Period: 01/06/2026 to 14/06/2026"])


def build_inconsistent_totals_pdf() -> bytes:
    """Net pay far exceeds gross pay - should trigger a validation warning."""
    return _render_text_pdf(["Gross Pay: $500.00", "Net Pay: $5,000.00"])


def build_no_payroll_fields_pdf() -> bytes:
    """Has a real text layer but nothing resembling payroll data."""
    return _render_text_pdf(["This is just a cover letter.", "Thank you for your time."])


def build_scanned_pdf(text: str = "Gross Pay: $1,000.00\nNet Pay: $800.00") -> bytes:
    """A PDF with no embedded text layer - an image of text instead, to
    exercise the scanned/OCR-fallback code path."""
    image = Image.new("RGB", (800, 400), color="white")
    draw = ImageDraw.Draw(image)
    draw.multiline_text((20, 20), text, fill="black")
    image_buf = io.BytesIO()
    image.save(image_buf, format="PNG")

    doc = pymupdf.open()
    page = doc.new_page(width=800, height=400)
    page.insert_image(pymupdf.Rect(0, 0, 800, 400), stream=image_buf.getvalue())
    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()


def build_blank_scanned_pdf() -> bytes:
    """An image-only PDF with no text at all in the image - OCR (if available)
    should find nothing, exercising the FAILED path."""
    image = Image.new("RGB", (400, 200), color="white")
    image_buf = io.BytesIO()
    image.save(image_buf, format="PNG")
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=200)
    page.insert_image(pymupdf.Rect(0, 0, 400, 200), stream=image_buf.getvalue())
    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()


def build_empty_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page()
    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()


def build_encrypted_pdf(password: str = "secret") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Gross Pay: $1,000.00")
    out = io.BytesIO()
    doc.save(out, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=f"{password}-owner")
    doc.close()
    return out.getvalue()


def build_corrupted_pdf() -> bytes:
    return b"%PDF-1.7\n" + bytes([0, 1, 2, 3] * 50)


def build_not_a_pdf() -> bytes:
    return b"This is just a plain text file pretending to be a payslip."


def _render_text_pdf(lines: list[str]) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=11)
        y += 18
    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()
