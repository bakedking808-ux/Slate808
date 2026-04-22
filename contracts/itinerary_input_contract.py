from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from contracts.clarification_contract import ClarificationResponse
from planning_policy import PlanningDecision
from contracts.travel_brief_contract import TravelBrief


class ItineraryRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    destination: str
    traveller: str
    timing: str
    budget: str | None
    intent: str | None
    activity: str | None
    transport: str | None
    accommodation: str | None
    constraints: str | None
    calendar: str | None
    ready: bool


def build_itinerary_request(
    brief: TravelBrief,
    decision: PlanningDecision,
    clarification: ClarificationResponse,
) -> ItineraryRequest | None:
    # Contract invariant: if an ItineraryRequest is returned, it is always ready.
    # If the system is not ready, this function must return None.
    if decision.action != "proceed":
        return None

    if clarification.safe_to_proceed is False:
        return None

    if brief.is_minimum_ready is False:
        return None

    if brief.destination.value is None:
        raise ValueError("destination.value must be present when building itinerary")

    if brief.traveller.value is None:
        raise ValueError("traveller.value must be present when building itinerary")

    if brief.timing.value is None:
        raise ValueError("timing.value must be present when building itinerary")

    return ItineraryRequest(
        destination=brief.destination.value,
        traveller=brief.traveller.value,
        timing=brief.timing.value,
        budget=brief.budget.value,
        intent=brief.intent.value,
        activity=brief.activity.value,
        transport=brief.transport.value,
        accommodation=brief.accommodation.value,
        constraints=brief.constraints.value,
        calendar=brief.calendar.value,
        ready=True,
    )
