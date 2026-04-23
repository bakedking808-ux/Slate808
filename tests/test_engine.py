import re

import pytest
from pydantic import ValidationError

import engine.checker as checker
from engine.clarification_runner import run, reset_state
from engine.formatter import format_output
from engine.generator import detect_task_type, generate_plan, is_travel_intent
from engine.planning_policy import derive_planning_constraints
from engine.runner import run_engine
from engine.travel_brief import (
    TimingModel,
    TravelBriefModel,
    extract_traveller_count,
    summarize_timing,
    extract_timing,
    extract_budget_info,
    build_travel_brief,
    enforce_travel_brief_schema,
    get_missing_critical_fields,
    extract_trip_mood,
)


def setup_function():
    reset_state()


def _extract_numbered_steps(output: str) -> list[str]:
    return re.findall(r"^\d+\.\s+(.+)$", output, re.MULTILINE)


def test_timing_model_exact_timing_payload_validates():
    timing = TimingModel(
        raw_text="10 april to 14 april",
        start_date="10 april",
        end_date="14 april",
        date_flexibility="fixed",
        state="exact_timing",
        confidence="high",
    )

    assert timing.start_date == "10 april"
    assert timing.end_date == "14 april"


def test_timing_model_relative_timing_payload_validates():
    timing = TimingModel(
        raw_text="next weekend",
        date_flexibility="fixed",
        state="relative_timing",
        confidence="medium",
    )

    assert timing.state == "relative_timing"
    assert timing.raw_text == "next weekend"


def test_timing_model_duration_only_payload_validates():
    timing = TimingModel(
        raw_text="for 3 days",
        duration_days=3,
        date_flexibility="unknown",
        state="duration_only",
        confidence="medium",
    )

    assert timing.duration_days == 3


def test_timing_model_month_only_payload_validates():
    timing = TimingModel(
        raw_text="april",
        date_flexibility="flexible",
        state="month_only",
        confidence="low",
    )

    assert timing.raw_text == "april"


def test_timing_model_missing_timing_payload_validates():
    timing = TimingModel()

    assert timing.state == "missing_timing"
    assert timing.raw_text == ""


def test_timing_model_vague_timing_payload_validates():
    timing = TimingModel(
        raw_text="soon",
        date_flexibility="unknown",
        state="vague_timing",
        confidence="low",
    )

    assert timing.state == "vague_timing"


def test_timing_model_duration_only_without_duration_fails():
    with pytest.raises(ValidationError):
        TimingModel(
            raw_text="for a while",
            date_flexibility="unknown",
            state="duration_only",
            confidence="low",
        )


def test_timing_model_end_date_without_start_date_fails():
    with pytest.raises(ValidationError):
        TimingModel(
            raw_text="14 april",
            end_date="14 april",
            date_flexibility="fixed",
            state="exact_timing",
            confidence="high",
        )


def test_timing_model_unsupported_state_fails():
    with pytest.raises(ValidationError):
        TimingModel(
            raw_text="next year",
            date_flexibility="unknown",
            state="annual_timing",
            confidence="low",
        )


def test_timing_model_unsupported_confidence_and_flexibility_fail():
    with pytest.raises(ValidationError):
        TimingModel(
            raw_text="april",
            date_flexibility="semi_flexible",
            state="month_only",
            confidence="certain",
        )


def test_travel_brief_model_completed_payload_validates():
    brief = TravelBriefModel(
        destination="diani",
        traveller_count=2,
        timing=TimingModel(
            raw_text="next weekend",
            date_flexibility="fixed",
            state="relative_timing",
            confidence="medium",
        ),
        budget_amount=45000,
        budget_level="medium",
        trip_mood="relaxed",
    )

    assert brief.destination == "diani"
    assert brief.timing.state == "relative_timing"


def test_travel_brief_model_partial_clarification_payload_validates():
    brief = TravelBriefModel(
        destination=None,
        traveller_count=None,
        timing=TimingModel(),
        budget_amount=None,
        budget_level="unspecified",
        trip_mood=None,
    )

    assert brief.timing.state == "missing_timing"
    assert brief.destination is None


def test_travel_brief_model_negative_traveller_count_fails():
    with pytest.raises(ValidationError):
        TravelBriefModel(
            destination="diani",
            traveller_count=-1,
            timing=TimingModel(),
            budget_level="unspecified",
        )


def test_travel_brief_model_negative_budget_amount_fails():
    with pytest.raises(ValidationError):
        TravelBriefModel(
            destination="diani",
            traveller_count=2,
            timing=TimingModel(),
            budget_amount=-100,
            budget_level="low",
        )


def test_travel_brief_model_unsupported_budget_level_fails():
    with pytest.raises(ValidationError):
        TravelBriefModel(
            destination="diani",
            traveller_count=2,
            timing=TimingModel(),
            budget_level="premium",
        )


def test_travel_brief_model_unsupported_trip_mood_fails():
    with pytest.raises(ValidationError):
        TravelBriefModel(
            destination="diani",
            traveller_count=2,
            timing=TimingModel(),
            budget_level="low",
            trip_mood="party",
        )


def test_travel_brief_model_timing_field_must_validate_as_timing_model():
    with pytest.raises(ValidationError):
        TravelBriefModel(
            destination="diani",
            traveller_count=2,
            timing={"state": "duration_only", "raw_text": "for some time"},
            budget_level="low",
        )


def test_clarification_flow_trip():
    result_1 = run("Plan a trip")
    assert "Where would you like to go?" in result_1

    result_2 = run("Naivasha")
    assert "What exact dates are you planning?" in result_2

    result_3 = run("next weekend")
    assert "What exact dates are you planning for next weekend?" in result_3
    assert "Slate808 Output" not in result_3

    result_4 = run("10 April to 12 April")
    assert "How many travellers?" in result_4
    assert "Slate808 Output" not in result_4

    result_5 = run("3 people")
    assert "Slate808 Output" in result_5
    assert "Destination: naivasha" in result_5
    assert "Traveller Count: 3" in result_5
    assert "Timing: 10 april to 12 april" in result_5


def test_bare_number_word_reply_supported():
    assert extract_traveller_count("four") == 4
    assert extract_traveller_count("7") == 7


def test_timing_range_dash_format_supported():
    timing = extract_timing("10-28 April")
    assert summarize_timing(timing) == "10 april to 28 april"


def test_direct_complete_trip_request():
    result = run("Plan a trip to diani for 3 couples 10 April to 12 April")
    assert "Slate808 Output" in result
    assert "Destination: diani" in result
    assert "Traveller Count: 6" in result
    assert "Timing: 10 april to 12 april" in result


def test_staycation_routes_to_trip_pipeline():
    result = run_engine("Plan a staycation in nairobi for 2 people next weekend")

    assert "Slate808 Output" in result
    assert "Status: pass" in result
    assert "Travel Brief:" in result
    assert "Traveller Count: 2" in result
    assert "Timing: next weekend" in result
    assert "Slate808 currently supports travel planning only." not in result


def test_relaxed_staycation_routes_to_trip_pipeline():
    result = run_engine("Plan a relaxed staycation to kisumu for 2 people next weekend")

    assert "Slate808 Output" in result
    assert "Status: pass" in result
    assert "Travel Brief:" in result
    assert "Destination: kisumu" in result
    assert "Timing: next weekend" in result


def test_staycation_without_destination_restarts_trip_clarification():
    result = run("Plan a staycation for my family of 6")

    assert "Where would you like to go?" in result
    assert "Slate808 currently supports travel planning only." not in result


