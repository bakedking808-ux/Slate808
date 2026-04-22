from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from contracts.cross_field_validation_contract import validate_travel_brief_cross_fields
from contracts.travel_brief_contract import TravelBrief


MISSING_FIELD_PRIORITY = (
    "destination",
    "traveller",
    "timing",
)

QUESTION_BY_FIELD = {
    "destination": "Where would you like to go?",
    "traveller": "How many people are travelling?",
    "timing": "When are you planning to travel?",
}
FALLBACK_QUESTION = "What trip detail should I clarify next?"


class PlanningDecision(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    action: Literal["proceed", "clarify"]
    reason: str
    missing_fields: list[str] = Field(default_factory=list)
    next_question: str | None


def _select_first_missing_field(missing_fields: list[str]) -> str | None:
    missing_field_set = set(missing_fields)
    for field in MISSING_FIELD_PRIORITY:
        if field in missing_field_set:
            return field
    return missing_fields[0] if missing_fields else None


def evaluate_travel_brief(brief: TravelBrief) -> PlanningDecision:
    validation = validate_travel_brief_cross_fields(brief)
    if validation.valid is False:
        invalid_fields = [
            violation.field_name
            for violation in validation.violations
            if violation.severity == "error"
        ]
        first_invalid_field = _select_first_missing_field(invalid_fields)
        issues = [
            violation.issue
            for violation in validation.violations
            if violation.severity == "error"
        ]
        return PlanningDecision(
            action="clarify",
            reason="Cross-field validation failed: " + "; ".join(issues),
            missing_fields=invalid_fields,
            next_question=QUESTION_BY_FIELD.get(
                first_invalid_field,
                FALLBACK_QUESTION,
            ),
        )

    if brief.clarification_needed:
        first_missing_field = _select_first_missing_field(brief.missing_fields)
        return PlanningDecision(
            action="clarify",
            reason="Minimum required planning fields are missing.",
            missing_fields=list(brief.missing_fields),
            next_question=QUESTION_BY_FIELD.get(
                first_missing_field,
                FALLBACK_QUESTION,
            ),
        )

    return PlanningDecision(
        action="proceed",
        reason="Minimum required planning fields are resolved.",
        missing_fields=list(brief.missing_fields),
        next_question=None,
    )
