from engine.runner import run_engine
from engine.plan_refiner import refine_plan
from engine.planning_policy import build_planning_constraints


def test_trip_output_includes_guest_comfort_check_and_risk():
    output = run_engine("Plan a family trip to Diani for 2 adults and 2 kids 10 April to 12 April with a budget of 60000")

    assert "Guest Comfort:" in output
    assert "Guest Comfort:" in output
    assert "Guest Comfort Risk:" in output


def test_refiner_default_operational_checks_include_guest_comfort_for_legacy_plans():
    brief = {
        "destination": "diani",
        "traveller_count": 4,
        "budget_level": "medium",
        "trip_mood": "family",
        "timing": {"state": "exact_timing"},
    }

    legacy_plan = {
        "task_type": "trip",
        "goal": "Plan a family trip",
        "brief": brief,
        "steps": ["Choose transport", "Choose stay"],
        "checks": ["Old generic check"],
        "risks": ["Old generic risk"],
        "planning_constraints": build_planning_constraints(brief),
    }

    refined = refine_plan(legacy_plan)

    assert any(check.startswith("Guest Comfort:") for check in refined["checks"])
    assert any(risk.startswith("Guest Comfort Risk:") for risk in refined["risks"])