@pytest.mark.parametrize(
    "travel_request",
    [
        "Plan a trip to diani for 2 people next weekend",
        "Plan a travel to naivasha for 2 people next weekend",
        "Plan a journey to watamu for 2 people next weekend",
        "Plan a getaway to ukunda for 2 people next weekend",
        "Plan a holiday to diani for 2 people next weekend",
        "Plan a vacation to diani for 2 people next weekend",
        "Plan a retreat to naivasha for 4 people next weekend",
        "Plan an escape to watamu for 2 people next weekend",
        "Plan a staycation in nairobi for 2 people next weekend",
    ],
)
def test_travel_intent_keywords_route_to_trip_classification(travel_request):
    assert detect_task_type(travel_request) == "trip"


@pytest.mark.parametrize(
    "travel_request",
    [
        "Help me plan a 3-day break in early July.",
        "I’m thinking of a long weekend in November.",
        "Arrange a getaway for 3-5 Jan.",
        "Help me organise a family holiday.",
        "Create a 2-night trip this coming weekend.",
    ],
)
def test_natural_travel_intent_phrasing_passes_gate_safely(travel_request):
    assert detect_task_type(travel_request) == "trip"

    result = run(travel_request)
    assert "Slate808 currently supports travel planning only." not in result
    assert "Destination: None" not in result
    assert "Traveller Count: None" not in result


def test_natural_travel_intent_gate_is_deterministic():
    request = "Help me plan a 3-day break in early July."

    assert detect_task_type(request) == detect_task_type(request) == "trip"


@pytest.mark.parametrize(
    "text",
    [
        "Plan something warm for 2 people 10 April to 12 April",
        "Near Diani for 2 people",
        "Thinking maybe a chilled coast thing for me and my partner sometime in July",
        "I want something romantic, maybe Mara, maybe coast, for two in August",
        "Can you sort a quiet break in Watamu for 3 people, low budget, probably mid June",
        "Somewhere warm next month for 2 people",
        "We could use a break in Watamu 22 May to 24 May",
    ],
)
def test_natural_operational_travel_requests_enter_controlled_flow(text):
    result = run(text)

    assert is_travel_intent(text) is True
    assert "Slate808 currently supports travel planning only." not in result
    assert "?" in result


@pytest.mark.parametrize(
    "text",
    [
        "Thinking of heading somewhere coastal… not sure which place yet.",
        "Could you help me plan something around the lakeside?",
        "Thinking of a place with wildlife… not sure which park.",
        "I want a warm destination, but I don’t have a specific place in mind.",
        "Could you help me plan something affordable for a few days?",
        "I need a short break — you tell me what you need from me.",
        "Plan something for us; I’ll confirm the timing once you ask.",
        "I want a premium experience, but I don’t know where or when.",
    ],
)
def test_destination_discovery_prompts_enter_destination_clarification(text):
    result = run(text)

    assert is_travel_intent(text) is True
    assert "Slate808 currently supports travel planning only." not in result
    assert "Where would you like to go?" in result
    assert result.count("?") == 1


@pytest.mark.parametrize(
    "text",
    [
        "Somewhere near Nairobi but not too crowded — any ideas?",
        "I’m open to anything coastal, maybe Watamu, maybe something else.",
        "I want to visit Lamuu — or is it Lamu? That one.",
        "I want to go to Mombassa or maybe Dianii, whichever works.",
        "I’m considering a mountain area — maybe Kenya, maybe Tanzania.",
    ],
)
def test_destination_discovery_language_variants_clarify_destination(text):
    brief = build_travel_brief(text)
    result = run(text)

    assert is_travel_intent(text) is True
    assert brief["destination"] is None
    assert "Slate808 currently supports travel planning only." not in result
    assert "Where would you like to go?" in result
    assert "Destination:" not in result


@pytest.mark.parametrize(
    "text",
    [
        "uhh plan something for us maybe next month idk budget medium",
        "Need a calm break, no idea where, for 3 people, 10 April to 12 April",
        "somewhere quiet for me and my partner, exact dates are 5 May to 7 May",
        "Watamu 18 June to 21 June, not sure who all is coming",
        "I want a scenic place for a few nights — timing is open.",
    ],
)
def test_messy_travel_intent_prompts_enter_controlled_flow(text):
    result = run(text)

    assert is_travel_intent(text) is True
    assert "Slate808 currently supports travel planning only." not in result
    assert "Where would you like to go?" in result
    assert result.count("?") == 1


def test_natural_operational_intent_preserves_non_travel_rejection():
    result = run("Summarize the project status for tomorrow")

    assert is_travel_intent("Summarize the project status for tomorrow") is False
    assert "Slate808 currently supports travel planning only." in result


def test_stay_travel_noun_with_budget_enters_controlled_flow():
    text = "Nairobi stay with 85,001 budget"

    brief = build_travel_brief(text)
    result = run(text)

    assert is_travel_intent(text) is True
    assert brief["destination"] == "nairobi"
    assert brief["budget_level"] == "high"
    assert "Slate808 currently supports travel planning only." not in result
    assert "?" in result


def test_stay_travel_noun_with_exact_dates_enters_travel_flow():
    text = "Plan a Nairobi stay for 2 people 9 August to 10 August"

    brief = build_travel_brief(text)
    result = run(text)

    assert is_travel_intent(text) is True
    assert brief["destination"] == "nairobi"
    assert brief["timing"]["state"] == "exact_timing"
    assert "Slate808 currently supports travel planning only." not in result


def test_stay_support_preserves_non_travel_rejection():
    text = "Please stay focused for tomorrow"

    result = run(text)

    assert is_travel_intent(text) is False
    assert "Slate808 currently supports travel planning only." in result


def test_build_travel_brief_returns_validated_dict_shape_for_engine_compatibility():
    brief = build_travel_brief("Plan a trip to diani for 2 people next weekend")

    assert isinstance(brief, dict)
    assert isinstance(brief["timing"], dict)
    assert brief["destination"] == "diani"
    assert brief["timing"]["state"] == "relative_timing"


def test_travel_brief_schema_gate_valid_payload_passes_unchanged():
    brief = build_travel_brief("Plan a trip to diani for 2 people next weekend")

    assert enforce_travel_brief_schema(brief) == brief


def test_travel_brief_schema_gate_malformed_payload_fails_loudly():
    brief = build_travel_brief("Plan a trip to diani for 2 people next weekend")
    brief.pop("timing")

    with pytest.raises(ValidationError):
        enforce_travel_brief_schema(brief)


def test_budget_extraction_numeric_amount_supported():
    brief = build_travel_brief("Plan a trip to diani for 2 people next weekend budget is 45000")
    assert brief["budget_amount"] == 45000
    assert brief["budget_level"] == "low"


def test_budget_extraction_numeric_k_format_supported():
    brief = build_travel_brief("Plan a trip to diani for 2 people next weekend budget is 25k")
    assert brief["budget_amount"] == 25000
    assert brief["budget_level"] == "low"


def test_budget_extraction_signal_cheap_supported():
    brief = build_travel_brief("Plan a cheap trip to diani for 2 people next weekend")
    assert brief["budget_amount"] is None
    assert brief["budget_level"] == "low"


def test_budget_extraction_signal_luxury_supported():
    brief = build_travel_brief("Plan a luxury trip to diani for 2 people next weekend")
    assert brief["budget_amount"] is None
    assert brief["budget_level"] == "high"


