from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.schemas.verification import VerificationResultResponse


def mock_verification(payslip_id: UUID) -> VerificationResultResponse:
    return VerificationResultResponse(id=uuid4(), payslip_id=payslip_id, expected_pay=Decimal("1842.50"), actual_pay=Decimal("1745.20"), underpaid_amount=Decimal("97.30"), overpaid_amount=Decimal("0.00"), tax_deducted=Decimal("348.00"), deductions=Decimal("42.50"), status="underpaid", notes="Mock result: weekend loadings may require review.", created_at=datetime.now(timezone.utc))
