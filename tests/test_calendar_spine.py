from contracts.calendar_action_contract import build_calendar_action
from contracts.calendar_input_contract import build_calendar_request
from contracts.calendar_integration_readiness_contract import (
    build_calendar_integration_readiness,
)
from contracts.calendar_policy_contract import evaluate_calendar_request
from contracts.calendar_review_contract import build_calendar_review
from contracts.clarification_contract import build_clarification_response
from contracts.extractor_contract import extract_catalogue_signals
from contracts.itinerary_input_contract import build_itinerary_request
from planning_policy import evaluate_travel_brief
from contracts.travel_brief_contract import build_travel_brief


def _build_calendar_spine(user_input: str):
    extraction_result = extract_catalogue_signals(user_input)
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)
    itinerary_request = build_itinerary_request(brief, decision, clarification)
    calendar_request = build_calendar_request(brief, itinerary_request)
    calendar_decision = evaluate_calendar_request(calendar_request)
    calendar_action = build_calendar_action(calendar_decision, calendar_request)
    calendar_review = build_calendar_review(calendar_action)
    readiness = build_calendar_integration_readiness(calendar_review)
    return {
        "extraction_result": extraction_result,
        "brief": brief,
        "decision": decision,
        "clarification": clarification,
        "itinerary_request": itinerary_request,
        "calendar_request": calendar_request,
        "calendar_decision": calendar_decision,
        "calendar_action": calendar_action,
        "calendar_review": calendar_review,
        "readiness": readiness,
    }


def test_calendar_spine_review_flow_is_calendar_ready():
    spine = _build_calendar_spine(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend check my schedule"
    )

    assert spine["itinerary_request"] is not None
    assert spine["itinerary_request"].ready is True
    assert spine["calendar_request"] is not None
    assert spine["calendar_request"].ready_for_calendar is True
    assert spine["calendar_decision"].action == "calendar_review_required"
    assert spine["calendar_decision"].ready_for_calendar is True
    assert spine["calendar_action"].action == "review_calendar"
    assert spine["calendar_action"].ready is True
    assert spine["calendar_review"].review_required is True
    assert spine["calendar_review"].ready is True
    assert spine["readiness"].integration_ready is True


def test_calendar_spine_non_calendar_flow_is_not_integration_ready():
    spine = _build_calendar_spine(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )

    assert spine["itinerary_request"] is not None
    assert spine["itinerary_request"].ready is True
    assert spine["calendar_request"] is not None
    assert spine["calendar_request"].ready_for_calendar is True
    assert spine["calendar_decision"].action == "no_calendar_action"
    assert spine["calendar_action"].action == "none"
    assert spine["calendar_review"].review_required is False
    assert spine["readiness"].integration_ready is False
