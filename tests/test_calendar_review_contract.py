from contracts.calendar_action_contract import CalendarAction
from contracts.calendar_review_contract import build_calendar_review


def test_builds_review_payload_for_none_action():
    action = CalendarAction(
        action="none",
        reason="No calendar review is required.",
        destination="destination_fixed",
        timing="weekend_trip",
        calendar_preference=None,
        ready=True,
    )

    review = build_calendar_review(action)

    assert review.review_required is False
    assert review.action == "none"
    assert review.reason == "No calendar review is required."
    assert review.destination == "destination_fixed"
    assert review.timing == "weekend_trip"
    assert review.calendar_preference is None
    assert review.ready is True


def test_builds_review_payload_for_review_calendar_action():
    action = CalendarAction(
        action="review_calendar",
        reason="Calendar review is required by the resolved calendar preference.",
        destination="destination_fixed",
        timing="weekend_trip",
        calendar_preference="calendar_check_required",
        ready=True,
    )

    review = build_calendar_review(action)

    assert review.review_required is True
    assert review.action == "review_calendar"
    assert review.reason == "Calendar review is required by the resolved calendar preference."
    assert review.destination == "destination_fixed"
    assert review.timing == "weekend_trip"
    assert review.calendar_preference == "calendar_check_required"
    assert review.ready is True


def test_repeated_call_determinism():
    action = CalendarAction(
        action="review_calendar",
        reason="Calendar review is required by the resolved calendar preference.",
        destination="destination_fixed",
        timing="weekend_trip",
        calendar_preference="calendar_check_required",
        ready=True,
    )

    first = build_calendar_review(action)
    second = build_calendar_review(action)

    assert first.model_dump() == second.model_dump()
