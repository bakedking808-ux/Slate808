from engine.runner import run_engine
from engine.plan_refiner import refine_plan
from engine.planning_policy import build_planning_constraints


def test_trip_output_includes_activity_readiness_check_and_risk():
    output = run_engine("Plan a trip to Diani for 2 people 10 April to 12 April with a budget of 60000")

    assert "Activity Readiness:" in output
    assert "Verify activity feasibility, access requirements, age suitability, weather sensitivity, available time, and backup options before final confirmation." in output
    assert "Activity Constraint Risk:" in output


def test_refiner_default_operational_checks_include_activity_readiness_for_legacy_plans():
    brief = {
        "destination": "diani",
        "traveller_count": 2,
        "budget_level": "medium",
        "timing": {"state": "exact_timing"},
    }

    legacy_plan = {
        "task_type": "trip",
        "goal": "Plan a trip",
        "brief": brief,
        "steps": ["Choose transport", "Choose stay"],
        "checks": ["Old generic check"],
        "risks": ["Old generic risk"],
        "planning_constraints": build_planning_constraints(brief),
    }

    refined = refine_plan(legacy_plan)

    assert any(check.startswith("Activity Readiness:") for check in refined["checks"])
    assert any(risk.startswith("Activity Constraint Risk:") for risk in refined["risks"])
