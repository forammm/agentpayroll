import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.langgraph_app.errors import AccessDeniedError, PayslipNotFoundError, VerificationNotFoundError
from app.langgraph_app.graph import run_verification
from app.schemas.verification import VerificationResultResponse, VerificationRunRequest
from app.services.verification_service import get_verification_result, list_verification_results

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["verification"])


@router.get("", response_model=list[VerificationResultResponse])
def list_verification_history_endpoint(user_id: UUID, db: Session = Depends(get_db)) -> list[VerificationResultResponse]:
    return list_verification_results(db, user_id)


@router.post("/run", response_model=VerificationResultResponse)
def run_verification_endpoint(payload: VerificationRunRequest, db: Session = Depends(get_db)) -> VerificationResultResponse:
    try:
        run_verification(db, payload.user_id, payload.payslip_id)
    except PayslipNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Payslip not found.") from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="You do not have access to this payslip.") from exc
    except Exception as exc:  # noqa: BLE001 - never leak internals (stack traces, document content) to the client
        logger.exception("Verification run failed for payslip %s", payload.payslip_id)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification could not be completed due to an internal error.",
        ) from exc

    return VerificationResultResponse.model_validate(get_verification_result(db, payload.user_id, payload.payslip_id))


@router.get("/{payslip_id}", response_model=VerificationResultResponse)
def get_verification_endpoint(payslip_id: UUID, user_id: UUID, db: Session = Depends(get_db)) -> VerificationResultResponse:
    try:
        result = get_verification_result(db, user_id, payslip_id)
    except VerificationNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No saved verification result for this payslip yet. Call POST /verification/run first.",
        ) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="You do not have access to this payslip.") from exc
    return VerificationResultResponse.model_validate(result)
