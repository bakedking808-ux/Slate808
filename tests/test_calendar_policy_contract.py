from calendar_input_contract import CalendarRequest
from calendar_policy_contract import evaluate_calendar_request


def test_returns_no_action_when_request_is_none():
    decision = evaluate_calendar_request(None)

    assert decision.action == "no_calendar_action"
    assert decision.reason == "Calendar request is not available."
    assert decision.calendar_check_required is False
    assert decision.ready_for_calendar is False


def test_returns_no_action_when_request_is_not_ready():
    request = CalendarRequest(
        timing="weekend_trip",
        calendar=None,
        destination="destination_fixed",
        ready_for_calendar=False,
        calendar_check_required=False,
    )

    decision = evaluate_calendar_request(request)

    assert decision.action == "no_calendar_action"
    assert decision.reason == "Calendar request is not ready."
    assert decision.calendar_check_required is False
    assert decision.ready_for_calendar is False


def test_returns_no_action_when_request_is_ready_without_calendar_check():
    request = CalendarRequest(
        timing="weekend_trip",
        calendar=None,
        destination="destination_fixed",
        ready_for_calendar=True,
        calendar_check_required=False,
    )

    decision = evaluate_calendar_request(request)

    assert decision.action == "no_calendar_action"
    assert decision.reason == "No calendar review is required."
    assert decision.calendar_check_required is False
    assert decision.ready_for_calendar is True


def test_returns_calendar_review_when_request_requires_calendar_check():
    request = CalendarRequest(
        timing="weekend_trip",
        calendar="calendar_check_required",
        destination="destination_fixed",
        ready_for_calendar=True,
        calendar_check_required=True,
    )

    decision = evaluate_calendar_request(request)

    assert decision.action == "calendar_review_required"
    assert decision.reason == "Calendar review is required by the resolved calendar preference."
    assert decision.calendar_check_required is True
    assert decision.ready_for_calendar is True


def test_repeated_call_determinism():
    request = CalendarRequest(
        timing="weekend_trip",
        calendar="calendar_check_required",
        destination="destination_fixed",
        ready_for_calendar=True,
        calendar_check_required=True,
    )

    first = evaluate_calendar_request(request)
    second = evaluate_calendar_request(request)

    assert first.model_dump() == second.model_dump()
