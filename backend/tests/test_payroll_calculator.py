"""Unit tests for the deterministic payroll calculator (Prompt 3) - previously
untested directly (only exercised indirectly through single-day LangGraph
verification scenarios, which never surfaced the multi-day bug covered here).

Regression coverage for a real bug found via live testing: calculate_gross_pay
used a single ordinary-hours-per-day allowance that was never reset across
multiple calendar days, so any pay period spanning more than one day billed
almost everything after the first ~7.6 hours as overtime - even on days with
entirely ordinary shifts. The fix computes gross pay per calendar day and sums
the results; see app/services/payroll_calculator.py for the full explanation.
"""

from datetime import date, time
from decimal import Decimal

from app.services.payroll_calculator import calculate_payroll_summary

MONDAY = date(2026, 6, 1)
TUESDAY = date(2026, 6, 2)
WEDNESDAY = date(2026, 6, 3)


def test_single_day_within_ordinary_threshold_has_no_overtime(make_payroll_rule, make_timesheet, seeded_user):
    rule = make_payroll_rule(seeded_user.id)
    shift = make_timesheet(seeded_user.id, MONDAY, start_time=time(9, 0), end_time=time(17, 0))  # 7.5h

    summary = calculate_payroll_summary([shift], rule)

    assert summary.ordinary_hours == Decimal("7.50")
    assert summary.overtime_hours == Decimal("0.00")
    assert summary.gross_pay == Decimal("7.50") * Decimal(rule.normal_rate)


def test_single_day_over_threshold_splits_into_overtime(make_payroll_rule, make_timesheet, seeded_user):
    rule = make_payroll_rule(seeded_user.id)
    # 7:00-18:00 with a 30 min break = 10.5h, entirely within the "normal" time
    # window (avoids the 18:00-22:00 evening rate and 5:00-7:00 early-morning
    # rate so this isolates the ordinary/overtime split from other policy
    # windows). 7.6h of the 10.5h is ordinary (456 min/day allowance).
    shift = make_timesheet(seeded_user.id, MONDAY, start_time=time(7, 0), end_time=time(18, 0))

    summary = calculate_payroll_summary([shift], rule)

    assert summary.ordinary_hours == Decimal("7.60")
    assert summary.overtime_hours == Decimal("2.90")
    expected_gross = Decimal("7.60") * Decimal(rule.normal_rate) + Decimal("2.90") * Decimal(rule.overtime_rate)
    assert summary.gross_pay == expected_gross.quantize(Decimal("0.01"))


def test_multiple_ordinary_days_do_not_bleed_into_each_other(make_payroll_rule, make_timesheet, seeded_user):
    """The regression case: three separate 7.5h weekday shifts must each be
    fully ordinary - none of them should spill into overtime just because
    their combined total (22.5h) exceeds one day's 7.6h allowance."""
    rule = make_payroll_rule(seeded_user.id)
    shifts = [
        make_timesheet(seeded_user.id, MONDAY, start_time=time(9, 0), end_time=time(17, 0)),
        make_timesheet(seeded_user.id, TUESDAY, start_time=time(9, 0), end_time=time(17, 0)),
        make_timesheet(seeded_user.id, WEDNESDAY, start_time=time(9, 0), end_time=time(17, 0)),
    ]

    summary = calculate_payroll_summary(shifts, rule)

    assert summary.ordinary_hours == Decimal("22.50")
    assert summary.overtime_hours == Decimal("0.00")
    assert summary.gross_pay == Decimal("22.50") * Decimal(rule.normal_rate)


def test_overtime_on_one_day_does_not_reduce_the_next_days_ordinary_allowance(make_payroll_rule, make_timesheet, seeded_user):
    rule = make_payroll_rule(seeded_user.id)
    # 7:00-18:00 with no break = 11h, entirely "normal" category -> 7.6 ordinary + 3.4 overtime
    long_day = make_timesheet(seeded_user.id, MONDAY, start_time=time(7, 0), end_time=time(18, 0), break_minutes=0)
    normal_day = make_timesheet(seeded_user.id, TUESDAY, start_time=time(9, 0), end_time=time(17, 0))  # 7.5h, should be fully ordinary

    summary = calculate_payroll_summary([long_day, normal_day], rule)

    assert summary.ordinary_hours == Decimal("7.60") + Decimal("7.50")
    assert summary.overtime_hours == Decimal("3.40")


def test_weekend_shift_does_not_consume_the_ordinary_allowance_for_a_later_normal_shift(make_payroll_rule, make_timesheet, seeded_user):
    rule = make_payroll_rule(seeded_user.id)
    saturday = date(2026, 6, 6)
    weekend_shift = make_timesheet(seeded_user.id, saturday, start_time=time(9, 0), end_time=time(17, 0), shift_type="saturday")  # 7.5h
    normal_shift = make_timesheet(seeded_user.id, MONDAY, start_time=time(9, 0), end_time=time(17, 0))  # 7.5h

    summary = calculate_payroll_summary([weekend_shift, normal_shift], rule)

    assert summary.weekend_hours == Decimal("7.50")
    # The weekend shift must not have eaten into Monday's 7.6h ordinary allowance.
    assert summary.ordinary_hours == Decimal("7.50")
    assert summary.overtime_hours == Decimal("0.00")
    expected_gross = Decimal("7.50") * Decimal(rule.saturday_rate) + Decimal("7.50") * Decimal(rule.normal_rate)
    assert summary.gross_pay == expected_gross.quantize(Decimal("0.01"))
