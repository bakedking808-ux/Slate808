from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from travel_brief_contract import TravelBrief


_TIMING_FRAGMENT_PATTERN = re.compile(
    r"\b("
    r"january|february|march|april|may|june|july|august|"
    r"september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec|"
    r"today|tomorrow|weekend|week|month|monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday|"
    r"\d{1,2}(?:st|nd|rd|th)?"
    r")\b",
    re.IGNORECASE,
)

_HIGH_PRECISION_TIMING_KEYS = frozenset({"exact_date", "date_range"})
_LOWER_PRECISION_TIMING_KEYS = frozenset({"weekend_trip", "flexible_timing"})


class ValidationViolation(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    field_name: str
    issue: str
    severity: Literal["warning", "error"]


class CrossFieldValidationResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    valid: bool
    violations: list[ValidationViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _destination_timing_contamination(
    brief: TravelBrief,
) -> list[ValidationViolation]:
    destination_value = brief.destination.value or ""
    if not destination_value:
        return []

    if not _TIMING_FRAGMENT_PATTERN.search(destination_value):
        return []

    return [
        ValidationViolation(
            field_name="destination",
            issue="Destination appears to contain timing-like fragments.",
            severity="warning",
        )
    ]


def _timing_readiness_violation(
    brief: TravelBrief,
) -> list[ValidationViolation]:
    if brief.timing.resolved:
        return []

    if not brief.is_minimum_ready and brief.clarification_needed:
        return []

    return [
        ValidationViolation(
            field_name="timing",
            issue="Timing is unresolved while downstream readiness is implied.",
            severity="error",
        )
    ]


def _timing_precision_conflict(
    brief: TravelBrief,
) -> list[ValidationViolation]:
    timing_keys = set(brief.timing.source_keys)
    if not timing_keys:
        return []

    if not (timing_keys & _HIGH_PRECISION_TIMING_KEYS):
        return []

    if not (timing_keys & _LOWER_PRECISION_TIMING_KEYS):
        return []

    return [
        ValidationViolation(
            field_name="timing",
            issue="Timing contains conflicting precision levels.",
            severity="error",
        )
    ]


def validate_travel_brief_cross_fields(
    brief: TravelBrief,
) -> CrossFieldValidationResult:
    violations = (
        _destination_timing_contamination(brief)
        + _timing_readiness_violation(brief)
        + _timing_precision_conflict(brief)
    )
    warnings = [
        violation.issue
        for violation in violations
        if violation.severity == "warning"
    ]
    valid = all(violation.severity != "error" for violation in violations)

    return CrossFieldValidationResult(
        valid=valid,
        violations=violations,
        warnings=warnings,
    )
