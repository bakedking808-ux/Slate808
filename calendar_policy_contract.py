from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from calendar_input_contract import CalendarRequest


class CalendarDecision(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    action: Literal["no_calendar_action", "calendar_review_required"]
    reason: str
    calendar_check_required: bool
    ready_for_calendar: bool


def evaluate_calendar_request(request: CalendarRequest | None) -> CalendarDecision:
    if request is None:
        return CalendarDecision(
            action="no_calendar_action",
            reason="Calendar request is not available.",
            calendar_check_required=False,
            ready_for_calendar=False,
        )

    if request.ready_for_calendar is False:
        return CalendarDecision(
            action="no_calendar_action",
            reason="Calendar request is not ready.",
            calendar_check_required=False,
            ready_for_calendar=False,
        )

    if request.calendar_check_required is True:
        return CalendarDecision(
            action="calendar_review_required",
            reason="Calendar review is required by the resolved calendar preference.",
            calendar_check_required=True,
            ready_for_calendar=True,
        )

    return CalendarDecision(
        action="no_calendar_action",
        reason="No calendar review is required.",
        calendar_check_required=False,
        ready_for_calendar=True,
    )
