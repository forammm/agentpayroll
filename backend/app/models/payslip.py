from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.verification_result import VerificationResult


class Payslip(Base):
    __tablename__ = "payslips"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    gross_pay: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax_deducted: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    deductions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    upload_status: Mapped[str] = mapped_column(String(40), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="payslips")
    verification_result: Mapped["VerificationResult | None"] = relationship(back_populates="payslip", cascade="all, delete-orphan", uselist=False)
