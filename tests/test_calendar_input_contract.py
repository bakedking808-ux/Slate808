from contracts.calendar_input_contract import build_calendar_request
from contracts.clarification_contract import build_clarification_response
from contracts.extractor_contract import extract_catalogue_signals
from contracts.itinerary_input_contract import build_itinerary_request
from planning_policy import evaluate_travel_brief
from contracts.travel_brief_contract import build_travel_brief


def _build_inputs(user_input: str):
    extraction_result = extract_catalogue_signals(user_input)
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)
    request = build_itinerary_request(brief, decision, clarification)
    return brief, request


def test_request_builds_when_timing_exists_and_itinerary_request_exists():
    brief, request = _build_inputs(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )

    calendar_request = build_calendar_request(brief, request)

    assert calendar_request is not None
    assert calendar_request.timing == "weekend_trip"
    assert calendar_request.destination == "destination_fixed"
    assert calendar_request.ready_for_calendar is True
    assert calendar_request.calendar_check_required is False


def test_returns_none_when_itinerary_request_is_none():
    brief = build_travel_brief(extract_catalogue_signals("Need a driver next weekend"))

    calendar_request = build_calendar_request(brief, None)

    assert calendar_request is None


def test_returns_none_when_timing_is_unresolved():
    brief, request = _build_inputs("Plan a trip to Naivasha for 2 adults and 3 kids")

    calendar_request = build_calendar_request(brief, request)

    assert calendar_request is None


def test_calendar_check_required_becomes_true_for_supported_calendar_keys():
    brief, request = _build_inputs(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend check my schedule"
    )

    calendar_request = build_calendar_request(brief, request)

    assert calendar_request is not None
    assert calendar_request.calendar == "calendar_check_required"
    assert calendar_request.calendar_check_required is True


def test_repeated_call_stability():
    brief, request = _build_inputs(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )

    first = build_calendar_request(brief, request)
    second = build_calendar_request(brief, request)

    assert first is not None
    assert second is not None
    assert first.model_dump() == second.model_dump()
