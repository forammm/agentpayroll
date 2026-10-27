from app.services.pdf_validation import open_pdf_document
from app.services.pdf_text_extraction import extract_text_from_document
from tests.pdf_factory import build_scanned_pdf, build_text_payslip_pdf


def test_extracts_embedded_text_without_ocr():
    doc = open_pdf_document(build_text_payslip_pdf())
    try:
        text, used_ocr, warnings = extract_text_from_document(doc, ocr_enabled=True)
    finally:
        doc.close()
    assert "Gross Pay" in text
    assert used_ocr is False
    assert warnings == []


def test_scanned_pdf_without_ocr_available_warns_and_returns_no_text():
    # Tesseract is not installed in this environment, so pytesseract.get_tesseract_version()
    # fails and the OCR fallback correctly reports itself as unavailable rather than crashing.
    doc = open_pdf_document(build_scanned_pdf())
    try:
        text, used_ocr, warnings = extract_text_from_document(doc, ocr_enabled=True)
    finally:
        doc.close()
    assert text == ""
    assert used_ocr is False
    assert any("scanned" in w.lower() or "ocr" in w.lower() for w in warnings)


def test_scanned_pdf_with_ocr_disabled_warns_without_attempting_ocr():
    doc = open_pdf_document(build_scanned_pdf())
    try:
        text, used_ocr, warnings = extract_text_from_document(doc, ocr_enabled=False)
    finally:
        doc.close()
    assert text == ""
    assert used_ocr is False
    assert any("ocr is disabled" in w.lower() for w in warnings)
