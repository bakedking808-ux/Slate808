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
_MONTH_NAMES = (
    "january|february|march|april|may|june|july|august|"
    "september|october|november|december|"
    "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
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


def _normalize_traveller_phrases(text: str, applied_rules: list[str]) -> str:
    normalized = text
    replacements = (
        (r"\bjust me and my sister\b", "2 people"),
        (r"\bme,\s*my partner,\s*and our son\b", "3 people"),
        (r"\bme and my partner and our son\b", "3 people"),
        (r"\bjust me\b", "for 1 person"),
        (r"\bme and my partner\b", "2 people"),
        (r"\btwo adults and one teen\b", "3 people"),
        (r"\btwo adults and a child\b", "3 people"),
        (r"\b2 adults and a child\b", "3 people"),
    )

    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        if updated != normalized:
            applied_rules.append(f"traveller_phrase_normalization:{pattern}->{replacement}")
            normalized = updated

    updated = re.sub(r"\bfamily of (\d+)\b", r"group of \1", normalized, flags=re.IGNORECASE)
    if updated != normalized:
        applied_rules.append("traveller_phrase_normalization:family_of->group_of")
        normalized = updated

    return normalized


def _normalize_date_range_variants(text: str, applied_rules: list[str]) -> str:
    normalized = text

    updated = normalized.replace("–", "-").replace("—", "-")
    if updated != normalized:
        applied_rules.append("date_range_separator_normalization")
        normalized = updated

    updated = re.sub(
        rf"(\d{{1,2}}(?:st|nd|rd|th)?)(?=({_MONTH_NAMES})\b)",
        r"\1 ",
        normalized,
        flags=re.IGNORECASE,
    )
    if updated != normalized:
        applied_rules.append("date_token_spacing_normalization")
        normalized = updated

    return normalized


def _normalize_punctuation_noise(text: str, applied_rules: list[str]) -> str:
    normalized = text

    updated = re.sub(r"\.{2,}", ", ", normalized)
    updated = re.sub(r",{2,}", ", ", updated)
    updated = re.sub(r"(?<=\D)\s*-\s*(?=\d)", " - ", updated)
    updated = re.sub(r"(?<=\d)\s*-\s*(?=\D)", " - ", updated)
    updated = re.sub(r",\s*,\s*", ", ", updated)
    if updated != normalized:
        applied_rules.append("punctuation_noise_normalization")
        normalized = updated

    return normalized


def _normalize_conversational_fragments(text: str, applied_rules: list[str]) -> str:
    normalized = text
    updated = normalized

    while True:
        candidate = re.sub(
            r"^\s*(?:uhh|uh|umm|um|hmm|idk)(?:[,\s]+|$)",
            "",
            updated,
            flags=re.IGNORECASE,
        )
        candidate = re.sub(
            r"^\s*maybe(?:(?:\s*,)|(?:\s+\.\.\.)|(?:\s+)|(?:,\s+)|(?:\.\.\.\s+))",
            "",
            candidate,
            flags=re.IGNORECASE,
        )
        if candidate == updated:
            break
        updated = candidate

    if updated != normalized:
        applied_rules.append("conversational_fragment_normalization")
        normalized = updated

    return normalized


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
    normalized = _normalize_traveller_phrases(normalized, applied_rules)
    normalized = _normalize_date_range_variants(normalized, applied_rules)
    normalized = _normalize_punctuation_noise(normalized, applied_rules)
    normalized = _normalize_conversational_fragments(normalized, applied_rules)
    normalized = _cleanup_punctuation_spacing(normalized, applied_rules)
    normalized = _collapse_whitespace(normalized, applied_rules)
    return NormalizedInput(
        raw_input=user_input,
        normalized_input=normalized,
        applied_rules=applied_rules,
    )
