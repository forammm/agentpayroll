from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.db import Base

if TYPE_CHECKING:
    from app.models.payroll_rule import PayrollRule
    from app.models.payslip import Payslip
    from app.models.timesheet import Timesheet


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    timesheets: Mapped[list["Timesheet"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payroll_rules: Mapped[list["PayrollRule"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payslips: Mapped[list["Payslip"]] = relationship(back_populates="user", cascade="all, delete-orphan")
