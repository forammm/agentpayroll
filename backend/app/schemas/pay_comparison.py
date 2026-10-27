from decimal import Decimal

from pydantic import BaseModel


class PayComparison(BaseModel):
    """Expected (calculated) vs actual (extracted from payslip) pay, compared
    like-for-like - gross against gross, net against net, never mixed."""

    expected_gross_pay: Decimal
    actual_gross_pay: Decimal | None
    expected_net_pay: Decimal | None
    actual_net_pay: Decimal | None
    gross_difference: Decimal | None
    net_difference: Decimal | None
    tolerance: Decimal
    discrepancies: list[str] = []
