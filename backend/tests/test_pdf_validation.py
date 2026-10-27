import pytest

from app.services.pdf_validation import EncryptedPdfError, InvalidPdfError, file_hash, looks_like_pdf, open_pdf_document
from tests.pdf_factory import build_corrupted_pdf, build_encrypted_pdf, build_minimal_payslip_pdf, build_not_a_pdf, build_text_payslip_pdf


def test_looks_like_pdf_true_for_pdf_magic_bytes():
    assert looks_like_pdf(build_text_payslip_pdf())


def test_looks_like_pdf_false_for_non_pdf_content():
    assert not looks_like_pdf(build_not_a_pdf())


def test_open_pdf_document_succeeds_for_valid_pdf():
    doc = open_pdf_document(build_text_payslip_pdf())
    try:
        assert doc.page_count == 1
    finally:
        doc.close()


def test_open_pdf_document_rejects_corrupted_pdf():
    with pytest.raises(InvalidPdfError):
        open_pdf_document(build_corrupted_pdf())


def test_open_pdf_document_rejects_encrypted_pdf():
    with pytest.raises(EncryptedPdfError):
        open_pdf_document(build_encrypted_pdf())


def test_file_hash_is_stable_for_same_content():
    data = build_text_payslip_pdf()
    assert file_hash(data) == file_hash(data)


def test_file_hash_differs_for_different_content():
    assert file_hash(build_text_payslip_pdf()) != file_hash(build_minimal_payslip_pdf())