def test_budget_extraction_signal_affordable_supported():
    brief = build_travel_brief("Plan an affordable trip to diani for 2 people next weekend")
    assert brief["budget_amount"] is None
    assert brief["budget_level"] == "low"


def test_budget_extraction_real_world_family_request_supported():
    brief = build_travel_brief(
        "Plana 2 day trip to ukunda for 4 couples and 2 children, budget is 40000"
    )

    assert brief["destination"] == "ukunda"
    assert brief["traveller_count"] == 10
    assert brief["budget_amount"] == 40000
    assert brief["budget_level"] == "low"


def test_budget_and_destination_extraction_with_interleaved_currency_context():
    brief = build_travel_brief(
        "plan a trip with Kes 60000 for paris next week, a group of 6"
    )

    assert brief["destination"] == "paris"
    assert brief["traveller_count"] == 6
    assert brief["budget_amount"] == 60000
    assert brief["budget_level"] == "medium"
    assert brief["timing"]["raw_text"] == "next week"


@pytest.mark.parametrize(
    ("text", "amount", "level"),
    [
        ("Plan a trip to Diani for 2 people on a medium budget", None, "medium"),
        ("Plan a trip to Diani for 2 people medium budget", None, "medium"),
        ("Plan a trip to Diani for 2 people high budget", None, "high"),
        ("Plan a trip to Diani for 2 people low budget", None, "low"),
        ("Plan a trip to Diani for 2 people under 45,000", 45000, "low"),
        ("Plan a trip to Diani for 2 people under 45000", 45000, "low"),
        ("Plan a trip to Diani for 2 people under 50000", 50000, "medium"),
        ("Plan a trip to Diani for 2 people 45,000 budget", 45000, "low"),
        ("Plan a trip to Diani for 2 people 45,001 budget", 45001, "medium"),
        ("Plan a trip to Diani for 2 people 85,000 budget", 85000, "medium"),
        ("Plan a trip to Diani for 2 people 85,001 budget", 85001, "high"),
    ],
)
def test_budget_contract_bands_phrases_and_numeric_formats(text, amount, level):
    brief = build_travel_brief(text)

    assert brief["budget_amount"] == amount
    assert brief["budget_level"] == level


@pytest.mark.parametrize(
    "text",
    [
        "Plan a trip to Diani for 2 people no budget yet",
        "Plan a trip to Diani for 2 people budget not decided",
    ],
)
def test_budget_contract_unset_budget_remains_unspecified(text):
    brief = build_travel_brief(text)

    assert brief["budget_amount"] is None
    assert brief["budget_level"] == "unspecified"


def test_budget_wording_with_nearby_exact_date_does_not_parse_date_as_amount():
    brief = build_travel_brief(
        "Plan a quiet low-key Naivasha trip on a medium budget 10 April to 12 April"
    )

    assert brief["budget_amount"] is None
    assert brief["budget_level"] == "medium"


def test_exact_date_request_without_budget_stays_unspecified():
    brief = build_travel_brief("Plan a trip to Diani for 2 people 10 April to 12 April")

    assert brief["budget_amount"] is None
    assert brief["budget_level"] == "unspecified"


def test_numeric_budget_after_exact_dates_still_parses():
    brief = build_travel_brief("Plan a trip to Diani for 2 people 10 April to 12 April under 45,000")

    assert brief["budget_amount"] == 45000
    assert brief["budget_level"] == "low"


def test_budget_contract_no_budget_exact_date_request_still_runs():
    result = run("Plan a trip to Diani for 2 people 10 April to 12 April")

    assert "Slate808 Output" in result
    assert "Destination: diani" in result
    assert "Budget Level: unspecified" in result


def test_clarification_with_partial_trip_continues_from_next_missing_field():
    result_1 = run("Plan a trip to watamu")
    assert "What exact dates are you planning?" in result_1

    result_2 = run("next month")
    assert "What exact dates are you planning for next month?" in result_2
    assert "Slate808 Output" not in result_2

    result_3 = run("10-12 April")
    assert "How many travellers?" in result_3
    assert "Slate808 Output" not in result_3

    result_4 = run("2 people")
    assert "Slate808 Output" in result_4
    assert "Destination: watamu" in result_4
    assert "Traveller Count: 2" in result_4
    assert "Timing: 10 april to 12 april" in result_4


def test_destination_clarification_reply_is_routed_to_active_trip():
    run("Plan a trip")
    result = run("Naivasha")

    assert "What exact dates are you planning?" in result
    assert "How many travellers?" not in result
    assert "Where would you like to go?" not in result


def test_uncertain_destination_reply_keeps_destination_clarification_first():
    run("Plan a trip for 2 people 10 April to 12 April")
    result = run("near Diani")

    assert "Where would you like to go?" in result
    assert "How many travellers?" not in result
    assert "Slate808 Output" not in result


def test_traveller_count_clarification_reply_is_routed_to_active_trip():
    run("Plan a trip to naivasha")
    result = run("3 people")

    assert "What exact dates are you planning?" in result
    assert "How many travellers?" not in result


def test_timing_clarification_reply_is_routed_to_active_trip():
    run("Plan a trip to naivasha for 3 people")
    result = run("tomorrow")

    assert "What exact dates are you planning for tomorrow?" in result
    assert "Slate808 Output" not in result


def test_clarification_does_not_reask_known_destination():
    result = run("Plan a trip to Diani next weekend")

    assert "What exact dates are you planning for next weekend?" in result
    assert "Where would you like to go?" not in result
    assert "How many travellers?" not in result
    assert result.count("?") == 1


def test_clarification_route_logs_collected_field_names_only(monkeypatch):
    logged_events = []
    monkeypatch.setattr(
        "engine.clarification_runner.log_event",
        lambda **kwargs: logged_events.append(kwargs),
    )

    result = run("Plan a calm trip to Diani next month with a medium budget")

    assert "What exact dates are you planning for next month?" in result
    details = logged_events[0]["details"]
    assert details["collected_fields_count"] == 4
    assert details["collected_field_names"] == [
        "budget_level",
        "destination",
        "timing",
        "trip_mood",
    ]
    assert "diani" not in str(details)
    assert "medium" not in str(details)


def test_clarification_does_not_reask_known_travellers_for_month_timing():
    result = run("Plan a trip to Mauritius for 2 people sometime in June")

    assert "Which exact dates in June are you planning?" in result
    assert "How many travellers?" not in result
    assert "Where would you like to go?" not in result
    assert result.count("?") == 1


def test_destination_clarification_absorbs_multi_field_reply():
    run("Plan a trip")
    result = run("Diani, 10 April to 12 April, two people")

    assert "What kind of trip mood should this have?" in result
    assert "- Destination: diani" in result
    assert "- Traveller Count: 2" in result
    assert "- Timing: 10 april to 12 april" in result
    assert "Where would you like to go?" not in result
    assert "How many travellers?" not in result


def test_destination_clarification_absorbs_destination_and_broad_timing_reply():
    run("Plan a trip")
    result = run("Watamu next month")

    assert "What exact dates are you planning for next month?" in result
    assert "Where would you like to go?" not in result
    assert "How many travellers?" not in result


def test_explicit_destination_correction_overrides_stale_state():
    run("Plan a trip to Diani for 2 people")
    result = run("Actually make it Watamu instead")
    follow_up = run("10 April to 12 April")

    assert "What exact dates are you planning?" in result
    assert "How many travellers?" not in result
    assert "- Destination: watamu" in follow_up
    assert "- Destination: diani" not in follow_up


