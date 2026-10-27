from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payroll_rule import PayrollRule
from app.models.timesheet import Timesheet
from app.schemas.payroll_summary import PayrollSummary
from app.services.payroll_rule_service import get_latest_rule
from app.services.super_service import estimate_super
from app.services.tax_service import estimate_tax
from app.services.validation_service import (
    PayrollValidationError,
    shift_interval,
    validate_no_shift_overlaps,
    validate_required_rates,
    validate_shift_time_range,
)


MONEY = Decimal("0.01")
HOURS = Decimal("0.01")
REQUIRED_RATE_NAMES = (
    "normal_rate",
    "overtime_rate",
    "saturday_rate",
    "sunday_rate",
    "public_holiday_rate",
    "overnight_rate",
    "early_morning_rate",
    "evening_rate",
)


@dataclass(frozen=True)
class PayrollCalculationPolicy:
    ordinary_minutes_per_day: int = 456
    early_morning_start: time = time(5, 0)
    early_morning_end: time = time(7, 0)
    evening_start: time = time(18, 0)
    evening_end: time = time(22, 0)
    overnight_start: time = time(22, 0)
    overnight_end: time = time(6, 0)


@dataclass(frozen=True)
class PaySegment:
    category: str
    minutes: int
    rate: Decimal


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def minutes_to_hours(minutes: int) -> Decimal:
    if minutes < 0:
        raise PayrollValidationError("Invalid hours: minutes cannot be negative")
    return (Decimal(minutes) / Decimal(60)).quantize(HOURS, rounding=ROUND_HALF_UP)


