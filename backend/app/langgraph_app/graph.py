"""LangGraph payroll verification workflow.

build_graph wires the 9 nodes together with conditional routing: any hard
error from validate_payslip / load_timesheet / load_payroll_rules /
calculate_expected_pay short-circuits straight to classify_result (which
forces NEEDS_REVIEW), skipping every later loading/calculation step. Only a
fully evidenced run reaches compare_pay. generate_explanation and save_result
always run, even on the NEEDS_REVIEW path, so every run - reviewable or not -
ends up explained and persisted.

run_verification is the entrypoint the API layer calls: it fetches and
authorizes the payslip (the one DB access that happens outside the graph,
since Node 1 only validates data it's already been handed), builds the
initial state, and invokes the compiled graph.
"""

from uuid import UUID

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.langgraph_app.errors import AccessDeniedError, PayslipNotFoundError
from app.langgraph_app.nodes import (
    calculate_expected_pay_node,
    classify_result_node,
    compare_pay_node,
    generate_explanation_node,
    load_payroll_rules_node,
    load_timesheet_node,
    minimize_pii_node,
    save_result_node,
    validate_payslip_node,
)
from app.langgraph_app.state import PayrollVerificationState
from app.langgraph_app.tools.llm_client import ExplanationClient
from app.models.payslip import Payslip
from app.services.payslip_service import payslip_to_extracted_fields
from app.services.verification_service import get_verification_result  # noqa: F401 - re-exported for convenience


def _route_on(error_key: str):
    def _check(state: PayrollVerificationState) -> str:
        return "review" if state.get(error_key) else "continue"

    return _check


def build_graph(db: Session, llm_client: ExplanationClient | None = None):
    graph = StateGraph(PayrollVerificationState)

    graph.add_node("validate_payslip", validate_payslip_node)
    graph.add_node("minimize_pii", minimize_pii_node)
    graph.add_node("load_timesheet", load_timesheet_node(db))
    graph.add_node("load_payroll_rules", load_payroll_rules_node(db))
    graph.add_node("calculate_expected_pay", calculate_expected_pay_node)
    graph.add_node("compare_pay", compare_pay_node)
    graph.add_node("classify_result", classify_result_node)
    graph.add_node("generate_explanation", generate_explanation_node(llm_client))
    graph.add_node("save_result", save_result_node(db))

    graph.set_entry_point("validate_payslip")
    graph.add_conditional_edges("validate_payslip", _route_on("field_errors"), {"review": "classify_result", "continue": "minimize_pii"})
    graph.add_edge("minimize_pii", "load_timesheet")
    graph.add_conditional_edges("load_timesheet", _route_on("timesheet_errors"), {"review": "classify_result", "continue": "load_payroll_rules"})
    graph.add_conditional_edges("load_payroll_rules", _route_on("rule_errors"), {"review": "classify_result", "continue": "calculate_expected_pay"})
    graph.add_conditional_edges("calculate_expected_pay", _route_on("calculation_errors"), {"review": "classify_result", "continue": "compare_pay"})
    graph.add_edge("compare_pay", "classify_result")
    graph.add_edge("classify_result", "generate_explanation")
    graph.add_edge("generate_explanation", "save_result")
    graph.add_edge("save_result", END)

    return graph.compile()


def run_verification(
    db: Session,
    user_id: UUID,
    payslip_id: UUID,
    llm_client: ExplanationClient | None = None,
) -> PayrollVerificationState:
    payslip = db.get(Payslip, payslip_id)
    if payslip is None:
        raise PayslipNotFoundError(payslip_id)
    if payslip.user_id != user_id:
        raise AccessDeniedError(payslip_id)

    initial_state: PayrollVerificationState = {
        "user_id": user_id,
        "payslip_id": payslip_id,
        "payslip": payslip,
        "extracted_fields": payslip_to_extracted_fields(payslip),
    }

    compiled = build_graph(db, llm_client)
    return compiled.invoke(initial_state)
