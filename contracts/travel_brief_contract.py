from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from contracts.extractor_contract import ExtractionResult
from contracts.priority_resolution_contract import resolve_field_priorities


BRIEF_FAMILIES = (
    "destination",
    "traveller",
    "timing",
    "budget",
    "intent",
    "activity",
    "transport",
    "accommodation",
    "constraints",
    "calendar",
)


class TravelBriefField(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    family: str
    value: str | None
    source_keys: list[str] = Field(default_factory=list)
    resolved: bool


class TravelBrief(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    destination: TravelBriefField
    traveller: TravelBriefField
    timing: TravelBriefField
    budget: TravelBriefField
    intent: TravelBriefField
    activity: TravelBriefField
    transport: TravelBriefField
    accommodation: TravelBriefField
    constraints: TravelBriefField
    calendar: TravelBriefField
    missing_fields: list[str] = Field(default_factory=list)
    clarification_needed: bool = False
    is_minimum_ready: bool = False

    def resolved_families(self) -> list[str]:
        return [
            field.family
            for field in (
                self.destination,
                self.traveller,
                self.timing,
                self.budget,
                self.intent,
                self.activity,
                self.transport,
                self.accommodation,
                self.constraints,
                self.calendar,
            )
            if field.resolved
        ]


def _build_family_field(
    family: str,
    extraction_result: ExtractionResult,
    resolved_value: str | int | None,
) -> TravelBriefField:
    # Source key order follows ExtractionResult.signals encounter order
    # and is intentionally preserved as part of the deterministic contract.
    source_keys = [
        signal.key
        for signal in extraction_result.signals
        if signal.family == family
    ]
    resolved = bool(source_keys)

    return TravelBriefField(
        family=family,
        value=resolved_value if isinstance(resolved_value, str) else None,
        source_keys=source_keys,
        resolved=resolved,
    )


def build_travel_brief(extraction_result: ExtractionResult) -> TravelBrief:
    resolution = resolve_field_priorities(
        {
            family: [
                {
                    "value": ", ".join(
                        signal.key
                        for signal in extraction_result.signals
                        if signal.family == family
                    ),
                    "source": "explicit_user_input",
                    "precision": len(
                        [
                            signal
                            for signal in extraction_result.signals
                            if signal.family == family
                        ]
                    ),
                }
            ]
            for family in BRIEF_FAMILIES
            if any(signal.family == family for signal in extraction_result.signals)
        }
    )
    resolved_values = {
        field.field_name: field.value
        for field in resolution.resolved_fields
    }
    family_fields = {
        family: _build_family_field(
            family,
            extraction_result,
            resolved_values.get(family),
        )
        for family in BRIEF_FAMILIES
    }

    return TravelBrief(
        destination=family_fields["destination"],
        traveller=family_fields["traveller"],
        timing=family_fields["timing"],
        budget=family_fields["budget"],
        intent=family_fields["intent"],
        activity=family_fields["activity"],
        transport=family_fields["transport"],
        accommodation=family_fields["accommodation"],
        constraints=family_fields["constraints"],
        calendar=family_fields["calendar"],
        missing_fields=list(extraction_result.missing_fields),
        clarification_needed=extraction_result.clarification_needed,
        is_minimum_ready=not extraction_result.clarification_needed,
    )
