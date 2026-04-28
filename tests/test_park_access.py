from engine.runner import run_engine
from engine.plan_refiner import refine_plan
from engine.planning_policy import build_planning_constraints


def test_trip_output_includes_park_access_check_and_risk():
    output = run_engine("Plan a safari trip to Maasai Mara for 2 people 10 April to 12 April")

    assert "Park & Access:" in output
    assert "Park & Access:" in output
    assert "Access Rule Risk:" in output


def test_refiner_default_operational_checks_include_park_access_for_legacy_plans():
    brief = {
        "destination": "maasai mara",
        "traveller_count": 2,
        "budget_level": "medium",
        "timing": {"state": "exact_timing"},
    }

    legacy_plan = {
        "task_type": "trip",
        "goal": "Plan a safari trip",
        "brief": brief,
        "steps": ["Choose transport", "Choose stay"],
        "checks": ["Old generic check"],
        "risks": ["Old generic risk"],
        "planning_constraints": build_planning_constraints(brief),
    }

    refined = refine_plan(legacy_plan)

    assert any(check.startswith("Park & Access:") for check in refined["checks"])
    assert any(risk.startswith("Access Rule Risk:") for risk in refined["risks"])
