from contracts.extractor_contract import extract_catalogue_signals
from planning_policy import evaluate_travel_brief
from contracts.travel_brief_contract import build_travel_brief


def test_proceed_case_with_no_missing_required_fields():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )
    brief = build_travel_brief(extraction_result)

    decision = evaluate_travel_brief(brief)

    assert decision.action == "proceed"
    assert decision.reason == "Minimum required planning fields are resolved."
    assert decision.missing_fields == []
    assert decision.next_question is None


def test_clarify_case_with_missing_required_fields():
    extraction_result = extract_catalogue_signals("Need a driver next weekend")
    brief = build_travel_brief(extraction_result)

    decision = evaluate_travel_brief(brief)

    assert decision.action == "clarify"
    assert decision.reason == "Minimum required planning fields are missing."
    assert decision.missing_fields == ["destination", "traveller"]
    assert decision.next_question == "Where would you like to go?"


def test_deterministic_question_generation():
    extraction_result = extract_catalogue_signals("Plan something for 2 adults and 3 kids")
    brief = build_travel_brief(extraction_result)

    decision = evaluate_travel_brief(brief)

    assert decision.next_question == "Where would you like to go?"


def test_repeated_call_stability():
    extraction_result = extract_catalogue_signals("Plan a trip to Naivasha next weekend")
    brief = build_travel_brief(extraction_result)

    first = evaluate_travel_brief(brief)
    second = evaluate_travel_brief(brief)

    assert first.model_dump() == second.model_dump()


def test_resolved_families_do_not_affect_first_missing_field_question_ordering():
    extraction_result = extract_catalogue_signals("Plan a trip to Naivasha")
    brief = build_travel_brief(extraction_result).model_copy(
        update={"missing_fields": ["timing", "destination"], "clarification_needed": True}
    )

    decision = evaluate_travel_brief(brief)

    assert decision.action == "clarify"
    assert decision.next_question == "Where would you like to go?"


def test_unexpected_missing_field_uses_fallback_question():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )
    brief = build_travel_brief(extraction_result).model_copy(
        update={"missing_fields": ["weather"], "clarification_needed": True}
    )

    decision = evaluate_travel_brief(brief)

    assert decision.action == "clarify"
    assert decision.next_question == "What trip detail should I clarify next?"