def calculate_shift_paid_minutes(shift: Timesheet) -> int:
    validate_shift_time_range(shift)
    start, end = shift_interval(shift)
    return int((end - start).total_seconds() // 60) - shift.break_minutes


def calculate_total_hours_worked(shifts: Sequence[Timesheet]) -> Decimal:
    return minutes_to_hours(sum(calculate_shift_paid_minutes(shift) for shift in shifts))


def calculate_break_deduction_minutes(shifts: Sequence[Timesheet]) -> int:
    total = sum(shift.break_minutes for shift in shifts)
    if total < 0:
        raise PayrollValidationError("Invalid break: break minutes cannot be negative")
    return total


def calculate_ordinary_minutes(total_paid_minutes: int, policy: PayrollCalculationPolicy) -> int:
    if total_paid_minutes < 0:
        raise PayrollValidationError("Invalid hours: paid minutes cannot be negative")
    return min(total_paid_minutes, policy.ordinary_minutes_per_day)


def calculate_overtime_minutes(total_paid_minutes: int, policy: PayrollCalculationPolicy) -> int:
    if total_paid_minutes < 0:
        raise PayrollValidationError("Invalid hours: paid minutes cannot be negative")
    return max(0, total_paid_minutes - policy.ordinary_minutes_per_day)


def _normalise_shift_type(shift_type: str | None) -> str:
    return (shift_type or "normal").strip().lower().replace("-", "_").replace(" ", "_")


def _is_public_holiday(shift: Timesheet) -> bool:
    return _normalise_shift_type(shift.shift_type) in {"public_holiday", "publicholiday", "holiday"}


def _weekend_category(shift: Timesheet) -> str | None:
    shift_type = _normalise_shift_type(shift.shift_type)
    if shift_type == "saturday" or shift.work_date.weekday() == 5:
        return "saturday"
    if shift_type == "sunday" or shift.work_date.weekday() == 6:
        return "sunday"
    if shift_type == "weekend":
        return "saturday"
    return None


def _window_contains(moment: datetime, start: time, end: time) -> bool:
    current = moment.time()
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _minute_category(moment: datetime, policy: PayrollCalculationPolicy) -> str:
    if _window_contains(moment, policy.overnight_start, policy.overnight_end):
        return "overnight"
    if _window_contains(moment, policy.early_morning_start, policy.early_morning_end):
        return "early_morning"
    if _window_contains(moment, policy.evening_start, policy.evening_end):
        return "evening"
    return "normal"


def _rate_for_category(category: str, rule: PayrollRule) -> Decimal:
    rate_map = {
        "normal": rule.normal_rate,
        "overtime": rule.overtime_rate,
        "saturday": rule.saturday_rate,
        "sunday": rule.sunday_rate,
        "public_holiday": rule.public_holiday_rate,
        "overnight": rule.overnight_rate,
        "early_morning": rule.early_morning_rate,
        "evening": rule.evening_rate,
    }
    return Decimal(rate_map[category])


def _append_segment(segments: list[PaySegment], category: str, minutes: int, rate: Decimal) -> None:
    if minutes <= 0:
        return
    if segments and segments[-1].category == category and segments[-1].rate == rate:
        previous = segments[-1]
        segments[-1] = PaySegment(previous.category, previous.minutes + minutes, previous.rate)
        return
    segments.append(PaySegment(category=category, minutes=minutes, rate=rate))


def split_shift_into_pay_segments(
    shift: Timesheet,
    rule: PayrollRule,
    policy: PayrollCalculationPolicy = PayrollCalculationPolicy(),
) -> list[PaySegment]:
    paid_minutes = calculate_shift_paid_minutes(shift)
    start, _ = shift_interval(shift)

    if _is_public_holiday(shift):
        return [PaySegment("public_holiday", paid_minutes, _rate_for_category("public_holiday", rule))]

    weekend_category = _weekend_category(shift)
    if weekend_category:
        return [PaySegment(weekend_category, paid_minutes, _rate_for_category(weekend_category, rule))]

    shift_type = _normalise_shift_type(shift.shift_type)
    if shift_type in {"overnight", "early_morning", "evening"}:
        return [PaySegment(shift_type, paid_minutes, _rate_for_category(shift_type, rule))]

    segments: list[PaySegment] = []
    for offset in range(paid_minutes):
        category = _minute_category(start + timedelta(minutes=offset), policy)
        _append_segment(segments, category, 1, _rate_for_category(category, rule))
    return segments


def split_shifts_into_pay_segments(
    shifts: Sequence[Timesheet],
    rule: PayrollRule,
    policy: PayrollCalculationPolicy = PayrollCalculationPolicy(),
) -> list[PaySegment]:
    segments: list[PaySegment] = []
    for shift in sorted(shifts, key=lambda item: shift_interval(item)[0]):
        for segment in split_shift_into_pay_segments(shift, rule, policy):
            _append_segment(segments, segment.category, segment.minutes, segment.rate)
    return segments


def calculate_category_minutes(segments: Iterable[PaySegment], categories: set[str]) -> int:
    return sum(segment.minutes for segment in segments if segment.category in categories)


def calculate_gross_pay(
    segments: Sequence[PaySegment],
    rule: PayrollRule,
    policy: PayrollCalculationPolicy = PayrollCalculationPolicy(),
) -> Decimal:
    """Computes gross pay for segments belonging to a SINGLE calendar day.

    The ordinary-hours-per-day allowance (policy.ordinary_minutes_per_day) only
    makes sense within one day. Callers with shifts spanning multiple days
    (e.g. a full pay period) must call this once per calendar day and sum the
    results - see calculate_payroll_summary - otherwise every day after the
    first would be billed almost entirely at the overtime rate, since the
    allowance would never reset.

    Only "normal" segments draw against the ordinary allowance. Weekend/public
    holiday/overnight/early-morning/evening segments are paid at their own
    flat rate regardless of how many ordinary hours were already worked that
    day - they must not consume (or be split by) the ordinary/overtime split.
    """
    ordinary_remaining = policy.ordinary_minutes_per_day
    gross_pay = Decimal("0.00")

    for segment in segments:
        if segment.category == "normal":
            ordinary_minutes = min(segment.minutes, max(0, ordinary_remaining))
            overtime_minutes = segment.minutes - ordinary_minutes
            ordinary_remaining -= ordinary_minutes
            gross_pay += minutes_to_hours(ordinary_minutes) * Decimal(rule.normal_rate)
            gross_pay += minutes_to_hours(overtime_minutes) * Decimal(rule.overtime_rate)
        else:
            gross_pay += minutes_to_hours(segment.minutes) * segment.rate

    return quantize_money(gross_pay)


def calculate_penalty_rates_applied(segments: Sequence[PaySegment]) -> list[str]:
    labels = {
        "saturday": "Saturday rate",
        "sunday": "Sunday rate",
        "public_holiday": "Public holiday rate",
        "overnight": "Overnight rate",
        "early_morning": "Early morning rate",
        "evening": "Evening rate",
    }
    applied = [labels[category] for category in labels if calculate_category_minutes(segments, {category}) > 0]
    return applied


def calculate_payroll_summary(
    shifts: Sequence[Timesheet],
    rule: PayrollRule,
    policy: PayrollCalculationPolicy = PayrollCalculationPolicy(),
) -> PayrollSummary:
    if not shifts:
        raise PayrollValidationError("No timesheets found for payroll calculation")

    validate_required_rates(rule, REQUIRED_RATE_NAMES)
    for shift in shifts:
        validate_shift_time_range(shift)
    validate_no_shift_overlaps(shifts)

    ordered_shifts = sorted(shifts, key=lambda item: shift_interval(item)[0])
    employee_id = ordered_shifts[0].user_id
    if any(shift.user_id != employee_id for shift in ordered_shifts):
        raise PayrollValidationError("Timesheets must belong to the same employee")

    # The ordinary-hours-per-day allowance must reset every calendar day, so
    # gross pay (and the ordinary/overtime split) is computed one day at a
    # time and summed - see calculate_gross_pay's docstring for why passing
    # every shift in the pay period to it in one call would be wrong.
    shifts_by_day: dict = {}
    for shift in ordered_shifts:
        shifts_by_day.setdefault(shift.work_date, []).append(shift)

    gross_pay = Decimal("0.00")
    all_segments: list[PaySegment] = []
    ordinary_minutes_total = 0
    overtime_minutes_total = 0
    for work_date in sorted(shifts_by_day):
        day_shifts = shifts_by_day[work_date]
        day_segments = split_shifts_into_pay_segments(day_shifts, rule, policy)
        gross_pay += calculate_gross_pay(day_segments, rule, policy)
        day_normal_minutes = calculate_category_minutes(day_segments, {"normal"})
        ordinary_minutes_total += calculate_ordinary_minutes(day_normal_minutes, policy)
        overtime_minutes_total += calculate_overtime_minutes(day_normal_minutes, policy)
        all_segments.extend(day_segments)

    gross_pay = quantize_money(gross_pay)
    estimated_tax = estimate_tax(gross_pay)
    estimated_super = estimate_super(gross_pay)

    return PayrollSummary(
        employee_id=employee_id,
        pay_period=_format_pay_period(ordered_shifts),
        ordinary_hours=minutes_to_hours(ordinary_minutes_total),
        overtime_hours=minutes_to_hours(overtime_minutes_total),
        weekend_hours=minutes_to_hours(calculate_category_minutes(all_segments, {"saturday", "sunday"})),
        public_holiday_hours=minutes_to_hours(calculate_category_minutes(all_segments, {"public_holiday"})),
        early_morning_hours=minutes_to_hours(calculate_category_minutes(all_segments, {"early_morning"})),
        evening_hours=minutes_to_hours(calculate_category_minutes(all_segments, {"evening"})),
        overnight_hours=minutes_to_hours(calculate_category_minutes(all_segments, {"overnight"})),
        hourly_rate=Decimal(rule.normal_rate),
        overtime_rate=Decimal(rule.overtime_rate),
        penalty_rates_applied=calculate_penalty_rates_applied(all_segments),
        gross_pay=gross_pay,
        estimated_tax=estimated_tax,
        estimated_super=estimated_super,
        net_pay=quantize_money(gross_pay - estimated_tax),
    )


def _format_pay_period(shifts: Sequence[Timesheet]) -> str:
    dates = sorted({shift.work_date for shift in shifts})
    if len(dates) == 1:
        return dates[0].isoformat()
    return f"{dates[0].isoformat()} to {dates[-1].isoformat()}"


def calculate_payroll_for_timesheet(db: Session, timesheet_id: object) -> PayrollSummary:
    target = db.scalar(select(Timesheet).where(Timesheet.id == timesheet_id))
    if target is None:
        raise PayrollValidationError("Timesheet not found")

    rule = get_latest_rule(db, target.user_id)
    if rule is None:
        raise PayrollValidationError("Missing payroll rules for employee")

    pay_period_shifts = list(
        db.scalars(
            select(Timesheet)
            .where(Timesheet.user_id == target.user_id, Timesheet.work_date == target.work_date)
            .order_by(Timesheet.start_time.asc())
        ).all()
    )
    return calculate_payroll_summary(pay_period_shifts, rule)
