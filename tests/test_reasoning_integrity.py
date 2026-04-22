from clarification_contract import build_clarification_response
from clarification_state import ClarificationStateManager
from cross_field_validation_contract import validate_travel_brief_cross_fields
from engine.clarification_runner import reset_state, run
from engine.travel_brief import build_travel_brief as build_live_brief
from extractor_contract import extract_catalogue_signals
from input_normalization_contract import normalize_travel_input
from itinerary_input_contract import build_itinerary_request
from planning_policy import evaluate_travel_brief
from priority_resolution_contract import resolve_field_priorities
from travel_brief_contract import TravelBrief, TravelBriefField, build_travel_brief


def setup_function():
    reset_state()


def _contract_pipeline(user_input: str):
    extraction = extract_catalogue_signals(user_input)
    brief = build_travel_brief(extraction)
    decision = evaluate_travel_brief(brief)
    clarification = build_clarification_response(decision)
    request = build_itinerary_request(brief, decision, clarification)
    return {
        "extraction": extraction,
        "brief": brief,
        "decision": decision,
        "clarification": clarification,
        "request": request,
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


def _contract_brief(**overrides) -> TravelBrief:
    brief = TravelBrief(
        destination=_field("destination", "naivasha", True, ["destination_fixed"]),
        traveller=_field("traveller", "group", True, ["group"]),
        timing=_field("timing", "exact_date", True, ["exact_date"]),
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
    return brief.model_copy(update=overrides)


def _resolved_value(result, field_name: str):
    return next(
        field.value
        for field in result.resolved_fields
        if field.field_name == field_name
    )


def test_explicit_mood_survives_weaker_group_mood_signal():
    result = resolve_field_priorities(
        {
            "trip_mood": [
                {"value": "luxury", "source": "explicit_user_input"},
                {"value": "family", "source": "inferred_value"},
            ]
        }
    )

    assert _resolved_value(result, "trip_mood") == "luxury"
    assert result.warnings


def test_strong_budget_signal_does_not_regress_to_default():
    result = resolve_field_priorities(
        {
            "budget_level": [
                {"value": "high", "source": "explicit_user_input"},
                {"value": "unspecified", "source": "default_fallback"},
            ]
        }
    )

    assert _resolved_value(result, "budget_level") == "high"
    assert result.warnings


def test_exact_timing_precision_beats_month_only_signal():
    result = resolve_field_priorities(
        {
            "timing": [
                {"value": "april", "source": "explicit_user_input", "precision": 1},
                {
                    "value": "21 april",
                    "source": "explicit_user_input",
                    "precision": 2,
                },
            ]
        }
    )

    assert _resolved_value(result, "timing") == "21 april"
    assert result.warnings


def test_ambiguous_destination_triggers_clarification_not_guessing():
    result = run("Plan a quiet trip somewhere scenic for 2 people next weekend")

    assert "Where would you like to go?" in result
    assert "- Destination:" not in result


def test_ambiguous_timing_triggers_clarification_not_silent_acceptance():
    result = run("Plan a trip to Naivasha for 2 people sometime in April")

    assert "exact dates" in result


def test_missing_traveller_count_is_not_inferred_from_vague_group_wording():
    result = run("Plan a luxury trip to Diani for my group next weekend")

    assert "How many travellers?" in result
    assert "- Traveller Count:" not in result


def test_duration_date_range_mismatch_is_not_silently_accepted():
    first = run("Plan a luxury trip to Diani for 2 people for 3 days")
    second = run("10 April to 18 April")

    assert "What exact dates are you planning for those 3 days?" in first
    assert "Status: pass" not in second
    assert "What exact dates are you planning" in second


def test_destination_contamination_by_timing_fragment_is_detected():
    brief = _contract_brief(
        destination=_field("destination", "naivasha april", True, ["destination_fixed"])
    )

    result = validate_travel_brief_cross_fields(brief)

    assert result.warnings == ["Destination appears to contain timing-like fragments."]
    assert result.violations[0].field_name == "destination"


def test_mixed_timing_precision_conflict_is_surfaced():
    brief = _contract_brief(
        timing=_field(
            "timing",
            "exact_date, flexible_timing",
            True,
            ["exact_date", "flexible_timing"],
        )
    )

    decision = evaluate_travel_brief(brief)

    assert decision.action == "clarify"
    assert decision.missing_fields == ["timing"]
    assert "conflicting precision" in decision.reason


def test_mood_survives_clarification_turns():
    first = run("Plan an adventure trip to Mara for 3 people for 5 days")
    second = run("10 April to 14 April")

    assert "- Trip Mood: adventure" in first
    assert "- Trip Mood: adventure" in second


def test_budget_survives_clarification_turns():
    run("Plan a trip to Mara for 3 people for 5 days with a high budget")
    second = run("10 April to 14 April")

    assert "- Budget Level: high" in second


def test_destination_survives_clarification_turns():
    run("Plan a trip to Mara for 3 people for 5 days")
    second = run("10 April to 14 April")

    assert "- Destination: mara" in second


def test_timing_precision_is_not_reduced_after_clarification_completes():
    run("Plan a luxury trip to Diani for 2 people for 3 days")
    result = run("10 April to 12 April")

    assert "- Timing: 10 april to 12 april" in result
    assert "within april" not in result.lower()


def test_glued_token_destination_survives_normalization_and_planning_path():
    text = "Plan a trip toamboseli for 4 travellers next weekend"
    live = build_live_brief(normalize_travel_input(text).normalized_input)
    result = run(text)

    assert live["destination"] == "amboseli"
    assert "Where would you like to go?" not in result
    assert "What exact dates are you planning for next weekend?" in result


def test_missing_comma_spacing_input_resolves_after_normalization():
    text = "Plan a trip to Naivasha for 2 people next weekend,KES 600000"
    live = build_live_brief(text)
    result = run(text)

    assert live["destination"] == "naivasha"
    assert live["budget_amount"] == 600000
    assert "How many travellers?" not in result
    assert "What exact dates are you planning for next weekend?" in result


def test_typo_normalized_destination_does_not_trigger_missing_destination():
    text = "Plan a trip to coasta rico for 2 people next weekend"
    live = build_live_brief(normalize_travel_input(text).normalized_input)
    result = run(text)

    assert live["destination"] == "costa rica"
    assert "Where would you like to go?" not in result
    assert "What exact dates are you planning for next weekend?" in result


def test_clean_high_integrity_case_preserves_strong_values_end_to_end():
    live = build_live_brief(
        "Plan a luxury trip to Diani for 2 people on 21 April with a high budget"
    )
    contract = _contract_pipeline(
        "Plan a trip to Diani for 2 adults and 3 kids April 25 KES 50,000"
    )
    first = run(
        "Plan a luxury trip to Diani for 2 people on 21 April with a high budget"
    )
    second = run(
        "Plan a luxury trip to Diani for 2 people on 21 April with a high budget"
    )

    assert contract["decision"].action == "proceed"
    assert contract["clarification"].safe_to_proceed is True
    assert contract["request"] is not None
    assert live["destination"] == "diani"
    assert live["traveller_count"] == 2
    assert live["trip_mood"] == "luxury"
    assert live["budget_level"] == "high"
    assert live["timing"]["state"] == "exact_timing"
    assert live["timing"]["raw_text"] == "21 april"
    assert "What exact dates are you planning?" not in first
    assert "- Trip Mood: luxury" in first
    assert first == second


def test_conflict_heavy_case_blocks_or_clarifies_without_losing_strong_values():
    manager = ClarificationStateManager()
    manager.start(
        task_type="trip",
        original_input="Plan a luxury trip to Diani for 2 people for 3 days with a high budget",
        missing_fields=["timing"],
        collected_fields={
            "destination": "diani",
            "traveller_count": 2,
            "budget_level": "high",
            "trip_mood": "luxury",
            "timing": {
                "raw_text": "for 3 days",
                "start_date": None,
                "end_date": None,
                "duration_days": 3,
                "duration_nights": None,
                "date_flexibility": "unknown",
                "state": "duration_only",
                "confidence": "medium",
            },
        },
    )

    state = manager.get_state()
    result = run("Plan a luxury trip to Diani for 2 people for 3 days with a high budget")
    follow_up = run("10 April to 18 April")

    assert state["collected_fields"]["trip_mood"] == "luxury"
    assert state["collected_fields"]["budget_level"] == "high"
    assert "- Trip Mood: luxury" in result
    assert "- Budget Level: high" in result
    assert "Status: pass" not in follow_up
    assert "What exact dates are you planning" in follow_up