def test_explicit_correction_also_absorbs_additional_fields():
    run("Plan a trip to Diani")
    result = run("Actually Watamu, and we'll be 3 people")
    follow_up = run("10 April to 12 April")

    assert "What exact dates are you planning?" in result
    assert "How many travellers?" not in result
    assert "- Destination: watamu" in follow_up
    assert "- Traveller Count: 3" in follow_up
    assert "- Destination: diani" not in follow_up


@pytest.mark.parametrize(
    "text",
    [
        "Plan a trip to Diani for 2 people next month",
        "Diani next month for 2 people",
        "Coast next month for 2 people",
        "Plan a trip to Diani for 2 people this month",
        "Diani next week for 2 people",
        "Plan a trip to Diani for 2 people this weekend",
        "Plan a trip to Diani for 2 people next weekend",
        "Plan a trip to Coast for 2 people today",
        "Plan a trip to Coast for 2 people tomorrow",
    ],
)
def test_relative_timing_requires_exact_date_clarification(text):
    result = run(text)

    assert "exact dates" in result
    assert "Slate808 Output" not in result
    assert "Where would you like to go?" not in result
    assert "How many travellers?" not in result
    assert result.count("?") == 1


def test_explicit_around_june_refinement_remains_preserved():
    result = run("Plan a trip to coast for 2 people around June")

    assert "Which exact dates in June are you planning?" in result
    assert "Slate808 Output" not in result
    assert result.count("?") == 1


def test_exact_date_ready_trip_still_executes():
    result = run("Plan a trip to Diani for 2 people 10 April to 12 April")

    assert "Slate808 Output" in result
    assert "Destination: diani" in result
    assert "Traveller Count: 2" in result
    assert "Timing: 10 april to 12 april" in result


def test_clarification_asks_destination_when_timing_and_travellers_known():
    result = run("I want a getaway next month for 2 people")

    assert "Where would you like to go?" in result
    assert "How many travellers?" not in result
    assert "What exact dates are you planning?" not in result
    assert result.count("?") == 1


def test_clarification_priority_timing_before_traveller_when_destination_known():
    result = run("Plan a trip to Diani next month")

    assert "What exact dates are you planning for next month?" in result
    assert "How many travellers?" not in result
    assert "Where would you like to go?" not in result
    assert result.count("?") == 1


def test_clarification_priority_traveller_when_destination_and_timing_known():
    result = run("Plan a trip to Diani 10 April to 12 April")

    assert "How many travellers?" in result
    assert "Where would you like to go?" not in result
    assert "What exact dates are you planning?" not in result
    assert result.count("?") == 1


def test_clarification_priority_shaping_does_not_outrank_hard_fields():
    result = run("Plan a luxury trip to somewhere warm next month with a high budget")

    assert "Where would you like to go?" in result
    assert "What exact dates are you planning?" not in result
    assert "What kind of trip mood should this have?" not in result
    assert result.count("?") == 1


def test_soft_break_phrase_with_timing_is_travel_intent():
    result = run("I need a break next month")

    assert is_travel_intent("I need a break next month") is True
    assert "Slate808 currently supports travel planning only." not in result
    assert "Where would you like to go?" in result
    assert "Slate808 Output" not in result


def test_soft_break_phrase_with_coast_hint_stays_controlled():
    result = run("I need a break sometime next month maybe coast")

    assert is_travel_intent("I need a break sometime next month maybe coast") is True
    assert "Slate808 currently supports travel planning only." not in result
    assert "Slate808 Output" not in result
    assert result.count("?") == 1


@pytest.mark.parametrize(
    "text",
    [
        "I need a little break next month",
        "I really need a break next month",
        "We need a break next month",
        "Need a break next month",
        "I could use a break next month",
        "I want a break next month",
        "I need a short break next month",
    ],
)
def test_soft_break_variants_are_travel_intent(text):
    result = run(text)

    assert is_travel_intent(text) is True
    assert "Slate808 currently supports travel planning only." not in result
    assert "Slate808 Output" not in result
    assert result.count("?") == 1


@pytest.mark.parametrize(
    "text",
    [
        "I need a break from work next month",
        "I need a break on this project next month",
        "I need a break in the meeting next month",
        "I need a break from studying next month",
    ],
)
def test_non_travel_break_variants_remain_rejected(text):
    result = run(text)

    assert is_travel_intent(text) is False
    assert "Slate808 currently supports travel planning only." in result
    assert "Where would you like to go?" not in result


def test_relative_timing_followup_refines_to_exact_dates_only():
    run("Plan a trip to naivasha for 3 people")
    result = run("next month")

    assert "What exact dates are you planning for next month?" in result
    assert "Where would you like to go?" not in result
    assert "How many travellers?" not in result
    assert result.count("?") == 1


def test_clarification_quality_repeated_calls_are_deterministic():
    reset_state()
    first = run("Plan a trip to Mauritius for 2 people sometime in June")
    reset_state()
    second = run("Plan a trip to Mauritius for 2 people sometime in June")

    assert first == second


def test_clarification_preserves_budget_from_followup_answer():
    result_1 = run("Plan a trip to Paris")
    assert "What exact dates are you planning?" in result_1

    result_2 = run("10 April to 12 April")
    assert "How many travellers?" in result_2

    result_3 = run("7 people and a budget of 600000")
    assert "Slate808 Output" in result_3
    assert "Destination: paris" in result_3
    assert "Traveller Count: 7" in result_3
    assert "Timing: 10 april to 12 april" in result_3
    assert "- Budget: 600000 (high)" in result_3


def test_clarification_cancel_clears_active_state():
    run("Plan a trip")
    cancel_result = run("cancel")

    assert "Session reset. What would you like to plan?" in cancel_result

    follow_up = run("Plan a trip to naivasha")
    assert "Where would you like to go?" not in follow_up
    assert "What exact dates are you planning?" in follow_up
    assert "How many travellers?" not in follow_up


def test_clarification_restart_clears_active_state():
    run("Plan a trip to naivasha")
    restart_result = run("restart")

    assert "Session reset. What would you like to plan?" in restart_result

    fresh_request = run("Plan a trip")
    assert "Where would you like to go?" in fresh_request


def test_unrelated_new_request_during_clarification_is_not_treated_as_answer():
    run("Plan a trip")
    result = run("Plan a meeting agenda for Monday")

    assert "Slate808 Output" in result
    assert "Status: fail" in result
    assert "Slate808 currently supports travel planning only." in result
    assert "How many travellers?" not in result
    assert "What exact dates are you planning?" not in result
    assert "Break down the task into components" not in result
    assert "Travel Brief:" not in result


def test_exit_command_does_not_become_destination():
    run("Plan a trip")
    exit_result = run("exit")

    assert "Session reset. What would you like to plan?" in exit_result

    next_trip = run("Plan a trip to diani for 2 people 10 April to 12 April")
    assert "Destination: diani" in next_trip
    assert "Destination: exit" not in next_trip


def test_restart_command_clears_active_state():
    run("Plan a trip to naivasha")
    restart_result = run("restart")

    assert "Session reset. What would you like to plan?" in restart_result

    fresh_request = run("Plan a trip")
    assert "Where would you like to go?" in fresh_request


