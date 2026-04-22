from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from contracts.calendar_action_contract import CalendarAction


class CalendarReview(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    review_required: bool
    action: Literal["none", "review_calendar"]
    reason: str
    destination: str | None
    timing: str | None
    calendar_preference: str | None
    ready: bool


def build_calendar_review(action: CalendarAction) -> CalendarReview:
    review_required = action.action == "review_calendar"

    return CalendarReview(
        review_required=review_required,
        action=action.action,
        reason=action.reason,
        destination=action.destination,
        timing=action.timing,
        calendar_preference=action.calendar_preference,
        ready=action.ready,
    )
