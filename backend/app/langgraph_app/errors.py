"""Precondition errors raised before the graph runs (app.langgraph_app.graph.run_verification).

Kept distinct from the graph's own node-level error accumulation (which routes
to NEEDS_REVIEW rather than raising) because these two are genuine request
errors the API layer must map to specific HTTP status codes - a missing or
cross-user payslip is a 404/403, not a verification outcome.
"""

from uuid import UUID


class PayslipNotFoundError(Exception):
    def __init__(self, payslip_id: UUID):
        super().__init__(f"Payslip {payslip_id} not found.")
        self.payslip_id = payslip_id


class AccessDeniedError(Exception):
    """Raised when the given user_id does not own the given payslip_id."""

    def __init__(self, payslip_id: UUID):
        super().__init__("You do not have access to this payslip.")
        self.payslip_id = payslip_id


class VerificationNotFoundError(Exception):
    def __init__(self, payslip_id: UUID):
        super().__init__(f"No saved verification result for payslip {payslip_id}.")
        self.payslip_id = payslip_id
