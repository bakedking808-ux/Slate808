from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from contracts.calendar_review_contract import CalendarReview


class CalendarIntegrationReadiness(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    integration_ready: bool
    review_required: bool
    reason: str
    destination: str | None
    timing: str | None
    calendar_preference: str | None


def build_calendar_integration_readiness(
    review: CalendarReview,
) -> CalendarIntegrationReadiness:
    if review.action == "review_calendar" and review.review_required is not True:
        raise ValueError(
            "review.review_required must be True for review_calendar action"
        )

    if review.action == "none" and review.review_required is not False:
        raise ValueError(
            "review.review_required must be False for none action"
        )

    integration_ready = (
        review.review_required is True
        and review.ready is True
        and review.timing is not None
    )

    return CalendarIntegrationReadiness(
        integration_ready=integration_ready,
        review_required=review.review_required,
        reason=review.reason,
        destination=review.destination,
        timing=review.timing,
        calendar_preference=review.calendar_preference,
    )
