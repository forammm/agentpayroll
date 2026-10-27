"""Raw text extraction from an already-opened PDF document.

Text-based PDFs are read directly via PyMuPDF. Scanned/image-based PDFs fall
back to OCR (pytesseract) only when the Tesseract binary is actually
available on the host - if it isn't, extraction degrades to a clear warning
instead of failing or inventing data.

Never log the extracted text itself: payslip content is sensitive, and only
metadata (status, warning counts) belongs in logs.
"""

import io
import logging

import pymupdf

logger = logging.getLogger(__name__)

# Below this many non-whitespace characters, treat the page(s) as having no
# usable embedded text layer and fall back to OCR.
MIN_CHARS_FOR_TEXT_LAYER = 20


def extract_text_from_document(doc: pymupdf.Document, ocr_enabled: bool) -> tuple[str, bool, list[str]]:
    """Returns (extracted_text, used_ocr, warnings)."""
    warnings: list[str] = []
    combined = "\n".join(page.get_text("text") for page in doc)

    if len(combined.strip()) >= MIN_CHARS_FOR_TEXT_LAYER:
        return combined, False, warnings

    if not ocr_enabled:
        warnings.append("This appears to be a scanned or image-based PDF and OCR is disabled.")
        return "", False, warnings

    ocr_text, ocr_available = _extract_text_via_ocr(doc)
    if not ocr_available:
        warnings.append(
            "This appears to be a scanned or image-based PDF and OCR is not available in this environment."
        )
        return "", False, warnings

    if len(ocr_text.strip()) < MIN_CHARS_FOR_TEXT_LAYER:
        warnings.append("OCR did not detect readable text on this scanned PDF.")
        return ocr_text, True, warnings

    return ocr_text, True, warnings


def _extract_text_via_ocr(doc: pymupdf.Document) -> tuple[str, bool]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.info("OCR skipped: pytesseract/Pillow not installed")
        return "", False

    try:
        pytesseract.get_tesseract_version()
    except Exception:
        logger.info("OCR skipped: pytesseract installed but no Tesseract binary found on PATH")
        return "", False

    parts: list[str] = []
    for page_number, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            parts.append(pytesseract.image_to_string(image))
        except Exception:
            logger.warning("OCR failed on page %d", page_number)
    return "\n".join(parts), True
