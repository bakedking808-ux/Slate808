from engine.clarification_runner import run, reset_state


def assert_contains(output: str, expected: str, case_name: str) -> None:
    if expected.lower() not in output.lower():
        print("\nFAIL:", case_name)
        print("Expected to find:", expected)
        print("Actual output:")
        print(output)
        raise AssertionError(case_name)


def assert_not_contains(output: str, unexpected: str, case_name: str) -> None:
    if unexpected.lower() in output.lower():
        print("\nFAIL:", case_name)
        print("Did not expect to find:", unexpected)
        print("Actual output:")
        print(output)
        raise AssertionError(case_name)


def case_aug_23_30_resolves_range():
    reset_state()
    run("Plan a trip to Naivasha for 3 people")
    out = run("Aug 23-30")

    assert_contains(out, "23 august to 30 august", "Aug 23-30 resolves to exact range")
    assert_contains(out, "What kind of trip mood should this have?", "Aug 23-30 advances to mood")


def case_missing_month_prompts_correction():
    reset_state()
    run("Plan a trip to Naivasha for 3 people")
    out = run("23-30")

    assert_contains(out, "month", "23-30 asks for month")


def case_aug_2_is_timing_not_traveller():
    reset_state()
    run("Plan a trip to Naivasha for 3 people")
    out = run("Aug 2")

    assert_contains(out, "2 august", "Aug 2 resolves as timing")
    assert_contains(out, "What kind of trip mood should this have?", "Aug 2 advances to mood")


def case_80000k_is_corrected():
    reset_state()
    run("Plan a trip to Nakuru")
    out = run("80000K")

    assert_contains(out, "Please enter the budget as either 80k or 80,000", "80000K correction")


def case_budget_80k_not_traveller_count():
    reset_state()
    run("Plan a trip to Nakuru")
    run("4th-8th May")
    out = run("Budget 80k")

    assert_contains(out, "Budget noted", "Budget 80k is captured as budget")
    assert_contains(out, "How many travellers?", "Budget 80k returns to traveller question")


def case_watamu_next_month_preserves_destination():
    reset_state()
    run("Plan a trip")
    out = run("Watamu next month")

    assert_contains(out, "What exact dates are you planning for next month?", "Watamu next month asks exact dates")


def case_actually_watamu_replaces_destination_and_travellers():
    reset_state()
    run("Plan a trip to Diani 10 April to 12 April")
    out = run("Actually Watamu, 3 people")

    assert_contains(out, "- Destination: watamu", "Actually Watamu replaces destination")
    assert_contains(out, "- Traveller Count: 3", "Actually Watamu captures traveller count")
    assert_contains(out, "10 april to 12 april", "Actually Watamu preserves timing")


def case_actually_diani_preserves_travellers():
    reset_state()
    run("Plan a trip to Watamu 10 April to 12 April")
    run("3 people")
    out = run("Actually Diani")

    assert_contains(out, "- Destination: diani", "Actually Diani updates destination")
    assert_contains(out, "- Traveller Count: 3", "Actually Diani preserves traveller count")


def case_interrupt_with_timing_returns_to_mood():
    reset_state()
    run("Plan a trip to Naivasha for 3 people")
    run("next weekend")
    out = run("Aug 23-30")

    assert_contains(out, "23 august to 30 august", "Interrupt timing captures exact range")
    assert_contains(out, "What kind of trip mood should this have?", "Interrupt timing advances to mood")


def case_correction_style_timing_update_replaces_relative_timing():
    reset_state()
    run("Plan a trip to Naivasha for 3 people")
    run("next weekend")
    out = run("Wait, actually Aug 23-30")

    assert_contains(out, "23 august to 30 august", "Correction-style timing capture exact range")
    assert_contains(out, "What kind of trip mood should this have?", "Correction-style timing advances to mood")


def case_escape_resolves_relaxed_mood():
    reset_state()
    run("Plan a trip to Watamu")
    run("10 April to 12 April")
    run("3 people")
    out = run("escape")

    assert_contains(out, "- Trip Mood: relaxed", "escape resolves to relaxed mood")


def case_beach_escape_resolves_relaxed_mood():
    reset_state()
    run("Plan a trip to Watamu")
    run("10 April to 12 April")
    run("3 people")
    out = run("beach escape")

    assert_contains(out, "- Trip Mood: relaxed", "beach escape resolves to relaxed mood")


def case_solo_resolves_traveller_count_when_active():
    reset_state()
    run("Plan a trip to Watamu 10 April to 12 April")
    out = run("solo")

    assert_contains(out, "- Traveller Count: 1", "solo resolves traveller count when traveller count is active")


def case_solo_does_not_resolve_as_mood():
    reset_state()
    run("Plan a trip to Watamu")
    run("10 April to 12 April")
    run("1 person")
    out = run("solo")

    assert_contains(out, "What kind of trip mood should this have?", "solo does not satisfy mood clarification")
    assert_not_contains(out, "- Trip Mood:", "solo must not become trip mood")


CASES = [
    case_aug_23_30_resolves_range,
    case_missing_month_prompts_correction,
    case_aug_2_is_timing_not_traveller,
    case_80000k_is_corrected,
    case_budget_80k_not_traveller_count,
    case_watamu_next_month_preserves_destination,
    case_actually_watamu_replaces_destination_and_travellers,
    case_actually_diani_preserves_travellers,
    case_interrupt_with_timing_returns_to_mood,
    case_correction_style_timing_update_replaces_relative_timing,
    case_escape_resolves_relaxed_mood,
    case_beach_escape_resolves_relaxed_mood,
    case_solo_resolves_traveller_count_when_active,
    case_solo_does_not_resolve_as_mood,
]


def main():
    print("Post-IOC Regression Harvest")
    print("===========================")

    passed = 0

    for case in CASES:
        case()
        passed += 1
        print(f"PASS: {case.__name__}")

    print("===========================")
    print(f"{passed}/{len(CASES)} cases passed")


if __name__ == "__main__":
    main()
