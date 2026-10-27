"""Payslip upload orchestration.

Responsible for: validating the upload, persisting the file privately,
calling the PDF extraction pipeline, validating the result, and persisting
the Payslip row. Deliberately does not calculate payroll or decide
under/overpayment - that is the deterministic payroll calculator and
verification service's job (see app.services.payroll_calculator).

Architecture: api/payslips.py (HTTP) -> this module (orchestration) ->
pdf_validation / pdf_text_extraction (PDF handling) -> payslip_field_parser
(structured extraction) -> payslip_validation_service (data-quality checks)
-> SQLAlchemy persistence.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status as http_status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.payslip import Payslip
from app.models.user import User
from app.schemas.payslip import PayslipResponse
from app.schemas.payslip_extraction import ExtractedEarningLine, PayslipExtractedFields
from app.services import payslip_storage
from app.services.payslip_field_parser import parse_fields
from app.services.payslip_validation_service import validate_extracted_fields
from app.services.pdf_text_extraction import extract_text_from_document
from app.services.pdf_validation import EncryptedPdfError, InvalidPdfError, file_hash, looks_like_pdf, open_pdf_document

logger = logging.getLogger(__name__)

_ALLOWED_CONTENT_TYPES = {"application/pdf"}


async def upload_payslip(db: Session, user_id: UUID, file: UploadFile) -> PayslipResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="User not found.")

    _validate_declared_type(file)
    data = await _read_with_limit(file, settings.max_upload_size_mb * 1024 * 1024)

    if not looks_like_pdf(data):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a valid PDF.")

    try:
        doc = open_pdf_document(data)
    except EncryptedPdfError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except InvalidPdfError as exc:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    digest = file_hash(data)
    duplicate = (
        db.query(Payslip)
        .filter(Payslip.user_id == user_id, Payslip.file_hash == digest)
        .order_by(Payslip.created_at.desc())
        .first()
    )

    try:
        text, used_ocr, extraction_warnings = extract_text_from_document(doc, settings.ocr_enabled)
    finally:
        doc.close()

    payslip_id = uuid4()
    display_name = _safe_display_name(file.filename)
    warnings = list(extraction_warnings)
    if duplicate is not None:
        warnings.append(
            f"This file appears identical to a payslip you already uploaded on "
            f"{duplicate.created_at.date().isoformat()}."
        )

    if not text.strip():
        file_path = payslip_storage.save_payslip_file(user_id, payslip_id, data)
        payslip = Payslip(
            id=payslip_id,
            user_id=user_id,
            file_name=display_name,
            file_path=file_path,
            file_hash=digest,
            status="FAILED",
            used_ocr=used_ocr,
            extraction_warnings=warnings or None,
            extraction_errors=["No readable text could be extracted from this PDF."],
            extracted_at=datetime.now(timezone.utc),
        )
        db.add(payslip)
        db.commit()
        db.refresh(payslip)
        logger.info("payslip %s: extraction failed, no text available", payslip_id)
        return PayslipResponse.model_validate(payslip)

    fields = parse_fields(text)
    field_warnings, field_errors, derived_status = validate_extracted_fields(fields, used_ocr)
    warnings.extend(field_warnings)

    file_path = payslip_storage.save_payslip_file(user_id, payslip_id, data)
    payslip = Payslip(
        id=payslip_id,
        user_id=user_id,
        file_name=display_name,
        file_path=file_path,
        file_hash=digest,
        status=derived_status,
        used_ocr=used_ocr,
        employer_name=fields.employer_name,
        period_start=fields.period_start,
        period_end=fields.period_end,
        pay_date=fields.pay_date,
        gross_pay=fields.gross_pay,
        net_pay=fields.net_pay,
        tax_deducted=fields.tax_withheld,
        superannuation=fields.superannuation,
        deductions=fields.deductions,
        ordinary_hours=fields.ordinary_hours,
        overtime_hours=fields.overtime_hours,
        weekend_or_holiday_hours=fields.weekend_or_holiday_hours,
        hourly_rate=fields.hourly_rate,
        earnings_breakdown=[line.model_dump(mode="json") for line in fields.earnings_breakdown] or None,
        extraction_warnings=warnings or None,
        extraction_errors=field_errors or None,
        extracted_at=datetime.now(timezone.utc),
    )
    db.add(payslip)
    db.commit()
    db.refresh(payslip)
    logger.info("payslip %s: processed status=%s used_ocr=%s", payslip_id, derived_status, used_ocr)
    return PayslipResponse.model_validate(payslip)


def get_payslip(db: Session, payslip_id: UUID) -> PayslipResponse:
    payslip = db.get(Payslip, payslip_id)
    if payslip is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Payslip not found.")
    return PayslipResponse.model_validate(payslip)


def payslip_to_extracted_fields(payslip: Payslip) -> PayslipExtractedFields:
    """Rebuild the structured extraction schema from a stored Payslip row.

    Used by the LangGraph verification workflow (app.langgraph_app) so it consumes
    the same shape payslip_service produces, rather than re-deriving it from the
    Payslip model's column names.
    """
    earnings = [ExtractedEarningLine(**line) for line in (payslip.earnings_breakdown or [])]
    return PayslipExtractedFields(
        employer_name=payslip.employer_name,
        period_start=payslip.period_start,
        period_end=payslip.period_end,
        pay_date=payslip.pay_date,
        gross_pay=payslip.gross_pay,
        net_pay=payslip.net_pay,
        tax_withheld=payslip.tax_deducted,
        superannuation=payslip.superannuation,
        deductions=payslip.deductions,
        ordinary_hours=payslip.ordinary_hours,
        overtime_hours=payslip.overtime_hours,
        weekend_or_holiday_hours=payslip.weekend_or_holiday_hours,
        hourly_rate=payslip.hourly_rate,
        earnings_breakdown=earnings,
    )


def _validate_declared_type(file: UploadFile) -> None:
    declared_pdf = file.content_type in _ALLOWED_CONTENT_TYPES
    name_looks_pdf = (file.filename or "").lower().endswith(".pdf")
    if not declared_pdf and not name_looks_pdf:
        raise HTTPException(status_code=http_status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF files are accepted.")


async def _read_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds the maximum allowed size of {max_bytes // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _safe_display_name(filename: str | None) -> str:
    name = (filename or "payslip.pdf").strip().replace("\\", "/").split("/")[-1]
    return name[:255] if name else "payslip.pdf"
