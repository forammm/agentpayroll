"""Node 4: load the employee's payroll rules.

Reuses app.services.payroll_rule_service.get_latest_rule and the calculator's
own app.services.validation_service.validate_required_rates - never invents a
rate or employment condition that isn't on file.
"""

from sqlalchemy.orm import Session

from app.langgraph_app.state import PayrollVerificationState
from app.services.payroll_calculator import REQUIRED_RATE_NAMES
from app.services.payroll_rule_service import get_latest_rule
from app.services.validation_service import PayrollValidationError, validate_required_rates


def load_payroll_rules_node(db: Session):
    def _node(state: PayrollVerificationState) -> dict:
        rule = get_latest_rule(db, state["user_id"])
        if rule is None:
            return {
                "payroll_rule": None,
                "rule_errors": ["No payroll rules are configured for this employee."],
                "stage": "load_payroll_rules",
            }

        errors: list[str] = []
        try:
            validate_required_rates(rule, REQUIRED_RATE_NAMES)
        except PayrollValidationError as exc:
            errors.append(str(exc))

        return {"payroll_rule": rule, "rule_errors": errors, "stage": "load_payroll_rules"}

    return _node
