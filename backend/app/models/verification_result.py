from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

if TYPE_CHECKING:
    from app.models.payslip import Payslip


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    payslip_id: Mapped[UUID] = mapped_column(ForeignKey("payslips.id", ondelete="CASCADE"), unique=True, index=True)
    # Denormalized from payslip.user_id: lets ownership checks and per-user queries
    # run without a join, matching the Payslip/Timesheet/PayrollRule convention.
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    pay_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    pay_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    expected_gross_pay: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    actual_gross_pay: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    expected_net_pay: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    actual_net_pay: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    gross_difference: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    net_difference: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Null when no comparison was made at all (e.g. NEEDS_REVIEW due to missing
    # evidence short-circuiting before compare_pay ever ran), not just when it's zero.
    tolerance: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    estimated_tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_super: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    deductions: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="NEEDS_REVIEW")

    # PayrollSummary fields (hours/rates/loadings) from the deterministic calculator,
    # kept as-is for display - never recomputed from this stored copy.
    calculation_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    explanation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    explanation_uncertainties: Mapped[list | None] = mapped_column(JSON, nullable=True)
    explanation_next_steps: Mapped[list | None] = mapped_column(JSON, nullable=True)

    warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    errors: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    payslip: Mapped["Payslip"] = relationship(back_populates="verification_result")
