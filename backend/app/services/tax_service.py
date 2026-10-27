from decimal import Decimal, ROUND_HALF_UP


TAX_QUANTUM = Decimal("0.01")


def estimate_tax(gross_pay: Decimal) -> Decimal:
    """Return a deterministic placeholder tax estimate.

    This is intentionally simple until real Australian tax tables are introduced.
    Keeping it isolated makes the tax implementation replaceable without changing
    payroll calculation orchestration.
    """
    if gross_pay <= 0:
        return Decimal("0.00")
    return (gross_pay * Decimal("0.20")).quantize(TAX_QUANTUM, rounding=ROUND_HALF_UP)
