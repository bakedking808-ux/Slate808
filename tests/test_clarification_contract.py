from clarification_contract import build_clarification_response
from extractor_contract import extract_catalogue_signals
from planning_policy import evaluate_travel_brief
from travel_brief_contract import build_travel_brief


def test_clarify_decision_produces_needs_clarification_response():
    extraction_result = extract_catalogue_signals("Need a driver next weekend")
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)

    response = build_clarification_response(decision)

    assert response.status == "needs_clarification"
    assert response.question == "Where would you like to go?"
    assert response.safe_to_proceed is False


def test_proceed_decision_produces_ready_response():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)

    response = build_clarification_response(decision)

    assert response.status == "ready"
    assert response.question is None
    assert response.safe_to_proceed is True


def test_repeated_call_stability():
    extraction_result = extract_catalogue_signals("Need a driver next weekend")
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)

    first = build_clarification_response(decision)
    second = build_clarification_response(decision)

    assert first.model_dump() == second.model_dump()


def test_missing_fields_pass_through_unchanged():
    extraction_result = extract_catalogue_signals("Need a driver next weekend")
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)

    response = build_clarification_response(decision)

    assert response.missing_fields == decision.missing_fields
