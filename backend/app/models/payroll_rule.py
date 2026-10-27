from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

if TYPE_CHECKING:
    from app.models.user import User


class PayrollRule(Base):
    __tablename__ = "payroll_rules"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    normal_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    overtime_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    saturday_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    sunday_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    public_holiday_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    overnight_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    early_morning_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    evening_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="payroll_rules")
