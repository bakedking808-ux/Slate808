from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from contracts.calendar_input_contract import CalendarRequest
from contracts.calendar_policy_contract import CalendarDecision


class CalendarAction(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    action: Literal["none", "review_calendar"]
    reason: str
    destination: str | None
    timing: str | None
    calendar_preference: str | None
    ready: bool


def build_calendar_action(
    decision: CalendarDecision,
    request: CalendarRequest | None,
) -> CalendarAction:
    if request is None:
        return CalendarAction(
            action="none",
            reason="Calendar request is not available.",
            destination=None,
            timing=None,
            calendar_preference=None,
            ready=False,
        )

    if (
        decision.action == "calendar_review_required"
        and request.ready_for_calendar is not True
    ):
        raise ValueError(
            "request.ready_for_calendar must be True for calendar review"
        )

    if decision.action == "calendar_review_required":
        return CalendarAction(
            action="review_calendar",
            reason=decision.reason,
            destination=request.destination,
            timing=request.timing,
            calendar_preference=request.calendar,
            ready=True,
        )

    return CalendarAction(
        action="none",
        reason=decision.reason,
        destination=request.destination,
        timing=request.timing,
        calendar_preference=request.calendar,
        ready=request.ready_for_calendar,
    )
