from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

if TYPE_CHECKING:
    from app.models.payslip import Payslip


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    payslip_id: Mapped[UUID] = mapped_column(ForeignKey("payslips.id", ondelete="CASCADE"), unique=True, index=True)
    expected_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    actual_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    underpaid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    overpaid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    tax_deducted: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(40), default="needs_review")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    payslip: Mapped["Payslip"] = relationship(back_populates="verification_result")