def test_new_task_override_during_clarification():
    run("Plan a trip")
    result = run("Plan a meeting agenda for Monday")

    assert "Slate808 Output" in result
    assert "Status: fail" in result
    assert "Slate808 currently supports travel planning only." in result
    assert "How many travellers?" not in result
    assert "What exact dates are you planning?" not in result
    assert "Gather necessary resources" not in result


def test_non_travel_override_exits_clarification_state_cleanly():
    run("Plan a trip")
    override_result = run("Plan a meeting agenda for Monday")

    assert "Slate808 currently supports travel planning only." in override_result

    follow_up = run("Plan a trip to naivasha for 2 people 10 April to 12 April")
    assert "Status: pass" in follow_up
    assert "Destination: naivasha" in follow_up


def test_incomplete_travel_override_restarts_clarification_safely():
    run("Plan a trip to diani")
    override_result = run("plan a journey")

    assert "Where would you like to go?" in override_result
    assert "Status: pass" not in override_result
    assert "Destination: None" not in override_result
    assert "Timing: timing not specified" not in override_result


@pytest.mark.parametrize(
    ("text", "expected_state", "expected_summary"),
    [
        ("next month", "relative_timing", "next month"),
        ("april", "month_only", "april"),
        ("for 3 days", "duration_only", "for 3 days"),
        ("2 nights", "duration_only", "2 nights"),
        ("10-23rd april", "exact_timing", "10 april to 23rd april"),
        ("20-10th may", "exact_timing", "20 april to 10 may"),
        ("10-20 may", "exact_timing", "10 may to 20 may"),
        ("20th-14th may", "exact_timing", "20 april to 14 may"),
        ("20 april to 10 may", "exact_timing", "20 april to 10 may"),
        ("3rd to 4th jan", "exact_timing", "3rd january to 4th january"),
        ("jan 14th to february 14th", "exact_timing", "14th january to 14th february"),
        ("jan 14th to febuary 14th", "exact_timing", "14th january to 14th february"),
    ],
)
def test_timing_current_behavior_matches_engine_behavior(text, expected_state, expected_summary):
    timing = extract_timing(text)

    assert timing["state"] == expected_state
    assert summarize_timing(timing) == expected_summary


@pytest.mark.parametrize(
    "text",
    [
        "4th july - 31st september",
        "31st september",
        "3rd to 4th",
        "30th february",
    ],
)
def test_invalid_or_ambiguous_timing_inputs_remain_unusable(text):
    timing = extract_timing(text)

    assert timing["state"] == "missing_timing"
    assert summarize_timing(timing) == "timing not specified"


def test_timing_month_only_is_detected_but_requires_clarification():
    brief = build_travel_brief("Plan a trip to diani for 2 people in april")

    assert brief["timing"]["state"] == "month_only"
    assert get_missing_critical_fields(brief) == ["timing"]


def test_month_only_timing_in_april_triggers_state_aware_clarification():
    result = run("Plan a trip to diani for 2 people in April")

    assert "Which exact dates in April are you planning?" in result
    assert "Slate808 Output" not in result


def test_month_only_timing_answer_is_accepted_in_clarification():
    run("Plan a trip to naivasha for 3 people")
    result = run("April")

    assert "Which exact dates in April are you planning?" in result
    assert "Slate808 Output" not in result


def test_short_destination_reply_does_not_trigger_new_task_override():
    run("Plan a trip")
    result = run("travel to nairobi")

    assert "What exact dates are you planning?" in result
    assert "How many travellers?" not in result
    assert "Where would you like to go?" not in result


def test_timing_duration_only_is_detected_but_requires_clarification():
    brief = build_travel_brief("Plan a trip to diani for 2 people for 3 days")

    assert brief["timing"]["state"] == "duration_only"
    assert get_missing_critical_fields(brief) == ["timing"]


def test_dual_duration_compatible_pair_prefers_days():
    timing = extract_timing("3 days and 2 nights")

    assert timing["state"] == "duration_only"
    assert timing["raw_text"] == "for 3 days"
    assert timing["duration_days"] == 3
    assert timing["duration_nights"] is None


@pytest.mark.parametrize("text", ["3 days and 3 nights", "3 days and 4 nights"])
def test_dual_duration_conflicts_force_clarification(text):
    timing = extract_timing(text)

    assert timing["state"] == "missing_timing"
    assert summarize_timing(timing) == "timing not specified"


def test_timing_vague_reasks_in_clarification():
    run("Plan a trip to naivasha for 2 people")
    result = run("soon")

    assert "What exact dates are you planning?" in result
    assert "Slate808 Output" not in result


def test_partial_timing_reply_does_not_advance_past_current_hard_field():
    run("Plan a trip to diani for 2 people")
    result = run("Maybe early June")

    assert "Which exact dates in June are you planning?" in result
    assert "Where would you like to go?" not in result
    assert "How many travellers?" not in result
    assert "Slate808 Output" not in result


def test_duration_only_timing_triggers_state_aware_clarification():
    result = run("Plan a trip to diani for 2 people for 4 days")

    assert "What exact dates are you planning for those 4 days?" in result
    assert "Slate808 Output" not in result


def test_duration_only_timing_answer_is_accepted_but_still_requires_exact_dates():
    run("Plan a trip to diani for 2 people")
    result = run("for 4 days")

    assert "What exact dates are you planning for those 4 days?" in result
    assert "Slate808 Output" not in result


def test_numeric_separation_people_budget_and_duration():
    brief = build_travel_brief(
        "Plan a trip to diani for 5 people with a budget of 20000 for 3 days"
    )

    assert brief["traveller_count"] == 5
    assert brief["budget_amount"] == 20000
    assert brief["budget_level"] == "low"
    assert brief["timing"]["state"] == "duration_only"
    assert brief["timing"]["duration_days"] == 3


def test_numeric_separation_couples_budget_and_duration():
    brief = build_travel_brief(
        "Plan a trip to naivasha for 2 couples and a budget of 30000 for 3 days"
    )

    assert brief["destination"] == "naivasha"
    assert brief["traveller_count"] == 4
    assert brief["budget_amount"] == 30000
    assert brief["budget_level"] == "low"
    assert brief["timing"]["state"] == "duration_only"
    assert brief["timing"]["duration_days"] == 3


def test_numeric_separation_does_not_contaminate_timing_or_budget():
    brief = build_travel_brief(
        "Plan a trip to diani for 4 people next weekend with a budget of 45000"
    )

    assert brief["destination"] == "diani"
    assert brief["traveller_count"] == 4
    assert brief["budget_amount"] == 45000
    assert brief["timing"]["state"] == "relative_timing"
    assert brief["timing"]["raw_text"] == "next weekend"


def test_budget_visibility_numeric_budget_and_level_appear_in_output():
    result = run("Plan a trip to diani for 2 people 10 April to 12 April budget is 45000")

    assert "- Budget: 45000 (low)" in result
    assert "Budget Level:" not in result


@pytest.mark.parametrize(
    ("trip_request", "expected_budget_line"),
    [
        ("Plan a cheap trip to diani for 2 people 10 April to 12 April", "- Budget Level: low"),
        ("Plan a luxury trip to diani for 2 people 10 April to 12 April", "- Budget Level: high"),
    ],
)
def test_budget_visibility_signal_based_levels_appear_in_output(trip_request, expected_budget_line):
    result = run(trip_request)

    assert expected_budget_line in result


