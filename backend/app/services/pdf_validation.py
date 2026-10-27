"""Low-level PDF validation: is this actually a PDF, and can we open it.

Deliberately has no knowledge of payroll fields - that belongs to
app.services.payslip_field_parser. This module answers one question: is the
byte stream a readable, non-encrypted PDF we can hand to extraction.
"""

import hashlib

import pymupdf

PDF_MAGIC = b"%PDF-"


class InvalidPdfError(Exception):
    """The file is not a readable PDF (wrong format, truncated, corrupted)."""


class EncryptedPdfError(Exception):
    """The PDF is password-protected and could not be opened with an empty password."""


def looks_like_pdf(data: bytes) -> bool:
    return data[:5] == PDF_MAGIC


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def open_pdf_document(data: bytes) -> pymupdf.Document:
    """Open and sanity-check a PDF byte stream.

    Raises InvalidPdfError for corrupted/unreadable/empty files and
    EncryptedPdfError for password-protected files we cannot open.
    """
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise InvalidPdfError("The file could not be read as a PDF. It may be corrupted.") from exc

    if doc.is_encrypted:
        if not doc.authenticate(""):
            doc.close()
            raise EncryptedPdfError(
                "This PDF is password-protected and cannot be processed. Please upload an unprotected copy."
            )

    if doc.page_count == 0:
        doc.close()
        raise InvalidPdfError("The PDF does not contain any pages.")

    return doc
