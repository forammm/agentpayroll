from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.schemas.payslip import PayslipResponse
from app.services.payslip_service import get_payslip, upload_payslip

router = APIRouter(prefix="/payslips", tags=["payslips"])


@router.post("/upload", response_model=PayslipResponse)
async def upload_payslip_endpoint(user_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db)) -> PayslipResponse:
    return await upload_payslip(db, user_id, file)


@router.get("/{payslip_id}", response_model=PayslipResponse)
def get_payslip_endpoint(payslip_id: UUID, db: Session = Depends(get_db)) -> PayslipResponse:
    return get_payslip(db, payslip_id)
