from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.schemas.payslip import PayslipResponse


async def mock_upload(user_id: UUID, file: UploadFile) -> PayslipResponse:
    """Return metadata only. File persistence and PDF extraction are intentionally deferred."""
    return PayslipResponse(id=uuid4(), user_id=user_id, file_name=file.filename or "payslip.pdf", upload_status="mock_uploaded", created_at=datetime.now(timezone.utc))
