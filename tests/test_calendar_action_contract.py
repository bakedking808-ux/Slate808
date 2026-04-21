from calendar_action_contract import build_calendar_action
from calendar_input_contract import CalendarRequest
from calendar_policy_contract import CalendarDecision
import pytest


def test_returns_none_action_when_request_is_none():
    decision = CalendarDecision(
        action="no_calendar_action",
        reason="Calendar request is not available.",
        calendar_check_required=False,
        ready_for_calendar=False,
    )

    action = build_calendar_action(decision, None)

    assert action.action == "none"
    assert action.reason == "Calendar request is not available."
    assert action.destination is None
    assert action.timing is None
    assert action.calendar_preference is None
    assert action.ready is False


def test_returns_none_action_when_no_calendar_action_is_required():
    decision = CalendarDecision(
        action="no_calendar_action",
        reason="No calendar review is required.",
        calendar_check_required=False,
        ready_for_calendar=True,
    )
    request = CalendarRequest(
        timing="weekend_trip",
        calendar=None,
        destination="destination_fixed",
        ready_for_calendar=True,
        calendar_check_required=False,
    )

    action = build_calendar_action(decision, request)

    assert action.action == "none"
    assert action.reason == "No calendar review is required."
    assert action.destination == "destination_fixed"
    assert action.timing == "weekend_trip"
    assert action.calendar_preference is None
    assert action.ready is True


def test_returns_review_calendar_action_when_calendar_review_is_required():
    decision = CalendarDecision(
        action="calendar_review_required",
        reason="Calendar review is required by the resolved calendar preference.",
        calendar_check_required=True,
        ready_for_calendar=True,
    )
    request = CalendarRequest(
        timing="weekend_trip",
        calendar="calendar_check_required",
        destination="destination_fixed",
        ready_for_calendar=True,
        calendar_check_required=True,
    )

    action = build_calendar_action(decision, request)

    assert action.action == "review_calendar"
    assert action.reason == "Calendar review is required by the resolved calendar preference."
    assert action.destination == "destination_fixed"
    assert action.timing == "weekend_trip"
    assert action.calendar_preference == "calendar_check_required"
    assert action.ready is True


def test_repeated_call_determinism():
    decision = CalendarDecision(
        action="calendar_review_required",
        reason="Calendar review is required by the resolved calendar preference.",
        calendar_check_required=True,
        ready_for_calendar=True,
    )
    request = CalendarRequest(
        timing="weekend_trip",
        calendar="calendar_check_required",
        destination="destination_fixed",
        ready_for_calendar=True,
        calendar_check_required=True,
    )

    first = build_calendar_action(decision, request)
    second = build_calendar_action(decision, request)

    assert first.model_dump() == second.model_dump()


def test_fails_loudly_when_calendar_review_is_requested_but_request_is_not_ready():
    decision = CalendarDecision(
        action="calendar_review_required",
        reason="Calendar review is required by the resolved calendar preference.",
        calendar_check_required=True,
        ready_for_calendar=True,
    )
    request = CalendarRequest(
        timing="weekend_trip",
        calendar="calendar_check_required",
        destination="destination_fixed",
        ready_for_calendar=False,
        calendar_check_required=True,
    )

    with pytest.raises(ValueError, match="request.ready_for_calendar must be True"):
        build_calendar_action(decision, request)
