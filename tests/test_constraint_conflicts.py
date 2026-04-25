import engine.generator as generator
from engine.runner import run_engine
from engine.planning_policy import (
    build_planning_constraints,
    derive_budget_policy,
    derive_destination_policy,
    derive_mood_policy,
    derive_planning_constraints,
    derive_timing_policy,
    resolve_constraint_conflicts,
)
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


def test_slow_pace_and_high_activity_conflict_resolves_for_adventure():
    brief = _brief(trip_mood="adventure")

    resolved = resolve_constraint_conflicts(
        constraint_policy={
            "family_safe": False,
            "low_risk": False,
            "avoid_premium": False,
            "value_focused": False,
            "group_coordination": False,
            "kids_present": False,
            "low_mobility": False,
            "quiet_preferred": False,
            "slow_pace": True,
            "high_activity": True,
        },
        brief=brief,
        destination_policy=derive_destination_policy(brief),
        mood_policy=derive_mood_policy(brief),
        budget_policy=derive_budget_policy(brief),
        timing_policy=derive_timing_policy(brief),
    )

    assert resolved["constraint_policy"]["high_activity"] is True
    assert resolved["constraint_policy"]["slow_pace"] is False
    assert "slow_pace_vs_high_activity" in resolved["conflict_flags"]


def test_avoid_premium_wins_over_premium_pressure_for_medium_budget():
    brief = _brief(trip_mood="luxury", budget_level="medium")

    resolved = resolve_constraint_conflicts(
        constraint_policy={
            "family_safe": False,
            "low_risk": False,
            "avoid_premium": True,
            "value_focused": False,
            "group_coordination": False,
            "kids_present": False,
            "low_mobility": False,
            "quiet_preferred": False,
            "slow_pace": False,
            "high_activity": False,
        },
        brief=brief,
        destination_policy=derive_destination_policy(brief),
        mood_policy=derive_mood_policy(brief),
        budget_policy=derive_budget_policy(brief),
        timing_policy=derive_timing_policy(brief),
    )

    assert resolved["constraint_policy"]["avoid_premium"] is True
    assert "avoid_premium_vs_premium_experience" in resolved["conflict_flags"]
    assert "avoid_premium_preserved" in resolved["resolved_constraints"]


def test_budget_safety_removes_luxury_language_from_generated_steps():
    brief = _brief(trip_mood="luxury", budget_level="medium")
    constraints = derive_planning_constraints(brief)

    steps = generator.build_steps("trip", {"brief": brief, "planning_constraints": constraints})
    joined = " ".join(steps).lower()

    assert "avoid_premium_vs_premium_experience" in constraints["global_flags"]["conflict_flags"]
    assert "premium_experience" not in constraints["global_flags"]["constraints"]
    assert "premium" not in joined
    assert "curated" not in joined


def test_budget_safety_removes_premium_posture_from_rendered_plan():
    result = run_engine("Plan a luxury trip to Diani for 2 people next weekend with a budget of 60000")
    rendered = result.lower()

    assert "premium" not in rendered
    assert "curated" not in rendered
    assert "high-quality" not in rendered


def test_family_safety_beats_adventure_activity_pressure():
    brief = _brief(trip_mood="adventure")

    resolved = resolve_constraint_conflicts(
        constraint_policy={
            "family_safe": True,
            "low_risk": False,
            "avoid_premium": False,
            "value_focused": False,
            "group_coordination": True,
            "kids_present": True,
            "low_mobility": False,
            "quiet_preferred": False,
            "slow_pace": False,
            "high_activity": True,
        },
        brief=brief,
        destination_policy=derive_destination_policy(brief),
        mood_policy=derive_mood_policy(brief),
        budget_policy=derive_budget_policy(brief),
        timing_policy=derive_timing_policy(brief),
    )

    assert resolved["constraint_policy"]["family_safe"] is True
    assert resolved["constraint_policy"]["high_activity"] is False
    assert resolved["constraint_policy"]["low_risk"] is True
    assert "family_safe_vs_high_activity" in resolved["conflict_flags"]
    assert "family_safety_preserved" in resolved["resolved_constraints"]


def test_low_mobility_remains_enforced_for_mountain_bias():
    brief = _brief(destination="mt kenya", trip_mood="relaxed")

    constraints = derive_planning_constraints(brief)

    assert constraints["constraint_policy"]["low_mobility"] is True
    assert "low_mobility_vs_mountain_bias" in constraints["global_flags"]["conflict_flags"]
    assert "low_mobility_preserved" in constraints["global_flags"]["resolved_constraints"]


def test_low_mobility_suppresses_injected_high_activity():
    brief = _brief(destination="mt kenya", trip_mood="relaxed")

    resolved = resolve_constraint_conflicts(
        constraint_policy={
            "family_safe": False,
            "low_risk": False,
            "avoid_premium": False,
            "value_focused": False,
            "group_coordination": False,
            "kids_present": False,
            "low_mobility": True,
            "quiet_preferred": False,
            "slow_pace": True,
            "high_activity": True,
        },
        brief=brief,
        destination_policy=derive_destination_policy(brief),
        mood_policy=derive_mood_policy(brief),
        budget_policy=derive_budget_policy(brief),
        timing_policy=derive_timing_policy(brief),
    )

    assert resolved["constraint_policy"]["high_activity"] is False
    assert "low_mobility_vs_high_activity" in resolved["conflict_flags"]


def test_quiet_preferred_remains_enforced_for_city_bias():
    brief = _brief(destination="nairobi", trip_mood="romantic")

    constraints = derive_planning_constraints(brief)

    assert constraints["constraint_policy"]["quiet_preferred"] is True
    assert constraints["constraint_policy"]["high_activity"] is False
    assert constraints["constraint_policy"]["low_risk"] is True
    assert "quiet_preferred_vs_city_bias" in constraints["global_flags"]["conflict_flags"]
    assert "quiet_preference_preserved" in constraints["global_flags"]["resolved_constraints"]


def test_generator_uses_resolved_constraints_not_conflicting_inputs():
    brief = _brief(destination="nairobi", trip_mood="adventure", budget_level="medium")
    planning_constraints = build_planning_constraints(brief)
    planning_constraints["budget_policy"]["budget_posture"] = "premium"
    planning_constraints["mood_policy"]["experience_style"] = "elevated"
    planning_constraints["constraint_policy"] = {
        "family_safe": False,
        "low_risk": False,
        "avoid_premium": True,
        "value_focused": False,
        "group_coordination": False,
        "kids_present": False,
        "low_mobility": False,
        "quiet_preferred": False,
        "slow_pace": False,
        "high_activity": True,
    }
    planning_constraints["global_flags"]["constraints"] = ["avoid_premium", "high_activity"]
    planning_constraints["global_flags"]["conflict_flags"] = ["avoid_premium_vs_premium_experience"]
    planning_constraints["global_flags"]["resolved_constraints"] = ["avoid_premium_preserved"]

    details = {
        "brief": brief,
        "planning_constraints": planning_constraints,
    }

    steps = generator.build_steps("trip", details)
    joined = " ".join(steps).lower()

    assert "premium" not in joined
    assert "curated" not in joined
    assert "active and well-structured movement" in joined