def test_formatter_shows_zero_budget_amount():
    final_output = {
        "status": "pass",
        "goal": "Test",
        "steps": [],
        "checks": [],
        "risks": [],
        "brief": {
            "destination": "diani",
            "traveller_count": 2,
            "timing": {"state": "relative_timing", "raw_text": "next weekend"},
            "budget_amount": 0,
            "budget_level": "low",
            "trip_mood": None,
        },
    }

    output = format_output(final_output)
    assert "- Budget: 0 (low)" in output


def test_trip_output_regressions_stay_fixed():
    result = run_engine("Plan a trip to naivasha for 2 people next weekend")
    steps = _extract_numbered_steps(result)

    assert "Travel Brief:" in result
    assert "Destination: naivasha" in result
    assert "transport" in result.lower()
    assert "Gather necessary resources" not in result
    assert "Define a smooth arrival" not in result
    assert "Shape the timing of the journey" not in result
    assert len(steps) == len(set(step.lower() for step in steps))


def test_family_relative_timing_step_is_checker_safe_and_concrete():
    plan = generate_plan("Plan a family trip to the coast for 4 people next weekend")
    timing_step = plan["steps"][4].lower()

    assert "next weekend" in timing_step
    assert "align bookings" in timing_step
    assert "manageable pacing" not in timing_step
    assert "clear transitions" not in timing_step
    assert checker.check_plan(plan)["status"] == "pass"


def test_duration_only_timing_step_is_concrete():
    plan = generate_plan("Plan a family trip to diani for 4 people for 2 nights")
    timing_step = plan["steps"][4].lower()

    assert "2 nights" in timing_step
    assert "align transport and accommodation" in timing_step
    assert checker.check_plan(plan)["status"] == "pass"


def test_shorthand_trip_inputs_classify_as_trip():
    assert detect_task_type("Mt kenya for 2 night with a group of 4. Budget is 1200000") == "trip"
    assert detect_task_type("Coast for 3 nights with a Budget of 120000") == "trip"


def test_shorthand_trip_inputs_route_to_trip_pipeline():
    result = run_engine("Coast for 3 nights with a Budget of 120000")

    assert "Travel Brief:" in result
    assert "Destination: coast" in result
    assert "Timing: 3 nights" in result


def test_non_travel_requests_fail_clearly():
    result = run_engine("Plan a meeting agenda for Monday")

    assert is_travel_intent("Plan a meeting agenda for Monday") is False
    assert "Slate808 Output" in result
    assert "Status: fail" in result
    assert "Slate808 currently supports travel planning only." in result
    assert "Break down the task into components" not in result
    assert "Gather necessary resources" not in result


def test_generate_plan_non_travel_returns_failure_without_generic_steps():
    plan = generate_plan("Plan a meeting agenda for Monday")

    assert plan["task_type"] == "unsupported"
    assert plan["status"] == "fail"
    assert plan["errors"] == ["Slate808 currently supports travel planning only."]
    assert plan["steps"] == []


def test_clarification_rebuild_does_not_insert_at_for_days():
    run("Plan a trip to diani for 5 people")
    result = run("for 3 days")

    assert "What exact dates are you planning for those 3 days?" in result
    assert "Slate808 Output" not in result
    assert "at for 3 days" not in result


def test_destination_extraction_avoids_action_prefix_capture():
    brief = build_travel_brief("Execute a travel plan for zanzibar for 2 people next weekend")

    assert brief["destination"] == "zanzibar"


@pytest.mark.parametrize("text", ["10 april to", "10 april to may", "10 april to 12"])
def test_incomplete_timing_range_remains_unusable(text):
    timing = extract_timing(text)

    assert timing["state"] == "missing_timing"
    assert summarize_timing(timing) == "timing not specified"


def test_clarification_rebuild_does_not_insert_at_for_weeks():
    run("Plan a trip to kisumu for 6 people")
    result = run("for 4 weeks")

    assert "What exact dates are you planning for those 4 weeks?" in result
    assert "Slate808 Output" not in result
    assert "at for 4 weeks" not in result


def test_malformed_destination_prefix_cleanup_works():
    brief = build_travel_brief("Plan a trip to travelto coast for 5 people at may")

    assert brief["destination"] == "coast"
    assert brief["timing"]["state"] == "month_only"


@pytest.mark.parametrize(
    ("text", "destination"),
    [
        ("Maybe Diani next month for 2 people", "diani"),
        ("Possibly Watamu for 2 people 10 April to 12 April", "watamu"),
        ("at the coast for 2 people 10 April to 12 April", "coast"),
        ("Diani sometime next month for 2 people", "diani"),
        ("Plan a trip to Diani for 2 people next month", "diani"),
        ("Coast next month for 2 people", "coast"),
        ("Plan a trip to the coast for 2 people 10 April to 12 April", "coast"),
        ("Plan a trip to Mara for 2 people 10 April to 12 April", "maasai mara"),
        ("Plan a trip to the Mara for 2 people 10 April to 12 April", "maasai mara"),
    ],
)
def test_destination_cleanup_removes_weak_prefixes_and_timing_leakage(
    text,
    destination,
):
    brief = build_travel_brief(text)

    assert brief["destination"] == destination


def test_destination_canonical_registry_preserves_clean_known_destination():
    brief = build_travel_brief("Plan a trip to Diani for 2 people 10 April to 12 April")

    assert brief["destination"] == "diani"


@pytest.mark.parametrize(
    "text",
    [
        "I need an escape next month",
        "I need a weekend away next month",
    ],
)
def test_destination_cleanup_preserves_non_destination_phrases(text):
    brief = build_travel_brief(text)

    assert brief["destination"] is None


@pytest.mark.parametrize(
    "text",
    [
        "Could you help me do like a small getaway for us",
        "Help me set up a trip",
        "Set up a trip for 2 Jan.",
        "I want to travel from Jan 18-20",
        "Plan a trip to book a solo trip for 1 people at tomorrow",
        "Let’s plan a trip — ask me whatever you need to continue.",
    ],
)
def test_contaminated_destination_routes_to_destination_clarification(text):
    result = run(text)

    assert "Where would you like to go?" in result
    assert "Slate808 Output" not in result


@pytest.mark.parametrize("destination", ["coast"])
def test_supported_flexible_destinations_still_plan(destination):
    result = run(f"Plan a trip to {destination} for 2 people 10 April to 12 April")

    assert "Slate808 Output" in result
    assert f"Destination: {destination}" in result
    assert "Where would you like to go?" not in result


@pytest.mark.parametrize(
    "text",
    [
        "Plan a trip to Mombassa or Dianii for 2 people 10 April to 12 April",
        "maybe the coast or mara next month for two, romantic but flexible",
        "romantic getaway maybe Naivasha maybe coast sometime in June",
        "I want something romantic, maybe Naivasha maybe coast, for two in August",
    ],
)
def test_multi_option_destination_phrases_route_to_destination_clarification(text):
    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] is None
    assert "Where would you like to go?" in result
    assert "Destination:" not in result


@pytest.mark.parametrize(
    "text",
    [
        "somewhere warm for 2 people 10 April to 12 April",
        "near Nairobi for 2 people 10 April to 12 April",
        "near Diani for 2 people 10 April to 12 April",
        "outside Kenya for 2 people 10 April to 12 April",
    ],
)
def test_ambiguous_destination_phrases_route_to_destination_clarification(text):
    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] is None
    assert "Where would you like to go?" in result
    assert "Slate808 Output" not in result


