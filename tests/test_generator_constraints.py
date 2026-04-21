import engine.generator as generator
from engine.planning_policy import build_planning_constraints
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


def test_generator_applies_value_group_and_slow_constraints_deterministically():
    brief = _brief()
    planning_constraints = build_planning_constraints(brief)
    planning_constraints["constraint_policy"] = {
        "family_safe": False,
        "low_risk": True,
        "avoid_premium": True,
        "value_focused": True,
        "group_coordination": True,
        "kids_present": False,
        "low_mobility": False,
        "quiet_preferred": True,
        "slow_pace": True,
        "high_activity": False,
    }
    details = {
        "brief": brief,
        "planning_constraints": planning_constraints,
    }

    first = generator.build_steps("trip", details)
    second = generator.build_steps("trip", details)

    assert first == second
    assert len(first) == 5
    assert "cost-conscious budget" in first[1].lower()
    assert "practical and safe movement" in first[2].lower()
    assert "shared meeting points and aligned movement" in first[2].lower()
    assert "good-value options" in first[3].lower()
    assert "calm and quieter settings" in first[3].lower()
    assert "more recovery time" in first[3].lower()
    assert "shared schedule for the group" in first[4].lower()
    assert "planned clearly" not in first[2].lower()
    assert "with shared meeting points" not in first[2].lower()


def test_generator_removes_premium_wording_when_constraints_require_it():
    brief = _brief(trip_mood="luxury", budget_level="high")
    planning_constraints = build_planning_constraints(brief)
    planning_constraints["budget_policy"]["budget_posture"] = "premium"
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
        "high_activity": False,
    }
    steps = generator.build_steps(
        "trip",
        {
            "brief": brief,
            "planning_constraints": planning_constraints,
        },
    )

    joined = " ".join(steps).lower()

    assert "premium" not in joined
    assert "curated" not in joined
    assert "practical budget" in joined
    assert "balanced and memorable experiences" in joined


def test_generator_always_preserves_activity_step_for_valid_trip_requests():
    brief = _brief(destination="diani", traveller_count=4, trip_mood="family", budget_level="low")
    planning_constraints = build_planning_constraints(brief)

    steps = generator.build_steps(
        "trip",
        {
            "brief": brief,
            "planning_constraints": planning_constraints,
        },
    )

    assert len(steps) == 5
    assert "activity" in steps[3].lower() or "family-friendly" in steps[3].lower() or "experiences" in steps[3].lower()


def test_generator_constraint_suffix_merge_avoids_repeated_segments():
    brief = _brief(traveller_count=4, trip_mood="family", budget_level="low")
    planning_constraints = build_planning_constraints(brief)

    steps = generator.build_steps(
        "trip",
        {
            "brief": brief,
            "planning_constraints": planning_constraints,
        },
    )

    assert steps[2].lower().count("shared meeting points and aligned movement") == 1
    assert steps[3].lower().count("family-friendly and comfortable options") == 1
