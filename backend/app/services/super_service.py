from decimal import Decimal, ROUND_HALF_UP


SUPER_QUANTUM = Decimal("0.01")
DEFAULT_SUPER_RATE = Decimal("0.115")


def estimate_super(gross_pay: Decimal, rate: Decimal = DEFAULT_SUPER_RATE) -> Decimal:
    """Return estimated employer superannuation based on gross ordinary earnings."""
    if gross_pay <= 0:
        return Decimal("0.00")
    return (gross_pay * rate).quantize(SUPER_QUANTUM, rounding=ROUND_HALF_UP)
