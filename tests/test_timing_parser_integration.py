from engine.clarification_runner import reset_state, run
from engine.travel_brief import build_travel_brief


def setup_function():
    reset_state()


def _assert_exact_timing(user_input: str, expected_date: str):
    brief = build_travel_brief(user_input)
    output = run(user_input)

    assert brief["timing"]["state"] == "exact_timing"
    assert brief["timing"]["raw_text"] == expected_date
    assert brief["timing"]["start_date"] == expected_date
    assert brief["timing"]["confidence"] == "high"
    display_date = expected_date.replace("april", "April").replace("july", "July").replace("january", "January").replace("may", "May")
    assert f"- Timing: {display_date}" in output


def test_live_timing_parser_preserves_kisumu_exact_date():
    _assert_exact_timing(
        "Plan a trip to kisumu for 5 people at 21st april",
        "21 april",
    )


def test_live_timing_parser_preserves_rwanda_exact_date():
    _assert_exact_timing(
        "Plan a trip to rwanda for 1 people at 3rd july",
        "3 july",
    )


def test_live_timing_parser_preserves_wasini_exact_date_with_budget():
    _assert_exact_timing(
        "Plan a trip to wasini islands for 4 people at 5th january with a low budget",
        "5 january",
    )


def test_live_timing_parser_preserves_watamu_exact_date():
    _assert_exact_timing(
        "Plan a trip to watamu for 6 people at 4th may",
        "4 may",
    )


def test_live_timing_parser_exact_date_is_deterministic():
    user_input = "Plan a trip to kisumu for 5 people at 21st april"

    first = build_travel_brief(user_input)
    second = build_travel_brief(user_input)

    assert first["timing"] == second["timing"]
