from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


OperatorSignalType = Literal[
    "intent_declaration",
    "information_correction",
    "information_supply",
    "clarification_request",
    "meta_instruction",
    "goal_shift",
    "completion_signal",
    "unknown",
]
OperatorConfidence = Literal["low", "medium", "high"]


class OperatorSignal(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    signal_type: OperatorSignalType
    raw_text: str
    normalized_text: str
    confidence: OperatorConfidence


class OperatorFlowResult(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    matched: bool
    signal: OperatorSignal | None = None
    warnings: list[str] = Field(default_factory=list)


def classify_operator_flow(user_input: str) -> OperatorFlowResult:
    normalized = _normalize(user_input)
    if not normalized:
        return _unknown(user_input, normalized)

    for signal_type, confidence, patterns in _CLASSIFICATION_RULES:
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns):
            return OperatorFlowResult(
                matched=True,
                signal=OperatorSignal(
                    signal_type=signal_type,
                    raw_text=user_input,
                    normalized_text=normalized,
                    confidence=confidence,
                ),
                warnings=[],
            )

    return _unknown(user_input, normalized)


def _normalize(user_input: str) -> str:
    return re.sub(r"\s+", " ", user_input.strip())


def _unknown(raw_text: str, normalized_text: str) -> OperatorFlowResult:
    return OperatorFlowResult(
        matched=False,
        signal=OperatorSignal(
            signal_type="unknown",
            raw_text=raw_text,
            normalized_text=normalized_text,
            confidence="low",
        ),
        warnings=[],
    )


_CLASSIFICATION_RULES: tuple[
    tuple[OperatorSignalType, OperatorConfidence, tuple[str, ...]],
    ...,
] = (
    (
        "meta_instruction",
        "high",
        (
            r"\bignore\s+(?:the\s+)?(?:earlier|previous|old)\b",
            r"\bcontinue\s+from\s+where\s+we\s+left\s+off\b",
            r"\bstart\s+over\b",
            r"\brestart\b",
            r"\buse\s+(?:the\s+)?(?:earlier|previous)\s+\w+\b",
        ),
    ),
    (
        "information_correction",
        "high",
        (
            r"\bactually\b.*\b(?:make|change|set|switch)\s+it\b",
            r"\bchange\s+it\s+to\b",
            r"\bmake\s+it\s+for\b",
            r"\bno,\s*not\s+that\b",
            r"\bi\s+meant\b",
            r"\bnot\s+[a-z][a-z\s'-]+,\s*[a-z][a-z\s'-]+\b",
        ),
    ),
    (
        "goal_shift",
        "high",
        (
            r"\b(?:let'?s|lets)\s+switch\s+to\b",
            r"\bswitch\s+to\s+(?:a\s+)?\w+",
            r"\bmake\s+it\s+(?:a\s+)?(?:safari|beach|luxury|quiet|relaxing|romantic|adventure)\b",
            r"\bchange\s+it\s+to\s+(?:a\s+)?(?:safari|beach|luxury|quiet|relaxing|romantic|adventure)\b",
            r"\bactually,\s*i\s+want\s+(?:a\s+)?(?:quiet|relaxing|luxury|beach|safari)\b",
        ),
    ),
    (
        "clarification_request",
        "high",
        (
            r"\bwhat\s+options\s+do\s+i\s+have\b",
            r"\bcan\s+you\s+suggest\b",
            r"\bsuggest\s+destinations\b",
            r"\bwhat\s+do\s+you\s+mean\b",
        ),
    ),
    (
        "completion_signal",
        "high",
        (
            r"\bthat\s+looks\s+good\b",
            r"\bthis\s+works\b",
            r"\bokay,\s*proceed\b",
            r"\bperfect\b",
        ),
    ),
    (
        "intent_declaration",
        "high",
        (
            r"\bplan\s+a\s+trip\s+for\s+me\b",
            r"\bi\s+want\s+(?:a\s+)?(?:getaway|holiday|trip)\b",
            r"\bhelp\s+me\s+plan\s+(?:a\s+)?(?:holiday|trip|getaway)\b",
        ),
    ),
    (
        "information_supply",
        "medium",
        (
            r"\bnext\s+month\s+works\s+for\s+me\b",
            r"^\d+\s+(?:people|persons|travellers|travelers)\.?$",
            r"^\d+\.?$",
            r"\bhigh\s+budget\b",
            r"\blow\s+budget\b",
            r"\bsomething\s+affordable\b",
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+\s+to\s+\d{1,2}(?:st|nd|rd|th)?\s+[a-z]+\b",
            r"^(?:luxury|relaxing|romantic|adventure|family)$",
        ),
    ),
)
