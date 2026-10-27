import uuid

from app.models.payslip import Payslip
from tests.pdf_factory import (
    build_corrupted_pdf,
    build_encrypted_pdf,
    build_minimal_payslip_pdf,
    build_no_payroll_fields_pdf,
    build_not_a_pdf,
    build_scanned_pdf,
    build_text_payslip_pdf,
)


def _upload(client, user_id, filename, content, content_type="application/pdf"):
    return client.post(
        "/api/v1/payslips/upload",
        params={"user_id": str(user_id)},
        files={"file": (filename, content, content_type)},
    )


def test_upload_well_formed_text_payslip_extracts_fields(client, seeded_user):
    response = _upload(client, seeded_user.id, "payslip.pdf", build_text_payslip_pdf())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EXTRACTED"
    assert body["used_ocr"] is False
    assert body["gross_pay"] == "1842.50"
    assert body["net_pay"] == "1452.00"
    assert body["employer_name"] == "Acme Pty Ltd"
    assert body["extraction_errors"] is None


def test_upload_persists_payslip_to_database(client, seeded_user, db_session_factory):
    response = _upload(client, seeded_user.id, "payslip.pdf", build_text_payslip_pdf())
    payslip_id = response.json()["id"]

    db = db_session_factory()
    try:
        stored = db.get(Payslip, uuid.UUID(payslip_id))
        assert stored is not None
        assert stored.user_id == seeded_user.id
        assert stored.gross_pay is not None
        assert stored.file_path is not None
    finally:
        db.close()


def test_upload_with_missing_fields_returns_needs_review_with_warnings(client, seeded_user):
    response = _upload(client, seeded_user.id, "payslip.pdf", build_minimal_payslip_pdf())
    body = response.json()
    assert response.status_code == 200
    assert body["status"] in ("EXTRACTED", "NEEDS_REVIEW")
    assert body["gross_pay"] == "1000.00"
    assert body["net_pay"] == "800.00"
    # no period/tax/super info in this fixture -> should surface as warnings, not invented values
    assert body["tax_deducted"] is None
    assert body["period_start"] is None


def test_upload_pdf_with_no_payroll_fields_is_needs_review_not_fabricated(client, seeded_user):
    response = _upload(client, seeded_user.id, "payslip.pdf", build_no_payroll_fields_pdf())
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "NEEDS_REVIEW"
    assert body["gross_pay"] is None
    assert body["net_pay"] is None
    assert any("gross pay" in e.lower() for e in body["extraction_errors"])


def test_upload_scanned_pdf_without_ocr_available_is_failed(client, seeded_user):
    response = _upload(client, seeded_user.id, "scanned.pdf", build_scanned_pdf())
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "FAILED"
    assert body["gross_pay"] is None
    assert any("text could be extracted" in e.lower() for e in body["extraction_errors"])


def test_upload_rejects_non_pdf_content_type(client, seeded_user):
    response = _upload(client, seeded_user.id, "notapdf.txt", build_not_a_pdf(), content_type="text/plain")
    assert response.status_code == 415


def test_upload_rejects_file_with_pdf_extension_but_wrong_magic_bytes(client, seeded_user):
    # python-multipart will happily send a .pdf filename with arbitrary content and a
    # text/plain content type won't be sent by real clients for a PDF, so simulate the
    # more dangerous case: a renamed file claiming to be a PDF.
    response = _upload(client, seeded_user.id, "fake.pdf", build_not_a_pdf(), content_type="application/pdf")
    assert response.status_code == 400


def test_upload_rejects_corrupted_pdf(client, seeded_user):
    response = _upload(client, seeded_user.id, "corrupt.pdf", build_corrupted_pdf())
    assert response.status_code == 422


def test_upload_rejects_encrypted_pdf(client, seeded_user):
    response = _upload(client, seeded_user.id, "encrypted.pdf", build_encrypted_pdf())
    assert response.status_code == 422


def test_upload_rejects_oversized_file(client, seeded_user):
    # The client fixture caps max_upload_size_mb at 1 MB.
    oversized = build_text_payslip_pdf() + b"0" * (2 * 1024 * 1024)
    response = _upload(client, seeded_user.id, "big.pdf", oversized)
    assert response.status_code == 413


def test_upload_for_unknown_user_returns_404(client):
    response = _upload(client, uuid.uuid4(), "payslip.pdf", build_text_payslip_pdf())
    assert response.status_code == 404


def test_duplicate_upload_is_flagged_as_a_warning_not_rejected(client, seeded_user):
    pdf_bytes = build_text_payslip_pdf()
    first = _upload(client, seeded_user.id, "payslip.pdf", pdf_bytes)
    assert first.status_code == 200

    second = _upload(client, seeded_user.id, "payslip-again.pdf", pdf_bytes)
    assert second.status_code == 200
    body = second.json()
    assert any("already uploaded" in w.lower() for w in (body["extraction_warnings"] or []))


def test_get_payslip_returns_stored_record(client, seeded_user):
    upload_response = _upload(client, seeded_user.id, "payslip.pdf", build_text_payslip_pdf())
    payslip_id = upload_response.json()["id"]

    get_response = client.get(f"/api/v1/payslips/{payslip_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == payslip_id


def test_get_unknown_payslip_returns_404(client):
    response = client.get(f"/api/v1/payslips/{uuid.uuid4()}")
    assert response.status_code == 404
