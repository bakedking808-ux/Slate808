import pytest

from engine.checker import ConstraintViolationError, check_plan
from engine.planning_policy import build_planning_constraints
from engine.travel_brief import build_timing


def _plan_with_constraints(steps, constraint_policy):
    brief = {
        "destination": "diani",
        "traveller_count": 4,
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
    planning_constraints = build_planning_constraints(brief)
    planning_constraints["constraint_policy"] = constraint_policy

    return {
        "task_type": "trip",
        "goal": "Plan a trip",
        "steps": steps,
        "checks": [],
        "risks": [],
        "brief": {
            "destination": "diani",
            "traveller_count": 4,
            "timing": {
                "raw_text": "next weekend",
                "state": "relative_timing",
            },
        },
        "planning_constraints": planning_constraints,
    }


def test_checker_raises_for_family_safe_and_avoid_premium_violations():
    plan = _plan_with_constraints(
        [
            "Define the trip goal clearly and set the destination to diani",
            "Set a premium budget and estimate the main costs",
            "Choose transport arrangements with unsafe movement and rough access",
            "Select nightlife and adult-only activities at a loud venue",
            "Confirm the trip timing window as next weekend and align bookings",
        ],
        {
            "family_safe": True,
            "low_risk": True,
            "avoid_premium": True,
            "value_focused": False,
            "group_coordination": False,
            "kids_present": True,
            "low_mobility": False,
            "quiet_preferred": True,
            "slow_pace": False,
            "high_activity": False,
        },
    )

    with pytest.raises(ConstraintViolationError) as exc_info:
        check_plan(plan)

    violations = exc_info.value.violations
    assert any("family_safe" in violation for violation in violations)
    assert any("avoid_premium" in violation for violation in violations)
    assert any("quiet_preferred" in violation for violation in violations)


def test_checker_raises_for_low_mobility_violation():
    plan = _plan_with_constraints(
        [
            "Define the trip goal clearly and set the destination to naivasha",
            "Set a practical budget and estimate the main costs",
            "Choose transport arrangements that keep movement smooth",
            "Select activities with a steep hike and strenuous movement",
            "Confirm the trip timing as 2 days and align transport and accommodation",
        ],
        {
            "family_safe": False,
            "low_risk": False,
            "avoid_premium": False,
            "value_focused": False,
            "group_coordination": False,
            "kids_present": False,
            "low_mobility": True,
            "quiet_preferred": False,
            "slow_pace": True,
            "high_activity": False,
        },
    )

    with pytest.raises(ConstraintViolationError) as exc_info:
        check_plan(plan)

    assert any("low_mobility" in violation for violation in exc_info.value.violations)


def test_checker_passes_when_constraint_compliant():
    plan = _plan_with_constraints(
        [
            "Define the trip goal clearly and set the destination to diani",
            "Set a practical budget and estimate the main costs carefully",
            "Choose transport arrangements with safe and comfortable movement for everyone",
            "Select family-friendly activities in calm and quieter settings",
            "Confirm the trip timing window as next weekend and align bookings",
        ],
        {
            "family_safe": True,
            "low_risk": True,
            "avoid_premium": True,
            "value_focused": True,
            "group_coordination": False,
            "kids_present": True,
            "low_mobility": False,
            "quiet_preferred": True,
            "slow_pace": True,
            "high_activity": False,
        },
    )

    result = check_plan(plan)
    assert result["status"] == "pass"
