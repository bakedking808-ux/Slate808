from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from contracts.input_normalization_contract import normalize_travel_input
from slate808_catalogue import CatalogueItem, FULL_CATALOGUE


REQUIRED_FAMILIES = ("destination", "traveller", "timing")


class ExtractedSignal(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    key: str
    family: str
    matched_text: str
    match_source: str


class ExtractionResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    matched_keys: list[str] = Field(default_factory=list)
    signals: list[ExtractedSignal] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    unresolved_tokens: list[str] = Field(default_factory=list)
    clarification_needed: bool = False


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    without_punctuation = re.sub(r"[^\w\s]", " ", lowered)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def _find_catalogue_match(
    normalized_input: str,
    item: CatalogueItem,
) -> tuple[str, str] | None:
    for example_input in item.example_inputs:
        if not example_input:
            continue

        normalized_example = _normalize_text(example_input)
        if not normalized_example:
            continue

        if normalized_example in normalized_input:
            return normalized_example, "exact_phrase"

    return None


def _collect_unresolved_tokens(
    normalized_input: str,
    matched_phrases: list[str],
) -> list[str]:
    remaining_text = normalized_input
    for phrase in matched_phrases:
        remaining_text = remaining_text.replace(phrase, " ")

    normalized_remaining = re.sub(r"\s+", " ", remaining_text).strip()
    if not normalized_remaining:
        return []

    return normalized_remaining.split(" ")


def extract_catalogue_signals(user_input: str) -> ExtractionResult:
    intake = normalize_travel_input(user_input)
    normalized_input = _normalize_text(intake.normalized_input)
    matched_keys: list[str] = []
    signals: list[ExtractedSignal] = []
    matched_phrases: list[str] = []
    seen_keys: set[str] = set()
    matched_families: set[str] = set()

    for item in FULL_CATALOGUE:
        match = _find_catalogue_match(normalized_input, item)
        if match is None or item.key in seen_keys:
            continue

        matched_text, match_source = match
        matched_keys.append(item.key)
        signals.append(
            ExtractedSignal(
                key=item.key,
                family=item.family,
                matched_text=matched_text,
                match_source=match_source,
            )
        )
        matched_phrases.append(matched_text)
        matched_families.add(item.family)
        seen_keys.add(item.key)

    missing_fields = [
        family
        for family in REQUIRED_FAMILIES
        if family not in matched_families
    ]

    return ExtractionResult(
        matched_keys=matched_keys,
        signals=signals,
        missing_fields=missing_fields,
        unresolved_tokens=_collect_unresolved_tokens(normalized_input, matched_phrases),
        clarification_needed=bool(missing_fields),
    )
