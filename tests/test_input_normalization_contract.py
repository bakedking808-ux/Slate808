from engine.clarification_runner import reset_state, run
from input_normalization_contract import normalize_travel_input


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
