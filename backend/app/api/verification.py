from uuid import UUID

from fastapi import APIRouter

from app.schemas.verification import VerificationResultResponse
from app.services.verification_service import mock_verification

router = APIRouter(prefix="/verification", tags=["verification"])


@router.post("/{payslip_id}", response_model=VerificationResultResponse)
def verify_payslip(payslip_id: UUID):
    return mock_verification(payslip_id)


@router.get("/{payslip_id}", response_model=VerificationResultResponse)
def get_verification(payslip_id: UUID):
    return mock_verification(payslip_id)