def test_soft_travel_scaffolding_preserves_safe_at_place_hint():
    brief = build_travel_brief("We need a short break at the coast 10 April to 12 April")
    result = run("We need a short break at the coast 10 April to 12 April")

    assert brief["destination"] == "coast"
    assert "Destination: we need a short break" not in result
    assert "How many travellers?" in result
    assert "Where would you like to go?" not in result


def test_soft_travel_scaffolding_preserves_safe_in_place_hint():
    brief = build_travel_brief("I need a break in Diani 10 April to 12 April")
    result = run("I need a break in Diani 10 April to 12 April")

    assert brief["destination"] == "diani"
    assert "Destination: i need a break" not in result
    assert "How many travellers?" in result


def test_soft_travel_relational_place_hint_still_clarifies_destination():
    brief = build_travel_brief("I want a getaway near Naivasha 10 April to 12 April")
    result = run("I want a getaway near Naivasha 10 April to 12 April")

    assert brief["destination"] is None
    assert "Where would you like to go?" in result
    assert "Slate808 Output" not in result


def test_quiet_break_in_place_hint_is_preserved_with_shaping_fields():
    text = "Can you sort a quiet break in Watamu for 3 people, low budget, probably mid June"

    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] == "watamu"
    assert brief["budget_level"] == "low"
    assert brief["timing"]["state"] == "month_only"
    assert "exact dates in June" in result
    assert "Where would you like to go?" not in result


def test_comma_shaped_quiet_break_in_place_hint_is_preserved():
    text = "Quiet break in Watamu, low budget, mid June"

    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] == "watamu"
    assert brief["budget_level"] == "low"
    assert brief["timing"]["state"] == "month_only"
    assert "Which exact dates in June are you planning?" in result
    assert "Destination: quiet break" not in result


def test_comma_shaped_calm_break_in_place_hint_is_preserved():
    brief = build_travel_brief("Calm break in Diani, medium budget, mid June")

    assert brief["destination"] == "diani"
    assert brief["budget_level"] == "medium"


def test_comma_shaped_near_place_hint_remains_clarification_safe():
    text = "Quiet break near Naivasha, low budget, mid June"

    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] is None
    assert "Where would you like to go?" in result
    assert "Destination: naivasha" not in result


def test_calm_break_in_place_hint_is_preserved():
    brief = build_travel_brief("Can you sort a calm break in Diani for 2 people 10 April to 12 April")

    assert brief["destination"] == "diani"


def test_quiet_break_near_place_hint_remains_clarification_safe():
    text = "Can you sort a quiet break near Naivasha for 2 people"

    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] is None
    assert "Where would you like to go?" in result
    assert "Destination: naivasha" not in result


@pytest.mark.parametrize(
    ("text", "destination"),
    [
        ("Book out a calm Watamu trip for 4 people 18 June to 21 June", "watamu"),
        ("Organize a luxury Nairobi staycation for 2 people 14 July to 16 July", "nairobi"),
        ("Book a coast getaway for two tomorrow", "coast"),
        ("Set up a Mara trip for 4 people this month", "maasai mara"),
        ("Plan a Diani beach trip for 2 people 10 April to 12 April", "diani"),
        ("Plan a quiet low-key Naivasha trip for 2 people on a medium budget 10 April to 12 April", "naivasha"),
    ],
)
def test_modifier_place_travel_noun_destination_is_preserved(text, destination):
    brief = build_travel_brief(text)

    assert brief["destination"] == destination


def test_loose_thing_destination_candidate_does_not_pollute_destination():
    text = "Thinking maybe a chilled coast thing for me and my partner sometime in July"

    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] is None
    assert "Destination: thinking maybe a chilled coast thing" not in result
    assert "Where would you like to go?" in result


@pytest.mark.parametrize(
    "text",
    [
        "Looking for a short, affordable trip — maybe 2 nights.",
        "Maybe a quick escape this month, something not too pricey.",
        "Help me plan a quick escape this month, for two",
    ],
)
def test_scouting_scaffold_destination_candidate_does_not_pollute_destination(text):
    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] is None
    assert "Where would you like to go?" in result


@pytest.mark.parametrize(
    "text",
    [
        "I want a simple stay, Nairobi, tomorrow maybe",
        "I want a simple stay for 2 adults, Nairobi, tomorrow maybe",
    ],
)
def test_simple_stay_comma_place_hint_is_preserved(text):
    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] == "nairobi"
    assert "Destination: i want a simple stay" not in result
    assert "exact dates" in result


def test_polluted_loose_thing_with_known_fields_keeps_destination_first():
    text = "Thinking maybe a chilled coast thing for 2 people 10 April to 12 April"

    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] is None
    assert "Where would you like to go?" in result
    assert "How many travellers?" not in result
    assert "Slate808 Output" not in result


def test_polluted_relational_trip_destination_does_not_execute():
    text = "I need a trip near Nairobi for 3 people 8 June to 10 June"

    brief = build_travel_brief(text)
    result = run(text)

    assert brief["destination"] is None
    assert "Where would you like to go?" in result
    assert "Slate808 Output" not in result


def test_destination_contamination_repeated_calls_are_deterministic():
    text = "Plan a trip to book a solo trip for 1 people at tomorrow"

    first = build_travel_brief(text)
    second = build_travel_brief(text)

    assert first == second
    assert first["destination"] is None


def test_planning_policy_logs_decision_trace(monkeypatch):
    logged = []

    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: logged.append((filename, line)))

    brief = build_travel_brief("Plan a family trip to the coast for 4 people next weekend with a budget of 45000")
    constraints = derive_planning_constraints(brief, trace_id="trace-engine-1")

    assert logged
    assert logged[0][0] == "decisions.log"
    assert "'trace_id': 'trace-engine-1'" in logged[0][1]
    assert "constraint_policy" in logged[0][1]
    assert "conflict_flags" in logged[0][1]
    assert "refinement_flags" in logged[0][1]
    assert constraints["timing_policy"]["is_timing_usable"] is False


