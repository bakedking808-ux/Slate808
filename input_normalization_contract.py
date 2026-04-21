from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field


class NormalizedInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    raw_input: str
    normalized_input: str
    applied_rules: list[str] = Field(default_factory=list)


_EXPLICIT_REPLACEMENTS = (
    (r"\btoamboseli\b", "to amboseli"),
    (r"\btoplan\b", "to plan"),
    (r"\bmakeit\b", "make it"),
    (r"\btravelplan\b", "travel plan"),
    (r"\bgroup of8\b", "group of 8"),
    (r"\bplana\b", "plan a"),
    (r"\bmasaimara\b", "masai mara"),
    (r"\bcoasta rico\b", "costa rica"),
    (r"\bolpejeta\b", "ol pejeta"),
)


def _apply_explicit_repairs(text: str, applied_rules: list[str]) -> str:
    cursor = 0
    parts: list[str] = []

    while cursor < len(text):
        earliest_match = None
        earliest_rule = None
        for pattern, replacement in _EXPLICIT_REPLACEMENTS:
            match = re.search(pattern, text[cursor:], flags=re.IGNORECASE)
            if match is None:
                continue
            start = cursor + match.start()
            end = cursor + match.end()
            if earliest_match is None or start < earliest_match[0]:
                earliest_match = (start, end)
                earliest_rule = (pattern, replacement)

        if earliest_match is None or earliest_rule is None:
            parts.append(text[cursor:])
            break

        start, end = earliest_match
        pattern, replacement = earliest_rule
        parts.append(text[cursor:start])
        parts.append(replacement)
        applied_rules.append(f"explicit_replacement:{pattern}->{replacement}")
        cursor = end

    return "".join(parts)


def _cleanup_punctuation_spacing(text: str, applied_rules: list[str]) -> str:
    cleaned = re.sub(r"\s*([,;:!?])\s*", r"\1 ", text)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    if cleaned != text:
        applied_rules.append("punctuation_spacing_cleanup")
    return cleaned


def _collapse_whitespace(text: str, applied_rules: list[str]) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if collapsed != text:
        applied_rules.append("whitespace_collapse")
    return collapsed


def normalize_travel_input(user_input: str) -> NormalizedInput:
    applied_rules: list[str] = []
    normalized = _apply_explicit_repairs(user_input, applied_rules)
    normalized = _cleanup_punctuation_spacing(normalized, applied_rules)
    normalized = _collapse_whitespace(normalized, applied_rules)
    return NormalizedInput(
        raw_input=user_input,
        normalized_input=normalized,
        applied_rules=applied_rules,
    )
