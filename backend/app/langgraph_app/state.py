"""Typed state for the payroll verification graph (app.langgraph_app.graph).

Each pipeline stage writes to its OWN error/warning key (field_errors,
timesheet_errors, rule_errors, calculation_errors, ...) rather than a single
shared list. LangGraph's default state reducer overwrites a key when a node
returns it, so two different nodes both writing "errors" would silently drop
whichever ran first - separate keys per stage sidesteps that entirely, and
classify_result combines them when it runs.
"""

from typing import TypedDict
from uuid import UUID

from app.models.payroll_rule import PayrollRule
from app.models.payslip import Payslip
from app.models.timesheet import Timesheet
from app.schemas.pay_comparison import PayComparison
from app.schemas.payroll_summary import PayrollSummary
from app.schemas.payslip_extraction import PayslipExtractedFields
from app.schemas.verification import VerificationExplanation, VerificationStatus


class PayrollVerificationState(TypedDict, total=False):
    # Input (set by app.langgraph_app.graph.run_verification before the graph starts)
    user_id: UUID
    payslip_id: UUID
    payslip: Payslip
    extracted_fields: PayslipExtractedFields

    stage: str  # last node executed - for logging/debugging only

    # Node 1: validate_payslip
    field_errors: list[str]
    field_warnings: list[str]

    # Node 2: minimize_pii
    minimized_fields: dict

    # Node 3: load_timesheet
    timesheets: list[Timesheet]
    timesheet_errors: list[str]
    timesheet_warnings: list[str]

    # Node 4: load_payroll_rules
    payroll_rule: PayrollRule
    rule_errors: list[str]

    # Node 5: calculate_expected_pay
    payroll_summary: PayrollSummary
    calculation_errors: list[str]

    # Node 6: compare_pay
    comparison: PayComparison

    # Node 7: classify_result
    classification: VerificationStatus
    blocking_errors: list[str]

    # Node 8: generate_explanation
    explanation: VerificationExplanation
    explanation_warnings: list[str]
    used_llm: bool

    # Node 9: save_result
    verification_result_id: UUID
