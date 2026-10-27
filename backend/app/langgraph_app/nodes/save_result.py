"""Node 9: persist the verification result via the existing verification service."""

from sqlalchemy.orm import Session

from app.langgraph_app.state import PayrollVerificationState
from app.services.verification_service import persist_verification_result


def save_result_node(db: Session):
    def _node(state: PayrollVerificationState) -> dict:
        result = persist_verification_result(db, state)
        return {"verification_result_id": result.id, "stage": "save_result"}

    return _node
