from uuid import UUID

from fastapi import APIRouter, File, UploadFile

from app.schemas.payslip import PayslipResponse
from app.services.payslip_service import mock_upload

router = APIRouter(prefix="/payslips", tags=["payslips"])


@router.post("/upload", response_model=PayslipResponse)
async def upload_payslip(user_id: UUID, file: UploadFile = File(...)):
    return await mock_upload(user_id, file)
