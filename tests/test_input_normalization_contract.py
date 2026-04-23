from engine.clarification_runner import reset_state, run
from contracts.input_normalization_contract import normalize_travel_input
from engine.travel_brief import build_travel_brief


def setup_function():
    reset_state()


def test_whitespace_collapse():
    result = normalize_travel_input("Plan   a   trip   to   Amboseli")

    assert result.normalized_input == "Plan a trip to Amboseli"
    assert result.applied_rules == ["whitespace_collapse"]


def test_comma_spacing_cleanup():
    result = normalize_travel_input("Plan a trip for 2 weeks,KES 600000")

    assert result.normalized_input == "Plan a trip for 2 weeks, KES 600000"
    assert result.applied_rules == ["punctuation_spacing_cleanup"]


def test_glued_token_repair():
    result = normalize_travel_input("Plan a trip toamboseli")

    assert result.normalized_input == "Plan a trip to amboseli"
    assert "explicit_replacement:\\btoamboseli\\b->to amboseli" in result.applied_rules


def test_typo_map_repair():
    result = normalize_travel_input("Plan a trip to coasta rico")

    assert result.normalized_input == "Plan a trip to costa rica"
    assert "explicit_replacement:\\bcoasta rico\\b->costa rica" in result.applied_rules


def test_multiple_rules_in_one_input():
    result = normalize_travel_input("  Plana   trip toamboseli for group of8,KES 600000  ")

    assert result.normalized_input == "plan a trip to amboseli for group of 8, KES 600000"
    assert result.applied_rules == [
        "explicit_replacement:\\bplana\\b->plan a",
        "explicit_replacement:\\btoamboseli\\b->to amboseli",
        "explicit_replacement:\\bgroup of8\\b->group of 8",
        "punctuation_spacing_cleanup",
        "whitespace_collapse",
    ]


def test_repeated_call_determinism():
    user_input = "Plan a trip toamboseli for 2 weeks,KES 600000 and group of8"

    first = normalize_travel_input(user_input)
    second = normalize_travel_input(user_input)

    assert first.model_dump() == second.model_dump()


def test_live_run_path_uses_normalized_destination_repair():
    result = run("Plan a trip toamboseli for 2 weeks,KES 600000 and 4 travellers")

    assert "Where would you like to go?" not in result
    assert "What exact dates are you planning for those 2 weeks?" in result


def test_just_me_normalizes_to_extractable_traveller_count():
    result = normalize_travel_input("Plan a trip to Diani just me 10 April to 12 April")
    brief = build_travel_brief(result.normalized_input)

    assert brief["traveller_count"] == 1
    assert "traveller_phrase_normalization:\\bjust me\\b->for 1 person" in result.applied_rules


def test_me_and_my_partner_normalizes_to_extractable_traveller_count():
    result = normalize_travel_input("Thinking maybe a trip to Diani for me and my partner next month")
    brief = build_travel_brief(result.normalized_input)

    assert brief["traveller_count"] == 2
    assert "traveller_phrase_normalization:\\bme and my partner\\b->2 people" in result.applied_rules


def test_two_adults_and_one_teen_normalizes_to_extractable_traveller_count():
    result = normalize_travel_input("Plan a trip to Nanyuki for two adults and one teen")
    brief = build_travel_brief(result.normalized_input)

    assert brief["traveller_count"] == 3
    assert (
        "traveller_phrase_normalization:\\btwo adults and one teen\\b->3 people"
        in result.applied_rules
    )


def test_en_dash_date_range_normalizes_to_stable_range_form():
    result = normalize_travel_input("Plan a trip to Nanyuki 18–20 September")
    brief = build_travel_brief(result.normalized_input)

    assert result.normalized_input == "Plan a trip to Nanyuki 18-20 September"
    assert brief["timing"]["raw_text"] == "18 september to 20 september"
    assert "date_range_separator_normalization" in result.applied_rules


def test_glued_month_date_range_normalizes_to_stable_range_form():
    result = normalize_travel_input("Plan a trip to Diani 3rd June to 4thJune")
    brief = build_travel_brief(result.normalized_input)

    assert result.normalized_input == "Plan a trip to Diani 3rd June to 4th June"
    assert brief["timing"]["state"] == "exact_timing"
    assert brief["timing"]["start_date"] == "3rd june"
    assert brief["timing"]["end_date"] == "4th june"
    assert "date_token_spacing_normalization" in result.applied_rules


def test_live_path_just_me_keeps_destination_clean():
    result = run("Plan a trip to Diani just me 10 April to 12 April")

    assert "Destination: diani" in result
    assert "Destination: diani solo" not in result
    assert "Traveller Count: 1" in result
    assert "Timing: 10 april to 12 april" in result


def test_ellipsis_noise_keeps_destination_timing_and_travellers_extractable():
    result = normalize_travel_input("Diani... 10 April to 12 April, 2 people")
    brief = build_travel_brief(f"Plan a trip to {result.normalized_input}")

    assert result.normalized_input == "Diani, 10 April to 12 April, 2 people"
    assert brief["destination"] == "diani"
    assert brief["traveller_count"] == 2
    assert brief["timing"]["raw_text"] == "10 april to 12 april"
    assert "punctuation_noise_normalization" in result.applied_rules


def test_repeated_comma_noise_keeps_destination_and_timing_extractable():
    result = normalize_travel_input("Watamu,, next month")
    brief = build_travel_brief(f"Plan a trip to {result.normalized_input}")

    assert result.normalized_input == "Watamu, next month"
    assert brief["destination"] == "watamu"
    assert brief["timing"]["raw_text"] == "next month"
    assert "punctuation_noise_normalization" in result.applied_rules


def test_idk_filler_before_destination_does_not_pollute_destination():
    result = normalize_travel_input("Plan a trip to idk, maybe Diani, 2 people")
    brief = build_travel_brief(result.normalized_input)

    assert result.normalized_input == "Plan a trip to Diani, 2 people"
    assert brief["destination"] == "diani"
    assert brief["traveller_count"] == 2
    assert "conversational_fragment_normalization" in result.applied_rules


def test_hmm_filler_before_destination_does_not_pollute_destination():
    result = normalize_travel_input("Plan a trip to hmm Watamu... just me")
    brief = build_travel_brief(result.normalized_input)

    assert result.normalized_input == "Plan a trip to Watamu, for 1 person"
    assert brief["destination"] == "watamu"
    assert brief["traveller_count"] == 1
    assert "punctuation_noise_normalization" in result.applied_rules
    assert "conversational_fragment_normalization" in result.applied_rules


def test_maybe_fragment_around_destination_and_timing_does_not_pollute_destination():
    result = normalize_travel_input("Plan a trip to Watamu maybe... 4th-8 march for 2 people")
    brief = build_travel_brief(result.normalized_input)

    assert result.normalized_input == "Plan a trip to Watamu, 4th-8 march for 2 people"
    assert brief["destination"] == "watamu"
    assert brief["traveller_count"] == 2
    assert brief["timing"]["raw_text"] == "4th march to 8 march"
    assert "punctuation_noise_normalization" in result.applied_rules
    assert "conversational_fragment_normalization" in result.applied_rules
