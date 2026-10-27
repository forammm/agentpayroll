from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol


class ShiftLike(Protocol):
    work_date: object
    start_time: object
    end_time: object
    break_minutes: int
    hours_worked: Decimal


class PayrollValidationError(ValueError):
    """Raised when payroll input data is incomplete or internally inconsistent."""


def shift_interval(shift: ShiftLike) -> tuple[datetime, datetime]:
    start = datetime.combine(shift.work_date, shift.start_time)
    end = datetime.combine(shift.work_date, shift.end_time)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def validate_shift_time_range(shift: ShiftLike) -> None:
    start, end = shift_interval(shift)
    total_minutes = int((end - start).total_seconds() // 60)
    if total_minutes <= 0:
        raise PayrollValidationError("Invalid time range: shift duration must be positive")
    if total_minutes > 24 * 60:
        raise PayrollValidationError("Invalid time range: shifts cannot exceed 24 hours")
    if shift.break_minutes < 0:
        raise PayrollValidationError("Invalid break: break minutes cannot be negative")
    if shift.break_minutes >= total_minutes:
        raise PayrollValidationError("Invalid break: break cannot equal or exceed shift duration")
    if Decimal(shift.hours_worked) < 0:
        raise PayrollValidationError("Invalid hours: hours worked cannot be negative")


def validate_no_shift_overlaps(shifts: Sequence[ShiftLike]) -> None:
    intervals = sorted(((shift_interval(shift), shift) for shift in shifts), key=lambda item: item[0][0])
    for index in range(1, len(intervals)):
        previous_end = intervals[index - 1][0][1]
        current_start = intervals[index][0][0]
        if current_start < previous_end:
            raise PayrollValidationError("Shift overlap detected for the selected pay period")


def validate_required_rates(rule: object, rate_names: Sequence[str]) -> None:
    if rule is None:
        raise PayrollValidationError("Missing payroll rules for employee")

    for rate_name in rate_names:
        rate = getattr(rule, rate_name, None)
        if rate is None:
            raise PayrollValidationError(f"Missing payroll rate: {rate_name}")
        if Decimal(rate) < 0:
            raise PayrollValidationError(f"Invalid payroll rate: {rate_name} cannot be negative")
