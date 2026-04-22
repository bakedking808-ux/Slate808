from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TimingCategory = Literal[
    "exact_date",
    "date_range",
    "month_only",
    "month_year",
    "relative_timing",
    "duration",
    "season_period",
    "named_period",
    "composite_timing",
    "unknown",
]
TimingConfidence = Literal["low", "medium", "high"]


class ParsedTiming(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    category: TimingCategory
    raw_text: str
    normalized_text: str | None
    start_date: str | None = None
    end_date: str | None = None
    duration_days: int | None = Field(default=None, gt=0)
    duration_nights: int | None = Field(default=None, gt=0)
    month: str | None = None
    year: int | None = None
    relative_label: str | None = None
    season_label: str | None = None
    named_period_label: str | None = None
    confidence: TimingConfidence
    warnings: list[str] = Field(default_factory=list)


class TimingParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    matched: bool
    parsed: ParsedTiming | None = None


MONTH_ALIASES = {
    "jan": "january",
    "january": "january",
    "feb": "february",
    "february": "february",
    "mar": "march",
    "march": "march",
    "apr": "april",
    "april": "april",
    "may": "may",
    "jun": "june",
    "june": "june",
    "jul": "july",
    "july": "july",
    "aug": "august",
    "august": "august",
    "sep": "september",
    "sept": "september",
    "september": "september",
    "oct": "october",
    "october": "october",
    "nov": "november",
    "november": "november",
    "dec": "december",
    "december": "december",
}

MONTH_PATTERN = "|".join(sorted(MONTH_ALIASES, key=len, reverse=True))
DAY_PATTERN = r"0?[1-9]|[12]\d|3[01]"
DAY_TOKEN = rf"(?P<day>{DAY_PATTERN})(?:st|nd|rd|th)?"
YEAR_TOKEN = r"(?P<year>\d{4})"
CONNECTOR = r"(?:-|to)"

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def parse_timing_text(user_input: str) -> TimingParseResult:
    text = _normalize_input(user_input)
    if not text:
        return TimingParseResult(matched=False, parsed=None)

    components = [
        parser(text)
        for parser in (
            _parse_date_range,
            _parse_exact_date,
            _parse_month_year,
            _parse_month_only,
            _parse_relative_timing,
            _parse_duration,
            _parse_season_period,
            _parse_named_period,
        )
    ]
    components = [component for component in components if component is not None]

    if not components:
        return TimingParseResult(matched=False, parsed=None)

    components = _drop_subordinate_components(components)

    if _is_composite(components):
        return TimingParseResult(matched=True, parsed=_build_composite(components))

    return TimingParseResult(matched=True, parsed=_choose_primary(components))


def _normalize_input(value: str) -> str:
    lowered = value.lower().strip()
    lowered = lowered.replace("–", "-")
    lowered = re.sub(r"\s*,\s*", ", ", lowered)
    return re.sub(r"\s+", " ", lowered)


def _month(value: str) -> str:
    return MONTH_ALIASES[value.lower()]


def _day(value: str) -> int:
    return int(re.sub(r"(st|nd|rd|th)$", "", value.lower()).lstrip("0") or "0")


def _date_text(day: int, month: str, year: int | None = None) -> str:
    value = f"{day} {month}"
    return f"{value} {year}" if year is not None else value


def _parsed(
    category: TimingCategory,
    raw_text: str,
    normalized_text: str | None,
    confidence: TimingConfidence,
    **kwargs,
) -> ParsedTiming:
    return ParsedTiming(
        category=category,
        raw_text=raw_text.strip(" ,"),
        normalized_text=normalized_text,
        confidence=confidence,
        **kwargs,
    )


def _parse_date_range(text: str) -> ParsedTiming | None:
    patterns = [
        rf"\b(?P<d1>{DAY_PATTERN})(?:st|nd|rd|th)?\s*{CONNECTOR}\s*"
        rf"(?P<d2>{DAY_PATTERN})(?:st|nd|rd|th)?\s+(?P<m>{MONTH_PATTERN})"
        rf"(?:\s+(?P<y>\d{{4}}))?\b",
        rf"\b(?P<m>{MONTH_PATTERN})\s+(?P<d1>{DAY_PATTERN})(?:st|nd|rd|th)?"
        rf"\s*{CONNECTOR}\s*(?P<d2>{DAY_PATTERN})(?:st|nd|rd|th)?"
        rf"(?:\s+(?P<y>\d{{4}}))?\b",
        rf"\b(?P<d1>{DAY_PATTERN})(?:st|nd|rd|th)?\s+(?P<m1>{MONTH_PATTERN})"
        rf"\s*{CONNECTOR}\s*(?P<d2>{DAY_PATTERN})(?:st|nd|rd|th)?\s+"
        rf"(?P<m2>{MONTH_PATTERN})(?:\s+(?P<y>\d{{4}}))?\b",
        rf"\b(?P<m1>{MONTH_PATTERN})\s+(?P<d1>{DAY_PATTERN})(?:st|nd|rd|th)?"
        rf"\s*{CONNECTOR}\s*(?P<m2>{MONTH_PATTERN})\s+"
        rf"(?P<d2>{DAY_PATTERN})(?:st|nd|rd|th)?(?:\s+(?P<y>\d{{4}}))?\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        data = match.groupdict()
        month_1 = _month(data.get("m1") or data.get("m"))
        month_2 = _month(data.get("m2") or data.get("m"))
        year = int(data["y"]) if data.get("y") else None
        start = _date_text(_day(data["d1"]), month_1, year)
        end = _date_text(_day(data["d2"]), month_2, year)
        return _parsed(
            "date_range",
            match.group(0),
            f"{start} to {end}",
            "high",
            start_date=start,
            end_date=end,
            month=month_1 if month_1 == month_2 else None,
            year=year,
        )

    return None


def _parse_exact_date(text: str) -> ParsedTiming | None:
    patterns = [
        rf"\b(?P<day>{DAY_PATTERN})(?:st|nd|rd|th)?\s+(?P<month>{MONTH_PATTERN})"
        rf"(?:,?\s+(?P<year>\d{{4}}))?\b",
        rf"\b(?P<month>{MONTH_PATTERN})\s+(?P<day>{DAY_PATTERN})(?:st|nd|rd|th)?"
        rf"(?:,?\s+(?P<year>\d{{4}}))?\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        data = match.groupdict()
        month = _month(data["month"])
        year = int(data["year"]) if data.get("year") else None
        normalized = _date_text(_day(data["day"]), month, year)
        return _parsed(
            "exact_date",
            match.group(0),
            normalized,
            "high",
            start_date=normalized,
            month=month,
            year=year,
        )

    return None


def _parse_month_year(text: str) -> ParsedTiming | None:
    match = re.search(
        rf"\b(?:in|during)?\s*(?P<month>{MONTH_PATTERN})\s+(?P<year>\d{{4}})\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    month = _month(match.group("month"))
    year = int(match.group("year"))
    return _parsed(
        "month_year",
        match.group(0),
        f"{month} {year}",
        "high",
        month=month,
        year=year,
    )


def _parse_month_only(text: str) -> ParsedTiming | None:
    match = re.search(
        rf"\b(?:(?:in|during|sometime in)\s+)?(?P<month>{MONTH_PATTERN})\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    month = _month(match.group("month"))
    return _parsed(
        "month_only",
        match.group(0),
        month,
        "medium",
        month=month,
    )


def _parse_relative_timing(text: str) -> ParsedTiming | None:
    labels = {
        "later this month": "later this month",
        "sometime next month": "sometime next month",
        "this weekend": "this weekend",
        "next weekend": "next weekend",
        "this week": "this week",
        "next week": "next week",
        "this month": "this month",
        "next month": "next month",
        "this year": "this year",
        "next year": "next year",
        "soon": "soon",
    }
    for phrase, label in labels.items():
        match = re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE)
        if match:
            return _parsed(
                "relative_timing",
                match.group(0),
                label,
                "medium",
                relative_label=label,
            )
    return None


def _parse_duration(text: str) -> ParsedTiming | None:
    day_match = re.search(
        rf"\b(?P<num>\d+|{'|'.join(NUMBER_WORDS)})[- ]days?\b", text
    )
    night_match = re.search(
        rf"\b(?P<num>\d+|{'|'.join(NUMBER_WORDS)})[- ]nights?\b", text
    )
    week_match = re.search(
        rf"\b(?P<num>\d+|{'|'.join(NUMBER_WORDS)}|a)[- ]weeks?\b", text
    )

    days = _duration_number(day_match) if day_match else None
    nights = _duration_number(night_match) if night_match else None
    warnings: list[str] = []
    raw_parts = []

    if week_match:
        days = _duration_number(week_match) * 7
        raw_parts.append(week_match.group(0))
    if day_match:
        raw_parts.append(day_match.group(0))
    if night_match:
        raw_parts.append(night_match.group(0))

    if days or nights:
        normalized = _duration_text(days, nights)
        return _parsed(
            "duration",
            " ".join(raw_parts),
            normalized,
            "high",
            duration_days=days,
            duration_nights=nights,
            warnings=warnings,
        )

    named = {
        "a long weekend": (None, 3, "long weekend approximated as 3 nights"),
        "long weekend": (None, 3, "long weekend approximated as 3 nights"),
        "a week": (7, None, None),
        "a few days": (3, None, "a few days approximated as 3 days"),
        "a short break": (2, None, "short break approximated as 2 days"),
        "short break": (2, None, "short break approximated as 2 days"),
        "a quick getaway": (2, None, "quick getaway approximated as 2 days"),
        "quick getaway": (2, None, "quick getaway approximated as 2 days"),
    }
    for phrase, (named_days, named_nights, warning) in named.items():
        match = re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE)
        if not match:
            continue
        if warning:
            warnings.append(warning)
        return _parsed(
            "duration",
            match.group(0),
            _duration_text(named_days, named_nights),
            "medium",
            duration_days=named_days,
            duration_nights=named_nights,
            warnings=warnings,
        )

    return None


def _duration_number(match: re.Match) -> int:
    value = match.group("num")
    if value == "a":
        return 1
    if value.isdigit():
        return int(value)
    return NUMBER_WORDS[value]


def _duration_text(days: int | None, nights: int | None) -> str:
    parts = []
    if days:
        parts.append(f"{days} day" if days == 1 else f"{days} days")
    if nights:
        parts.append(f"{nights} night" if nights == 1 else f"{nights} nights")
    return " ".join(parts)


def _parse_season_period(text: str) -> ParsedTiming | None:
    labels = {
        "rainy season": "rainy season",
        "dry season": "dry season",
        "high season": "high season",
        "low season": "low season",
        "summer": "summer",
        "winter": "winter",
        "spring": "spring",
        "autumn": "autumn",
        "fall": "fall",
    }
    for phrase, label in labels.items():
        match = re.search(
            rf"\b(?:in|during|over)?\s*(?:the\s+)?{re.escape(phrase)}\b",
            text,
            re.IGNORECASE,
        )
        if match:
            return _parsed(
                "season_period",
                match.group(0),
                label,
                "medium",
                season_label=label,
            )
    return None


def _parse_named_period(text: str) -> ParsedTiming | None:
    labels = {
        "the school break": "school break",
        "school break": "school break",
        "the public holiday": "public holiday",
        "public holiday": "public holiday",
        "the holidays": "holidays",
        "holidays": "holidays",
        "christmas": "christmas",
        "easter": "easter",
        "the long weekend": "long weekend",
        "long weekend": "long weekend",
    }
    for phrase, label in labels.items():
        match = re.search(
            rf"\b(?:during|over|around|for)?\s*{re.escape(phrase)}\b",
            text,
            re.IGNORECASE,
        )
        if match:
            return _parsed(
                "named_period",
                match.group(0),
                label,
                "medium",
                named_period_label=label,
            )
    return None


def _is_composite(components: list[ParsedTiming]) -> bool:
    categories = {component.category for component in components}
    if len(categories) <= 1:
        return False
    return any(
        component.category in {"exact_date", "date_range", "duration", "month_only", "month_year", "relative_timing"}
        for component in components
    )


def _drop_subordinate_components(components: list[ParsedTiming]) -> list[ParsedTiming]:
    primary = _choose_primary(components)
    if primary.category not in {"exact_date", "date_range", "month_year", "duration"}:
        return components

    filtered = []
    for component in components:
        if component is primary:
            filtered.append(component)
            continue
        if component.category == "month_only" and component.raw_text in primary.raw_text:
            continue
        if component.category == "month_year" and component.raw_text in primary.raw_text:
            continue
        if component.category == "exact_date" and component.raw_text in primary.raw_text:
            continue
        if primary.category == "duration" and component.category == "named_period":
            if component.raw_text in primary.raw_text:
                continue
        filtered.append(component)
    return filtered


def _choose_primary(components: list[ParsedTiming]) -> ParsedTiming:
    order = {
        "date_range": 0,
        "exact_date": 1,
        "month_year": 2,
        "relative_timing": 3,
        "duration": 4,
        "month_only": 5,
        "season_period": 6,
        "named_period": 7,
        "unknown": 8,
        "composite_timing": 9,
    }
    return sorted(components, key=lambda component: order[component.category])[0]


def _build_composite(components: list[ParsedTiming]) -> ParsedTiming:
    primary = _choose_primary(components)
    duration = next((item for item in components if item.category == "duration"), None)
    month = next((item for item in components if item.category in {"month_year", "month_only"}), None)
    relative = next((item for item in components if item.category == "relative_timing"), None)
    warnings = [warning for item in components for warning in item.warnings]

    if primary.category == "date_range" and duration and duration.duration_days:
        expected_days = _range_day_difference(primary.start_date, primary.end_date)
        if expected_days is not None and expected_days != duration.duration_days:
            warnings.append("composite timing contains possible duration mismatch")
    elif len({item.category for item in components}) > 1:
        warnings.append("composite timing contains multiple timing signals")

    normalized_parts = []
    if primary.category in {"date_range", "exact_date"} and primary.normalized_text:
        normalized_parts.append(primary.normalized_text)
    if duration and duration.normalized_text:
        normalized_parts.append(duration.normalized_text)
    if relative and relative.normalized_text:
        normalized_parts.append(relative.normalized_text)
    elif month and month.normalized_text and primary.category not in {"date_range", "exact_date"}:
        normalized_parts.append(month.normalized_text)

    return _parsed(
        "composite_timing",
        _composite_raw_text(components),
        " ".join(dict.fromkeys(normalized_parts)),
        "high" if primary.category in {"date_range", "exact_date", "month_year"} else "medium",
        start_date=primary.start_date,
        end_date=primary.end_date,
        duration_days=duration.duration_days if duration else None,
        duration_nights=duration.duration_nights if duration else None,
        month=primary.month or (month.month if month else None),
        year=primary.year or (month.year if month else None),
        relative_label=relative.relative_label if relative else None,
        season_label=primary.season_label,
        named_period_label=primary.named_period_label,
        warnings=list(dict.fromkeys(warnings)),
    )


def _composite_raw_text(components: list[ParsedTiming]) -> str:
    ordered = sorted(components, key=lambda item: _normalize_input(item.raw_text))
    return ", ".join(dict.fromkeys(item.raw_text for item in ordered))


def _range_day_difference(start_date: str | None, end_date: str | None) -> int | None:
    if not start_date or not end_date:
        return None
    start_match = re.match(r"(?P<day>\d+)\s+", start_date)
    end_match = re.match(r"(?P<day>\d+)\s+", end_date)
    if not start_match or not end_match:
        return None
    start_day = int(start_match.group("day"))
    end_day = int(end_match.group("day"))
    if end_day < start_day:
        return None
    return end_day - start_day + 1
