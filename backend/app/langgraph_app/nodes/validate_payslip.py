"""Node 1: validate the already-extracted payslip data.

Reuses app.services.payslip_validation_service (built in Prompt 4) rather than
re-deriving field-consistency rules - this node's job is only to decide whether
the pipeline has enough reliable evidence to proceed, not to re-validate from
scratch.
"""

from app.langgraph_app.state import PayrollVerificationState
from app.services.payslip_validation_service import validate_extracted_fields


def validate_payslip_node(state: PayrollVerificationState) -> dict:
    payslip = state["payslip"]
    fields = state["extracted_fields"]

    if payslip.status == "FAILED":
        return {
            "field_errors": ["Payslip extraction failed; no reliable data is available for verification."],
            "field_warnings": [],
            "stage": "validate_payslip",
        }

    warnings, errors, _status = validate_extracted_fields(fields, payslip.used_ocr)

    # Carry over anything already flagged at upload time too (e.g. OCR warnings),
    # de-duplicated while preserving order.
    combined_warnings = list(dict.fromkeys((payslip.extraction_warnings or []) + warnings))
    combined_errors = list(dict.fromkeys((payslip.extraction_errors or []) + errors))

    return {
        "field_errors": combined_errors,
        "field_warnings": combined_warnings,
        "stage": "validate_payslip",
    }
