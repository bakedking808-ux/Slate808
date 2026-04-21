from calendar_integration_readiness_contract import (
    build_calendar_integration_readiness,
)
from calendar_review_contract import CalendarReview
import pytest


def test_returns_not_ready_when_review_is_not_required():
    review = CalendarReview(
        review_required=False,
        action="none",
        reason="No calendar review is required.",
        destination="destination_fixed",
        timing="weekend_trip",
        calendar_preference=None,
        ready=True,
    )

    readiness = build_calendar_integration_readiness(review)

    assert readiness.integration_ready is False
    assert readiness.review_required is False
    assert readiness.reason == "No calendar review is required."
    assert readiness.destination == "destination_fixed"
    assert readiness.timing == "weekend_trip"
    assert readiness.calendar_preference is None


def test_returns_ready_when_review_is_required_and_ready():
    review = CalendarReview(
        review_required=True,
        action="review_calendar",
        reason="Calendar review is required by the resolved calendar preference.",
        destination="destination_fixed",
        timing="weekend_trip",
        calendar_preference="calendar_check_required",
        ready=True,
    )

    readiness = build_calendar_integration_readiness(review)

    assert readiness.integration_ready is True
    assert readiness.review_required is True
    assert readiness.reason == "Calendar review is required by the resolved calendar preference."
    assert readiness.destination == "destination_fixed"
    assert readiness.timing == "weekend_trip"
    assert readiness.calendar_preference == "calendar_check_required"


def test_returns_not_ready_when_review_is_required_but_not_ready():
    review = CalendarReview(
        review_required=True,
        action="review_calendar",
        reason="Calendar review is required by the resolved calendar preference.",
        destination="destination_fixed",
        timing="weekend_trip",
        calendar_preference="calendar_check_required",
        ready=False,
    )

    readiness = build_calendar_integration_readiness(review)

    assert readiness.integration_ready is False
    assert readiness.review_required is True
    assert readiness.reason == "Calendar review is required by the resolved calendar preference."
    assert readiness.destination == "destination_fixed"
    assert readiness.timing == "weekend_trip"
    assert readiness.calendar_preference == "calendar_check_required"


def test_returns_not_ready_when_review_is_required_but_timing_is_missing():
    review = CalendarReview(
        review_required=True,
        action="review_calendar",
        reason="Calendar review is required by the resolved calendar preference.",
        destination="destination_fixed",
        timing=None,
        calendar_preference="calendar_check_required",
        ready=True,
    )

    readiness = build_calendar_integration_readiness(review)

    assert readiness.integration_ready is False
    assert readiness.review_required is True
    assert readiness.reason == "Calendar review is required by the resolved calendar preference."
    assert readiness.destination == "destination_fixed"
    assert readiness.timing is None
    assert readiness.calendar_preference == "calendar_check_required"


def test_repeated_call_determinism():
    review = CalendarReview(
        review_required=True,
        action="review_calendar",
        reason="Calendar review is required by the resolved calendar preference.",
        destination="destination_fixed",
        timing="weekend_trip",
        calendar_preference="calendar_check_required",
        ready=True,
    )

    first = build_calendar_integration_readiness(review)
    second = build_calendar_integration_readiness(review)

    assert first.model_dump() == second.model_dump()


def test_fails_loudly_when_review_action_requires_review_but_flag_is_false():
    review = CalendarReview(
        review_required=False,
        action="review_calendar",
        reason="Calendar review is required by the resolved calendar preference.",
        destination="destination_fixed",
        timing="weekend_trip",
        calendar_preference="calendar_check_required",
        ready=True,
    )

    with pytest.raises(
        ValueError,
        match="review.review_required must be True for review_calendar action",
    ):
        build_calendar_integration_readiness(review)


def test_fails_loudly_when_none_action_has_review_required_true():
    review = CalendarReview(
        review_required=True,
        action="none",
        reason="No calendar review is required.",
        destination="destination_fixed",
        timing="weekend_trip",
        calendar_preference=None,
        ready=True,
    )

    with pytest.raises(
        ValueError,
        match="review.review_required must be False for none action",
    ):
        build_calendar_integration_readiness(review)
