"""Node 6: compare calculated expected pay against the payslip's actual pay.

Gross is compared only with gross, net only with net - never mixed. Each side
is computed independently from its own top-line total (the calculator's gross/
net vs. the payslip's extracted gross/net), so there is no double-counting of
deductions, penalties, or loadings between the two.
"""

from decimal import Decimal

from app.config import settings
from app.langgraph_app.state import PayrollVerificationState
from app.schemas.pay_comparison import PayComparison


def compare_pay_node(state: PayrollVerificationState) -> dict:
    summary = state["payroll_summary"]
    fields = state["extracted_fields"]
    tolerance = Decimal(settings.verification_tolerance)

    expected_gross = summary.gross_pay
    actual_gross = fields.gross_pay
    expected_net = summary.net_pay
    actual_net = fields.net_pay

    gross_difference = (actual_gross - expected_gross) if actual_gross is not None else None
    net_difference = (actual_net - expected_net) if actual_net is not None else None

    discrepancies: list[str] = []
    if actual_gross is None:
        discrepancies.append("Actual gross pay was not found on the payslip, so gross pay could not be compared.")
    if actual_net is None:
        discrepancies.append("Actual net pay was not found on the payslip, so net pay could not be compared.")

    comparison = PayComparison(
        expected_gross_pay=expected_gross,
        actual_gross_pay=actual_gross,
        expected_net_pay=expected_net,
        actual_net_pay=actual_net,
        gross_difference=gross_difference,
        net_difference=net_difference,
        tolerance=tolerance,
        discrepancies=discrepancies,
    )
    return {"comparison": comparison, "stage": "compare_pay"}
