"""Heuristic, regex-based parsing of payroll fields out of raw payslip text.

This module never calculates payroll and never invents a value: every field
starts as None and is only filled in when a reasonably confident match is
found. Different employers format payslips differently, so each field is
tried against a short list of label variants rather than one fixed layout.

This is pattern matching, not natural-language understanding - unusual
layouts will legitimately come back with fields missing, which the
validation service turns into warnings rather than silent zeros.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.schemas.payslip_extraction import ExtractedEarningLine, PayslipExtractedFields

_MONEY = r"\(?-?\$?\s?[\d,]+\.\d{2}\)?"
_HOURS = r"-?[\d,]+(?:\.\d+)?"
_DATE_TOKEN = (
    r"(?:\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"
    r"|\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})"
)

_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d",
    "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y",
]

_MONEY_FIELD_PATTERNS: dict[str, list[str]] = {
    # The suffix word (pay/earnings/income) is optional: some real payslips use a
    # bare column header like "Gross" or "Net" with the amount in a separate
    # column rather than "Gross Pay: $X" on one line. A leading \b on "net" stops
    # this from matching mid-word (e.g. "Internet").
    "gross_pay": [rf"gross\s*(?:pay|earnings|income)?\s*[:\-]?\s*({_MONEY})"],
    "net_pay": [
        rf"\bnet\s*(?:pay|amount|income)?\s*[:\-]?\s*({_MONEY})",
        rf"take[ \-]?home\s*pay\s*[:\-]?\s*({_MONEY})",
    ],
    "tax_withheld": [rf"(?:payg\s*)?tax\s*(?:withheld|deducted)?\s*[:\-]?\s*({_MONEY})"],
    "superannuation": [rf"super(?:annuation)?(?:\s*contributions?)?\s*[:\-]?\s*({_MONEY})"],
    "deductions": [rf"(?:total\s*)?deductions\s*[:\-]?\s*({_MONEY})"],
    "hourly_rate": [
        rf"hourly\s*rate\s*[:\-]?\s*({_MONEY})",
        rf"rate\s*per\s*hour\s*[:\-]?\s*({_MONEY})",
    ],
}

_HOURS_FIELD_PATTERNS: dict[str, list[str]] = {
    "ordinary_hours": [
        rf"ordinary\s*hours\s*[:\-]?\s*({_HOURS})",
        rf"normal\s*hours\s*[:\-]?\s*({_HOURS})",
    ],
    "overtime_hours": [rf"overtime\s*hours\s*[:\-]?\s*({_HOURS})"],
    "weekend_or_holiday_hours": [
        rf"(?:weekend|saturday|sunday|public\s*holiday)\s*hours\s*[:\-]?\s*({_HOURS})"
    ],
}

_PAY_DATE_PATTERNS = [rf"pay\s*date\s*[:\-]?\s*({_DATE_TOKEN})"]

_PERIOD_RANGE_RE = re.compile(
    rf"pay\s*period\s*[:\-]?\s*({_DATE_TOKEN})\s*(?:to|-|–|through)\s*({_DATE_TOKEN})", re.IGNORECASE
)
_PERIOD_START_RE = re.compile(rf"period\s*start(?:\s*date)?\s*[:\-]?\s*({_DATE_TOKEN})", re.IGNORECASE)
_PERIOD_END_RE = re.compile(rf"period\s*end(?:\s*date)?\s*[:\-]?\s*({_DATE_TOKEN})", re.IGNORECASE)
_PERIOD_ENDING_RE = re.compile(rf"pay\s*period\s*ending\s*[:\-]?\s*({_DATE_TOKEN})", re.IGNORECASE)
_EMPLOYER_RE = re.compile(r"(?:employer|company)(?:\s*name)?\s*[:\-]\s*(.+)", re.IGNORECASE)

_EARNINGS_SECTION_START_RE = re.compile(r"^\s*earnings\b", re.IGNORECASE)
_EARNINGS_SECTION_STOP_RE = re.compile(
    r"^\s*(deductions|tax|summary|net\s*pay|leave|superannuation)\b", re.IGNORECASE
)
_EARNINGS_LINE_RE = re.compile(
    r"^(?P<label>[A-Za-z][A-Za-z \-/&]{2,40}?)\s+"
    r"(?:[\d,]+(?:\.\d+)?\s+)?(?:\$?[\d,]+\.\d{2}\s+)?"
    r"\$?(?P<amount>[\d,]+\.\d{2})\s*$"
)


def parse_money(raw: str | None) -> Decimal | None:
    """Parse a currency string into a Decimal. Handles $, commas, and
    parenthesised/negative amounts (common for deductions on payslips)."""
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = re.sub(r"[^0-9.\-]", "", s.replace(",", ""))
    if s.startswith("-"):
        negative = True
        s = s[1:]
    s = s.strip(".")
    if not s:
        return None
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    return -value if negative else value


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    s = raw.strip().strip(",")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _find_money(text: str, patterns: list[str]) -> Decimal | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = parse_money(match.group(1))
            if value is not None:
                return value
    return None


def _find_hours(text: str, patterns: list[str]) -> Decimal | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                return abs(Decimal(raw))
            except InvalidOperation:
                continue
    return None


def _find_date(text: str, patterns: list[str]) -> date | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = parse_date(match.group(1))
            if value:
                return value
    return None


def _find_period(text: str) -> tuple[date | None, date | None]:
    range_match = _PERIOD_RANGE_RE.search(text)
    if range_match:
        return parse_date(range_match.group(1)), parse_date(range_match.group(2))

    start = None
    end = None
    start_match = _PERIOD_START_RE.search(text)
    if start_match:
        start = parse_date(start_match.group(1))
    end_match = _PERIOD_END_RE.search(text)
    if end_match:
        end = parse_date(end_match.group(1))
    if end is None:
        ending_match = _PERIOD_ENDING_RE.search(text)
        if ending_match:
            end = parse_date(ending_match.group(1))
    return start, end


def _find_employer(text: str) -> str | None:
    match = _EMPLOYER_RE.search(text)
    if not match:
        return None
    name = match.group(1).splitlines()[0].strip()
    return name[:255] if name else None


def _extract_earnings_breakdown(text: str) -> list[ExtractedEarningLine]:
    """Best-effort read of an "Earnings" table into {label, amount} rows.
    Heuristic by nature: tuned for a simple columnar layout and will miss
    more elaborate table formats, which is acceptable since this field is
    supplementary detail rather than a verification-critical figure."""
    lines = text.splitlines()
    start_idx = next((i for i, line in enumerate(lines) if _EARNINGS_SECTION_START_RE.search(line)), None)
    if start_idx is None:
        return []

    breakdown: list[ExtractedEarningLine] = []
    for line in lines[start_idx + 1 :]:
        if _EARNINGS_SECTION_STOP_RE.search(line):
            break
        match = _EARNINGS_LINE_RE.match(line.strip())
        if match:
            amount = parse_money(match.group("amount"))
            if amount is not None:
                breakdown.append(ExtractedEarningLine(label=match.group("label").strip(), amount=amount))
    return breakdown[:20]


def parse_fields(text: str) -> PayslipExtractedFields:
    """Parse raw payslip text into structured, validated fields.

    Pure function: does not touch the database or make a verification
    decision. Any field it cannot confidently find is left as None.
    """
    period_start, period_end = _find_period(text)

    return PayslipExtractedFields(
        employer_name=_find_employer(text),
        period_start=period_start,
        period_end=period_end,
        pay_date=_find_date(text, _PAY_DATE_PATTERNS),
        gross_pay=_find_money(text, _MONEY_FIELD_PATTERNS["gross_pay"]),
        net_pay=_find_money(text, _MONEY_FIELD_PATTERNS["net_pay"]),
        tax_withheld=_find_money(text, _MONEY_FIELD_PATTERNS["tax_withheld"]),
        superannuation=_find_money(text, _MONEY_FIELD_PATTERNS["superannuation"]),
        deductions=_find_money(text, _MONEY_FIELD_PATTERNS["deductions"]),
        hourly_rate=_find_money(text, _MONEY_FIELD_PATTERNS["hourly_rate"]),
        ordinary_hours=_find_hours(text, _HOURS_FIELD_PATTERNS["ordinary_hours"]),
        overtime_hours=_find_hours(text, _HOURS_FIELD_PATTERNS["overtime_hours"]),
        weekend_or_holiday_hours=_find_hours(text, _HOURS_FIELD_PATTERNS["weekend_or_holiday_hours"]),
        earnings_breakdown=_extract_earnings_breakdown(text),
    )