def test_rules_loading_is_path_safe(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    rules = checker.load_rules()

    assert rules["min_steps"] == 3


def test_runner_does_not_call_llm_when_disabled(monkeypatch):
    called = {"count": 0}

    def fake_llm(request):
        called["count"] += 1
        return None

    monkeypatch.setattr("engine.runner.generate_with_llm", fake_llm)
    monkeypatch.setattr("engine.runner.is_llm_enabled", lambda: False)

    result = run_engine("Plan a trip to diani for 2 people next weekend")

    assert called["count"] == 0
    assert "Slate808 Output" in result


def test_runner_falls_back_to_deterministic_when_llm_enabled_but_fails(monkeypatch):
    called = {"count": 0}

    def fail_llm(request):
        called["count"] += 1
        raise RuntimeError("LLM failed")

    monkeypatch.setattr("engine.runner.generate_with_llm", fail_llm)
    monkeypatch.setattr("engine.runner.is_llm_enabled", lambda: True)

    result = run_engine("Plan a trip to diani for 2 people next weekend")

    assert called["count"] == 0
    assert "Slate808 Output" in result
    assert "Destination: diani" in result


def test_mood_driven_relaxed_plan_content():
    result = run_engine("Plan a relaxed trip to diani for 2 people next weekend")
    steps = _extract_numbered_steps(result)

    assert "transport" in steps[2].lower()
    assert "smooth" in steps[2].lower() or "low-friction" in steps[2].lower()
    assert "restful" in steps[3].lower()
    assert "timing" in steps[4].lower()
    assert "relaxed" in steps[4].lower()


def test_mood_driven_adventure_plan_content():
    result = run_engine("Plan an adventure trip to mara for 3 people for 5 days")
    steps = _extract_numbered_steps(result)

    assert "transport" in steps[2].lower()
    assert "active" in steps[2].lower()
    assert "adventur" in steps[3].lower()
    assert "timing" in steps[4].lower()
    assert "active" in steps[4].lower()


def test_mood_driven_luxury_plan_content():
    result = run_engine("Plan a luxury trip to zanzibar for 2 people next month")
    steps = _extract_numbered_steps(result)

    assert "budget" in steps[1].lower()
    assert "premium" in steps[1].lower()
    assert "transport" in steps[2].lower()
    assert "comfortable" in steps[2].lower()
    assert "high-quality" in steps[3].lower() or "curated" in steps[3].lower()


def test_mood_driven_romantic_plan_content():
    result = run_engine("Plan a romantic getaway to nairobi for 2 people for 3 days")
    steps = _extract_numbered_steps(result)

    assert "intimate" in steps[3].lower() or "shared" in steps[3].lower()
    assert "timing" in steps[4].lower()
    assert "unrushed" in steps[4].lower() or "special" in steps[4].lower()


def test_mood_driven_family_plan_content():
    result = run_engine("Plan a family trip to the coast for 4 people next weekend")
    steps = _extract_numbered_steps(result)

    assert "transport" in steps[2].lower()
    assert "family" in steps[2].lower()
    assert "family-friendly" in steps[3].lower()
    assert "timing" in steps[4].lower()
    assert "next weekend" in steps[4].lower()
    assert "align bookings" in steps[4].lower()


def test_mood_driven_corporate_plan_content():
    result = run_engine("Plan a corporate team retreat to nairobi for 10 people for 2 days")
    steps = _extract_numbered_steps(result)

    assert "budget" in steps[1].lower()
    assert "team" in steps[1].lower() or "logistics" in steps[1].lower()
    assert "transport" in steps[2].lower()
    assert "coordination" in steps[2].lower() or "efficien" in steps[2].lower()
    assert "structured" in steps[3].lower()
    assert "timing" in steps[4].lower()
    assert "efficient" in steps[4].lower()


def test_mood_influence_preserves_transport_and_timing_coverage():
    result = run_engine("Plan a corporate retreat to nairobi for 8 people next month")
    steps = _extract_numbered_steps(result)
    joined = " ".join(steps).lower()

    assert "transport" in joined
    assert "timing" in joined
    assert len(steps) == 5
    assert len(steps) == len(set(step.lower() for step in steps))


def test_no_mood_preserves_default_plan_behavior():
    result = run_engine("Plan a trip to diani for 2 people next weekend")
    steps = _extract_numbered_steps(result)
    joined = " ".join(steps).lower()

    for forbidden in ["calm", "restful", "active", "premium", "intimate", "family-friendly", "efficient", "team"]:
        assert forbidden not in joined


@pytest.mark.parametrize(
    ("trip_request", "expected_mood", "expected_phrase"),
    [
        ("Plan a cheap relaxed trip to diani for 2 people next weekend", "relaxed", "smooth"),
        ("Plan a romantic luxury getaway to zanzibar for 2 people next month", "romantic", "intimate"),
        ("Plan a family trip to mombasa for 5 people next weekend", "family", "family-friendly"),
        ("Plan a corporate retreat to nairobi for 12 people next month", "corporate", "efficient"),
        ("Plan an adventure trip to mara for 3 people 10-14 April", "adventure", "adventur"),
    ],
)
def test_mood_regressions_for_special_inputs(trip_request, expected_mood, expected_phrase):
    brief = build_travel_brief(trip_request)
    assert brief["trip_mood"] == expected_mood

    result = run_engine(trip_request)
    steps = _extract_numbered_steps(result)
    joined = " ".join(steps).lower()
    assert expected_phrase in joined


def test_mood_extraction_relaxed():
    brief = build_travel_brief("Plan a relaxed trip to diani for 2 people next weekend")
    assert brief["trip_mood"] == "relaxed"


def test_mood_extraction_adventure():
    brief = build_travel_brief("Plan an adventure trip to mara for 3 people for 5 days")
    assert brief["trip_mood"] == "adventure"


def test_mood_extraction_luxury():
    brief = build_travel_brief("Plan a luxury getaway to zanzibar for 2 people")
    assert brief["trip_mood"] == "luxury"


def test_mood_extraction_romantic():
    brief = build_travel_brief("Plan a romantic getaway to nairobi for 2 people next month")
    assert brief["trip_mood"] == "romantic"


def test_mood_extraction_family():
    brief = build_travel_brief("Plan a family trip to the coast for 5 people next weekend")
    assert brief["trip_mood"] == "family"


def test_mood_extraction_corporate():
    brief = build_travel_brief("Plan a corporate team retreat for 20 people next month")
    assert brief["trip_mood"] == "corporate"


def test_mood_extraction_none_when_no_signal():
    brief = build_travel_brief("Plan a trip to diani for 2 people next weekend")
    assert brief["trip_mood"] is None


def test_mood_extraction_quiet_low_key_maps_to_relaxed():
    brief = build_travel_brief("Plan a quiet low-key trip to naivasha for 2 people 10 April to 12 April")
    assert brief["trip_mood"] == "relaxed"


def test_mood_extraction_none_when_only_budget_signal():
    brief = build_travel_brief("Plan a trip to diani for 2 people next weekend with a budget of 50000")
    assert brief["trip_mood"] is None


def test_mood_extraction_priority_romantic_over_family():
    brief = build_travel_brief("Plan a romantic family getaway for 2 people next weekend")
    assert brief["trip_mood"] == "romantic"


def test_mood_extraction_priority_corporate_over_relaxed():
    brief = build_travel_brief("Plan a corporate team retreat for a relaxed atmosphere")
    assert brief["trip_mood"] == "corporate"


def test_mood_extraction_does_not_break_budget_extraction():
    brief = build_travel_brief("Plan a luxury trip to diani for 2 people with a budget of 100000")
    assert brief["trip_mood"] == "luxury"
    assert brief["budget_amount"] == 100000
    assert brief["budget_level"] == "high"


def test_mood_extraction_does_not_break_traveller_extraction():
    brief = build_travel_brief("Plan an adventure trip for 5 couples next weekend")
    assert brief["trip_mood"] == "adventure"
    assert brief["traveller_count"] == 10


def test_mood_extraction_does_not_break_timing_extraction():
    brief = build_travel_brief("Plan a relaxed trip to mara for 2 people for 4 days")
    assert brief["trip_mood"] == "relaxed"
    assert brief["timing"]["state"] == "duration_only"
    assert brief["timing"]["duration_days"] == 4


def test_mood_extraction_all_moods_visible_in_output():
    reset_state()
    moods_and_requests = [
        ("relaxed", "Plan a relaxed trip to diani for 2 people next weekend"),
        ("adventure", "Plan an adventure trip to mara for 3 people for 5 days"),
        ("luxury", "Plan a luxury trip to zanzibar for 2 people next month"),
        ("romantic", "Plan a romantic getaway to nairobi for 2 people for 3 days"),
        ("family", "Plan a family trip to the coast for 4 people next weekend"),
        ("corporate", "Plan a corporate team retreat to nairobi for 10 people for 2 days"),
    ]

    for mood, request in moods_and_requests:
        reset_state()
        result = run(request)
        assert f"- Trip Mood: {mood}" in result, f"Expected mood '{mood}' not found in output for request: {request}"
