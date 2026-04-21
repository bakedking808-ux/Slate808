from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from itinerary_input_contract import ItineraryRequest


OPTIONAL_FIELD_ORDER = (
    "budget",
    "intent",
    "activity",
    "transport",
    "accommodation",
    "constraints",
    "calendar",
)

ASSUMPTION_BY_FIELD = {
    "budget": "Budget not yet specified.",
    "intent": "Trip intent not yet specified.",
    "activity": "Activity preference not yet specified.",
    "transport": "Transport preference not yet specified.",
    "accommodation": "Accommodation preference not yet specified.",
    "constraints": "Constraints not yet specified.",
    "calendar": "Calendar preference not yet specified.",
}


class ItineraryStep(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    order: int
    title: str
    detail: str


class ItineraryPlan(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    title: str
    destination: str
    traveller: str
    timing: str
    steps: list[ItineraryStep] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    missing_optional_fields: list[str] = Field(default_factory=list)


def _build_optional_summary(request: ItineraryRequest) -> str:
    return (
        "Optional preferences: "
        f"budget={request.budget or 'not specified'}; "
        f"intent={request.intent or 'not specified'}; "
        f"activity={request.activity or 'not specified'}; "
        f"transport={request.transport or 'not specified'}; "
        f"accommodation={request.accommodation or 'not specified'}; "
        f"constraints={request.constraints or 'not specified'}; "
        f"calendar={request.calendar or 'not specified'}"
    )


def _collect_missing_optional_fields(request: ItineraryRequest) -> list[str]:
    missing_fields: list[str] = []
    for field in OPTIONAL_FIELD_ORDER:
        if getattr(request, field) is None:
            missing_fields.append(field)
    return missing_fields


def build_itinerary_plan(request: ItineraryRequest) -> ItineraryPlan:
    """Builds a deterministic 5-step itinerary skeleton from a validated ItineraryRequest."""
    if request.ready is not True:
        raise ValueError("request.ready must be True when building itinerary plan")

    missing_optional_fields = _collect_missing_optional_fields(request)
    assumptions = [
        ASSUMPTION_BY_FIELD[field]
        for field in missing_optional_fields
    ]

    return ItineraryPlan(
        title=f"Trip Plan: {request.destination}",
        destination=request.destination,
        traveller=request.traveller,
        timing=request.timing,
        steps=[
            ItineraryStep(
                order=1,
                title="Confirm destination and trip scope",
                detail=f"Destination selection: {request.destination}",
            ),
            ItineraryStep(
                order=2,
                title="Confirm traveller setup",
                detail=f"Traveller setup: {request.traveller}",
            ),
            ItineraryStep(
                order=3,
                title="Confirm timing and schedule window",
                detail=f"Timing window: {request.timing}",
            ),
            ItineraryStep(
                order=4,
                title="Review optional preferences",
                detail=_build_optional_summary(request),
            ),
            ItineraryStep(
                order=5,
                title="Prepare execution-ready itinerary",
                detail=(
                    "Execution-ready itinerary can be prepared from the "
                    "resolved minimum planning fields."
                ),
            ),
        ],
        assumptions=assumptions,
        missing_optional_fields=missing_optional_fields,
    )
