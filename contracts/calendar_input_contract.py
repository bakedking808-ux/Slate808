from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from contracts.itinerary_input_contract import ItineraryRequest
from contracts.travel_brief_contract import TravelBrief


CALENDAR_CHECK_KEYS = (
    "calendar_check_required",
    "schedule_conflict_check",
    "best_time_suggestion",
)


class CalendarRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    timing: str
    calendar: str | None
    destination: str
    ready_for_calendar: bool
    calendar_check_required: bool


def build_calendar_request(
    brief: TravelBrief,
    request: ItineraryRequest | None,
) -> CalendarRequest | None:
    if request is None:
        return None

    if brief.timing.resolved is False:
        return None

    calendar_value = brief.calendar.value
    calendar_check_required = False

    if calendar_value is not None:
        for key in CALENDAR_CHECK_KEYS:
            if key in calendar_value:
                calendar_check_required = True
                break

    return CalendarRequest(
        timing=request.timing,
        calendar=calendar_value,
        destination=request.destination,
        ready_for_calendar=True,
        calendar_check_required=calendar_check_required,
    )
