from engine.planning_policy import derive_planning_constraints
from engine.travel_brief import build_timing


def _brief(**overrides):
    brief = {
        "destination": "diani",
        "traveller_count": 2,
        "timing": build_timing(),
        "budget_amount": None,
        "budget_level": "unspecified",
        "trip_mood": None,
    }
    brief.update(overrides)
    return brief


def test_constraint_policy_derives_expected_flags_from_family_month_only_brief(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    constraints = derive_planning_constraints(
        _brief(
            traveller_count=5,
            trip_mood="family",
            budget_level="low",
            timing=build_timing(
                raw_text="april",
                date_flexibility="flexible",
                state="month_only",
                confidence="low",
            ),
        )
    )

    policy = constraints["constraint_policy"]
    compatibility = constraints["global_flags"]["constraints"]

    assert policy["family_safe"] is True
    assert policy["kids_present"] is True
    assert policy["low_risk"] is True
    assert policy["avoid_premium"] is True
    assert policy["value_focused"] is True
    assert policy["group_coordination"] is True
    assert policy["low_mobility"] is False
    assert policy["quiet_preferred"] is True
    assert policy["slow_pace"] is True
    assert policy["high_activity"] is False

    assert "constraint_policy" in constraints
    assert "family_safe" in compatibility
    assert "kids_present" in compatibility
    assert "provisional_timing" in compatibility


def test_constraint_policy_derives_expected_flags_from_relaxed_and_adventure_cases(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    relaxed_constraints = derive_planning_constraints(
        _brief(
            traveller_count=2,
            trip_mood="relaxed",
            budget_level="medium",
            timing=build_timing(
                raw_text="next weekend",
                date_flexibility="fixed",
                state="relative_timing",
                confidence="medium",
            ),
        )
    )
    adventure_constraints = derive_planning_constraints(
        _brief(
            traveller_count=3,
            trip_mood="adventure",
            budget_level="high",
            timing=build_timing(
                raw_text="10 april to 14 april",
                start_date="10 april",
                end_date="14 april",
                date_flexibility="fixed",
                state="exact_timing",
                confidence="high",
            ),
        )
    )

    relaxed_policy = relaxed_constraints["constraint_policy"]
    adventure_policy = adventure_constraints["constraint_policy"]

    assert relaxed_policy["low_risk"] is True
    assert relaxed_policy["low_mobility"] is True
    assert relaxed_policy["quiet_preferred"] is True
    assert relaxed_policy["slow_pace"] is True
    assert relaxed_policy["avoid_premium"] is True

    assert adventure_policy["high_activity"] is True
    assert adventure_policy["avoid_premium"] is False
    assert adventure_policy["low_risk"] is False
    assert adventure_policy["slow_pace"] is False
