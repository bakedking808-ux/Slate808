from clarification_contract import build_clarification_response
from extractor_contract import extract_catalogue_signals
from itinerary_input_contract import build_itinerary_request
from planning_policy import evaluate_travel_brief
from travel_brief_contract import build_travel_brief


def test_request_builds_successfully_for_fully_ready_trip_brief():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)

    request = build_itinerary_request(brief, decision, clarification)

    assert request is not None
    assert request.destination == "destination_fixed"
    assert request.traveller == "family"
    assert request.timing == "weekend_trip"
    assert request.ready is True


def test_request_returns_none_when_clarification_is_still_needed():
    extraction_result = extract_catalogue_signals("Need a driver next weekend")
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)

    request = build_itinerary_request(brief, decision, clarification)

    assert request is None


def test_optional_unresolved_fields_remain_none():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)

    request = build_itinerary_request(brief, decision, clarification)

    assert request is not None
    assert request.budget is None
    assert request.intent is None
    assert request.activity is None
    assert request.transport is None
    assert request.accommodation is None
    assert request.constraints is None
    assert request.calendar is None


def test_repeated_call_stability():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)

    first = build_itinerary_request(brief, decision, clarification)
    second = build_itinerary_request(brief, decision, clarification)

    assert first is not None
    assert second is not None
    assert first.model_dump() == second.model_dump()


def test_missing_required_value_fails_loudly_even_if_guards_are_bypassed():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )
    brief = build_travel_brief(extraction_result).model_copy(
        update={
            "destination": build_travel_brief(extraction_result).destination.model_copy(
                update={"value": None}
            )
        }
    )
    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)

    try:
        build_itinerary_request(brief, decision, clarification)
    except ValueError as exc:
        assert str(exc) == "destination.value must be present when building itinerary"
    else:
        assert False, "Expected ValueError for missing destination value"
