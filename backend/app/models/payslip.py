from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, func
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

    # Upload metadata. file_name is the original filename shown to the user only;
    # the on-disk path is always derived from the server-generated payslip id, never
    # from user input, so a crafted filename cannot escape the storage directory.
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(20), default="UPLOADED")
    used_ocr: Mapped[bool] = mapped_column(Boolean, default=False)

    # Extracted payroll fields. All nullable: a missing value means "not found",
    # never zero - the extraction service must not invent figures.
    employer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    pay_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gross_pay: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    net_pay: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tax_deducted: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    superannuation: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    deductions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    ordinary_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    overtime_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    weekend_or_holiday_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    earnings_breakdown: Mapped[list | None] = mapped_column(JSON, nullable=True)

    extraction_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extraction_errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="payslips")
    verification_result: Mapped["VerificationResult | None"] = relationship(back_populates="payslip", cascade="all, delete-orphan", uselist=False)
