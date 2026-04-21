from clarification_contract import build_clarification_response
from extractor_contract import extract_catalogue_signals
from itinerary_builder_contract import build_itinerary_plan
from itinerary_input_contract import build_itinerary_request
from planning_policy import evaluate_travel_brief
from travel_brief_contract import TravelBrief, TravelBriefField, build_travel_brief


def _run_pipeline(user_input: str):
    extraction_result = extract_catalogue_signals(user_input)
    brief = build_travel_brief(extraction_result)
    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)
    request = build_itinerary_request(brief, decision, clarification)
    plan = build_itinerary_plan(request) if request is not None else None
    return {
        "extraction_result": extraction_result,
        "brief": brief,
        "decision": decision,
        "clarification": clarification,
        "request": request,
        "plan": plan,
    }


def _field(
    family: str,
    value: str | None = None,
    resolved: bool = False,
    source_keys: list[str] | None = None,
) -> TravelBriefField:
    return TravelBriefField(
        family=family,
        value=value,
        resolved=resolved,
        source_keys=source_keys or [],
    )


def _invalid_ready_brief() -> TravelBrief:
    return TravelBrief(
        destination=_field("destination", "destination_fixed", True, ["destination_fixed"]),
        traveller=_field("traveller", "family", True, ["family"]),
        timing=_field("timing"),
        budget=_field("budget"),
        intent=_field("intent"),
        activity=_field("activity"),
        transport=_field("transport"),
        accommodation=_field("accommodation"),
        constraints=_field("constraints"),
        calendar=_field("calendar"),
        missing_fields=[],
        clarification_needed=False,
        is_minimum_ready=True,
    )


def test_full_pipeline_success_flow():
    result = _run_pipeline(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )

    assert result["decision"].action == "proceed"
    assert result["clarification"].safe_to_proceed is True
    assert result["request"] is not None
    assert result["request"].ready is True
    assert result["plan"] is not None
    assert result["plan"].destination == "destination_fixed"
    assert result["plan"].traveller == "family"
    assert result["plan"].timing == "weekend_trip"
    assert len(result["plan"].steps) == 5


def test_full_pipeline_requires_clarification():
    result = _run_pipeline("Need a driver next weekend")

    assert result["decision"].action == "clarify"
    assert result["clarification"].safe_to_proceed is False
    assert result["request"] is None


def test_full_pipeline_is_deterministic():
    first = _run_pipeline(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )
    second = _run_pipeline(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )

    assert first["extraction_result"].model_dump() == second["extraction_result"].model_dump()
    assert first["brief"].model_dump() == second["brief"].model_dump()
    assert first["decision"].model_dump() == second["decision"].model_dump()
    assert first["clarification"].model_dump() == second["clarification"].model_dump()
    assert first["request"].model_dump() == second["request"].model_dump()
    assert first["plan"].model_dump() == second["plan"].model_dump()


def test_valid_brief_continues_normally_after_cross_field_validation():
    result = _run_pipeline(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )

    assert result["decision"].action == "proceed"
    assert result["request"] is not None
    assert result["plan"] is not None


def test_invalid_brief_is_blocked_before_planning_policy_progresses():
    brief = _invalid_ready_brief()

    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)
    request = build_itinerary_request(brief, decision, clarification)

    assert decision.action == "clarify"
    assert decision.reason == (
        "Cross-field validation failed: "
        "Timing is unresolved while downstream readiness is implied."
    )
    assert decision.missing_fields == ["timing"]
    assert decision.next_question == "When are you planning to travel?"
    assert clarification.safe_to_proceed is False
    assert request is None
