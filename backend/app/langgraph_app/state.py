from typing import TypedDict


class PayrollVerificationState(TypedDict, total=False):
    user_id: str
    payslip_id: str
    status: str
    errors: list[str]
