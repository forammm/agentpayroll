"""Node 2: build the minimal payroll-only view that may ever reach the LLM.

Allowlist, not denylist: only fields explicitly copied here can reach
generate_explanation (Node 8). The Payslip model never stores bank details,
government identifiers, or home addresses in the first place (see Prompt 4),
so this node's main job is excluding internal database identifiers (payslip
id, user id, file path/hash) and anything not needed to explain the result -
not redacting sensitive fields that were never persisted.
"""

from app.langgraph_app.state import PayrollVerificationState


def _decimal_str(value) -> str | None:
    return str(value) if value is not None else None


def minimize_pii_node(state: PayrollVerificationState) -> dict:
    fields = state["extracted_fields"]

    minimized = {
        "employer_name": fields.employer_name,
        "pay_period_start": fields.period_start.isoformat() if fields.period_start else None,
        "pay_period_end": fields.period_end.isoformat() if fields.period_end else None,
        "gross_pay": _decimal_str(fields.gross_pay),
        "net_pay": _decimal_str(fields.net_pay),
        "tax_withheld": _decimal_str(fields.tax_withheld),
        "superannuation": _decimal_str(fields.superannuation),
        "deductions": _decimal_str(fields.deductions),
        "ordinary_hours": _decimal_str(fields.ordinary_hours),
        "overtime_hours": _decimal_str(fields.overtime_hours),
        "weekend_or_holiday_hours": _decimal_str(fields.weekend_or_holiday_hours),
    }
    return {"minimized_fields": minimized, "stage": "minimize_pii"}
