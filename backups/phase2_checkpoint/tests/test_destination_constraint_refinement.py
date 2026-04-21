import engine.generator as generator
from engine.planning_policy import derive_planning_constraints
from engine.travel_brief import build_timing


def _brief(**overrides):
    brief = {
        "destination": "diani",
        "traveller_count": 2,
        "timing": build_timing(
            raw_text="next weekend",
            date_flexibility="fixed",
            state="relative_timing",
            confidence="medium",
        ),
        "budget_amount": None,
        "budget_level": "medium",
        "trip_mood": None,
    }
    brief.update(overrides)
    return brief


def test_mountain_low_mobility_refines_to_safe_low_exertion_bias(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    constraints = derive_planning_constraints(
        _brief(destination="mt kenya", trip_mood="relaxed")
    )

    policy = constraints["constraint_policy"]
    flags = constraints["global_flags"]["refinement_flags"]

    assert policy["low_mobility"] is True
    assert policy["low_risk"] is True
    assert policy["slow_pace"] is True
    assert policy["high_activity"] is False
    assert "mountain_low_mobility_safety_bias" in flags


def test_coastal_slow_pace_and_value_focused_strengthen_calm_value_signals(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    constraints = derive_planning_constraints(
        _brief(destination="diani", trip_mood="family", budget_level="low")
    )

    policy = constraints["constraint_policy"]
    flags = constraints["global_flags"]["refinement_flags"]

    assert policy["slow_pace"] is True
    assert policy["value_focused"] is True
    assert policy["quiet_preferred"] is True
    assert policy["low_risk"] is True
    assert policy["avoid_premium"] is True
    assert "coastal_slow_pace_bias" in flags
    assert "coastal_value_focus_bias" in flags

    steps = generator.build_steps(
        "trip",
        {
            "brief": _brief(destination="diani", trip_mood="family", budget_level="low"),
            "planning_constraints": constraints,
        },
    )
    joined = " ".join(steps).lower()

    assert "good-value" in joined
    assert "calm and quieter settings" in joined
    assert "recovery time" in joined


def test_city_quiet_preferred_bias_suppresses_loud_direction(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    constraints = derive_planning_constraints(
        _brief(destination="nairobi", trip_mood="romantic")
    )

    policy = constraints["constraint_policy"]
    flags = constraints["global_flags"]["refinement_flags"]

    assert policy["quiet_preferred"] is True
    assert policy["low_risk"] is True
    assert policy["high_activity"] is False
    assert "city_quiet_preference_bias" in flags

    steps = generator.build_steps(
        "trip",
        {
            "brief": _brief(destination="nairobi", trip_mood="romantic"),
            "planning_constraints": constraints,
        },
    )
    joined = " ".join(steps).lower()

    assert "calm and quieter settings" in joined
    assert "party" not in joined
    assert "nightlife" not in joined


def test_safari_group_coordination_strengthens_coordination_signals(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    constraints = derive_planning_constraints(
        _brief(destination="maasai mara", traveller_count=6)
    )

    policy = constraints["constraint_policy"]
    flags = constraints["global_flags"]["refinement_flags"]

    assert policy["group_coordination"] is True
    assert policy["low_risk"] is True
    assert "safari_group_coordination_bias" in flags

    steps = generator.build_steps(
        "trip",
        {
            "brief": _brief(destination="maasai mara", traveller_count=6),
            "planning_constraints": constraints,
        },
    )
    joined = " ".join(steps).lower()

    assert "shared meeting points and aligned movement" in joined


def test_generator_output_stays_deterministic_with_destination_refinement(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    brief = _brief(destination="nairobi", traveller_count=5, trip_mood="family", budget_level="low")
    constraints = derive_planning_constraints(brief)
    details = {
        "brief": brief,
        "planning_constraints": constraints,
    }

    first = generator.build_steps("trip", details)
    second = generator.build_steps("trip", details)

    assert first == second
